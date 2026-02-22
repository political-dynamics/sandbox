"""Registry tests."""

from __future__ import annotations

import unittest
from pathlib import Path

from policy_data_ai.registry.loader import SourceRegistry


class SourceRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = SourceRegistry.from_directory(Path("sources_registry"))

    def test_expected_sources_exist(self) -> None:
        expected = {
            "destatis",
            "eurostat",
            "oecd",
            "worldbank",
            "fred",
            "un_data",
            "un_migration",
            "owid",
            "migration_portal",
        }
        self.assertEqual(expected, set(self.registry.sources.keys()))

    def test_search_unemployment_returns_multiple_sources(self) -> None:
        results = self.registry.search_datasets("unemployment")
        source_ids = {item["source_id"] for item in results}
        self.assertIn("worldbank", source_ids)
        self.assertIn("eurostat", source_ids)

    def test_variable_metadata_exists(self) -> None:
        variables = self.registry.list_variables("worldbank", "SL.UEM.TOTL.ZS")
        self.assertTrue(any(v.get("var_code") == "value" for v in variables))


if __name__ == "__main__":
    unittest.main()

