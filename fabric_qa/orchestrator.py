from __future__ import annotations

from fabric_qa.models import Report
from fabric_qa.ports import Ports


def ask(question: str, ports: Ports) -> Report:
    fabric_result = ports.fabric.fetch(question)
    summary = ports.llm.summarize(question, fabric_result.data)
    report = Report(summary=summary, images=list(fabric_result.images))
    ports.email.draft(report)
    return report
