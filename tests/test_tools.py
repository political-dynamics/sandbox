"""Tool wrapper tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from policy_data_ai.tools.api import PolicyDataRuntime, ToolFetchResponse


class ToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        cache_path = Path(self.tmpdir.name) / "cache.sqlite3"
        self.runtime = PolicyDataRuntime(
            registry_dir="sources_registry",
            cache_path=cache_path,
            docs_index_path=Path(self.tmpdir.name) / "index.json",
        )

    def tearDown(self) -> None:
        self.runtime.close()
        self.tmpdir.cleanup()

    def test_list_sources(self) -> None:
        sources = self.runtime.tool_list_sources()
        self.assertGreaterEqual(len(sources), 9)

    def test_search_datasets(self) -> None:
        hits = self.runtime.tool_search_datasets("population")
        source_ids = {hit["source_id"] for hit in hits}
        self.assertIn("owid", source_ids)

    def test_explain_variable_registry_first(self) -> None:
        out = self.runtime.tool_explain_variable("worldbank", "SL.UEM.TOTL.ZS", "value")
        self.assertEqual("registry", out["source"])
        self.assertTrue(out["answer"])

    def test_show_provenance_from_wrapper(self) -> None:
        payload = ToolFetchResponse(data=[], provenance={"source": "test"})
        self.assertEqual({"source": "test"}, self.runtime.tool_show_provenance(payload))


if __name__ == "__main__":
    unittest.main()
