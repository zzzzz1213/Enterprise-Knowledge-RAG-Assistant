"""
Minimal DeepResearch agent for Agentic RAG phase 2.

The agent keeps the existing RAG chain untouched. It decomposes a user task into
small sub-questions, calls KnowledgeSearchTool for each one, deduplicates sources,
and returns a structured research result for debugging in FastAPI docs.
"""

from __future__ import annotations

import re
from typing import Any, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agent_tools.knowledge_search_tool import KnowledgeSearchTool
from chat_units.chat_management.chat_send import DEFAULT_MODEL, _run_rag_query

router = APIRouter(prefix="/api/agent", tags=["Agent-DeepResearch"])

_MAX_SUB_QUESTIONS = 4
_TOPIC_HINTS = {
    "\u8bf7\u5047": "\u5458\u5de5\u8bf7\u5047\u6709\u4ec0\u4e48\u89c4\u5b9a\uff1f",
    "\u75c5\u5047": "\u5458\u5de5\u75c5\u5047\u6709\u4ec0\u4e48\u89c4\u5b9a\uff1f",
    "\u8fdf\u5230": "\u5458\u5de5\u8fdf\u5230\u4f1a\u600e\u4e48\u5904\u7406\uff1f",
    "\u8003\u52e4": "\u5458\u5de5\u8003\u52e4\u6709\u4ec0\u4e48\u89c4\u5b9a\uff1f",
    "\u62a5\u9500": "\u5458\u5de5\u62a5\u9500\u6709\u4ec0\u4e48\u89c4\u5b9a\uff1f",
    "\u5dee\u65c5": "\u5dee\u65c5\u62a5\u9500\u6709\u4ec0\u4e48\u89c4\u5b9a\uff1f",
    "\u52a0\u73ed": "\u52a0\u73ed\u76f8\u5173\u89c4\u5b9a\u662f\u4ec0\u4e48\uff1f",
    "\u9910\u8865": "\u52a0\u73ed\u9910\u8865\u6807\u51c6\u662f\u4ec0\u4e48\uff1f",
    "\u5e74\u7ec8\u5956": "\u5e74\u7ec8\u5956\u6709\u4ec0\u4e48\u89c4\u5b9a\uff1f",
}
_SPLIT_PATTERNS = re.compile(r"[?\uff1f;\uff1b\u3002\n]+|\u4ee5\u53ca|\u5e76\u4e14|\u540c\u65f6|\u5206\u522b|\u5bf9\u6bd4|\u6bd4\u8f83|\u548c")


class DeepResearchRequest(BaseModel):
    question: str = Field(..., min_length=1, description="User research question")
    kb_id: str = Field(..., min_length=1, description="Knowledge base ID")
    model: Optional[str] = Field(default=None, description="Ollama model")
    retrieval_config: Optional[dict[str, Any]] = Field(default=None, description="Retrieval config")
    max_sub_questions: int = Field(default=3, ge=1, le=_MAX_SUB_QUESTIONS)


