"""
rag_pipeline.py
RAG 核心流水线 v3
新增：
  - 检索策略扩展（接收前端 RetrievalConfig 参数，支持 vector/BM25/hybrid/RRF/MMR）
  - 混合检索（HybridRetriever：BM25 + 向量 + RRF 融合）
  - 引用溯源（返回 sources 列表，含文件名、页码、得分）
  - 流式回答生成（generator 模式，配合 SSE 使用）
"""

from __future__ import annotations

import os
import re
import sys
from typing import List, Dict, Any, Generator, Optional, Set

from langchain_ollama.llms import OllamaLLM
from langchain_community.vectorstores import FAISS
from langchain.docstore.document import Document
from langchain.prompts import PromptTemplate

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
from models.model_config import get_model_config
from src.rag.hybrid_retriever import HybridRetriever

# Retrieval strategy
try:
    import sys as _sys

    _BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..")
    if _BACKEND_DIR not in _sys.path:
        _sys.path.insert(0, _BACKEND_DIR)
    from document_processing.retrieval_strategy import (
        RetrievalStrategyExecutor,
        RetrievalConfig,
    )

    _STRATEGY_AVAILABLE = True
except ImportError:
    _STRATEGY_AVAILABLE = False
    RetrievalStrategyExecutor = None  # type: ignore
    RetrievalConfig = None  # type: ignore


# - Prompt
_PROMPT_TEMPLATE = """你是知识管理助手，专门回答基于文档的问题。

规则：
1. 只根据"参考文档"中的内容回答，不要编造制度、金额、处罚或日期。
2. 如果参考文档没有明确答案，直接说明"知识库未提供该规定"。
3. 引用来源时，只能使用参考文档标题里的真实来源名，例如【来源 1：xxx.txt】；不要输出"文件名"这类占位词。
4. 不要把不同制度条款强行拼接成因果关系；只回答用户问题直接相关的条款。
5. 不要列出同一文档中的其他无关制度；例如用户问"迟到"时，只回答考勤/迟到相关内容，不要展开请假、报销、餐补等条款。
6. 文档只说明"未规定/未提供/未说明"时，必须照实回答未提供，不要补充金额、补贴、处罚或日期。
7. 用户未指定语言时默认使用中文。
8. 回答要简洁、清晰；涉及代码/公式/表格时再给出对应示例。

参考文档（已按相关度排序）：
{context}

用户问题：{question}

回答："""

PROMPT = PromptTemplate(
    template=_PROMPT_TEMPLATE,
    input_variables=["context", "question"],
)

_MAX_CONTEXT_CHARS_PER_SOURCE = 450
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[。！？；;!?])\s*|\n+")
_QUESTION_STOPWORDS = {
    "什么",
    "怎么",
    "怎样",
    "如何",
    "多少",
    "需要",
    "员工",
    "公司",
    "规定",
    "处理",
    "这个",
    "那个",
    "是否",
    "可以",
}
_TOPIC_HINTS = {
    "迟到": {"迟到", "考勤", "上班", "下班", "工作日", "提醒", "事假"},
    "考勤": {"考勤", "迟到", "上班", "下班", "工作日", "提醒", "事假"},
    "请假": {"请假", "病假", "事假", "申请", "医院", "证明"},
    "病假": {"病假", "请假", "医院", "证明", "申请"},
    "报销": {"报销", "差旅", "出差", "发票", "报销单"},
    "差旅": {"差旅", "出差", "报销", "发票", "报销单"},
    "餐补": {"餐补", "加班", "补贴", "标准", "未规定"},
    "加班": {"加班", "餐补", "补贴", "标准", "未规定"},
    "年终奖": {"年终奖", "发放", "时间", "未说明"},
}


def _extract_query_keywords(question: str) -> Set[str]:
    keywords: Set[str] = set()
    normalized = question.lower()

    for topic, hints in _TOPIC_HINTS.items():
        if topic in question:
            keywords.update(hints)

    keywords.update(re.findall(r"[a-z0-9]+", normalized))
    for token in re.findall(r"[\u4e00-\u9fff]{2,}", question):
        if token not in _QUESTION_STOPWORDS:
            keywords.add(token)

    return {kw for kw in keywords if kw}


