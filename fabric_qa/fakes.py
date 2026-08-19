from __future__ import annotations

from typing import Any, Callable

from fabric_qa.classify import Verdict
from fabric_qa.models import AssetReadings, DiagnosisResult, EmailDraft, FabricResult, MaintenanceRecord, Report
from fabric_qa.router import RouterDecision


class FakeLLMPort:
    def __init__(
        self,
        response: str = "fake summary",
        route_response: RouterDecision | None = None,
        diagnosis_response: DiagnosisResult | None = None,
    ) -> None:
        self._response = response
        self._route_response = route_response if route_response is not None else RouterDecision(topic="general_data")
        self._diagnosis_response = diagnosis_response
        self.calls: list[tuple[str, Any]] = []
        self.route_calls: list[str] = []
        self.diagnose_calls: list[tuple[list[Verdict], str, list[MaintenanceRecord]]] = []

    def summarize(self, question: str, data: Any) -> str:
        self.calls.append((question, data))
        return self._response

    def route(self, question: str) -> RouterDecision:
        self.route_calls.append(question)
        return self._route_response

    def diagnose(
        self,
        verdicts: list[Verdict],
        guidance: str,
        maintenance_history: list[MaintenanceRecord],
    ) -> DiagnosisResult:
        self.diagnose_calls.append((verdicts, guidance, maintenance_history))
        if self._diagnosis_response is None:
            raise ValueError(
                "FakeLLMPort has no diagnosis_response configured; "
                "pass diagnosis_response=DiagnosisResult(...) for diagnosis tests"
            )
        return self._diagnosis_response


class FakeFabricPort:
    def __init__(
        self,
        result: FabricResult | None = None,
        readings_result: AssetReadings | None = None,
        maintenance_history_result: list[MaintenanceRecord] | None = None,
    ) -> None:
        self._result = result if result is not None else FabricResult(data={}, images=[])
        self._readings_result = readings_result
        self._maintenance_history_result = maintenance_history_result if maintenance_history_result is not None else []
        self.calls: list[str] = []
        self.readings_calls: list[str] = []
        self.maintenance_history_calls: list[str] = []

    def fetch(self, question: str) -> FabricResult:
        self.calls.append(question)
        return self._result

    def fetch_readings(self, asset_id: str) -> AssetReadings:
        self.readings_calls.append(asset_id)
        if self._readings_result is None:
            raise ValueError(
                "FakeFabricPort has no readings_result configured; "
                "pass readings_result=AssetReadings(...) for asset-health tests"
            )
        return self._readings_result

    def fetch_maintenance_history(self, asset_id: str) -> list[MaintenanceRecord]:
        self.maintenance_history_calls.append(asset_id)
        return self._maintenance_history_result


class FakeKnowledgeBasePort:
    def __init__(self, guidance: str = "fake guidance") -> None:
        self._guidance = guidance
        self.calls: list[str] = []

    def retrieve(self, asset_model: str) -> str:
        self.calls.append(asset_model)
        return self._guidance


class FakeWebSearchPort:
    def __init__(self, result: str = "fake web result") -> None:
        self._result = result
        self.calls: list[str] = []

    def search(self, query: str) -> str:
        self.calls.append(query)
        return self._result


class FakeEmailPort:
    def __init__(self) -> None:
        self.drafted: list[EmailDraft] = []
        self.sent: list[EmailDraft] = []

    def draft(self, report: Report) -> EmailDraft:
        draft = EmailDraft(report=report)
        self.drafted.append(draft)
        return draft

    def send(self, draft: EmailDraft) -> None:
        draft.sent = True
        self.sent.append(draft)


class FakeSchedulerPort:
    def __init__(self) -> None:
        self.scheduled: list[tuple[str, Callable[[], None]]] = []

    def schedule(self, interval: str, callback: Callable[[], None]) -> None:
        self.scheduled.append((interval, callback))
