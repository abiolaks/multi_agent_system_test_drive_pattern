from __future__ import annotations

from typing import Callable

import agent_framework as af

from fabric_qa.models import EmailDraft, Report


class DraftEmailExecutor(af.Executor):
    def __init__(
        self,
        draft: Callable[[Report], EmailDraft],
        build_report: Callable[[af.AgentExecutorResponse], Report],
        *,
        id: str = "draft_email",
    ) -> None:
        super().__init__(id=id)
        self._draft = draft
        self._build_report = build_report

    @af.handler(input=af.AgentExecutorResponse, workflow_output=Report)
    async def handle(self, response: af.AgentExecutorResponse, ctx: af.WorkflowContext[None, Report]) -> None:
        report = self._build_report(response)
        self._draft(report)
        await ctx.yield_output(report)
