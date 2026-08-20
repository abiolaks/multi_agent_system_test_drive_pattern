from __future__ import annotations

import unittest

from fabric_qa.agent_chat import FakeChatClient
from fabric_qa.models import EmailDraft, FabricResult, Report
from fabric_qa.workflow import ask


class TestAskWorkflow(unittest.IsolatedAsyncioTestCase):
    async def test_returns_report_with_llm_summary(self) -> None:
        chat_client = FakeChatClient("Revenue rose 12% quarter over quarter.")
        drafted: list[EmailDraft] = []

        def fetch(question: str) -> FabricResult:
            return FabricResult(data={"revenue": [100, 112]})

        def email_draft(report: Report) -> EmailDraft:
            draft = EmailDraft(report=report)
            drafted.append(draft)
            return draft

        report = await ask(
            "how did revenue trend this quarter?", chat_client=chat_client, fetch=fetch, email_draft=email_draft
        )

        self.assertEqual(report.summary, "Revenue rose 12% quarter over quarter.")
        self.assertEqual(len(drafted), 1)
        self.assertIs(drafted[0].report, report)
        self.assertFalse(drafted[0].sent)

    async def test_images_are_empty_when_the_fetch_tool_is_never_invoked(self) -> None:
        # the LLM decides whether to call the tool - this proves the
        # workflow never fabricates images that were never actually fetched
        chat_client = FakeChatClient("General answer, no data needed.")

        report = await ask(
            "what day is it?",
            chat_client=chat_client,
            fetch=lambda q: FabricResult(data="unused"),
            email_draft=lambda r: EmailDraft(report=r),
        )

        self.assertEqual(report.images, [])

    async def test_email_is_drafted_but_never_sent(self) -> None:
        chat_client = FakeChatClient("s")
        drafted: list[EmailDraft] = []

        def email_draft(report: Report) -> EmailDraft:
            draft = EmailDraft(report=report)
            drafted.append(draft)
            return draft

        await ask(
            "q", chat_client=chat_client, fetch=lambda q: FabricResult(data="d"), email_draft=email_draft
        )

        self.assertEqual(len(drafted), 1)
        self.assertFalse(drafted[0].sent)


if __name__ == "__main__":
    unittest.main()
