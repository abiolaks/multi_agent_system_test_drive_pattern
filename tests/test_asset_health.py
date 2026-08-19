from __future__ import annotations

import unittest

from fabric_qa.classify import Verdict
from fabric_qa.fakes import FakeFabricPort, FakeKnowledgeBasePort, FakeLLMPort
from fabric_qa.models import AssetReadings, DiagnosisResult, MaintenanceRecord, Reading, Recommendation
from fabric_qa.orchestrator import ask
from fabric_qa.router import RouterDecision
from tests.test_ask import make_ports


class TestAssetHealthFlow(unittest.TestCase):
    def test_asset_health_question_returns_report_with_per_reading_verdicts(self) -> None:
        readings = AssetReadings(
            asset_id="ENG-001",
            asset_model="CFM56-7B26",
            readings=[
                Reading(parameter="egt_margin_c", value=14.0),  # Alarm
                Reading(parameter="oil_pressure_psi", value=58.0),  # Normal
            ],
        )
        # An Alarm verdict is present, so this goes through the diagnosis
        # branch (issue #4) - a minimal diagnosis_response is enough since
        # this test only asserts on the verdicts, not the diagnosis content.
        diagnosis = DiagnosisResult(
            summary="s", what_data_shows="d", what_guidance_says="g",
            combined_finding="c",
            recommendation=Recommendation(fault_signature="f", next_step="n", citation="cite"),
            caveats="caveats",
        )
        ports = make_ports(
            llm=FakeLLMPort(
                route_response=RouterDecision(topic="asset_health", asset_id="ENG-001"),
                diagnosis_response=diagnosis,
            ),
            fabric=FakeFabricPort(readings_result=readings),
        )

        report = ask("what is the health status of ENG-001?", ports)

        self.assertEqual(
            report.verdicts,
            [
                Verdict(parameter="egt_margin_c", value=14.0, health="Alarm"),
                Verdict(parameter="oil_pressure_psi", value=58.0, health="Normal"),
            ],
        )

    def test_asset_health_flow_uses_fetch_readings_not_the_general_fetch(self) -> None:
        readings = AssetReadings(asset_id="ENG-001", asset_model="CFM56-7B26", readings=[])
        fabric = FakeFabricPort(readings_result=readings)
        ports = make_ports(
            llm=FakeLLMPort(route_response=RouterDecision(topic="asset_health", asset_id="ENG-001")),
            fabric=fabric,
        )

        ask("what is the health status of ENG-001?", ports)

        self.assertEqual(fabric.calls, [])
        self.assertEqual(fabric.readings_calls, ["ENG-001"])

    def test_asset_health_without_an_asset_id_raises_a_clear_error(self) -> None:
        ports = make_ports(
            llm=FakeLLMPort(route_response=RouterDecision(topic="asset_health", asset_id=None)),
        )

        with self.assertRaises(ValueError):
            ask("what is the health status of my assets?", ports)

    def test_readings_with_no_threshold_entry_are_excluded_not_crashed_on(self) -> None:
        readings = AssetReadings(
            asset_id="ENG-001",
            asset_model="CFM56-7B26",
            readings=[
                Reading(parameter="egt_margin_c", value=56.0),  # Normal, has a threshold
                Reading(parameter="fuel_flow_pph", value=2500.0),  # no threshold entry for this
            ],
        )
        ports = make_ports(
            llm=FakeLLMPort(route_response=RouterDecision(topic="asset_health", asset_id="ENG-001")),
            fabric=FakeFabricPort(readings_result=readings),
        )

        report = ask("what is the health status of ENG-001?", ports)

        self.assertEqual(
            report.verdicts,
            [Verdict(parameter="egt_margin_c", value=56.0, health="Normal")],
        )

    def test_llm_summarizes_the_computed_verdicts_not_the_raw_readings(self) -> None:
        # Normal-only, so this stays on the simple summarize() path (issue
        # #3) rather than the diagnosis path (issue #4) added above.
        readings = AssetReadings(
            asset_id="ENG-001",
            asset_model="CFM56-7B26",
            readings=[Reading(parameter="egt_margin_c", value=56.0)],
        )
        llm = FakeLLMPort(route_response=RouterDecision(topic="asset_health", asset_id="ENG-001"))
        ports = make_ports(llm=llm, fabric=FakeFabricPort(readings_result=readings))

        report = ask("what is the health status of ENG-001?", ports)

        self.assertEqual(len(llm.calls), 1)
        _question, data_passed_to_llm = llm.calls[0]
        self.assertEqual(data_passed_to_llm, report.verdicts)

    def test_fake_fabric_port_fails_fast_when_readings_result_not_configured(self) -> None:
        fabric = FakeFabricPort()  # no readings_result given

        with self.assertRaises(ValueError):
            fabric.fetch_readings("ENG-001")


