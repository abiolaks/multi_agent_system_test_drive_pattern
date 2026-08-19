from __future__ import annotations

from typing import Any, Callable

from fabric_qa.models import EmailDraft, FabricResult, Report


class FakeLLMPort:
    def __init__(self, response: str = "fake summary") -> None:
        self._response = response
        self.calls: list[tuple[str, Any]] = []

    def summarize(self, question: str, data: Any) -> str:
        self.calls.append((question, data))
        return self._response


class FakeFabricPort:
    def __init__(self, result: FabricResult | None = None) -> None:
        self._result = result if result is not None else FabricResult(data={}, images=[])
        self.calls: list[str] = []

    def fetch(self, question: str) -> FabricResult:
        self.calls.append(question)
        return self._result


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
