"""Generic REST connector."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from policy_data_ai.cache.file_cache import SQLiteCache
from policy_data_ai.connectors.base import BaseConnector, FetchResult
from policy_data_ai.utils.provenance import make_provenance


def _normalize_params(params: dict[str, Any] | None) -> dict[str, Any]:
    if not params:
        return {}
    normalized: dict[str, Any] = {}
    for key, value in params.items():
        if isinstance(value, (list, tuple)):
            normalized[key] = [str(v) for v in value]
        else:
            normalized[key] = str(value)
    return normalized


class RESTConnector(BaseConnector):
    """Base class for JSON REST APIs."""

    def __init__(
        self,
        source_meta: dict[str, Any],
        *,
        cache: SQLiteCache | None = None,
        timeout_seconds: int = 30,
    ) -> None:
        super().__init__(source_meta, cache=cache, timeout_seconds=timeout_seconds)
        self.base_url = str(source_meta.get("base_url", "")).rstrip("/")
        if not self.base_url:
            raise ValueError(f"Source `{self.source_id}` is missing `base_url`.")

    def _resolve_url(self, endpoint: str) -> str:
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            return endpoint
        clean_endpoint = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        return f"{self.base_url}{clean_endpoint}"

    def _request_json(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        url = self._resolve_url(endpoint)
        normalized = _normalize_params(params)
        query = urlencode(normalized, doseq=True)
        full_url = f"{url}?{query}" if query else url

        cache_key = None
        if self.cache is not None:
            cache_key = SQLiteCache.build_key(
                namespace=f"http:{self.source_id}",
                payload={"url": full_url},
            )
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached

        self._apply_rate_limit()
        request = Request(
            full_url,
            headers={"User-Agent": "policy_data_ai/0.1 (+https://local-notebook)"},
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))

        if cache_key is not None:
            self.cache.set(cache_key, payload)
        return payload

    def fetch(
        self,
        dataset_id: str,
        filters: dict[str, Any] | None = None,
        start: str | None = None,
        end: str | None = None,
        format: str = "pandas",
    ) -> FetchResult:
        dataset = self._dataset(dataset_id)
        endpoint = dataset.get("endpoint", "")
        if not endpoint:
            raise ValueError(
                f"Dataset `{dataset_id}` for source `{self.source_id}` is missing `endpoint`."
            )

        params = dict(filters or {})
        if start is not None:
            params["start"] = start
        if end is not None:
            params["end"] = end

        payload = self._request_json(endpoint, params)
        rows = self._extract_rows(payload)
        provenance = make_provenance(
            source=self.source_id,
            dataset_id=dataset_id,
            endpoint=self._resolve_url(endpoint),
            params=params,
            doc_urls=[doc.get("url", "") for doc in dataset.get("docs", []) if isinstance(doc, dict)],
        )
        return self._build_result(rows, provenance=provenance, output_format=format)

    @staticmethod
    def _extract_rows(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            if payload and isinstance(payload[0], dict):
                if len(payload) == 2 and isinstance(payload[1], list):
                    return [dict(item) for item in payload[1] if isinstance(item, dict)]
                return [dict(item) for item in payload if isinstance(item, dict)]
            return [{"value": item} for item in payload]

        if isinstance(payload, dict):
            data = payload.get("data")
            if isinstance(data, list):
                return [dict(item) for item in data if isinstance(item, dict)]
            return [payload]

        return [{"value": payload}]