class TestAssetHealthDiagnosis(unittest.TestCase):
    def test_abnormal_verdict_retrieves_guidance_and_produces_full_skeleton_with_citation(self) -> None:
        readings = AssetReadings(
            asset_id="ENG-001",
            asset_model="CFM56-7B26",
            readings=[Reading(parameter="egt_margin_c", value=14.0)],  # Alarm
        )
        diagnosis = DiagnosisResult(
            summary="ENG-001 EGT margin has entered alarm range.",
            what_data_shows="EGT margin is 14.0C, below the 20C alarm floor.",
            what_guidance_says="CFM56-7B26 FIM 72-31: margin erosion with all "
            "other parameters nominal indicates hot-section wear.",
            combined_finding="Hot-section erosion is the probable cause.",
            recommendation=Recommendation(
                fault_signature="Hot-section erosion",
                next_step="Borescope inspection within 14 days per task 72-31-00.",
                citation="CFM56-7B26 FIM Section 72-31",
            ),
            caveats="Verify compressor wash history before confirming hot-section wear.",
        )
        knowledge_base = FakeKnowledgeBasePort(guidance="<CFM56-7B26 FIM text>")
        ports = make_ports(
            llm=FakeLLMPort(
                route_response=RouterDecision(topic="asset_health", asset_id="ENG-001"),
                diagnosis_response=diagnosis,
            ),
            fabric=FakeFabricPort(readings_result=readings),
            knowledge_base=knowledge_base,
        )

        report = ask("what is the health status of ENG-001?", ports)

        self.assertEqual(knowledge_base.calls, ["CFM56-7B26"])
        self.assertEqual(report.summary, diagnosis.summary)
        self.assertEqual(report.diagnosis, diagnosis)
        assert report.diagnosis is not None
        self.assertEqual(report.diagnosis.recommendation.citation, "CFM56-7B26 FIM Section 72-31")

    def test_all_normal_verdicts_skip_diagnosis_entirely(self) -> None:
        readings = AssetReadings(
            asset_id="ENG-002",
            asset_model="CFM56-7B26",
            readings=[Reading(parameter="egt_margin_c", value=56.0)],  # Normal
        )
        knowledge_base = FakeKnowledgeBasePort()
        llm = FakeLLMPort(route_response=RouterDecision(topic="asset_health", asset_id="ENG-002"))
        fabric = FakeFabricPort(readings_result=readings)
        ports = make_ports(
            llm=llm,
            fabric=fabric,
            knowledge_base=knowledge_base,
        )

        report = ask("what is the health status of ENG-002?", ports)

        self.assertEqual(knowledge_base.calls, [])
        self.assertEqual(llm.diagnose_calls, [])
        self.assertEqual(fabric.maintenance_history_calls, [])
        self.assertIsNone(report.diagnosis)

    def test_recurrence_after_prior_balance_is_escalated_not_re_recommended(self) -> None:
        readings = AssetReadings(
            asset_id="ENG-003",
            asset_model="GEnx-1B",
            readings=[Reading(parameter="vibration_n2_ips", value=4.9)],  # Alarm
        )
        prior_balance = [
            MaintenanceRecord(
                work_order_id="WO-1003",
                date="2026-03-08",
                finding="Fan blade balancing performed after N2 vibration advisory",
                parts_replaced="balance weights",
            ),
        ]
        escalated_diagnosis = DiagnosisResult(
            summary="ENG-003 N2 vibration has recurred and is now in alarm range.",
            what_data_shows="N2 vibration is 4.9 IPS, above the 4.0 IPS alarm ceiling.",
            what_guidance_says="GEnx-1B FIM 72-61: vibration recurring after a prior "
            "trim balance is a mechanical-fault signature (bearing wear), not a "
            "re-balanceable imbalance.",
            combined_finding="Recurrence after WO-1003's trim balance indicates "
            "bearing wear rather than blade imbalance.",
            recommendation=Recommendation(
                fault_signature="Bearing wear (recurrence after balance)",
                next_step="Remove and inspect fan module bearings per task 72-61-20.",
                citation="GEnx-1B FIM Section 72-61",
            ),
            caveats="Cross-check against the redundant accelerometer before condemning the engine.",
        )
        llm = FakeLLMPort(
            route_response=RouterDecision(topic="asset_health", asset_id="ENG-003"),
            diagnosis_response=escalated_diagnosis,
        )
        ports = make_ports(
            llm=llm,
            fabric=FakeFabricPort(readings_result=readings, maintenance_history_result=prior_balance),
            knowledge_base=FakeKnowledgeBasePort(guidance="<GEnx-1B FIM text>"),
        )

        report = ask("what is the health status of ENG-003?", ports)

        # the orchestrator must actually hand the prior maintenance history
        # to the LLM - without it, no diagnosis step could ever distinguish
        # first-occurrence from recurrence
        self.assertEqual(len(llm.diagnose_calls), 1)
        _verdicts, _guidance, maintenance_history_passed, _web_context = llm.diagnose_calls[0]
        self.assertEqual(maintenance_history_passed, prior_balance)

        assert report.diagnosis is not None
        self.assertNotIn("trim balance", report.diagnosis.recommendation.next_step.lower())
        self.assertEqual(report.diagnosis.recommendation.fault_signature, "Bearing wear (recurrence after balance)")

    def test_first_occurrence_with_no_prior_balance_gets_the_ordinary_recommendation(self) -> None:
        readings = AssetReadings(
            asset_id="ENG-003",
            asset_model="GEnx-1B",
            readings=[Reading(parameter="vibration_n2_ips", value=2.3)],  # Advisory
        )
        first_occurrence_diagnosis = DiagnosisResult(
            summary="ENG-003 N2 vibration has crossed the advisory threshold.",
            what_data_shows="N2 vibration is 2.3 IPS, above the 2.0 IPS advisory ceiling.",
            what_guidance_says="GEnx-1B FIM 72-61: first-occurrence advisory vibration "
            "with no prior balance on record indicates blade imbalance.",
            combined_finding="No prior balance on record; imbalance is the likely cause.",
            recommendation=Recommendation(
                fault_signature="Fan/LPC blade imbalance",
                next_step="Perform a fan trim balance per task 72-61-00.",
                citation="GEnx-1B FIM Section 72-61",
            ),
            caveats="Cross-check against the redundant accelerometer.",
        )
        llm = FakeLLMPort(
            route_response=RouterDecision(topic="asset_health", asset_id="ENG-003"),
            diagnosis_response=first_occurrence_diagnosis,
        )
        ports = make_ports(
            llm=llm,
            fabric=FakeFabricPort(readings_result=readings, maintenance_history_result=[]),
            knowledge_base=FakeKnowledgeBasePort(guidance="<GEnx-1B FIM text>"),
        )

        report = ask("what is the health status of ENG-003?", ports)

        _verdicts, _guidance, maintenance_history_passed, _web_context = llm.diagnose_calls[0]
        self.assertEqual(maintenance_history_passed, [])
        assert report.diagnosis is not None
        self.assertIn("trim balance", report.diagnosis.recommendation.next_step.lower())

    def test_maintenance_history_is_fetched_using_the_resolved_asset_id_not_the_raw_router_one(self) -> None:
        # Simulates a Fabric adapter that resolves an alias/partial id the
        # router passed in to a different canonical asset_id.
        readings = AssetReadings(
            asset_id="ENG-003-CANONICAL",
            asset_model="GEnx-1B",
            readings=[Reading(parameter="vibration_n2_ips", value=4.9)],  # Alarm
        )
        diagnosis = DiagnosisResult(
            summary="s", what_data_shows="d", what_guidance_says="g", combined_finding="c",
            recommendation=Recommendation(fault_signature="f", next_step="n", citation="cite"),
            caveats="cav",
        )
        fabric = FakeFabricPort(readings_result=readings, maintenance_history_result=[])
        ports = make_ports(
            llm=FakeLLMPort(
                route_response=RouterDecision(topic="asset_health", asset_id="ENG-003-ALIAS"),
                diagnosis_response=diagnosis,
            ),
            fabric=fabric,
            knowledge_base=FakeKnowledgeBasePort(),
        )

        ask("what is the health status of ENG-003?", ports)

        self.assertEqual(fabric.maintenance_history_calls, ["ENG-003-CANONICAL"])


if __name__ == "__main__":
    unittest.main()
