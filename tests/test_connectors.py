"""Connector tests with mocked payloads."""

from __future__ import annotations

import unittest
from typing import Any

from policy_data_ai.connectors.eurostat import EurostatConnector
from policy_data_ai.connectors.owid import OWIDConnector
from policy_data_ai.connectors.worldbank import WorldBankConnector
from policy_data_ai.registry.loader import SourceRegistry


class StubWorldBankConnector(WorldBankConnector):
    def _request_json(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        return [
            {"page": 1},
            [
                {
                    "countryiso3code": "DEU",
                    "country": {"id": "DE", "value": "Germany"},
                    "date": "2020",
                    "value": 4.1,
                    "unit": "%",
                    "indicator": {"id": "SL.UEM.TOTL.ZS", "value": "Unemployment"},
                    "obs_status": "",
                    "decimal": 1,
                }
            ],
        ]


class StubOWIDConnector(OWIDConnector):
    def _request_text(self, endpoint: str, params: dict[str, Any] | None = None) -> str:
        return (
            "Entity,Code,Year,population\n"
            "Germany,DEU,2019,83000000\n"
            "Germany,DEU,2020,83100000\n"
            "France,FRA,2020,67000000\n"
        )


class StubEurostatConnector(EurostatConnector):
    def _request_json(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        return {
            "id": ["geo", "time"],
            "size": [2, 2],
            "dimension": {
                "geo": {"category": {"index": {"DE": 0, "FR": 1}}},
                "time": {"category": {"index": {"2020": 0, "2021": 1}}},
            },
            "value": {
                "0": 4.0,
                "1": 3.8,
                "2": 8.1,
                "3": 7.9
            },
        }


class ConnectorTests(unittest.TestCase):
    def setUp(self) -> None:
        registry = SourceRegistry.from_directory("sources_registry")
        self.worldbank = StubWorldBankConnector(registry.get_source("worldbank"))
        self.owid = StubOWIDConnector(registry.get_source("owid"))
        self.eurostat = StubEurostatConnector(registry.get_source("eurostat"))

    def test_worldbank_fetch(self) -> None:
        result = self.worldbank.fetch(
            "SL.UEM.TOTL.ZS",
            filters={"country": ["DE"]},
            start="2020",
            end="2020",
            format="records",
        )
        self.assertEqual(1, len(result.data))
        self.assertEqual("Germany", result.data[0]["country_name"])

    def test_owid_fetch_filters_rows(self) -> None:
        result = self.owid.fetch(
            "population",
            filters={"Entity": ["Germany"]},
            start="2020",
            end="2020",
            format="records",
        )
        self.assertEqual(1, len(result.data))
        self.assertEqual("83100000", result.data[0]["population"])

    def test_eurostat_jsonstat_decode(self) -> None:
        result = self.eurostat.fetch(
            "une_rt_a",
            filters={"geo": ["DE", "FR"]},
            start="2020",
            end="2021",
            format="records",
        )
        self.assertEqual(4, len(result.data))
        first = result.data[0]
        self.assertIn("geo", first)
        self.assertIn("time", first)
        self.assertIn("value", first)


if __name__ == "__main__":
    unittest.main()

