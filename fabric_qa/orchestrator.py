from __future__ import annotations

from fabric_qa.classify import Verdict, classify
from fabric_qa.models import Report
from fabric_qa.ports import Ports
from fabric_qa.router import RouterDecision
from fabric_qa.thresholds import load_thresholds


def ask(question: str, ports: Ports) -> Report:
    decision = ports.llm.route(question)
    if decision.topic == "asset_health":
        report = _ask_asset_health(question, decision, ports)
    else:
        report = _ask_general_data(question, ports)
    ports.email.draft(report)
    return report


def _ask_general_data(question: str, ports: Ports) -> Report:
    fabric_result = ports.fabric.fetch(question)
    summary = ports.llm.summarize(question, fabric_result.data)
    return Report(summary=summary, images=list(fabric_result.images))


def _ask_asset_health(question: str, decision: RouterDecision, ports: Ports) -> Report:
    if decision.asset_id is None:
        raise ValueError("asset_health question routed with no asset_id to resolve")
    asset_readings = ports.fabric.fetch_readings(decision.asset_id)
    thresholds = load_thresholds(asset_readings.asset_model)
    verdicts = [
        Verdict(
            parameter=reading.parameter,
            value=reading.value,
            health=classify(reading.value, thresholds[reading.parameter]),
        )
        for reading in asset_readings.readings
        if reading.parameter in thresholds
    ]

    if any(verdict.is_abnormal for verdict in verdicts):
        guidance = ports.knowledge_base.retrieve(asset_readings.asset_model)
        maintenance_history = ports.fabric.fetch_maintenance_history(asset_readings.asset_id)
        diagnosis = ports.llm.diagnose(verdicts, guidance, maintenance_history)
        return Report(summary=diagnosis.summary, verdicts=verdicts, diagnosis=diagnosis)

    summary = ports.llm.summarize(question, verdicts)
    return Report(summary=summary, verdicts=verdicts)