def _split_sentences(text: str) -> List[str]:
    sentences = [
        re.sub(r"\s+", " ", s).strip()
        for s in _SENTENCE_SPLIT_RE.split(text)
        if s.strip()
    ]
    return sentences or [text.strip()]


def _compress_document_content(text: str, question: str) -> str:
    clean_text = re.sub(r"\s+", " ", text).strip()
    keywords = _extract_query_keywords(question)
    if not keywords:
        return clean_text[:_MAX_CONTEXT_CHARS_PER_SOURCE]

    sentences = _split_sentences(clean_text)
    scored = []
    for index, sentence in enumerate(sentences):
        matched = {kw for kw in keywords if kw in sentence}
        if matched:
            scored.append((len(matched), index, sentence))

    if not scored:
        return clean_text[:_MAX_CONTEXT_CHARS_PER_SOURCE]

    selected = [item[2] for item in sorted(scored, key=lambda x: (-x[0], x[1]))]
    compressed = ""
    for sentence in selected:
        candidate = f"{compressed}{sentence}"
        if len(candidate) > _MAX_CONTEXT_CHARS_PER_SOURCE:
            break
        compressed = candidate

    return compressed or selected[0][:_MAX_CONTEXT_CHARS_PER_SOURCE]


def _source_label(source_info: Dict[str, Any]) -> str:
    file_name = source_info.get("file_name", "未知来源")
    page = source_info.get("page")
    page_str = f" 第 {page} 页" if page is not None else ""
    return f"【来源 {source_info['rank']}：{file_name}{page_str}】"


def _direct_query_terms(question: str) -> Set[str]:
    terms: Set[str] = set()
    for topic in _TOPIC_HINTS:
        if topic in question:
            terms.add(topic)

    for token in re.findall(r"[\u4e00-\u9fff]{2,}", question):
        if token not in _QUESTION_STOPWORDS:
            terms.add(token)

    return {term for term in terms if term}


def _answer_subject(question: str, direct_terms: Set[str]) -> str:
    if "餐补" in question:
        return "加班餐补标准" if "加班" in question else "餐补标准"
    if "年终奖" in question:
        return "年终奖发放时间" if any(x in question for x in ("时间", "发放", "什么时候")) else "年终奖"
    if "迟到" in question:
        return "迟到处理"
    if direct_terms:
        return f"{sorted(direct_terms, key=len, reverse=True)[0]}相关规定"
    return "该规定"


def _try_build_extractive_answer(
    docs_with_sources: List[Dict[str, Any]], question: str
) -> Optional[str]:
    direct_terms = _direct_query_terms(question)
    if not direct_terms:
        return None

    relevant_by_source: List[Dict[str, Any]] = []
    seen_sentences: Set[str] = set()
    for item in docs_with_sources:
        source_info = item["source_info"]
        sentences = _split_sentences(item["document"].page_content)
        matches = []
        for sentence in sentences:
            if not any(term in sentence for term in direct_terms):
                continue
            if sentence in seen_sentences:
                continue
            seen_sentences.add(sentence)
            matches.append(sentence)
        if matches:
            relevant_by_source.append(
                {"label": _source_label(source_info), "sentences": matches}
            )

    if not relevant_by_source:
        return None

    negative_markers = ("未规定", "未说明", "未提供", "没有规定", "没有说明")
    first = relevant_by_source[0]
    negative_sentence = next(
        (
            sentence
            for sentence in first["sentences"]
            if any(marker in sentence for marker in negative_markers)
        ),
        "",
    )
    if negative_sentence:
        subject = _answer_subject(question, direct_terms)
        return f"根据{first['label']}，知识库未提供{subject}。"

    selected = first["sentences"][:3]
    answer_body = "".join(selected)
    subject = _answer_subject(question, direct_terms)
    suffix = "" if subject.endswith(("规定", "处理", "标准", "时间")) else "规定"
    return f"根据{first['label']}，{answer_body}知识库未提供除上述内容外的其他{subject}{suffix}。"


