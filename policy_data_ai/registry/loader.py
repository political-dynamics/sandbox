"""Loading and querying the source registry."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from policy_data_ai.registry.schema import validate_source_config

REGISTRY_SUFFIXES = (".yaml", ".yml", ".json")


def _load_yaml_or_json(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        return json.loads(text)

    try:
        import yaml  # type: ignore

        return yaml.safe_load(text)
    except ModuleNotFoundError:
        # JSON is valid YAML, so this fallback works for JSON-formatted *.yaml files.
        return json.loads(text)


@dataclass(slots=True)
class SourceRegistry:
    """Registry object backed by source files."""

    sources: dict[str, dict[str, Any]]

    @classmethod
    def from_directory(cls, registry_dir: str | Path) -> "SourceRegistry":
        base = Path(registry_dir)
        if not base.exists():
            raise FileNotFoundError(f"Registry directory not found: {base}")

        sources: dict[str, dict[str, Any]] = {}
        for path in sorted(base.iterdir()):
            if not path.is_file() or path.suffix.lower() not in REGISTRY_SUFFIXES:
                continue
            payload = _load_yaml_or_json(path)
            validate_source_config(payload, context=str(path))
            source_id = payload["source_id"]
            sources[source_id] = payload

        if not sources:
            raise ValueError(f"No registry files found in {base}")
        return cls(sources=sources)

    def list_sources(self) -> list[dict[str, Any]]:
        result = []
        for source_id, source in sorted(self.sources.items()):
            result.append(
                {
                    "source_id": source_id,
                    "name": source.get("name", source_id),
                    "description": source.get("description", ""),
                    "api_type": source.get("api_type", ""),
                }
            )
        return result

    def get_source(self, source_id: str) -> dict[str, Any]:
        if source_id not in self.sources:
            raise KeyError(f"Unknown source: {source_id}")
        return self.sources[source_id]

    def get_dataset(self, source_id: str, dataset_id: str) -> dict[str, Any]:
        source = self.get_source(source_id)
        for dataset in source.get("datasets", []):
            if dataset.get("dataset_id") == dataset_id:
                return dataset
        raise KeyError(f"Unknown dataset `{dataset_id}` for source `{source_id}`")

    def list_dimensions(self, source_id: str, dataset_id: str) -> list[dict[str, Any]]:
        return list(self.get_dataset(source_id, dataset_id).get("dimensions", []))

    def list_variables(self, source_id: str, dataset_id: str) -> list[dict[str, Any]]:
        return list(self.get_dataset(source_id, dataset_id).get("variables", []))

    def search_datasets(self, query: str) -> list[dict[str, Any]]:
        q = query.lower().strip()
        results: list[dict[str, Any]] = []
        if not q:
            return results

        for source_id, source in self.sources.items():
            for dataset in source.get("datasets", []):
                haystack_parts = [
                    dataset.get("dataset_id", ""),
                    dataset.get("name", ""),
                    dataset.get("description", ""),
                ]
                for variable in dataset.get("variables", []):
                    haystack_parts.extend(
                        [
                            variable.get("var_code", ""),
                            variable.get("label", ""),
                            variable.get("definition", ""),
                        ]
                    )
                haystack = " ".join(str(x).lower() for x in haystack_parts)
                if q in haystack:
                    results.append(
                        {
                            "source_id": source_id,
                            "dataset_id": dataset.get("dataset_id"),
                            "name": dataset.get("name"),
                            "description": dataset.get("description"),
                        }
                    )

        results.sort(key=lambda item: (item["source_id"], item["dataset_id"]))
        return results

