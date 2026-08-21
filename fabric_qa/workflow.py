from __future__ import annotations

from typing import Callable

import agent_framework as af

from fabric_qa.asset_health import FetchAndClassifyExecutor, build_asset_health_report
from fabric_qa.classify import Verdict
from fabric_qa.email_executor import DraftEmailExecutor
from fabric_qa.fabric_tool import build_general_data_report, make_fetch_fabric_data_tool
from fabric_qa.models import AssetReadings, EmailDraft, FabricResult, Report
from fabric_qa.router import RouterDecision
from fabric_qa.router_agent import ROUTER_INSTRUCTIONS, ExtractRouterDecisionExecutor, RouterOutput

GENERAL_DATA_INSTRUCTIONS = (
    "You answer questions about data in the user's Fabric workspace. "
    "Use the fetch_fabric_data tool to get relevant data, then summarize it clearly."
)

ASSET_HEALTH_INSTRUCTIONS = (
    "You narrate asset-health verdicts for an aircraft engine maintenance "
    "audience. Summarize the given verdicts clearly and concisely."
)


class _ToOriginalQuestion(af.Executor):
    # the switch-case's Default target receives the routed RouterDecision,
    # but the general-data Agent needs the original question text instead
    def __init__(self, question: str) -> None:
        super().__init__(id="to_original_question")
        self._question = question

    @af.handler(input=RouterDecision, output=str)
    async def handle(self, decision: RouterDecision, ctx: af.WorkflowContext[str]) -> None:
        await ctx.send_message(self._question)


async def ask(
    question: str,
    *,
    chat_client: af.SupportsChatGetResponse,
    fetch: Callable[[str], FabricResult],
    fetch_readings: Callable[[str], AssetReadings],
    email_draft: Callable[[Report], EmailDraft],
) -> Report:
    router_agent = af.Agent(
        chat_client,
        ROUTER_INSTRUCTIONS,
        name="router",
        default_options=af.ChatOptions(response_format=RouterOutput),  # type: ignore[arg-type]
    )
    extract = ExtractRouterDecisionExecutor()

    fabric_captured: list[FabricResult] = []
    fabric_tool = make_fetch_fabric_data_tool(fetch, fabric_captured)
    general_data_agent = af.Agent(
        chat_client, GENERAL_DATA_INSTRUCTIONS, name="general_data_answerer", tools=[fabric_tool]
    )
    general_data_email = DraftEmailExecutor(
        email_draft, build_general_data_report(fabric_captured), id="draft_email_general_data"
    )

    verdicts_captured: list[list[Verdict]] = []
    fetch_and_classify = FetchAndClassifyExecutor(fetch_readings, verdicts_captured)
    asset_health_agent = af.Agent(chat_client, ASSET_HEALTH_INSTRUCTIONS, name="asset_health_summarizer")
    asset_health_email = DraftEmailExecutor(
        email_draft, build_asset_health_report(verdicts_captured), id="draft_email_asset_health"
    )

    to_original_question = _ToOriginalQuestion(question)

    builder = af.WorkflowBuilder(start_executor=router_agent, output_from=[general_data_email, asset_health_email])
    builder.add_edge(router_agent, extract)
    builder.add_switch_case_edge_group(
        extract,
        [
            af.Case(condition=lambda decision: decision.topic == "asset_health", target=fetch_and_classify),
            af.Default(target=to_original_question),
        ],
    )
    builder.add_edge(to_original_question, general_data_agent)
    builder.add_edge(general_data_agent, general_data_email)
    builder.add_edge(fetch_and_classify, asset_health_agent)
    builder.add_edge(asset_health_agent, asset_health_email)

    workflow = builder.build()
    result = await workflow.run(question)
    return result.get_outputs()[0]
