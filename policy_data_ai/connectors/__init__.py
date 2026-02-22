"""Connector interfaces and provider adapters."""

from policy_data_ai.connectors.base import BaseConnector, FetchResult
from policy_data_ai.connectors.factory import build_connector
from policy_data_ai.connectors.worldbank import WorldBankConnector
from policy_data_ai.connectors.owid import OWIDConnector
from policy_data_ai.connectors.eurostat import EurostatConnector

__all__ = [
    "BaseConnector",
    "FetchResult",
    "build_connector",
    "WorldBankConnector",
    "OWIDConnector",
    "EurostatConnector",
]

