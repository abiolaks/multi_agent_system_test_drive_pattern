from __future__ import annotations

import asyncio
from typing import Callable

import agent_framework as af

from fabric_qa.asset_health import (
    AssetHealthContext,
    FetchAndClassifyExecutor,
    PrepareNormalSummaryExecutor,
    build_asset_health_report,
    compute_verdicts,
    format_verdicts_for_summary,
)
from fabric_qa.classify import Verdict
from fabric_qa.diagnosis import (
    DIAGNOSIS_INSTRUCTIONS,
    DiagnosisOutput,
    DiagnosisPrepExecutor,
    build_diagnosis_report,
    format_diagnosis_prompt,
    make_kb_tool,
    make_web_search_tool,
    to_diagnosis_result,
)
from fabric_qa.email_executor import DraftEmailExecutor
from fabric_qa.fabric_tool import build_general_data_report, make_fetch_fabric_data_tool
from fabric_qa.models import AssetReadings, EmailDraft, FabricResult, MaintenanceRecord, Report
from fabric_qa.router import RouterDecision
from fabric_qa.router_agent import ROUTER_INSTRUCTIONS, ExtractRouterDecisionExecutor, RouterOutput
from fabric_qa.scheduling import SchedulingSetupExecutor

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
    fetch_maintenance_history: Callable[[str], list[MaintenanceRecord]],
    retrieve_guidance: Callable[[str], str],
    web_search: Callable[[str], str],
    email_draft: Callable[[Report], EmailDraft],
    schedule: Callable[[str, Callable[[], None]], None],
) -> Report:
    router_agent = af.Agent(
        chat_client,
        ROUTER_INSTRUCTIONS,
        name="router",
        default_options=af.ChatOptions(response_format=RouterOutput),  # type: ignore[arg-type]
    )
    extract = ExtractRouterDecisionExecutor()

    # general_data branch
    fabric_captured: list[FabricResult] = []
    fabric_tool = make_fetch_fabric_data_tool(fetch, fabric_captured)
    general_data_agent = af.Agent(
        chat_client, GENERAL_DATA_INSTRUCTIONS, name="general_data_answerer", tools=[fabric_tool]
    )
    general_data_email = DraftEmailExecutor(
        email_draft, build_general_data_report(fabric_captured), id="draft_email_general_data"
    )
    to_original_question = _ToOriginalQuestion(question)

    # asset_health branch
    fetch_and_classify = FetchAndClassifyExecutor(fetch_readings)

    normal_verdicts_captured: list[list[Verdict]] = []
    prepare_normal_summary = PrepareNormalSummaryExecutor(normal_verdicts_captured)
    asset_health_agent = af.Agent(chat_client, ASSET_HEALTH_INSTRUCTIONS, name="asset_health_summarizer")
    asset_health_email = DraftEmailExecutor(
        email_draft, build_asset_health_report(normal_verdicts_captured), id="draft_email_asset_health"
    )

    diagnosis_context_captured: list[AssetHealthContext] = []
    diagnosis_prep = DiagnosisPrepExecutor(fetch_maintenance_history, diagnosis_context_captured)
    diagnosis_agent = af.Agent(
        chat_client,
        DIAGNOSIS_INSTRUCTIONS,
        name="diagnosis",
        tools=[
            make_kb_tool(retrieve_guidance),
            make_web_search_tool(web_search, lambda: diagnosis_context_captured[0]),
        ],
        default_options=af.ChatOptions(response_format=DiagnosisOutput),  # type: ignore[arg-type]
    )
    diagnosis_email = DraftEmailExecutor(
        email_draft, build_diagnosis_report(diagnosis_context_captured), id="draft_email_diagnosis"
    )

    # recurring branch (ADR 0003): a fire re-runs only the already-classified
    # branch via _run_and_draft, never the full ask() - the question text is
    # identical on every fire, so going through the router again would
    # re-classify it as recurring and register a duplicate schedule on top
    # of itself.
    def make_fire(decision: RouterDecision) -> Callable[[], None]:
        def fire() -> None:
            asyncio.run(
                _run_and_draft(
                    question,
                    decision,
                    chat_client=chat_client,
                    fetch=fetch,
                    fetch_readings=fetch_readings,
                    fetch_maintenance_history=fetch_maintenance_history,
                    retrieve_guidance=retrieve_guidance,
                    web_search=web_search,
                    email_draft=email_draft,
                )
            )

        return fire

    scheduling_setup = SchedulingSetupExecutor(schedule=schedule, make_fire=make_fire)

    builder = af.WorkflowBuilder(
        start_executor=router_agent,
        output_from=[general_data_email, asset_health_email, diagnosis_email, scheduling_setup],
    )
    builder.add_edge(router_agent, extract)
    builder.add_switch_case_edge_group(
        extract,
        [
            af.Case(condition=lambda decision: decision.recurring, target=scheduling_setup),
            af.Case(condition=lambda decision: decision.topic == "asset_health", target=fetch_and_classify),
            af.Default(target=to_original_question),
        ],
    )
    builder.add_edge(to_original_question, general_data_agent)
    builder.add_edge(general_data_agent, general_data_email)

    builder.add_switch_case_edge_group(
        fetch_and_classify,
        [
            af.Case(
                condition=lambda context: any(v.is_abnormal for v in context.verdicts),
                target=diagnosis_prep,
            ),
            af.Default(target=prepare_normal_summary),
        ],
    )
    builder.add_edge(prepare_normal_summary, asset_health_agent)
    builder.add_edge(asset_health_agent, asset_health_email)

    builder.add_edge(diagnosis_prep, diagnosis_agent)
    builder.add_edge(diagnosis_agent, diagnosis_email)

    workflow = builder.build()
    result = await workflow.run(question)
    return result.get_outputs()[0]


