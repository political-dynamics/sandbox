"""World Bank API adapter."""

from __future__ import annotations

from typing import Any

from policy_data_ai.connectors.base import FetchResult
from policy_data_ai.connectors.rest import RESTConnector
from policy_data_ai.utils.provenance import make_provenance


class WorldBankConnector(RESTConnector):
    """World Bank v2 REST API connector."""

    def fetch(
        self,
        dataset_id: str,
        filters: dict[str, Any] | None = None,
        start: str | None = None,
        end: str | None = None,
        format: str = "pandas",
    ) -> FetchResult:
        dataset = self._dataset(dataset_id)
        filters = dict(filters or {})

        countries = filters.pop("country", "all")
        if isinstance(countries, (list, tuple)):
            countries_path = ";".join(str(country) for country in countries)
        else:
            countries_path = str(countries)

        endpoint_template = dataset.get("endpoint") or "/v2/country/{countries}/indicator/{dataset_id}"
        endpoint = endpoint_template.format(countries=countries_path, dataset_id=dataset_id)

        params: dict[str, Any] = {
            "format": "json",
            "per_page": 20000,
        }
        if start or end:
            left = start or ""
            right = end or ""
            params["date"] = f"{left}:{right}"
        params.update(filters)

        payload = self._request_json(endpoint, params)
        rows = self._extract_world_bank_rows(payload)
        provenance = make_provenance(
            source=self.source_id,
            dataset_id=dataset_id,
            endpoint=self._resolve_url(endpoint),
            params=params,
            doc_urls=[doc.get("url", "") for doc in dataset.get("docs", []) if isinstance(doc, dict)],
        )
        return self._build_result(rows, provenance=provenance, output_format=format)

    @staticmethod
    def _extract_world_bank_rows(payload: Any) -> list[dict[str, Any]]:
        if not isinstance(payload, list) or len(payload) < 2:
            return []
        records = payload[1]
        if not isinstance(records, list):
            return []

        rows: list[dict[str, Any]] = []
        for item in records:
            if not isinstance(item, dict):
                continue
            country = item.get("country", {})
            indicator = item.get("indicator", {})
            rows.append(
                {
                    "country_iso3": item.get("countryiso3code"),
                    "country_id": country.get("id") if isinstance(country, dict) else None,
                    "country_name": country.get("value") if isinstance(country, dict) else None,
                    "year": item.get("date"),
                    "value": item.get("value"),
                    "unit": item.get("unit"),
                    "indicator_id": indicator.get("id") if isinstance(indicator, dict) else None,
                    "indicator_name": indicator.get("value") if isinstance(indicator, dict) else None,
                    "obs_status": item.get("obs_status"),
                    "decimal": item.get("decimal"),
                }
            )
        return rows

