from __future__ import annotations

from typing import Callable

import agent_framework as af

from fabric_qa.models import Report
from fabric_qa.router import RouterDecision


class SchedulingSetupExecutor(af.Executor):
    # ADR 0003: in-process scheduler for the POV. Registration happens here,
    # at setup time - a recurring asset_health request with no resolved
    # asset_id must fail here, not on fire, since a fire has no caller to
    # surface a crash to. `fire` re-runs only the already-classified branch
    # (see workflow.py's _run_and_draft) rather than the full ask() flow,
    # so a fire never re-enters the router and can't register a duplicate
    # schedule on top of itself.
    def __init__(
        self,
        schedule: Callable[[str, Callable[[], None]], None],
        make_fire: Callable[[RouterDecision], Callable[[], None]],
        *,
        id: str = "scheduling_setup",
    ) -> None:
        super().__init__(id=id)
        self._schedule = schedule
        self._make_fire = make_fire

    @af.handler(input=RouterDecision, workflow_output=Report)
    async def handle(self, decision: RouterDecision, ctx: af.WorkflowContext[None, Report]) -> None:
        if decision.topic == "asset_health" and decision.asset_id is None:
            raise ValueError("asset_health question routed with no asset_id to resolve")
        if decision.interval is None:
            await ctx.yield_output(Report(summary="What day and time would you like this scheduled report sent?"))
            return
        self._schedule(decision.interval, self._make_fire(decision))
        await ctx.yield_output(Report(summary=f"Scheduled: this report will run {decision.interval}."))