async def _run_and_draft(
    question: str,
    decision: RouterDecision,
    *,
    chat_client: af.SupportsChatGetResponse,
    fetch: Callable[[str], FabricResult],
    fetch_readings: Callable[[str], AssetReadings],
    fetch_maintenance_history: Callable[[str], list[MaintenanceRecord]],
    retrieve_guidance: Callable[[str], str],
    web_search: Callable[[str], str],
    email_draft: Callable[[Report], EmailDraft],
) -> Report:
    # a scheduled fire's re-run path: runs only the branch decision already
    # picked, bypassing router_agent/WorkflowBuilder entirely (see the
    # make_fire comment in ask() for why re-routing on fire is unsafe)
    if decision.topic == "asset_health":
        report = await _run_asset_health(
            decision,
            chat_client=chat_client,
            fetch_readings=fetch_readings,
            fetch_maintenance_history=fetch_maintenance_history,
            retrieve_guidance=retrieve_guidance,
            web_search=web_search,
        )
    else:
        report = await _run_general_data(question, chat_client=chat_client, fetch=fetch)
    email_draft(report)
    return report


async def _run_general_data(
    question: str, *, chat_client: af.SupportsChatGetResponse, fetch: Callable[[str], FabricResult]
) -> Report:
    fabric_captured: list[FabricResult] = []
    fabric_tool = make_fetch_fabric_data_tool(fetch, fabric_captured)
    agent = af.Agent(chat_client, GENERAL_DATA_INSTRUCTIONS, name="general_data_answerer", tools=[fabric_tool])
    response = await agent.run(question)
    images = [image for result in fabric_captured for image in result.images]
    return Report(summary=response.text, images=images)


async def _run_asset_health(
    decision: RouterDecision,
    *,
    chat_client: af.SupportsChatGetResponse,
    fetch_readings: Callable[[str], AssetReadings],
    fetch_maintenance_history: Callable[[str], list[MaintenanceRecord]],
    retrieve_guidance: Callable[[str], str],
    web_search: Callable[[str], str],
) -> Report:
    if decision.asset_id is None:
        raise ValueError("asset_health question routed with no asset_id to resolve")
    asset_readings = fetch_readings(decision.asset_id)
    verdicts = compute_verdicts(asset_readings)

    if not any(v.is_abnormal for v in verdicts):
        agent = af.Agent(chat_client, ASSET_HEALTH_INSTRUCTIONS, name="asset_health_summarizer")
        response = await agent.run(format_verdicts_for_summary(verdicts))
        return Report(summary=response.text, verdicts=verdicts)

    context = AssetHealthContext(
        asset_id=asset_readings.asset_id, asset_model=asset_readings.asset_model, verdicts=verdicts
    )
    maintenance_history = fetch_maintenance_history(decision.asset_id)
    diagnosis_agent = af.Agent(
        chat_client,
        DIAGNOSIS_INSTRUCTIONS,
        name="diagnosis",
        tools=[make_kb_tool(retrieve_guidance), make_web_search_tool(web_search, lambda: context)],
        default_options=af.ChatOptions(response_format=DiagnosisOutput),  # type: ignore[arg-type]
    )
    response = await diagnosis_agent.run(format_diagnosis_prompt(verdicts, maintenance_history))
    if not isinstance(response.value, DiagnosisOutput):
        raise RuntimeError(f"diagnosis agent did not return structured DiagnosisOutput, got {type(response.value)!r}")
    diagnosis = to_diagnosis_result(response.value)
    return Report(summary=diagnosis.summary, verdicts=verdicts, diagnosis=diagnosis)
