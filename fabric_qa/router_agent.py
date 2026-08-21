from __future__ import annotations

from typing import Literal

import agent_framework as af
from pydantic import BaseModel

from fabric_qa.router import RouterDecision

ROUTER_INSTRUCTIONS = (
    "Classify the user's question. topic is 'asset_health' if it asks about "
    "the health, condition, or readings of a specific engine/asset (extract "
    "its asset_id, e.g. ENG-001, into asset_id), otherwise 'general_data'. "
    "Set recurring=true and interval to a short phrase (e.g. 'weekly', "
    "'daily') if the user asks for this on a recurring basis; otherwise "
    "recurring=false and interval=null."
)


class RouterOutput(BaseModel):
    topic: Literal["asset_health", "general_data"]
    asset_id: str | None = None
    recurring: bool = False
    interval: str | None = None


def to_router_decision(output: RouterOutput) -> RouterDecision:
    return RouterDecision(
        topic=output.topic,
        asset_id=output.asset_id,
        recurring=output.recurring,
        interval=output.interval,
    )


class ExtractRouterDecisionExecutor(af.Executor):
    def __init__(self) -> None:
        super().__init__(id="extract_router_decision")

    @af.handler(input=af.AgentExecutorResponse, output=RouterDecision)
    async def handle(self, response: af.AgentExecutorResponse, ctx: af.WorkflowContext[RouterDecision]) -> None:
        output = response.agent_response.value
        if not isinstance(output, RouterOutput):
            raise RuntimeError(f"router agent did not return structured RouterOutput, got {type(output)!r}")
        await ctx.send_message(to_router_decision(output))
