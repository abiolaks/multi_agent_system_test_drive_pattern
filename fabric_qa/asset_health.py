from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import agent_framework as af

from fabric_qa.classify import Verdict, classify
from fabric_qa.models import AssetReadings, Report
from fabric_qa.router import RouterDecision
from fabric_qa.thresholds import load_thresholds


@dataclass
class AssetHealthContext:
    asset_id: str
    asset_model: str
    verdicts: list[Verdict]


def compute_verdicts(asset_readings: AssetReadings) -> list[Verdict]:
    thresholds = load_thresholds(asset_readings.asset_model)
    return [
        Verdict(
            parameter=reading.parameter,
            value=reading.value,
            health=classify(reading.value, thresholds[reading.parameter]),
        )
        for reading in asset_readings.readings
        if reading.parameter in thresholds
    ]


def format_verdicts_for_summary(verdicts: list[Verdict]) -> str:
    lines = [f"{v.parameter}={v.value} ({v.health})" for v in verdicts]
    return "Summarize these asset-health verdicts: " + "; ".join(lines)


def build_asset_health_report(captured_verdicts: list[list[Verdict]]) -> Callable[[af.AgentExecutorResponse], Report]:
    def build_report(response: af.AgentExecutorResponse) -> Report:
        verdicts = captured_verdicts[0] if captured_verdicts else []
        return Report(summary=response.agent_response.text, verdicts=verdicts)

    return build_report


class FetchAndClassifyExecutor(af.Executor):
    # deterministic - ADR 0002: health verdicts are computed by pure Python
    # (classify(), unchanged from #3), never by the Router or any Agent.
    def __init__(self, fetch_readings: Callable[[str], AssetReadings]) -> None:
        super().__init__(id="fetch_and_classify")
        self._fetch_readings = fetch_readings

    @af.handler(input=RouterDecision, output=AssetHealthContext)
    async def handle(self, decision: RouterDecision, ctx: af.WorkflowContext[AssetHealthContext]) -> None:
        if decision.asset_id is None:
            raise ValueError("asset_health question routed with no asset_id to resolve")
        asset_readings = self._fetch_readings(decision.asset_id)
        verdicts = compute_verdicts(asset_readings)
        await ctx.send_message(
            AssetHealthContext(
                asset_id=asset_readings.asset_id,
                asset_model=asset_readings.asset_model,
                verdicts=verdicts,
            )
        )


class PrepareNormalSummaryExecutor(af.Executor):
    # normal-only branch: no diagnosis needed, just narrate the verdicts.
    # Verdicts are captured into a side-channel (same pattern as #10's image
    # capture) so the final Report can carry them even though only formatted
    # text is sent onward to the Summarize Agent.
    def __init__(self, captured_verdicts: list[list[Verdict]]) -> None:
        super().__init__(id="prepare_normal_summary")
        self._captured = captured_verdicts

    @af.handler(input=AssetHealthContext, output=str)
    async def handle(self, context: AssetHealthContext, ctx: af.WorkflowContext[str]) -> None:
        self._captured.append(context.verdicts)
        await ctx.send_message(format_verdicts_for_summary(context.verdicts))
