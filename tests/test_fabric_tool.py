from __future__ import annotations

import unittest

import agent_framework as af

from fabric_qa.fabric_tool import build_general_data_report, make_fetch_fabric_data
from fabric_qa.models import FabricResult


class TestMakeFetchFabricData(unittest.TestCase):
    def test_calls_fetch_and_captures_the_result(self) -> None:
        captured: list[FabricResult] = []
        result = FabricResult(data="revenue rose 12%", images=[b"chart-bytes"])

        def fetch(question: str) -> FabricResult:
            self.assertEqual(question, "how did revenue trend?")
            return result

        fetch_fabric_data = make_fetch_fabric_data(fetch, captured)

        text = fetch_fabric_data("how did revenue trend?")

        self.assertEqual(text, "revenue rose 12%")
        self.assertEqual(captured, [result])

    def test_stringifies_non_string_data(self) -> None:
        captured: list[FabricResult] = []

        def fetch(question: str) -> FabricResult:
            return FabricResult(data={"revenue": [100, 112]})

        fetch_fabric_data = make_fetch_fabric_data(fetch, captured)

        text = fetch_fabric_data("q")

        self.assertEqual(text, "{'revenue': [100, 112]}")

    def test_multiple_calls_each_get_captured(self) -> None:
        captured: list[FabricResult] = []
        results = [FabricResult(data="first"), FabricResult(data="second")]

        def fetch(question: str) -> FabricResult:
            return results.pop(0)

        fetch_fabric_data = make_fetch_fabric_data(fetch, captured)

        fetch_fabric_data("q1")
        fetch_fabric_data("q2")

        self.assertEqual([r.data for r in captured], ["first", "second"])


class TestBuildGeneralDataReport(unittest.TestCase):
    def make_response(self, text: str) -> af.AgentExecutorResponse:
        agent_response = af.AgentResponse(messages=[af.Message("assistant", [text])], response_id="r1")
        return af.AgentExecutorResponse(executor_id="agent", agent_response=agent_response, full_conversation=[])

    def test_report_carries_the_agents_text_as_summary(self) -> None:
        build_report = build_general_data_report(captured=[])

        report = build_report(self.make_response("Revenue rose 12%."))

        self.assertEqual(report.summary, "Revenue rose 12%.")

    def test_images_come_from_captured_fetches_never_from_the_llm(self) -> None:
        captured = [
            FabricResult(data="x", images=[b"img1"]),
            FabricResult(data="y", images=[b"img2"]),
        ]
        build_report = build_general_data_report(captured)

        report = build_report(self.make_response("s"))

        self.assertEqual(report.images, [b"img1", b"img2"])

    def test_no_images_when_the_fetch_tool_was_never_called(self) -> None:
        build_report = build_general_data_report(captured=[])

        report = build_report(self.make_response("s"))

        self.assertEqual(report.images, [])


if __name__ == "__main__":
    unittest.main()
