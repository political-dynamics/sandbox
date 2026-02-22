"""Connector factory by source metadata."""

from __future__ import annotations

from typing import Any

from policy_data_ai.cache.file_cache import SQLiteCache
from policy_data_ai.connectors.base import BaseConnector
from policy_data_ai.connectors.csv import CSVConnector
from policy_data_ai.connectors.eurostat import EurostatConnector
from policy_data_ai.connectors.owid import OWIDConnector
from policy_data_ai.connectors.rest import RESTConnector
from policy_data_ai.connectors.sdmx import SDMXConnector
from policy_data_ai.connectors.worldbank import WorldBankConnector


def build_connector(
    source_meta: dict[str, Any],
    *,
    cache: SQLiteCache | None = None,
    timeout_seconds: int = 30,
) -> BaseConnector:
    source_id = source_meta["source_id"]
    api_type = source_meta["api_type"]

    if source_id == "worldbank":
        return WorldBankConnector(source_meta, cache=cache, timeout_seconds=timeout_seconds)
    if source_id == "owid":
        return OWIDConnector(source_meta, cache=cache, timeout_seconds=timeout_seconds)
    if source_id == "eurostat":
        return EurostatConnector(source_meta, cache=cache, timeout_seconds=timeout_seconds)

    if api_type == "rest":
        return RESTConnector(source_meta, cache=cache, timeout_seconds=timeout_seconds)
    if api_type == "csv":
        return CSVConnector(source_meta, cache=cache, timeout_seconds=timeout_seconds)
    if api_type == "sdmx":
        return SDMXConnector(source_meta, cache=cache, timeout_seconds=timeout_seconds)
    raise ValueError(f"Unsupported connector API type `{api_type}` for source `{source_id}`.")

