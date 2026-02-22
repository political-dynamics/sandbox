"""Generic CSV connector."""

from __future__ import annotations

import csv
import io
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from policy_data_ai.cache.file_cache import SQLiteCache
from policy_data_ai.connectors.base import BaseConnector, FetchResult
from policy_data_ai.utils.provenance import make_provenance

TIME_COLUMNS = ("year", "date", "time", "period")


class CSVConnector(BaseConnector):
    """Fetch data from a CSV endpoint and filter client-side."""

    def __init__(
        self,
        source_meta: dict[str, Any],
        *,
        cache: SQLiteCache | None = None,
        timeout_seconds: int = 30,
    ) -> None:
        super().__init__(source_meta, cache=cache, timeout_seconds=timeout_seconds)
        self.base_url = str(source_meta.get("base_url", "")).rstrip("/")

    def _resolve_url(self, endpoint: str) -> str:
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            return endpoint
        if not self.base_url:
            raise ValueError(f"Source `{self.source_id}` does not define base_url.")
        clean_endpoint = endpoint.lstrip("/")
        return f"{self.base_url}/{clean_endpoint}"

    def _request_text(self, endpoint: str, params: dict[str, Any] | None = None) -> str:
        params = params or {}
        url = self._resolve_url(endpoint)
        query = urlencode(params, doseq=True)
        full_url = f"{url}?{query}" if query else url

        cache_key = None
        if self.cache is not None:
            cache_key = SQLiteCache.build_key(
                namespace=f"http-text:{self.source_id}",
                payload={"url": full_url},
            )
            cached = self.cache.get(cache_key)
            if isinstance(cached, dict) and "text" in cached:
                return str(cached["text"])

        self._apply_rate_limit()
        request = Request(
            full_url,
            headers={"User-Agent": "policy_data_ai/0.1 (+https://local-notebook)"},
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:
            text = response.read().decode("utf-8")

        if cache_key is not None:
            self.cache.set(cache_key, {"text": text})
        return text

    def fetch(
        self,
        dataset_id: str,
        filters: dict[str, Any] | None = None,
        start: str | None = None,
        end: str | None = None,
        format: str = "pandas",
    ) -> FetchResult:
        dataset = self._dataset(dataset_id)
        endpoint = dataset.get("csv_url") or dataset.get("endpoint")
        if not endpoint:
            raise ValueError(f"Dataset `{dataset_id}` does not define `csv_url` or `endpoint`.")

        text = self._request_text(str(endpoint))
        reader = csv.DictReader(io.StringIO(text))
        rows = [dict(row) for row in reader]
        rows = self._filter_rows(rows, filters=filters or {}, start=start, end=end)

        provenance = make_provenance(
            source=self.source_id,
            dataset_id=dataset_id,
            endpoint=self._resolve_url(str(endpoint)),
            params={"filters": filters or {}, "start": start, "end": end},
            doc_urls=[doc.get("url", "") for doc in dataset.get("docs", []) if isinstance(doc, dict)],
        )
        return self._build_result(rows, provenance=provenance, output_format=format)

    def _filter_rows(
        self,
        rows: list[dict[str, Any]],
        *,
        filters: dict[str, Any],
        start: str | None,
        end: str | None,
    ) -> list[dict[str, Any]]:
        filtered = []
        for row in rows:
            if not self._matches_filters(row, filters):
                continue
            if not self._matches_time(row, start=start, end=end):
                continue
            filtered.append(row)
        return filtered

    @staticmethod
    def _matches_filters(row: dict[str, Any], filters: dict[str, Any]) -> bool:
        if not filters:
            return True
        norm_row = {str(k).lower(): str(v) for k, v in row.items()}
        for key, expected in filters.items():
            actual = norm_row.get(str(key).lower())
            if actual is None:
                return False
            if isinstance(expected, (list, tuple, set)):
                expected_set = {str(item) for item in expected}
                if actual not in expected_set:
                    return False
            else:
                if actual != str(expected):
                    return False
        return True

    @staticmethod
    def _matches_time(row: dict[str, Any], *, start: str | None, end: str | None) -> bool:
        if start is None and end is None:
            return True
        key = next((col for col in TIME_COLUMNS if col in {k.lower() for k in row.keys()}), None)
        if key is None:
            return True
        time_value = None
        for raw_key, raw_val in row.items():
            if raw_key.lower() == key:
                time_value = str(raw_val)
                break
        if time_value is None:
            return True

        if len(time_value) == 4 and time_value.isdigit():
            value = int(time_value)
            if start is not None and len(start) == 4 and start.isdigit() and value < int(start):
                return False
            if end is not None and len(end) == 4 and end.isdigit() and value > int(end):
                return False
            return True

        # Fallback to lexical compare for ISO-like dates.
        if start is not None and time_value < start:
            return False
        if end is not None and time_value > end:
            return False
        return True
