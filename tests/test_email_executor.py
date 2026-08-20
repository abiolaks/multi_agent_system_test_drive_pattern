from __future__ import annotations

import unittest

import agent_framework as af

from fabric_qa.email_executor import DraftEmailExecutor
from fabric_qa.models import EmailDraft, FabricResult, Report


class FakeContext:
    def __init__(self) -> None:
        self.yielded: list[object] = []

    async def yield_output(self, value: object) -> None:
        self.yielded.append(value)


def make_agent_executor_response(text: str) -> af.AgentExecutorResponse:
    agent_response = af.AgentResponse(messages=[af.Message("assistant", [text])], response_id="r1")
    return af.AgentExecutorResponse(executor_id="agent", agent_response=agent_response, full_conversation=[])


class TestDraftEmailExecutor(unittest.IsolatedAsyncioTestCase):
    async def test_assembles_report_with_summary_and_captured_images_then_drafts(self) -> None:
        drafted: list[EmailDraft] = []

        def draft(report: Report) -> EmailDraft:
            email_draft = EmailDraft(report=report)
            drafted.append(email_draft)
            return email_draft

        captured = [FabricResult(data="x", images=[b"img1", b"img2"])]
        executor = DraftEmailExecutor(draft, captured)
        ctx = FakeContext()

        await executor.handle(make_agent_executor_response("Revenue rose 12%."), ctx)  # type: ignore[arg-type]

        self.assertEqual(len(drafted), 1)
        report = drafted[0].report
        self.assertEqual(report.summary, "Revenue rose 12%.")
        self.assertEqual(report.images, [b"img1", b"img2"])
        self.assertEqual(ctx.yielded, [report])

    async def test_images_from_multiple_captured_fetches_are_all_included(self) -> None:
        drafted: list[EmailDraft] = []

        def draft(report: Report) -> EmailDraft:
            email_draft = EmailDraft(report=report)
            drafted.append(email_draft)
            return email_draft

        captured = [
            FabricResult(data="x", images=[b"img1"]),
            FabricResult(data="y", images=[b"img2"]),
        ]
        executor = DraftEmailExecutor(draft, captured)

        await executor.handle(make_agent_executor_response("s"), FakeContext())  # type: ignore[arg-type]

        self.assertEqual(drafted[0].report.images, [b"img1", b"img2"])


if __name__ == "__main__":
    unittest.main()
