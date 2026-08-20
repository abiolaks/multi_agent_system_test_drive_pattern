from __future__ import annotations

from typing import Callable

import agent_framework as af

from fabric_qa.models import EmailDraft, FabricResult, Report


class DraftEmailExecutor(af.Executor):
    # images never pass through the LLM's responsibility - they're pulled
    # straight from the captured tool results, never described in text
    def __init__(
        self,
        draft: Callable[[Report], EmailDraft],
        captured_fabric_results: list[FabricResult],
    ) -> None:
        super().__init__(id="draft_email")
        self._draft = draft
        self._captured = captured_fabric_results

    @af.handler(input=af.AgentExecutorResponse, workflow_output=Report)
    async def handle(self, response: af.AgentExecutorResponse, ctx: af.WorkflowContext[None, Report]) -> None:
        images = [image for result in self._captured for image in result.images]
        report = Report(summary=response.agent_response.text, images=images)
        self._draft(report)
        await ctx.yield_output(report)