def _format_context(docs_with_sources: List[Dict[str, Any]], question: str) -> str:
    """将检索结果格式化为 LLM 可用的上下文字符串，附带来源标注"""
    parts = []
    for item in docs_with_sources:
        src = item["source_info"]
        file_name = src.get("file_name", "未知来源")
        page = src.get("page")
        page_str = f"第 {page} 页" if page is not None else ""
        header = f"【来源 {src['rank']}：{file_name}{' ' + page_str if page_str else ''}】"
        content = _compress_document_content(item["document"].page_content, question)
        parts.append(f"{header}\n{content}")
    return "\n\n---\n\n".join(parts)


class RAGPipeline:
    """
    RAG 流水线 v3
    支持：混合检索、引用溯源、流式/非流式两种输出模式
    新增：检索策略参数透传（strategy/topK/scoreThreshold/vectorWeight/bm25Weight/rerank）
    """

    def __init__(
        self,
        llm_model: Optional[str] = None,
        vectorstore: Optional[FAISS] = None,
        documents: Optional[List[Document]] = None,
        use_hybrid: bool = True,
        retrieval_config: Optional[dict] = None,  # Retrieval strategy
    ):
        # Model config
        if llm_model is None:
            model_config = get_model_config()
            llm_model = model_config.llm_model
            print(f"[RAGPipeline] 使用默认 LLM 模型: {llm_model}")

        self.llm = OllamaLLM(model=llm_model)
        self.vectorstore = vectorstore
        self.use_hybrid = use_hybrid
        self.documents = documents or []

        # Retrieval strategy
        self._retrieval_config = None
        if retrieval_config and _STRATEGY_AVAILABLE:
            self._retrieval_config = RetrievalConfig.from_dict(retrieval_config)
            print(
                f"[RAGPipeline] 检索策略: {self._retrieval_config.strategy}, topK={self._retrieval_config.topK}"
            )

        # Initialize
        self._strategy_executor = None
        if _STRATEGY_AVAILABLE and vectorstore is not None:
            self._strategy_executor = RetrievalStrategyExecutor(
                vectorstore=vectorstore,
                documents=self.documents,
            )

        # Hybrid retrieval fallback
        self._hybrid_retriever: Optional[HybridRetriever] = None
        if (
            use_hybrid
            and vectorstore is not None
            and self.documents
            and not _STRATEGY_AVAILABLE
        ):
            print(f"[RAGPipeline] 初始化混合检索器，文档块数量: {len(self.documents)}")
            self._hybrid_retriever = HybridRetriever(
                documents=self.documents,
                vectorstore=vectorstore,
            )
        elif (
            use_hybrid
            and vectorstore is not None
            and not self.documents
            and not _STRATEGY_AVAILABLE
        ):
            print("[RAGPipeline] 未传入 documents，混合检索降级为纯向量检索")
            self.use_hybrid = False

    def _retrieve(self, query: str) -> List[Dict[str, Any]]:
        if self._strategy_executor is not None:
            config = self._retrieval_config  # Noneexecutor
            return self._strategy_executor.retrieve(query, config)

        # fallbackHybrid retrieval
        if self.use_hybrid and self._hybrid_retriever:
            return self._hybrid_retriever.retrieve_with_scores(query)

        # fallbackVector retrieval
        raw = self.vectorstore.similarity_search_with_score(query, k=4)
        results = []
        for rank, (doc, score) in enumerate(raw, start=1):
            meta = doc.metadata or {}
            results.append(
                {
                    "document": doc,
                    "source_info": {
                        "rank": rank,
                        "rrf_score": float(score),
                        "file_name": _extract_filename_from_meta(meta),
                        "page": meta.get("page"),
                        "chunk_index": meta.get("chunk_index"),
                        "source_path": meta.get("source", ""),
                    },
                    "content_preview": doc.page_content[:200],
                }
            )
        return results

    def process_query(self, query: str) -> Dict[str, Any]:
        """
        处理查询，返回：
          answer: str
          sources: list[dict]  — 引用溯源列表
          retrieval_mode: str
        """
        docs_with_sources = self._retrieve(query)

        if not docs_with_sources:
            return {
                "answer": "未找到相关文档，无法回答该问题。",
                "sources": [],
                "retrieval_mode": "hybrid" if self.use_hybrid else "vector",
            }

        extractive_answer = _try_build_extractive_answer(docs_with_sources, query)
        if extractive_answer:
            return {
                "answer": extractive_answer,
                "sources": [
                    {
                        "rank": item["source_info"]["rank"],
                        "file_name": item["source_info"]["file_name"],
                        "page": item["source_info"]["page"],
                        "source_path": item["source_info"]["source_path"],
                        "rrf_score": item["source_info"].get("rrf_score"),
                        "content_preview": item["content_preview"],
                    }
                    for item in docs_with_sources
                ],
                "retrieval_mode": "hybrid" if self.use_hybrid else "vector",
            }

        context = _format_context(docs_with_sources, query)
        prompt_text = PROMPT.format(context=context, question=query)

        answer = self.llm.invoke(prompt_text)

        sources = [
            {
                "rank": item["source_info"]["rank"],
                "file_name": item["source_info"]["file_name"],
                "page": item["source_info"]["page"],
                "source_path": item["source_info"]["source_path"],
                "rrf_score": item["source_info"].get("rrf_score"),
                "content_preview": item["content_preview"],
            }
            for item in docs_with_sources
        ]

        return {
            "answer": answer,
            "sources": sources,
            "retrieval_mode": "hybrid" if self.use_hybrid else "vector",
        }

    # - generator SSE
    def stream_query(self, query: str) -> Generator[str, None, None]:
        """
        流式查询生成器
        yield 格式：SSE data 行，以 '\\n\\n' 结尾
        特殊行：
          SOURCES: <json>   — 检索来源信息
          COMPLETE           — 流式输出结束标志
        """
        import json

        yield f"data: 正在执行{'混合' if self.use_hybrid else '向量'}检索...\n\n"

        docs_with_sources = self._retrieve(query)

        if not docs_with_sources:
            yield "data: 未找到相关文档\n\n"
            yield "data: COMPLETE\n\n"
            return

        yield f"data: 检索完成，获取到 {len(docs_with_sources)} 个相关文档块\n\n"

        sources = [
            {
                "rank": item["source_info"]["rank"],
                "file_name": item["source_info"]["file_name"],
                "page": item["source_info"]["page"],
                "source_path": item["source_info"]["source_path"],
                "content_preview": item["content_preview"],
            }
            for item in docs_with_sources
        ]
        yield f"data: SOURCES: {json.dumps(sources, ensure_ascii=False)}\n\n"

        extractive_answer = _try_build_extractive_answer(docs_with_sources, query)
        if extractive_answer:
            yield "data: 正在生成回答...\n\n"
            yield f"data: {extractive_answer}\n\n"
            yield "data: COMPLETE\n\n"
            return

        # prompt
        context = _format_context(docs_with_sources, query)
        prompt_text = PROMPT.format(context=context, question=query)

        yield "data: 正在生成回答...\n\n"

        # OllamaLLM Streaming output
        try:
            for chunk in self.llm.stream(prompt_text):
                if chunk:
                    yield f"data: {chunk}\n\n"
        except Exception:
            answer = self.llm.invoke(prompt_text)
            for paragraph in answer.split("\n"):
                if paragraph.strip():
                    yield f"data: {paragraph}\n\n"

        yield "data: COMPLETE\n\n"


def _extract_filename_from_meta(meta: Dict[str, Any]) -> str:
    import os as _os

    for key in ("source", "file_path", "path", "filename", "file_name"):
        val = meta.get(key, "")
        if val:
            return _os.path.basename(str(val))
    return "未知来源"