def _normalize_question(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _split_by_known_topics(question: str, max_sub_questions: int) -> List[str]:
    sub_questions: List[str] = []
    for topic, template in _TOPIC_HINTS.items():
        if topic in question and template not in sub_questions:
            sub_questions.append(template)
        if len(sub_questions) >= max_sub_questions:
            break
    return sub_questions


def _split_question(question: str, max_sub_questions: int) -> List[str]:
    normalized = _normalize_question(question)
    if not normalized:
        return []

    topic_questions = _split_by_known_topics(normalized, max_sub_questions)
    if len(topic_questions) >= 2:
        return topic_questions

    parts = [p.strip(" \uff0c,\uff1a:\uff1f?") for p in _SPLIT_PATTERNS.split(normalized)]
    parts = [p for p in parts if len(p) >= 4]

    if len(parts) <= 1:
        return topic_questions or [normalized]

    sub_questions: List[str] = topic_questions[:]
    seen = set(sub_questions)
    for part in parts:
        if part in seen:
            continue
        seen.add(part)
        if not part.endswith(("\uff1f", "?")):
            part = f"{part}\uff1f"
        sub_questions.append(part)
        if len(sub_questions) >= max_sub_questions:
            break

    return sub_questions or [normalized]


def _dedupe_sources(items: List[dict[str, Any]]) -> List[dict[str, Any]]:
    seen = set()
    deduped = []
    for item in items:
        key = (
            item.get("filename"),
            item.get("page"),
            item.get("content", "")[:120],
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _build_summary(question: str, evidence: List[dict[str, Any]]) -> str:
    answered = [item for item in evidence if item.get("answer")]
    if not answered:
        return "\u77e5\u8bc6\u5e93\u672a\u68c0\u7d22\u5230\u8db3\u591f\u8bc1\u636e\uff0c\u6682\u65f6\u65e0\u6cd5\u5f62\u6210\u7ed3\u8bba\u3002"

    if len(answered) == 1:
        return answered[0]["answer"]

    lines = [f"\u9488\u5bf9\u201c{question}\u201d\uff0cDeepResearch \u5df2\u5b8c\u6210 {len(answered)} \u4e2a\u5b50\u95ee\u9898\u68c0\u7d22\uff1a"]
    for index, item in enumerate(answered, start=1):
        lines.append(f"{index}. {item['sub_question']}\uff1a{item['answer']}")
    return "\n".join(lines)


def _is_uncertain_answer(answer: str, sources: List[dict[str, Any]]) -> bool:
    if not sources:
        return True
    if "\u672a\u627e\u5230\u76f8\u5173\u6587\u6863" in answer:
        return True
    if "\u77e5\u8bc6\u5e93\u672a\u63d0\u4f9b\u8be5\u89c4\u5b9a" in answer:
        return True
    # "No extra rules beyond the cited content" is a grounded answer, not a failure.
    if "\u9664\u4e0a\u8ff0\u5185\u5bb9\u5916" in answer:
        return False
    return False


def _build_uncertainty(evidence: List[dict[str, Any]]) -> List[str]:
    uncertainty = []
    for item in evidence:
        answer = item.get("answer", "")
        sources = item.get("sources", [])
        if _is_uncertain_answer(answer, sources):
            uncertainty.append(
                f"{item.get('sub_question')}\uff1a\u77e5\u8bc6\u5e93\u8bc1\u636e\u4e0d\u8db3\u6216\u672a\u63d0\u4f9b\u660e\u786e\u89c4\u5b9a\u3002"
            )
    return uncertainty


def _topic_label(question: str) -> str:
    if "请假" in question:
        return "请假规定"
    if "病假" in question:
        return "病假规定"
    if "迟到" in question:
        return "迟到处理规定"
    if "报销" in question:
        return "报销规定"
    if "考勤" in question:
        return "考勤规定"
    if "餐补" in question:
        return "餐补标准"
    if "年终奖" in question:
        return "年终奖规定"
    return "相关规定"


def _clean_answer_for_research(answer: str, sub_question: str) -> str:
    if not answer:
        return answer
    label = _topic_label(sub_question)
    cleaned = re.sub(
        r"知识库未提供除上述内容外的其他.*?(相关规定|规定|处理|标准|时间)。$",
        f"知识库未提供除上述内容外的其他{label}。",
        answer,
    )
    cleaned = cleaned.replace("相关规定规定", "相关规定")
    cleaned = cleaned.replace("规定规定", "规定")
    return cleaned


class DeepResearchAgent:
    def __init__(self, search_tool: KnowledgeSearchTool):
        self.search_tool = search_tool

    def run(
        self,
        question: str,
        kb_id: str,
        model_id: str,
        retrieval_config: Optional[dict[str, Any]] = None,
        max_sub_questions: int = 3,
    ) -> dict[str, Any]:
        sub_questions = _split_question(question, max_sub_questions)
        if not sub_questions:
            raise HTTPException(status_code=400, detail="Question cannot be empty")

        evidence = []
        all_sources = []
        tool_calls = []

        for sub_question in sub_questions:
            result = self.search_tool.run(
                query=sub_question,
                model_id=model_id,
                kb_id=kb_id,
                retrieval_config=retrieval_config,
            )
            answer = _clean_answer_for_research(result.get("answer", ""), sub_question)
            evidence.append(
                {
                    "sub_question": sub_question,
                    "answer": answer,
                    "retrieval_mode": result.get("retrieval_mode"),
                    "sources": result.get("sources", []),
                }
            )
            all_sources.extend(result.get("sources", []))
            tool_calls.append(result.get("tool_call"))

        sources = _dedupe_sources(all_sources)
        return {
            "agent_mode": "deep_research",
            "question": question,
            "kb_id": kb_id,
            "model": model_id,
            "summary": _build_summary(question, evidence),
            "sub_questions": sub_questions,
            "evidence": evidence,
            "sources": sources,
            "uncertainty": _build_uncertainty(evidence),
            "tool_calls": [call for call in tool_calls if call],
        }


@router.post("/deep-research")
def deep_research(req: DeepResearchRequest):
    model_id = req.model or DEFAULT_MODEL
    agent = DeepResearchAgent(KnowledgeSearchTool(search_func=_run_rag_query))
    return agent.run(
        question=req.question,
        kb_id=req.kb_id,
        model_id=model_id,
        retrieval_config=req.retrieval_config,
        max_sub_questions=req.max_sub_questions,
    )
