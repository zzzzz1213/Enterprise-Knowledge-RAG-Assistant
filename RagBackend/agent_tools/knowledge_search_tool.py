"""
Agent-facing knowledge search tool.

This module intentionally wraps the existing RAG query function instead of
reimplementing retrieval. The chat API can call it as an Agent tool while the
original RAG pipeline remains the single source of truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional


RAGSearchCallable = Callable[[str, str, str, Optional[dict[str, Any]]], Dict[str, Any]]


@dataclass
class CitationSource:
    """Normalized citation shape returned by knowledge tools."""

    rank: int
    filename: str
    content: str
    score: Optional[float] = None
    page: Optional[int] = None
    source_path: str = ""

    @classmethod
    def from_raw(cls, index: int, raw: dict[str, Any]) -> "CitationSource":
        return cls(
            rank=int(raw.get("rank") or index),
            filename=str(raw.get("filename") or raw.get("file_name") or "unknown"),
            content=str(raw.get("content") or raw.get("content_preview") or ""),
            score=raw.get("score") if raw.get("score") is not None else raw.get("rrf_score"),
            page=raw.get("page"),
            source_path=str(raw.get("source_path") or ""),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "rank": self.rank,
            "filename": self.filename,
            "content": self.content,
            "score": self.score,
            "page": self.page,
            "source_path": self.source_path,
        }


class KnowledgeSearchTool:
    """Tool wrapper for querying a selected knowledge base."""

    name = "knowledge_search"
    description = "Search a selected knowledge base and return a grounded answer with citations."

    def __init__(self, search_func: RAGSearchCallable):
        self._search_func = search_func

    def run(
        self,
        query: str,
        model_id: str,
        kb_id: str,
        retrieval_config: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        raw_result = self._search_func(
            query=query,
            model_id=model_id,
            kb_id=kb_id,
            retrieval_config=retrieval_config,
        )
        sources = [
            CitationSource.from_raw(index, item).to_dict()
            for index, item in enumerate(raw_result.get("sources", []), start=1)
        ]
        tool_call = {
            "tool_name": self.name,
            "arguments": {
                "query": query,
                "kb_id": kb_id,
                "model_id": model_id,
                "retrieval_config": retrieval_config or {},
            },
            "result_summary": {
                "sources_count": len(sources),
                "retrieval_mode": raw_result.get("retrieval_mode", "unknown"),
            },
        }
        return {
            "tool_name": self.name,
            "tool_call": tool_call,
            "answer": raw_result.get("reply", ""),
            "sources": sources,
            "retrieval_mode": raw_result.get("retrieval_mode", "unknown"),
        }