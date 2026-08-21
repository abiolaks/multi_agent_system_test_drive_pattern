from __future__ import annotations

import unittest

import agent_framework as af

from fabric_qa.asset_health import FetchAndClassifyExecutor, build_asset_health_report, compute_verdicts
from fabric_qa.classify import Verdict
from fabric_qa.models import AssetReadings, Reading
from fabric_qa.router import RouterDecision


class FakeContext:
    def __init__(self) -> None:
        self.sent: list[object] = []

    async def send_message(self, value: object) -> None:
        self.sent.append(value)


class TestComputeVerdicts(unittest.TestCase):
    def test_computes_verdicts_against_real_thresholds_and_excludes_unknown_parameters(self) -> None:
        readings = AssetReadings(
            asset_id="ENG-001",
            asset_model="CFM56-7B26",
            readings=[
                Reading(parameter="egt_margin_c", value=14.0),  # Alarm
                Reading(parameter="fuel_flow_pph", value=2500.0),  # no threshold entry
            ],
        )

        verdicts = compute_verdicts(readings)

        self.assertEqual(verdicts, [Verdict(parameter="egt_margin_c", value=14.0, health="Alarm")])


class TestFetchAndClassifyExecutor(unittest.IsolatedAsyncioTestCase):
    async def test_fetches_readings_and_sends_a_formatted_summary_prompt_onward(self) -> None:
        readings = AssetReadings(
            asset_id="ENG-001",
            asset_model="CFM56-7B26",
            readings=[Reading(parameter="egt_margin_c", value=14.0)],
        )
        captured: list[list[Verdict]] = []
        executor = FetchAndClassifyExecutor(lambda asset_id: readings, captured)
        ctx = FakeContext()

        await executor.handle(RouterDecision(topic="asset_health", asset_id="ENG-001"), ctx)  # type: ignore[arg-type]

        self.assertEqual(captured, [[Verdict(parameter="egt_margin_c", value=14.0, health="Alarm")]])
        self.assertEqual(len(ctx.sent), 1)
        self.assertIn("egt_margin_c", ctx.sent[0])  # type: ignore[operator]

    async def test_raises_a_clear_error_when_no_asset_id_was_resolved(self) -> None:
        executor = FetchAndClassifyExecutor(lambda asset_id: (_ for _ in ()).throw(AssertionError()), [])

        with self.assertRaises(ValueError):
            await executor.handle(RouterDecision(topic="asset_health", asset_id=None), FakeContext())  # type: ignore[arg-type]


class TestBuildAssetHealthReport(unittest.TestCase):
    def make_response(self, text: str) -> af.AgentExecutorResponse:
        agent_response = af.AgentResponse(messages=[af.Message("assistant", [text])], response_id="r1")
        return af.AgentExecutorResponse(executor_id="agent", agent_response=agent_response, full_conversation=[])

    def test_report_carries_both_the_narration_and_the_captured_verdicts(self) -> None:
        verdicts = [Verdict(parameter="egt_margin_c", value=14.0, health="Alarm")]
        build_report = build_asset_health_report([verdicts])

        report = build_report(self.make_response("EGT margin is in alarm range."))

        self.assertEqual(report.summary, "EGT margin is in alarm range.")
        self.assertEqual(report.verdicts, verdicts)


if __name__ == "__main__":
    unittest.main()
