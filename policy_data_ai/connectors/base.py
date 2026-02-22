"""Base connector protocol."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from policy_data_ai.cache.file_cache import SQLiteCache
from policy_data_ai.utils.provenance import attach_provenance


@dataclass(slots=True)
class FetchResult:
    """Unified fetch output."""

    data: Any
    provenance: dict[str, Any]


class BaseConnector(ABC):
    """Common interface for all source connectors."""

    _last_request_by_source: dict[str, float] = {}

    def __init__(
        self,
        source_meta: dict[str, Any],
        *,
        cache: SQLiteCache | None = None,
        timeout_seconds: int = 30,
    ) -> None:
        self.source_meta = source_meta
        self.source_id = source_meta["source_id"]
        self.timeout_seconds = timeout_seconds
        self.cache = cache

    def list_datasets(self) -> list[dict[str, Any]]:
        return [
            {
                "dataset_id": dataset.get("dataset_id"),
                "name": dataset.get("name"),
                "description": dataset.get("description"),
                "api_type": self.source_meta.get("api_type"),
            }
            for dataset in self.source_meta.get("datasets", [])
        ]

    def list_dimensions(self, dataset_id: str) -> list[dict[str, Any]]:
        return list(self._dataset(dataset_id).get("dimensions", []))

    def list_variables(self, dataset_id: str) -> list[dict[str, Any]]:
        return list(self._dataset(dataset_id).get("variables", []))

    def get_metadata(self, dataset_id: str) -> dict[str, Any]:
        dataset = self._dataset(dataset_id)
        return {
            "source_id": self.source_id,
            "dataset_id": dataset_id,
            "name": dataset.get("name"),
            "description": dataset.get("description"),
            "dimensions": list(dataset.get("dimensions", [])),
            "variables": list(dataset.get("variables", [])),
            "docs": list(dataset.get("docs", [])),
        }

    @abstractmethod
    def fetch(
        self,
        dataset_id: str,
        filters: dict[str, Any] | None = None,
        start: str | None = None,
        end: str | None = None,
        format: str = "pandas",
    ) -> FetchResult:
        """Fetch data for a dataset and normalize output."""

    def _dataset(self, dataset_id: str) -> dict[str, Any]:
        for dataset in self.source_meta.get("datasets", []):
            if dataset.get("dataset_id") == dataset_id:
                return dataset
        raise KeyError(f"Dataset `{dataset_id}` not found for source `{self.source_id}`")

    def _apply_rate_limit(self) -> None:
        per_second = float(self.source_meta.get("rate_limit_per_second", 5))
        if per_second <= 0:
            return
        min_interval = 1.0 / per_second
        now = time.monotonic()
        last = self._last_request_by_source.get(self.source_id, 0.0)
        wait_time = min_interval - (now - last)
        if wait_time > 0:
            time.sleep(wait_time)
        self._last_request_by_source[self.source_id] = time.monotonic()

    def _to_format(self, rows: list[dict[str, Any]], output_format: str) -> Any:
        if output_format == "records":
            return rows
        if output_format != "pandas":
            raise ValueError(f"Unsupported format `{output_format}`.")

        try:
            import pandas as pd  # type: ignore
        except ModuleNotFoundError:
            return rows
        return pd.DataFrame(rows)

    def _build_result(
        self,
        rows: list[dict[str, Any]],
        *,
        provenance: dict[str, Any],
        output_format: str,
    ) -> FetchResult:
        data = self._to_format(rows, output_format)
        attach_provenance(data, provenance)
        return FetchResult(data=data, provenance=provenance)

