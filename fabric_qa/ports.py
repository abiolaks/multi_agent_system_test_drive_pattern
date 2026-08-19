from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol

from fabric_qa.classify import Verdict
from fabric_qa.models import AssetReadings, DiagnosisResult, EmailDraft, FabricResult, MaintenanceRecord, Report
from fabric_qa.router import RouterDecision


class LLMPort(Protocol):
    def summarize(self, question: str, data: Any) -> str: ...
    def route(self, question: str) -> RouterDecision: ...
    def diagnose(
        self,
        verdicts: list[Verdict],
        guidance: str,
        maintenance_history: list[MaintenanceRecord],
        web_context: str,
    ) -> DiagnosisResult: ...


class FabricPort(Protocol):
    def fetch(self, question: str) -> FabricResult: ...
    def fetch_readings(self, asset_id: str) -> AssetReadings: ...
    def fetch_maintenance_history(self, asset_id: str) -> list[MaintenanceRecord]: ...


class KnowledgeBasePort(Protocol):
    def retrieve(self, asset_model: str) -> str: ...


class WebSearchPort(Protocol):
    def search(self, query: str) -> str: ...


class EmailPort(Protocol):
    def draft(self, report: Report) -> EmailDraft: ...
    def send(self, draft: EmailDraft) -> None: ...


class SchedulerPort(Protocol):
    def schedule(self, interval: str, callback: Callable[[], None]) -> None: ...


@dataclass
class Ports:
    llm: LLMPort
    fabric: FabricPort
    knowledge_base: KnowledgeBasePort
    web_search: WebSearchPort
    email: EmailPort
    scheduler: SchedulerPort
