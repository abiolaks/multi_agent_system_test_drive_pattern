from __future__ import annotations

import unittest

import agent_framework as af

from fabric_qa.router_agent import ExtractRouterDecisionExecutor, RouterOutput, to_router_decision


class FakeContext:
    def __init__(self) -> None:
        self.sent: list[object] = []

    async def send_message(self, value: object) -> None:
        self.sent.append(value)


def make_response(output: RouterOutput) -> af.AgentExecutorResponse:
    agent_response = af.AgentResponse(messages=[af.Message("assistant", ["{}"])], response_id="r1", value=output)
    return af.AgentExecutorResponse(
        executor_id="router",
        agent_response=agent_response,  # type: ignore[arg-type]
        full_conversation=[],
    )


class TestToRouterDecision(unittest.TestCase):
    def test_converts_topic_asset_id_recurring_and_interval(self) -> None:
        output = RouterOutput(topic="asset_health", asset_id="ENG-001", recurring=True, interval="weekly")

        decision = to_router_decision(output)

        self.assertEqual(decision.topic, "asset_health")
        self.assertEqual(decision.asset_id, "ENG-001")
        self.assertTrue(decision.recurring)
        self.assertEqual(decision.interval, "weekly")

    def test_defaults_to_one_off_general_data(self) -> None:
        output = RouterOutput(topic="general_data")

        decision = to_router_decision(output)

        self.assertEqual(decision.topic, "general_data")
        self.assertIsNone(decision.asset_id)
        self.assertFalse(decision.recurring)
        self.assertIsNone(decision.interval)


class TestExtractRouterDecisionExecutor(unittest.IsolatedAsyncioTestCase):
    async def test_sends_the_converted_router_decision_onward(self) -> None:
        executor = ExtractRouterDecisionExecutor()
        ctx = FakeContext()
        output = RouterOutput(topic="asset_health", asset_id="ENG-003", recurring=True, interval="daily")

        await executor.handle(make_response(output), ctx)  # type: ignore[arg-type]

        self.assertEqual(len(ctx.sent), 1)
        decision = ctx.sent[0]
        self.assertEqual(decision.topic, "asset_health")  # type: ignore[union-attr]
        self.assertEqual(decision.asset_id, "ENG-003")  # type: ignore[union-attr]

    async def test_raises_a_clear_error_if_the_agent_did_not_return_structured_output(self) -> None:
        agent_response = af.AgentResponse(messages=[af.Message("assistant", ["not structured"])], response_id="r1")
        response = af.AgentExecutorResponse(executor_id="router", agent_response=agent_response, full_conversation=[])
        executor = ExtractRouterDecisionExecutor()

        with self.assertRaises(RuntimeError):
            await executor.handle(response, FakeContext())  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
