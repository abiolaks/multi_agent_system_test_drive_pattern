from __future__ import annotations

import unittest

from fabric_qa.classify import Verdict
from fabric_qa.fakes import FakeFabricPort, FakeLLMPort
from fabric_qa.models import AssetReadings, Reading
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
        ports = make_ports(
            llm=FakeLLMPort(route_response=RouterDecision(topic="asset_health", asset_id="ENG-001")),
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
        readings = AssetReadings(
            asset_id="ENG-001",
            asset_model="CFM56-7B26",
            readings=[Reading(parameter="egt_margin_c", value=14.0)],
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


if __name__ == "__main__":
    unittest.main()
