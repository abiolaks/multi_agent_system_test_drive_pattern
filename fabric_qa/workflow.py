from __future__ import annotations

from typing import Callable

import agent_framework as af
from agent_framework.orchestrations import SequentialBuilder

from fabric_qa.email_executor import DraftEmailExecutor
from fabric_qa.fabric_tool import make_fetch_fabric_data_tool
from fabric_qa.models import EmailDraft, FabricResult, Report

GENERAL_DATA_INSTRUCTIONS = (
    "You answer questions about data in the user's Fabric workspace. "
    "Use the fetch_fabric_data tool to get relevant data, then summarize it clearly."
)


async def ask(
    question: str,
    *,
    chat_client: af.SupportsChatGetResponse,
    fetch: Callable[[str], FabricResult],
    email_draft: Callable[[Report], EmailDraft],
) -> Report:
    captured: list[FabricResult] = []
    tool = make_fetch_fabric_data_tool(fetch, captured)
    agent = af.Agent(chat_client, GENERAL_DATA_INSTRUCTIONS, name="general_data_answerer", tools=[tool])
    email_executor = DraftEmailExecutor(email_draft, captured)

    workflow = SequentialBuilder(participants=[agent, email_executor]).build()
    result = await workflow.run(question)

    return result.get_outputs()[0]
