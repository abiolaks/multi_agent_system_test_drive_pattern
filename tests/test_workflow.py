from __future__ import annotations

import unittest

from fabric_qa.agent_chat import FakeChatClient
from fabric_qa.models import AssetReadings, EmailDraft, FabricResult, Reading, Report
from fabric_qa.router_agent import RouterOutput
from fabric_qa.workflow import ask


def unused_fetch_readings(asset_id: str) -> AssetReadings:
    raise AssertionError(f"fetch_readings should not have been called for asset_id={asset_id!r}")


def unused_fetch(question: str) -> FabricResult:
    raise AssertionError(f"fetch should not have been called for question={question!r}")


class TestGeneralDataFlow(unittest.IsolatedAsyncioTestCase):
    async def test_returns_report_with_llm_summary(self) -> None:
        chat_client = FakeChatClient(
            response_text="Revenue rose 12% quarter over quarter.",
            structured_value=RouterOutput(topic="general_data"),
        )
        drafted: list[EmailDraft] = []

        def fetch(question: str) -> FabricResult:
            return FabricResult(data={"revenue": [100, 112]})

        def email_draft(report: Report) -> EmailDraft:
            draft = EmailDraft(report=report)
            drafted.append(draft)
            return draft

        report = await ask(
            "how did revenue trend this quarter?",
            chat_client=chat_client,
            fetch=fetch,
            fetch_readings=unused_fetch_readings,
            email_draft=email_draft,
        )

        self.assertEqual(report.summary, "Revenue rose 12% quarter over quarter.")
        self.assertEqual(len(drafted), 1)
        self.assertIs(drafted[0].report, report)
        self.assertFalse(drafted[0].sent)

    async def test_images_are_empty_when_the_fetch_tool_is_never_invoked(self) -> None:
        chat_client = FakeChatClient(
            response_text="General answer, no data needed.",
            structured_value=RouterOutput(topic="general_data"),
        )

        report = await ask(
            "what day is it?",
            chat_client=chat_client,
            fetch=lambda q: FabricResult(data="unused"),
            fetch_readings=unused_fetch_readings,
            email_draft=lambda r: EmailDraft(report=r),
        )

        self.assertEqual(report.images, [])


class TestAssetHealthFlow(unittest.IsolatedAsyncioTestCase):
    async def test_returns_report_with_deterministic_verdicts_and_llm_narration(self) -> None:
        chat_client = FakeChatClient(
            response_text="EGT margin has entered alarm range.",
            structured_value=RouterOutput(topic="asset_health", asset_id="ENG-001"),
        )
        readings = AssetReadings(
            asset_id="ENG-001",
            asset_model="CFM56-7B26",
            readings=[Reading(parameter="egt_margin_c", value=14.0)],  # Alarm
        )
        drafted: list[EmailDraft] = []

        def email_draft(report: Report) -> EmailDraft:
            draft = EmailDraft(report=report)
            drafted.append(draft)
            return draft

        report = await ask(
            "what is the health status of ENG-001?",
            chat_client=chat_client,
            fetch=unused_fetch,
            fetch_readings=lambda asset_id: readings,
            email_draft=email_draft,
        )

        self.assertEqual(report.summary, "EGT margin has entered alarm range.")
        self.assertEqual(len(report.verdicts), 1)
        self.assertEqual(report.verdicts[0].parameter, "egt_margin_c")
        self.assertEqual(report.verdicts[0].health, "Alarm")
        self.assertEqual(len(drafted), 1)
        self.assertFalse(drafted[0].sent)

    async def test_a_general_data_question_never_touches_fetch_readings(self) -> None:
        chat_client = FakeChatClient(
            response_text="s", structured_value=RouterOutput(topic="general_data")
        )

        report = await ask(
            "how did revenue trend?",
            chat_client=chat_client,
            fetch=lambda q: FabricResult(data="d"),
            fetch_readings=unused_fetch_readings,
            email_draft=lambda r: EmailDraft(report=r),
        )

        self.assertEqual(report.verdicts, [])

    async def test_an_asset_health_question_never_touches_the_fabric_fetch_tool(self) -> None:
        chat_client = FakeChatClient(
            response_text="s",
            structured_value=RouterOutput(topic="asset_health", asset_id="ENG-002"),
        )
        readings = AssetReadings(
            asset_id="ENG-002",
            asset_model="CFM56-7B26",
            readings=[Reading(parameter="egt_margin_c", value=56.0)],  # Normal
        )

        report = await ask(
            "what is the health status of ENG-002?",
            chat_client=chat_client,
            fetch=unused_fetch,
            fetch_readings=lambda asset_id: readings,
            email_draft=lambda r: EmailDraft(report=r),
        )

        self.assertEqual(report.images, [])


if __name__ == "__main__":
    unittest.main()
