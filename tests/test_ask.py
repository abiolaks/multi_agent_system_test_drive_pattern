from __future__ import annotations

import unittest

from fabric_qa.fakes import (
    FakeEmailPort,
    FakeFabricPort,
    FakeKnowledgeBasePort,
    FakeLLMPort,
    FakeSchedulerPort,
    FakeWebSearchPort,
)
from fabric_qa.models import FabricResult
from fabric_qa.orchestrator import ask
from fabric_qa.ports import Ports


def make_ports(
    *,
    llm: FakeLLMPort | None = None,
    fabric: FakeFabricPort | None = None,
    knowledge_base: FakeKnowledgeBasePort | None = None,
    web_search: FakeWebSearchPort | None = None,
    email: FakeEmailPort | None = None,
    scheduler: FakeSchedulerPort | None = None,
) -> Ports:
    return Ports(
        llm=llm if llm is not None else FakeLLMPort(),
        fabric=fabric if fabric is not None else FakeFabricPort(),
        knowledge_base=knowledge_base if knowledge_base is not None else FakeKnowledgeBasePort(),
        web_search=web_search if web_search is not None else FakeWebSearchPort(),
        email=email if email is not None else FakeEmailPort(),
        scheduler=scheduler if scheduler is not None else FakeSchedulerPort(),
    )


class TestAsk(unittest.TestCase):
    def test_ask_returns_report_with_llm_summary(self) -> None:
        ports = make_ports(
            llm=FakeLLMPort(response="Revenue rose 12% quarter over quarter."),
            fabric=FakeFabricPort(FabricResult(data={"revenue": [100, 112]})),
        )

        report = ask("how did revenue trend this quarter?", ports)

        self.assertEqual(report.summary, "Revenue rose 12% quarter over quarter.")

    def test_ask_preserves_fabric_images_on_the_report(self) -> None:
        chart = b"fake-chart-png-bytes"
        ports = make_ports(
            fabric=FakeFabricPort(FabricResult(data={"revenue": [100, 112]}, images=[chart])),
        )

        report = ask("how did revenue trend this quarter?", ports)

        self.assertEqual(report.images, [chart])

    def test_ask_drafts_the_report_as_an_email_but_never_sends_it(self) -> None:
        email = FakeEmailPort()
        ports = make_ports(email=email)

        report = ask("how did revenue trend this quarter?", ports)

        self.assertEqual(len(email.drafted), 1)
        self.assertIs(email.drafted[0].report, report)
        self.assertEqual(email.sent, [])

    def test_email_send_only_fires_on_explicit_approval(self) -> None:
        email = FakeEmailPort()
        ports = make_ports(email=email)
        ask("how did revenue trend this quarter?", ports)
        draft = email.drafted[0]

        self.assertFalse(draft.sent)  # drafted, not sent, by default

        email.send(draft)  # simulates the user explicitly approving

        self.assertTrue(draft.sent)
        self.assertEqual(email.sent, [draft])

    def test_report_images_do_not_alias_the_fabric_result_images_list(self) -> None:
        shared_images = [b"chart-1"]
        ports = make_ports(fabric=FakeFabricPort(FabricResult(data={}, images=shared_images)))

        report = ask("q1", ports)
        report.images.append(b"chart-2")

        self.assertEqual(shared_images, [b"chart-1"])


if __name__ == "__main__":
    unittest.main()
