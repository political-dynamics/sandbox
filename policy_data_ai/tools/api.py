"""Stable tool wrappers for notebook/assistant usage."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from policy_data_ai.cache.file_cache import SQLiteCache
from policy_data_ai.connectors.base import FetchResult
from policy_data_ai.connectors.factory import build_connector
from policy_data_ai.rag.retrieve import answer_definition
from policy_data_ai.registry.loader import SourceRegistry
from policy_data_ai.utils.provenance import extract_provenance


@dataclass(slots=True)
class ToolFetchResponse:
    """Serializable wrapper around connector fetch results."""

    data: Any
    provenance: dict[str, Any]


class PolicyDataRuntime:
    """Runtime orchestrating registry, connectors, cache, and docs index."""

    def __init__(
        self,
        *,
        registry_dir: str | Path = "sources_registry",
        cache_path: str | Path = ".policy_data_ai/cache.sqlite3",
        docs_index_path: str | Path = "metadata_store/docs/index.json",
    ) -> None:
        self.registry = SourceRegistry.from_directory(registry_dir)
        self.cache = SQLiteCache(cache_path)
        self.docs_index_path = Path(docs_index_path)
        self._connectors: dict[str, Any] = {}

    def close(self) -> None:
        self.cache.close()

    def _connector(self, source: str):
        if source not in self._connectors:
            source_meta = self.registry.get_source(source)
            self._connectors[source] = build_connector(source_meta, cache=self.cache)
        return self._connectors[source]

    def tool_list_sources(self) -> list[dict[str, Any]]:
        return self.registry.list_sources()

    def tool_search_datasets(self, query: str) -> list[dict[str, Any]]:
        return self.registry.search_datasets(query)

    def tool_list_variables(self, source: str, dataset_id: str) -> list[dict[str, Any]]:
        return self._connector(source).list_variables(dataset_id)

    def tool_explain_variable(
        self,
        source: str,
        dataset_id: str,
        var_code: str,
    ) -> dict[str, Any]:
        variables = self.registry.list_variables(source, dataset_id)
        for variable in variables:
            if variable.get("var_code") != var_code:
                continue
            definition = variable.get("definition")
            if definition:
                return {
                    "answer": definition,
                    "source": "registry",
                    "citations": [
                        {
                            "url": variable.get("doc_url"),
                            "chunk_id": None,
                            "retrieved_at": None,
                            "score": None,
                        }
                    ],
                    "unit": variable.get("unit"),
                    "label": variable.get("label"),
                }
            break

        question = f"Define {var_code} in {dataset_id} ({source})."
        return answer_definition(
            question,
            context={
                "source_id": source,
                "dataset_id": dataset_id,
                "var_code": var_code,
            },
            index_path=self.docs_index_path,
        )

    def tool_fetch_data(
        self,
        source: str,
        dataset_id: str,
        filters: dict[str, Any] | None = None,
        start: str | None = None,
        end: str | None = None,
        format: str = "pandas",
    ) -> ToolFetchResponse:
        connector = self._connector(source)
        result: FetchResult = connector.fetch(
            dataset_id=dataset_id,
            filters=filters,
            start=start,
            end=end,
            format=format,
        )
        return ToolFetchResponse(data=result.data, provenance=result.provenance)

    def tool_show_provenance(self, data_obj: Any) -> dict[str, Any] | None:
        if isinstance(data_obj, ToolFetchResponse):
            return data_obj.provenance
        if isinstance(data_obj, FetchResult):
            return data_obj.provenance
        return extract_provenance(data_obj)


_RUNTIME: PolicyDataRuntime | None = None


def _runtime() -> PolicyDataRuntime:
    global _RUNTIME
    if _RUNTIME is None:
        _RUNTIME = PolicyDataRuntime()
    return _RUNTIME


def tool_list_sources() -> list[dict[str, Any]]:
    return _runtime().tool_list_sources()


def tool_search_datasets(query: str) -> list[dict[str, Any]]:
    return _runtime().tool_search_datasets(query)


def tool_list_variables(source: str, dataset_id: str) -> list[dict[str, Any]]:
    return _runtime().tool_list_variables(source, dataset_id)


def tool_explain_variable(source: str, dataset_id: str, var_code: str) -> dict[str, Any]:
    return _runtime().tool_explain_variable(source, dataset_id, var_code)


def tool_fetch_data(
    source: str,
    dataset_id: str,
    filters: dict[str, Any] | None = None,
    start: str | None = None,
    end: str | None = None,
    format: str = "pandas",
) -> ToolFetchResponse:
    return _runtime().tool_fetch_data(
        source=source,
        dataset_id=dataset_id,
        filters=filters,
        start=start,
        end=end,
        format=format,
    )


def tool_show_provenance(data_obj: Any) -> dict[str, Any] | None:
    return _runtime().tool_show_provenance(data_obj)
