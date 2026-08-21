from __future__ import annotations

import unittest

import agent_framework as af

from fabric_qa.email_executor import DraftEmailExecutor
from fabric_qa.models import EmailDraft, Report


class FakeContext:
    def __init__(self) -> None:
        self.yielded: list[object] = []

    async def yield_output(self, value: object) -> None:
        self.yielded.append(value)


def make_agent_executor_response(text: str) -> af.AgentExecutorResponse:
    agent_response = af.AgentResponse(messages=[af.Message("assistant", [text])], response_id="r1")
    return af.AgentExecutorResponse(executor_id="agent", agent_response=agent_response, full_conversation=[])


class TestDraftEmailExecutor(unittest.IsolatedAsyncioTestCase):
    async def test_builds_the_report_via_the_injected_callback_then_drafts(self) -> None:
        drafted: list[EmailDraft] = []

        def draft(report: Report) -> EmailDraft:
            email_draft = EmailDraft(report=report)
            drafted.append(email_draft)
            return email_draft

        def build_report(response: af.AgentExecutorResponse) -> Report:
            return Report(summary=f"built: {response.agent_response.text}")

        executor = DraftEmailExecutor(draft, build_report)
        ctx = FakeContext()

        await executor.handle(make_agent_executor_response("Revenue rose 12%."), ctx)  # type: ignore[arg-type]

        self.assertEqual(len(drafted), 1)
        self.assertEqual(drafted[0].report.summary, "built: Revenue rose 12%.")
        self.assertEqual(ctx.yielded, [drafted[0].report])

    async def test_never_sends_only_drafts(self) -> None:
        drafted: list[EmailDraft] = []

        def draft(report: Report) -> EmailDraft:
            email_draft = EmailDraft(report=report)
            drafted.append(email_draft)
            return email_draft

        executor = DraftEmailExecutor(draft, lambda response: Report(summary="s"))

        await executor.handle(make_agent_executor_response("s"), FakeContext())  # type: ignore[arg-type]

        self.assertFalse(drafted[0].sent)

    async def test_custom_id_is_used_when_given(self) -> None:
        executor = DraftEmailExecutor(lambda r: EmailDraft(report=r), lambda response: Report(summary="s"), id="custom")

        self.assertEqual(executor.id, "custom")


if __name__ == "__main__":
    unittest.main()
