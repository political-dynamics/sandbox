"""SDMX-style connector with JSON-stat decoding."""

from __future__ import annotations

import math
from typing import Any

from policy_data_ai.connectors.base import FetchResult
from policy_data_ai.connectors.rest import RESTConnector
from policy_data_ai.utils.provenance import make_provenance


def _pos_to_code(category_index: Any) -> dict[int, str]:
    if isinstance(category_index, list):
        return {idx: str(code) for idx, code in enumerate(category_index)}
    if isinstance(category_index, dict):
        mapped: dict[int, str] = {}
        for code, pos in category_index.items():
            try:
                mapped[int(pos)] = str(code)
            except (TypeError, ValueError):
                continue
        return mapped
    return {}


class SDMXConnector(RESTConnector):
    """Connector for SDMX APIs returning JSON-stat data."""

    def fetch(
        self,
        dataset_id: str,
        filters: dict[str, Any] | None = None,
        start: str | None = None,
        end: str | None = None,
        format: str = "pandas",
    ) -> FetchResult:
        dataset = self._dataset(dataset_id)
        endpoint = dataset.get("endpoint", "/{dataset_id}").format(dataset_id=dataset_id)
        params: dict[str, Any] = {}
        for key, value in (filters or {}).items():
            if isinstance(value, (list, tuple)):
                params[key] = ",".join(str(item) for item in value)
            else:
                params[key] = value
        if start:
            params["sinceTimePeriod"] = start
        if end:
            params["untilTimePeriod"] = end

        payload = self._request_json(endpoint, params)
        rows = self._decode_jsonstat(payload)
        provenance = make_provenance(
            source=self.source_id,
            dataset_id=dataset_id,
            endpoint=self._resolve_url(endpoint),
            params=params,
            doc_urls=[doc.get("url", "") for doc in dataset.get("docs", []) if isinstance(doc, dict)],
        )
        return self._build_result(rows, provenance=provenance, output_format=format)

    @staticmethod
    def _decode_jsonstat(payload: Any) -> list[dict[str, Any]]:
        if not isinstance(payload, dict):
            return []

        dim_ids = payload.get("id", [])
        sizes = payload.get("size", [])
        dimensions = payload.get("dimension", {})
        values = payload.get("value", {})
        if not isinstance(dim_ids, list) or not isinstance(sizes, list):
            return []
        if not isinstance(values, dict):
            # Some APIs may return list form.
            if isinstance(values, list):
                values = {str(i): v for i, v in enumerate(values)}
            else:
                return []

        code_maps: list[dict[int, str]] = []
        for dim_id in dim_ids:
            dim_payload = dimensions.get(dim_id, {}) if isinstance(dimensions, dict) else {}
            category = dim_payload.get("category", {}) if isinstance(dim_payload, dict) else {}
            index_map = category.get("index", {}) if isinstance(category, dict) else {}
            code_maps.append(_pos_to_code(index_map))

        total_points = 1
        for size in sizes:
            total_points *= int(size)

        rows: list[dict[str, Any]] = []
        for flat_idx in range(total_points):
            raw_value = values.get(str(flat_idx))
            if raw_value is None:
                continue

            coords = SDMXConnector._decode_coordinates(flat_idx, sizes)
            row: dict[str, Any] = {}
            for dim_pos, coord in enumerate(coords):
                dim_id = str(dim_ids[dim_pos])
                row[dim_id] = code_maps[dim_pos].get(coord, str(coord))
            row["value"] = raw_value
            rows.append(row)
        return rows

    @staticmethod
    def _decode_coordinates(flat_index: int, sizes: list[Any]) -> list[int]:
        numeric_sizes = [int(size) for size in sizes]
        coords: list[int] = []
        remainder = flat_index
        for dim_pos, current_size in enumerate(numeric_sizes):
            if dim_pos == len(numeric_sizes) - 1:
                stride = 1
            else:
                stride = math.prod(numeric_sizes[dim_pos + 1 :])
            coord = remainder // stride if stride else 0
            coords.append(coord)
            remainder = remainder % stride if stride else 0
        return coords

