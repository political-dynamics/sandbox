"""Build a local retrievable index for ingested docs."""

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


def _chunk_text(text: str, *, chunk_size: int = 900, overlap: int = 150) -> list[str]:
    if len(text) <= chunk_size:
        return [text]
    chunks: list[str] = []
    cursor = 0
    while cursor < len(text):
        end = min(len(text), cursor + chunk_size)
        chunks.append(text[cursor:end])
        if end == len(text):
            break
        cursor = max(end - overlap, cursor + 1)
    return chunks


def index_docs(
    *,
    raw_dir: str | Path = "metadata_store/docs/raw",
    index_path: str | Path = "metadata_store/docs/index.json",
    chunk_size: int = 900,
    overlap: int = 150,
) -> Path:
    """Chunk raw docs and persist a JSON vector-like index."""
    raw_base = Path(raw_dir)
    out = Path(index_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    index: dict[str, Any] = {
        "version": 1,
        "chunks": [],
    }
    next_chunk_id = 0
    for path in sorted(raw_base.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("status") != "ok":
            continue

        text = str(payload.get("text", "")).strip()
        if not text:
            continue
        for chunk in _chunk_text(text, chunk_size=chunk_size, overlap=overlap):
            tokens = _tokenize(chunk)
            if not tokens:
                continue
            tf = Counter(tokens)
            norm = math.sqrt(sum(value * value for value in tf.values()))
            index["chunks"].append(
                {
                    "chunk_id": f"chunk-{next_chunk_id}",
                    "source_id": payload.get("source_id"),
                    "dataset_id": payload.get("dataset_id"),
                    "var_code": payload.get("var_code"),
                    "url": payload.get("url"),
                    "retrieved_at": payload.get("retrieved_at"),
                    "text": chunk,
                    "tf": dict(tf),
                    "norm": norm,
                }
            )
            next_chunk_id += 1

    out.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


if __name__ == "__main__":
    created = index_docs()
    print(f"index_path={created}")

