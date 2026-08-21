from __future__ import annotations

from typing import Callable

import agent_framework as af

from fabric_qa.models import FabricResult, Report


def build_general_data_report(captured: list[FabricResult]) -> Callable[[af.AgentExecutorResponse], Report]:
    # images never pass through the LLM's responsibility - they're pulled
    # straight from the captured tool results, never described in text
    def build_report(response: af.AgentExecutorResponse) -> Report:
        images = [image for result in captured for image in result.images]
        return Report(summary=response.agent_response.text, images=images)

    return build_report


def make_fetch_fabric_data(
    fetch: Callable[[str], FabricResult],
    captured: list[FabricResult],
) -> Callable[[str], str]:
    def fetch_fabric_data(question: str) -> str:
        result = fetch(question)
        captured.append(result)
        return result.data if isinstance(result.data, str) else str(result.data)

    return fetch_fabric_data


def make_fetch_fabric_data_tool(
    fetch: Callable[[str], FabricResult],
    captured: list[FabricResult],
) -> af.FunctionTool:
    return af.tool(
        make_fetch_fabric_data(fetch, captured),
        name="fetch_fabric_data",
        description="Fetch data from the Fabric workspace to help answer a question.",
    )
