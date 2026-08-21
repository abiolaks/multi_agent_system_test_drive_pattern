from __future__ import annotations

from typing import Callable

import agent_framework as af
from pydantic import BaseModel

from fabric_qa.asset_health import AssetHealthContext
from fabric_qa.classify import Verdict
from fabric_qa.models import DiagnosisResult, MaintenanceRecord, Recommendation, Report
from fabric_qa.sanitize import sanitize_query

DIAGNOSIS_INSTRUCTIONS = (
    "You diagnose aircraft engine asset-health issues for abnormal readings. "
    "Use the retrieve_guidance tool to consult the asset model's Fault "
    "Isolation Manual, and web_search if you need general context. If the "
    "maintenance history shows a prior corrective action for the same issue "
    "that has recurred, escalate rather than repeating that action. Produce: "
    "summary, what_data_shows, what_guidance_says, combined_finding, a "
    "recommendation (fault_signature, next_step, citation to the guidance "
    "section), and caveats."
)


class RecommendationOutput(BaseModel):
    fault_signature: str
    next_step: str
    citation: str


class DiagnosisOutput(BaseModel):
    summary: str
    what_data_shows: str
    what_guidance_says: str
    combined_finding: str
    recommendation: RecommendationOutput
    caveats: str


def to_diagnosis_result(output: DiagnosisOutput) -> DiagnosisResult:
    return DiagnosisResult(
        summary=output.summary,
        what_data_shows=output.what_data_shows,
        what_guidance_says=output.what_guidance_says,
        combined_finding=output.combined_finding,
        recommendation=Recommendation(
            fault_signature=output.recommendation.fault_signature,
            next_step=output.recommendation.next_step,
            citation=output.recommendation.citation,
        ),
        caveats=output.caveats,
    )


def format_diagnosis_prompt(verdicts: list[Verdict], maintenance_history: list[MaintenanceRecord]) -> str:
    verdict_lines = [f"{v.parameter}={v.value} ({v.health})" for v in verdicts]
    history_lines = [f"{m.work_order_id} ({m.date}): {m.finding}" for m in maintenance_history]
    history_text = "; ".join(history_lines) if history_lines else "none on record"
    return f"Abnormal verdicts: {'; '.join(verdict_lines)}. Maintenance history: {history_text}."


def make_kb_tool(retrieve: Callable[[str], str]) -> af.FunctionTool:
    def retrieve_guidance(asset_model: str) -> str:
        return retrieve(asset_model)

    return af.tool(
        retrieve_guidance,
        name="retrieve_guidance",
        description="Retrieve the Guidance (Fault Isolation Manual) for an Asset Model.",
    )


def make_web_search_tool(
    search: Callable[[str], str],
    context_provider: Callable[[], AssetHealthContext],
) -> af.FunctionTool:
    # ADR 0006 guardrail: sanitize_query runs inside the tool itself, before
    # any real search call, regardless of what query the Agent asks for.
    # asset_id/verdicts are resolved lazily via context_provider because
    # they aren't known until fetch_and_classify/diagnosis_prep actually
    # run - never derived from anything the Agent itself supplies.
    def web_search(query: str) -> str:
        context = context_provider()
        sanitized = sanitize_query(query, asset_id=context.asset_id, verdicts=context.verdicts)
        return search(sanitized)

    return af.tool(
        web_search,
        name="web_search",
        description="Search the web for general context. Never include asset names or readings in the query.",
    )


def build_diagnosis_report(
    captured_context: list[AssetHealthContext],
) -> Callable[[af.AgentExecutorResponse], Report]:
    def build_report(response: af.AgentExecutorResponse) -> Report:
        output = response.agent_response.value
        if not isinstance(output, DiagnosisOutput):
            raise RuntimeError(f"diagnosis agent did not return structured DiagnosisOutput, got {type(output)!r}")
        diagnosis = to_diagnosis_result(output)
        verdicts = captured_context[0].verdicts if captured_context else []
        return Report(summary=diagnosis.summary, verdicts=verdicts, diagnosis=diagnosis)

    return build_report


class DiagnosisPrepExecutor(af.Executor):
    # deterministic: maintenance history is asset_id-scoped, not a
    # natural-language lookup, so this is a pre-fetch, not an agent tool
    # (per ADR 0010). Context is captured into a side-channel so the final
    # Report can carry verdicts even though only formatted text is sent to
    # the Diagnosis Agent.
    def __init__(
        self,
        fetch_maintenance_history: Callable[[str], list[MaintenanceRecord]],
        captured_context: list[AssetHealthContext],
    ) -> None:
        super().__init__(id="diagnosis_prep")
        self._fetch_maintenance_history = fetch_maintenance_history
        self._captured = captured_context

    @af.handler(input=AssetHealthContext, output=str)
    async def handle(self, context: AssetHealthContext, ctx: af.WorkflowContext[str]) -> None:
        self._captured.append(context)
        maintenance_history = self._fetch_maintenance_history(context.asset_id)
        await ctx.send_message(format_diagnosis_prompt(context.verdicts, maintenance_history))
