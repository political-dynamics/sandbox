"""Retrieve supporting definition snippets from local docs index."""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def _tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


def _matches_context(chunk: dict[str, Any], context: dict[str, Any]) -> bool:
    for key, expected in context.items():
        if expected is None:
            continue
        if str(chunk.get(key)) != str(expected):
            return False
    return True


def _score(tf_query: Counter[str], norm_query: float, chunk: dict[str, Any]) -> float:
    tf_chunk = chunk.get("tf", {})
    if not isinstance(tf_chunk, dict):
        return 0.0
    dot = 0.0
    for term, q_count in tf_query.items():
        c_count = tf_chunk.get(term, 0)
        dot += q_count * c_count
    norm_chunk = float(chunk.get("norm", 0.0))
    if norm_chunk <= 0 or norm_query <= 0:
        return 0.0
    return dot / (norm_query * norm_chunk)


def search_chunks(
    question: str,
    *,
    index_path: str | Path = "metadata_store/docs/index.json",
    context: dict[str, Any] | None = None,
    top_k: int = 3,
) -> list[dict[str, Any]]:
    index_file = Path(index_path)
    if not index_file.exists():
        return []

    payload = json.loads(index_file.read_text(encoding="utf-8"))
    chunks = payload.get("chunks", [])
    if not isinstance(chunks, list):
        return []

    q_tokens = _tokenize(question)
    tf_query = Counter(q_tokens)
    norm_query = math.sqrt(sum(value * value for value in tf_query.values()))
    context = context or {}

    ranked: list[tuple[float, dict[str, Any]]] = []
    for chunk in chunks:
        if not isinstance(chunk, dict):
            continue
        if not _matches_context(chunk, context):
            continue
        score = _score(tf_query, norm_query, chunk)
        if score <= 0:
            continue
        ranked.append((score, chunk))

    ranked.sort(key=lambda item: item[0], reverse=True)
    results: list[dict[str, Any]] = []
    for score, chunk in ranked[:top_k]:
        results.append(
            {
                "score": round(score, 6),
                "chunk_id": chunk.get("chunk_id"),
                "source_id": chunk.get("source_id"),
                "dataset_id": chunk.get("dataset_id"),
                "var_code": chunk.get("var_code"),
                "url": chunk.get("url"),
                "retrieved_at": chunk.get("retrieved_at"),
                "snippet": str(chunk.get("text", ""))[:320],
            }
        )
    return results


def answer_definition(
    question: str,
    *,
    context: dict[str, Any] | None = None,
    index_path: str | Path = "metadata_store/docs/index.json",
) -> dict[str, Any]:
    """Return a best-effort grounded answer with citations."""
    hits = search_chunks(question, context=context, index_path=index_path, top_k=3)
    if not hits:
        return {
            "answer": "No indexed documentation hit was found.",
            "citations": [],
            "source": "docs_index",
        }

    answer_lines = [f"Best matching documentation snippet: {hits[0]['snippet']}"]
    citations = []
    for hit in hits:
        citations.append(
            {
                "url": hit["url"],
                "chunk_id": hit["chunk_id"],
                "retrieved_at": hit["retrieved_at"],
                "score": hit["score"],
            }
        )
    return {
        "answer": " ".join(answer_lines),
        "citations": citations,
        "source": "docs_index",
    }

