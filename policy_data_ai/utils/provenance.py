"""Provenance helpers for fetched datasets."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Mapping


def make_provenance(
    *,
    source: str,
    dataset_id: str,
    endpoint: str,
    params: Mapping[str, Any],
    doc_urls: list[str] | None = None,
) -> dict[str, Any]:
    """Build a normalized provenance record."""
    return {
        "source": source,
        "dataset_id": dataset_id,
        "endpoint": endpoint,
        "params": dict(params),
        "doc_urls": doc_urls or [],
        "timestamp_utc": datetime.now(UTC).isoformat(),
    }


def attach_provenance(data: Any, provenance: Mapping[str, Any]) -> Any:
    """Attach provenance to pandas objects when possible."""
    attrs = getattr(data, "attrs", None)
    if isinstance(attrs, dict):
        attrs["policy_data_ai_provenance"] = dict(provenance)
    return data


def extract_provenance(data: Any) -> dict[str, Any] | None:
    """Extract provenance if present on an object."""
    attrs = getattr(data, "attrs", None)
    if isinstance(attrs, dict):
        payload = attrs.get("policy_data_ai_provenance")
        if isinstance(payload, dict):
            return payload
    return None

