from __future__ import annotations

import unittest

import agent_framework as af

from fabric_qa.asset_health import AssetHealthContext
from fabric_qa.classify import Verdict
from fabric_qa.diagnosis import (
    DiagnosisOutput,
    DiagnosisPrepExecutor,
    RecommendationOutput,
    build_diagnosis_report,
    format_diagnosis_prompt,
    make_kb_tool,
    make_web_search_tool,
    to_diagnosis_result,
)
from fabric_qa.models import MaintenanceRecord


class FakeContext:
    def __init__(self) -> None:
        self.sent: list[object] = []

    async def send_message(self, value: object) -> None:
        self.sent.append(value)


def make_diagnosis_output(
    fault_signature: str = "f", next_step: str = "n", citation: str = "cite"
) -> DiagnosisOutput:
    return DiagnosisOutput(
        summary="s",
        what_data_shows="d",
        what_guidance_says="g",
        combined_finding="c",
        recommendation=RecommendationOutput(fault_signature=fault_signature, next_step=next_step, citation=citation),
        caveats="cav",
    )


class TestToDiagnosisResult(unittest.TestCase):
    def test_converts_every_field_including_the_nested_recommendation(self) -> None:
        output = make_diagnosis_output(fault_signature="Hot-section erosion", next_step="borescope", citation="FIM 72-31")

        result = to_diagnosis_result(output)

        self.assertEqual(result.summary, "s")
        self.assertEqual(result.what_data_shows, "d")
        self.assertEqual(result.what_guidance_says, "g")
        self.assertEqual(result.combined_finding, "c")
        self.assertEqual(result.caveats, "cav")
        self.assertEqual(result.recommendation.fault_signature, "Hot-section erosion")
        self.assertEqual(result.recommendation.next_step, "borescope")
        self.assertEqual(result.recommendation.citation, "FIM 72-31")


class TestFormatDiagnosisPrompt(unittest.TestCase):
    def test_includes_verdicts_and_maintenance_history(self) -> None:
        verdicts = [Verdict(parameter="egt_margin_c", value=14.0, health="Alarm")]
        history = [MaintenanceRecord(work_order_id="WO-1", date="2026-01-01", finding="prior fix", parts_replaced="")]

        prompt = format_diagnosis_prompt(verdicts, history)

        self.assertIn("egt_margin_c=14.0", prompt)
        self.assertIn("Alarm", prompt)
        self.assertIn("WO-1", prompt)
        self.assertIn("prior fix", prompt)

    def test_says_none_on_record_when_there_is_no_prior_history(self) -> None:
        prompt = format_diagnosis_prompt([], [])

        self.assertIn("none on record", prompt)


class TestMakeKbTool(unittest.TestCase):
    def test_calls_retrieve_with_the_asset_model_the_agent_passes(self) -> None:
        calls: list[str] = []

        def retrieve(asset_model: str) -> str:
            calls.append(asset_model)
            return "guidance text"

        tool = make_kb_tool(retrieve)
        assert tool.func is not None
        result = tool.func("CFM56-7B26")

        self.assertEqual(result, "guidance text")
        self.assertEqual(calls, ["CFM56-7B26"])


class TestMakeWebSearchTool(unittest.TestCase):
    def test_sanitizes_the_query_before_the_real_search_call(self) -> None:
        # non-vacuous guardrail: the raw query below contains the asset id
        # and reading value verbatim - if the internal sanitize_query() call
        # were ever removed, this assertion would fail because the raw
        # (unsanitized) string would reach `search` unchanged
        search_calls: list[str] = []

        def search(query: str) -> str:
            search_calls.append(query)
            return "search result"

        context = AssetHealthContext(
            asset_id="ENG-003",
            asset_model="GEnx-1B",
            verdicts=[Verdict(parameter="vibration_n2_ips", value=4.9, health="Alarm")],
        )
        tool = make_web_search_tool(search, lambda: context)

        assert tool.func is not None
        tool.func("ENG-003 vibration_n2_ips 4.9 probable causes")

        self.assertEqual(len(search_calls), 1)
        self.assertNotIn("ENG-003", search_calls[0])
        self.assertNotIn("4.9", search_calls[0])

    def test_resolves_context_lazily_at_call_time_not_construction_time(self) -> None:
        # the real asset_id/verdicts aren't known when the tool is built
        # (before the workflow runs) - only once fetch_and_classify actually
        # executes, so the provider must be called lazily, not eagerly
        contexts: list[AssetHealthContext] = []
        tool = make_web_search_tool(lambda q: "r", lambda: contexts[0])

        contexts.append(AssetHealthContext(asset_id="ENG-001", asset_model="CFM56-7B26", verdicts=[]))
        assert tool.func is not None
        result = tool.func("some query")

        self.assertEqual(result, "r")


class TestBuildDiagnosisReport(unittest.TestCase):
    def make_response(self, value: DiagnosisOutput | None) -> af.AgentExecutorResponse:
        agent_response = af.AgentResponse(messages=[af.Message("assistant", ["{}"])], response_id="r1", value=value)
        return af.AgentExecutorResponse(
            executor_id="diagnosis", agent_response=agent_response, full_conversation=[]  # type: ignore[arg-type]
        )

    def test_report_carries_the_diagnosis_and_the_captured_verdicts(self) -> None:
        verdicts = [Verdict(parameter="egt_margin_c", value=14.0, health="Alarm")]
        context = AssetHealthContext(asset_id="ENG-001", asset_model="CFM56-7B26", verdicts=verdicts)
        output = make_diagnosis_output()
        build_report = build_diagnosis_report([context])

        report = build_report(self.make_response(output))

        self.assertEqual(report.summary, "s")
        self.assertEqual(report.verdicts, verdicts)
        assert report.diagnosis is not None
        self.assertEqual(report.diagnosis.recommendation.fault_signature, "f")

    def test_raises_a_clear_error_when_the_agent_did_not_return_structured_output(self) -> None:
        build_report = build_diagnosis_report([])

        with self.assertRaises(RuntimeError):
            build_report(self.make_response(None))


class TestDiagnosisPrepExecutor(unittest.IsolatedAsyncioTestCase):
    async def test_captures_context_fetches_history_by_the_contexts_asset_id_and_sends_a_prompt(self) -> None:
        history_calls: list[str] = []
        history = [MaintenanceRecord(work_order_id="WO-1003", date="2026-03-08", finding="fan trim balance", parts_replaced="")]

        def fetch_maintenance_history(asset_id: str) -> list[MaintenanceRecord]:
            history_calls.append(asset_id)
            return history

        verdicts = [Verdict(parameter="vibration_n2_ips", value=4.9, health="Alarm")]
        context = AssetHealthContext(asset_id="ENG-003", asset_model="GEnx-1B", verdicts=verdicts)
        captured: list[AssetHealthContext] = []
        executor = DiagnosisPrepExecutor(fetch_maintenance_history, captured)
        ctx = FakeContext()

        await executor.handle(context, ctx)  # type: ignore[arg-type]

        self.assertEqual(history_calls, ["ENG-003"])
        self.assertEqual(captured, [context])
        self.assertEqual(len(ctx.sent), 1)
        self.assertIn("WO-1003", ctx.sent[0])  # type: ignore[operator]
        self.assertIn("fan trim balance", ctx.sent[0])  # type: ignore[operator]


if __name__ == "__main__":
    unittest.main()
