"""Ingest documentation pages into a local raw-doc store."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from html import unescape
from pathlib import Path
from typing import Any, Iterable
from urllib.request import Request, urlopen

from policy_data_ai.registry.loader import SourceRegistry

TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")


@dataclass(slots=True)
class DocTarget:
    source_id: str
    dataset_id: str | None
    var_code: str | None
    url: str
    kind: str


def _collect_targets(registry: SourceRegistry) -> list[DocTarget]:
    targets: list[DocTarget] = []
    seen: set[tuple[str, str | None, str | None, str]] = set()
    for source_id, source in registry.sources.items():
        for doc in source.get("docs", []):
            url = doc.get("url") if isinstance(doc, dict) else None
            if not url:
                continue
            key = (source_id, None, None, str(url))
            if key in seen:
                continue
            seen.add(key)
            targets.append(
                DocTarget(
                    source_id=source_id,
                    dataset_id=None,
                    var_code=None,
                    url=str(url),
                    kind=str(doc.get("kind", "source")) if isinstance(doc, dict) else "source",
                )
            )
        for dataset in source.get("datasets", []):
            dataset_id = dataset.get("dataset_id")
            for doc in dataset.get("docs", []):
                url = doc.get("url") if isinstance(doc, dict) else None
                if not url:
                    continue
                key = (source_id, str(dataset_id), None, str(url))
                if key in seen:
                    continue
                seen.add(key)
                targets.append(
                    DocTarget(
                        source_id=source_id,
                        dataset_id=str(dataset_id),
                        var_code=None,
                        url=str(url),
                        kind=str(doc.get("kind", "dataset")) if isinstance(doc, dict) else "dataset",
                    )
                )
            for variable in dataset.get("variables", []):
                url = variable.get("doc_url")
                var_code = variable.get("var_code")
                if not url or not var_code:
                    continue
                key = (source_id, str(dataset_id), str(var_code), str(url))
                if key in seen:
                    continue
                seen.add(key)
                targets.append(
                    DocTarget(
                        source_id=source_id,
                        dataset_id=str(dataset_id),
                        var_code=str(var_code),
                        url=str(url),
                        kind="variable",
                    )
                )
    return targets


def _strip_html(html: str) -> str:
    text = TAG_RE.sub(" ", html)
    text = unescape(text)
    return WHITESPACE_RE.sub(" ", text).strip()


def _download_text(url: str, timeout_seconds: int = 30) -> str:
    request = Request(url, headers={"User-Agent": "policy_data_ai/0.1"})
    with urlopen(request, timeout=timeout_seconds) as response:
        raw = response.read().decode("utf-8", errors="replace")
    return _strip_html(raw)


def ingest_docs(
    *,
    registry_dir: str | Path = "sources_registry",
    output_dir: str | Path = "metadata_store/docs/raw",
    overwrite: bool = False,
) -> list[Path]:
    """Download docs referenced in registry files and save as JSON blobs."""
    registry = SourceRegistry.from_directory(registry_dir)
    targets = _collect_targets(registry)

    out_base = Path(output_dir)
    out_base.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    for target in targets:
        digest = hashlib.sha1(
            f"{target.source_id}|{target.dataset_id}|{target.var_code}|{target.url}".encode("utf-8")
        ).hexdigest()
        out_file = out_base / f"{digest}.json"
        if out_file.exists() and not overwrite:
            written.append(out_file)
            continue

        retrieved_at = datetime.now(UTC).isoformat()
        record: dict[str, Any] = {
            "source_id": target.source_id,
            "dataset_id": target.dataset_id,
            "var_code": target.var_code,
            "url": target.url,
            "kind": target.kind,
            "retrieved_at": retrieved_at,
        }
        try:
            record["text"] = _download_text(target.url)
            record["status"] = "ok"
        except Exception as exc:  # pragma: no cover - network/runtime dependent
            record["text"] = ""
            record["status"] = "error"
            record["error"] = str(exc)

        out_file.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        written.append(out_file)
    return written


if __name__ == "__main__":
    files = ingest_docs()
    print(f"ingested_docs={len(files)}")

