"""OWID grapher CSV adapter."""

from __future__ import annotations

from typing import Any

from policy_data_ai.connectors.base import FetchResult
from policy_data_ai.connectors.csv import CSVConnector


class OWIDConnector(CSVConnector):
    """Connector for Our World in Data grapher CSV endpoints."""

    def fetch(
        self,
        dataset_id: str,
        filters: dict[str, Any] | None = None,
        start: str | None = None,
        end: str | None = None,
        format: str = "pandas",
    ) -> FetchResult:
        dataset = self._dataset(dataset_id)
        if not dataset.get("csv_url"):
            raise ValueError(
                f"Dataset `{dataset_id}` is missing `csv_url`. "
                "Define `csv_url` in sources_registry/owid.yaml."
            )
        return super().fetch(dataset_id, filters=filters, start=start, end=end, format=format)
