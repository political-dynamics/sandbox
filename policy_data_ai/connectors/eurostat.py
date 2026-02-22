"""Eurostat SDMX adapter."""

from __future__ import annotations

from typing import Any

from policy_data_ai.connectors.base import FetchResult
from policy_data_ai.connectors.sdmx import SDMXConnector


class EurostatConnector(SDMXConnector):
    """Eurostat connector using the dissemination API."""

    def fetch(
        self,
        dataset_id: str,
        filters: dict[str, Any] | None = None,
        start: str | None = None,
        end: str | None = None,
        format: str = "pandas",
    ) -> FetchResult:
        merged = {
            "format": "JSON",
            **(filters or {}),
        }
        return super().fetch(dataset_id, filters=merged, start=start, end=end, format=format)

