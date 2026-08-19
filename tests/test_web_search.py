from __future__ import annotations

import unittest

from fabric_qa.fakes import FakeFabricPort, FakeKnowledgeBasePort, FakeLLMPort, FakeWebSearchPort
from fabric_qa.models import AssetReadings, DiagnosisResult, Reading, Recommendation
from fabric_qa.orchestrator import ask
from fabric_qa.router import RouterDecision
from tests.test_ask import make_ports


def make_diagnosis() -> DiagnosisResult:
    return DiagnosisResult(
        summary="s", what_data_shows="d", what_guidance_says="g", combined_finding="c",
        recommendation=Recommendation(fault_signature="f", next_step="n", citation="cite"),
        caveats="cav",
    )


class TestWebSearchPort(unittest.TestCase):
    def test_web_search_port_returns_its_configured_result_for_a_generic_query(self) -> None:
        web_search = FakeWebSearchPort(result="hot section erosion is commonly caused by FOD ingestion")

        result = web_search.search("hot section erosion probable causes")

        self.assertEqual(result, "hot section erosion is commonly caused by FOD ingestion")
        self.assertEqual(web_search.calls, ["hot section erosion probable causes"])


class TestWebSearchWiredIntoDiagnosis(unittest.TestCase):
    def test_diagnosis_branch_incorporates_sanitized_web_context_into_the_recommendation_step(self) -> None:
        readings = AssetReadings(
            asset_id="ENG-001",
            asset_model="CFM56-7B26",
            readings=[Reading(parameter="egt_margin_c", value=14.0)],  # Alarm
        )
        web_search = FakeWebSearchPort(result="hot section erosion is commonly caused by FOD ingestion")
        llm = FakeLLMPort(
            route_response=RouterDecision(topic="asset_health", asset_id="ENG-001"),
            diagnosis_response=make_diagnosis(),
        )
        ports = make_ports(
            llm=llm,
            fabric=FakeFabricPort(readings_result=readings),
            knowledge_base=FakeKnowledgeBasePort(),
            web_search=web_search,
        )

        ask("what is the health status of ENG-001?", ports)

        self.assertEqual(len(llm.diagnose_calls), 1)
        _verdicts, _guidance, _maintenance_history, web_context_passed = llm.diagnose_calls[0]
        self.assertEqual(web_context_passed, "hot section erosion is commonly caused by FOD ingestion")

    def test_normal_only_verdicts_never_invoke_web_search(self) -> None:
        readings = AssetReadings(
            asset_id="ENG-002",
            asset_model="CFM56-7B26",
            readings=[Reading(parameter="egt_margin_c", value=56.0)],  # Normal
        )
        web_search = FakeWebSearchPort()
        ports = make_ports(
            llm=FakeLLMPort(route_response=RouterDecision(topic="asset_health", asset_id="ENG-002")),
            fabric=FakeFabricPort(readings_result=readings),
            web_search=web_search,
        )

        ask("what is the health status of ENG-002?", ports)

        self.assertEqual(web_search.calls, [])

    def test_guardrail_the_asset_id_and_reading_values_never_reach_the_web_search_port(self) -> None:
        readings = AssetReadings(
            asset_id="ENG-003",
            asset_model="GEnx-1B",
            readings=[Reading(parameter="vibration_n2_ips", value=4.9)],  # Alarm
        )
        web_search = FakeWebSearchPort()
        ports = make_ports(
            llm=FakeLLMPort(
                route_response=RouterDecision(topic="asset_health", asset_id="ENG-003"),
                diagnosis_response=make_diagnosis(),
            ),
            fabric=FakeFabricPort(readings_result=readings),
            knowledge_base=FakeKnowledgeBasePort(),
            web_search=web_search,
        )

        # the question itself names the asset - the realistic leak vector
        # this guardrail exists to catch
        ask("what is the health status of ENG-003?", ports)

        self.assertEqual(len(web_search.calls), 1)
        query_sent = web_search.calls[0]
        self.assertNotIn("ENG-003", query_sent)
        self.assertNotIn("4.9", query_sent)


if __name__ == "__main__":
    unittest.main()
