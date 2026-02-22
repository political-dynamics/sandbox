"""Validation for source registry files."""

from __future__ import annotations

from typing import Any

REQUIRED_SOURCE_KEYS = {"source_id", "name", "description", "api_type", "datasets"}
REQUIRED_DATASET_KEYS = {"dataset_id", "name", "description"}
ALLOWED_API_TYPES = {"sdmx", "rest", "csv"}


def _expect_dict(value: Any, label: str, context: str) -> None:
    if not isinstance(value, dict):
        raise ValueError(f"{context}: `{label}` must be an object.")


def _expect_list(value: Any, label: str, context: str) -> None:
    if not isinstance(value, list):
        raise ValueError(f"{context}: `{label}` must be a list.")


def validate_source_config(config: dict[str, Any], *, context: str = "<unknown>") -> None:
    """Validate one source registry document."""
    _expect_dict(config, "source", context)

    missing = REQUIRED_SOURCE_KEYS - set(config.keys())
    if missing:
        raise ValueError(f"{context}: missing source keys: {sorted(missing)}")

    api_type = config.get("api_type")
    if api_type not in ALLOWED_API_TYPES:
        raise ValueError(f"{context}: unsupported api_type `{api_type}`.")

    datasets = config.get("datasets")
    _expect_list(datasets, "datasets", context)
    for idx, dataset in enumerate(datasets):
        item_ctx = f"{context}::datasets[{idx}]"
        _expect_dict(dataset, "dataset", item_ctx)
        ds_missing = REQUIRED_DATASET_KEYS - set(dataset.keys())
        if ds_missing:
            raise ValueError(f"{item_ctx}: missing dataset keys: {sorted(ds_missing)}")

        dimensions = dataset.get("dimensions", [])
        _expect_list(dimensions, "dimensions", item_ctx)

        variables = dataset.get("variables", [])
        _expect_list(variables, "variables", item_ctx)
        for v_idx, variable in enumerate(variables):
            var_ctx = f"{item_ctx}::variables[{v_idx}]"
            _expect_dict(variable, "variable", var_ctx)
            for req_key in ("var_code", "label"):
                if req_key not in variable:
                    raise ValueError(f"{var_ctx}: missing variable key `{req_key}`.")

