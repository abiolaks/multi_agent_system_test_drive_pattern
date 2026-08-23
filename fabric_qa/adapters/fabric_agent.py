from __future__ import annotations

import asyncio
import json
import os
import re
from typing import Any, Protocol

from azure.identity import ClientSecretCredential
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from fabric_qa.models import AssetReadings, FabricResult, MaintenanceRecord, Reading

FABRIC_SCOPE = "https://api.fabric.microsoft.com/.default"
DEFAULT_TOOL_NAME = "DataAgent_arik_air_data_agent"

# engine_readings columns, confirmed against the live Data Agent
READINGS_COLUMNS = [
    "egt_c",
    "egt_margin_c",
    "n1_pct",
    "n2_pct",
    "vibration_n1_ips",
    "vibration_n2_ips",
    "oil_pressure_psi",
    "oil_temp_c",
    "fuel_flow_pph",
]


class DataAgentClient(Protocol):
    async def ask(self, question: str) -> str: ...


class StreamableHttpDataAgentClient:
    def __init__(self, mcp_url: str, credential: ClientSecretCredential, tool_name: str) -> None:
        self._mcp_url = mcp_url
        self._credential = credential
        self._tool_name = tool_name

    async def ask(self, question: str) -> str:
        token = self._credential.get_token(FABRIC_SCOPE)
        headers = {"Authorization": f"Bearer {token.token}"}
        async with streamablehttp_client(self._mcp_url, headers=headers) as (read, write, _get_session_id):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(self._tool_name, {"userQuestion": question})
                if result.isError:
                    raise RuntimeError(f"Data Agent tool call failed: {result.content}")
                return "".join(block.text for block in result.content if block.type == "text")


class FabricDataAgentPort:
    """FabricPort backed by the Fabric Data Agent's MCP tool.

    The Data Agent is stateless and single-turn per call - no
    structuredContent, and chart images it describes generating are
    never actually returned as content blocks (confirmed by hand:
    no image block, no listable resource, and a follow-up "give me the
    chart" question loses all context). So FabricResult.images stays
    empty here; only text/JSON extraction is wired up. fetch_readings/
    fetch_maintenance_history ask for a specific JSON shape and retry
    on parse failure - the agent occasionally answers with a prose
    error instead of the requested JSON.
    """

    def __init__(self, client: DataAgentClient) -> None:
        self._client = client

    @classmethod
    def from_env(cls) -> "FabricDataAgentPort":
        credential = ClientSecretCredential(
            tenant_id=os.environ["FABRIC_AGENT_TENANT_ID"],
            client_id=os.environ["FABRIC_AGENT_CLIENT_ID"],
            client_secret=os.environ["FABRIC_AGENT_CLIENT_SECRET"],
        )
        client = StreamableHttpDataAgentClient(
            mcp_url=os.environ["FABRIC_AGENT_MCP_URL"],
            credential=credential,
            tool_name=os.environ.get("FABRIC_AGENT_TOOL_NAME", DEFAULT_TOOL_NAME),
        )
        return cls(client)

    def fetch(self, question: str) -> FabricResult:
        text = asyncio.run(self._client.ask(question))
        return FabricResult(data=text)

    def fetch_readings(self, asset_id: str) -> AssetReadings:
        payload = asyncio.run(self._ask_json(_readings_question(asset_id)))
        readings = [Reading(parameter=name, value=float(value)) for name, value in payload["readings"].items()]
        return AssetReadings(asset_id=asset_id, asset_model=payload["asset_model"], readings=readings)

    def fetch_maintenance_history(self, asset_id: str) -> list[MaintenanceRecord]:
        payload = asyncio.run(self._ask_json(_maintenance_history_question(asset_id)))
        return [
            MaintenanceRecord(
                work_order_id=row["work_order_id"],
                date=row["date"],
                finding=row["finding"],
                parts_replaced=row.get("parts_replaced") or "",
            )
            for row in payload
        ]

    async def _ask_json(self, question: str, *, retries: int = 2) -> Any:
        last_error: Exception | None = None
        for _ in range(retries + 1):
            text = await self._client.ask(question)
            try:
                return json.loads(_strip_markdown_fence(text))
            except json.JSONDecodeError as exc:
                last_error = exc
        raise ValueError(
            f"Data Agent did not return parseable JSON after {retries + 1} attempts: {last_error}"
        ) from last_error


def _readings_question(asset_id: str) -> str:
    columns = ", ".join(READINGS_COLUMNS)
    return (
        f"For asset_id {asset_id}, return ONLY a single JSON object (no prose, no markdown "
        f"fences) with keys 'asset_model' (its model from asset_registry) and 'readings' "
        f"(an object mapping each of these engine_readings columns to its latest value: {columns})."
    )


def _maintenance_history_question(asset_id: str) -> str:
    return (
        f"For asset_id {asset_id}, return ONLY a JSON array (no prose, no markdown fences) of "
        f"its maintenance_history rows, each with keys work_order_id, date, finding, "
        f"parts_replaced."
    )


def _strip_markdown_fence(text: str) -> str:
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL)
    return match.group(1) if match else text.strip()
