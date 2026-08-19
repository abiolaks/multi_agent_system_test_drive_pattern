from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol

from fabric_qa.models import EmailDraft, FabricResult, Report


class LLMPort(Protocol):
    def summarize(self, question: str, data: Any) -> str: ...


class FabricPort(Protocol):
    def fetch(self, question: str) -> FabricResult: ...


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
