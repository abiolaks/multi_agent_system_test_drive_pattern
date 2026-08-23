from __future__ import annotations

import asyncio
import unittest
from typing import Callable

from fabric_qa.agent_chat import FakeChatClient
from fabric_qa.models import AssetReadings, EmailDraft, FabricResult, MaintenanceRecord, Reading, Report
from fabric_qa.router_agent import RouterOutput
from fabric_qa.workflow import ask


class FakeScheduler:
    def __init__(self) -> None:
        self.scheduled: list[tuple[str, Callable[[], None]]] = []

    def __call__(self, interval: str, callback: Callable[[], None]) -> None:
        self.scheduled.append((interval, callback))


def unused_fetch_readings(asset_id: str) -> AssetReadings:
    raise AssertionError(f"fetch_readings should not have been called for asset_id={asset_id!r}")


def unused_fetch(question: str) -> FabricResult:
    raise AssertionError(f"fetch should not have been called for question={question!r}")


def unused_fetch_maintenance_history(asset_id: str) -> list[MaintenanceRecord]:
    raise AssertionError(f"fetch_maintenance_history should not have been called for asset_id={asset_id!r}")


def unused_retrieve_guidance(asset_model: str) -> str:
    raise AssertionError(f"retrieve_guidance should not have been called for asset_model={asset_model!r}")


def unused_web_search(query: str) -> str:
    raise AssertionError(f"web_search should not have been called for query={query!r}")


class TestSchedulingSetup(unittest.IsolatedAsyncioTestCase):
    async def test_recurring_request_with_interval_registers_the_schedule(self) -> None:
        scheduler = FakeScheduler()
        chat_client = FakeChatClient(
            structured_values={RouterOutput: RouterOutput(topic="general_data", recurring=True, interval="weekly")},
        )

        report = await ask(
            "send me this every week",
            chat_client=chat_client,
            fetch=unused_fetch,
            fetch_readings=unused_fetch_readings,
            fetch_maintenance_history=unused_fetch_maintenance_history,
            retrieve_guidance=unused_retrieve_guidance,
            web_search=unused_web_search,
            email_draft=lambda r: EmailDraft(report=r),
            schedule=scheduler,
        )

        self.assertEqual(len(scheduler.scheduled), 1)
        interval, _fire = scheduler.scheduled[0]
        self.assertEqual(interval, "weekly")
        self.assertIn("weekly", report.summary.lower())

    async def test_recurring_request_without_an_interval_asks_for_day_and_time_instead_of_scheduling(self) -> None:
        scheduler = FakeScheduler()
        chat_client = FakeChatClient(
            structured_values={RouterOutput: RouterOutput(topic="general_data", recurring=True, interval=None)},
        )

        report = await ask(
            "send me this regularly",
            chat_client=chat_client,
            fetch=unused_fetch,
            fetch_readings=unused_fetch_readings,
            fetch_maintenance_history=unused_fetch_maintenance_history,
            retrieve_guidance=unused_retrieve_guidance,
            web_search=unused_web_search,
            email_draft=lambda r: EmailDraft(report=r),
            schedule=scheduler,
        )

        self.assertEqual(scheduler.scheduled, [])
        self.assertIn("day", report.summary.lower())
        self.assertIn("time", report.summary.lower())

    async def test_scheduling_setup_itself_is_not_drafted_as_an_email(self) -> None:
        drafted: list[EmailDraft] = []
        chat_client = FakeChatClient(
            structured_values={RouterOutput: RouterOutput(topic="general_data", recurring=True, interval="weekly")},
        )

        await ask(
            "send me this every week",
            chat_client=chat_client,
            fetch=unused_fetch,
            fetch_readings=unused_fetch_readings,
            fetch_maintenance_history=unused_fetch_maintenance_history,
            retrieve_guidance=unused_retrieve_guidance,
            web_search=unused_web_search,
            email_draft=lambda r: drafted.append(EmailDraft(report=r)) or drafted[-1],
            schedule=FakeScheduler(),
        )

        self.assertEqual(drafted, [])

    async def test_a_non_recurring_request_never_touches_the_scheduler(self) -> None:
        scheduler = FakeScheduler()
        chat_client = FakeChatClient(
            response_text="s", structured_values={RouterOutput: RouterOutput(topic="general_data")}
        )

        await ask(
            "how did revenue trend this quarter?",
            chat_client=chat_client,
            fetch=lambda q: FabricResult(data="d"),
            fetch_readings=unused_fetch_readings,
            fetch_maintenance_history=unused_fetch_maintenance_history,
            retrieve_guidance=unused_retrieve_guidance,
            web_search=unused_web_search,
            email_draft=lambda r: EmailDraft(report=r),
            schedule=scheduler,
        )

        self.assertEqual(scheduler.scheduled, [])

    async def test_recurring_asset_health_request_without_a_resolved_asset_id_fails_fast_at_setup(self) -> None:
        # must fail here, not on fire - a fire has no caller to surface a
        # crash to, so a bad request should never be confirmed as scheduled
        scheduler = FakeScheduler()
        chat_client = FakeChatClient(
            structured_values={
                RouterOutput: RouterOutput(topic="asset_health", asset_id=None, recurring=True, interval="weekly")
            },
        )

        with self.assertRaises(ValueError):
            await ask(
                "email me my engines' health every week",
                chat_client=chat_client,
                fetch=unused_fetch,
                fetch_readings=unused_fetch_readings,
                fetch_maintenance_history=unused_fetch_maintenance_history,
                retrieve_guidance=unused_retrieve_guidance,
                web_search=unused_web_search,
                email_draft=lambda r: EmailDraft(report=r),
                schedule=scheduler,
            )

        self.assertEqual(scheduler.scheduled, [])


class TestScheduledFires(unittest.IsolatedAsyncioTestCase):
    async def test_a_fire_never_registers_another_schedule(self) -> None:
        # the regression this guards against: if a fire re-entered the
        # router instead of re-running the already-decided branch directly,
        # the identical question text would be re-classified as recurring
        # and register a duplicate schedule on top of itself, compounding
        # on every subsequent fire
        scheduler = FakeScheduler()
        chat_client = FakeChatClient(
            response_text="s",
            structured_values={RouterOutput: RouterOutput(topic="general_data", recurring=True, interval="daily")},
        )

        await ask(
            "send me revenue every day",
            chat_client=chat_client,
            fetch=lambda q: FabricResult(data={"revenue": [100]}),
            fetch_readings=unused_fetch_readings,
            fetch_maintenance_history=unused_fetch_maintenance_history,
            retrieve_guidance=unused_retrieve_guidance,
            web_search=unused_web_search,
            email_draft=lambda r: EmailDraft(report=r),
            schedule=scheduler,
        )
        self.assertEqual(len(scheduler.scheduled), 1)
        _interval, fire = scheduler.scheduled[0]

        await asyncio.to_thread(fire)
        await asyncio.to_thread(fire)

        self.assertEqual(len(scheduler.scheduled), 1)

    async def test_each_fire_re_runs_the_flow_and_drafts_a_fresh_report(self) -> None:
        scheduler = FakeScheduler()
        drafted: list[EmailDraft] = []
        chat_client = FakeChatClient(
            response_text="Revenue rose 12%.",
            structured_values={RouterOutput: RouterOutput(topic="general_data", recurring=True, interval="weekly")},
        )

        def email_draft(report: Report) -> EmailDraft:
            draft = EmailDraft(report=report)
            drafted.append(draft)
            return draft

        await ask(
            "send me revenue every week",
            chat_client=chat_client,
            fetch=lambda q: FabricResult(data={"revenue": [100, 112]}),
            fetch_readings=unused_fetch_readings,
            fetch_maintenance_history=unused_fetch_maintenance_history,
            retrieve_guidance=unused_retrieve_guidance,
            web_search=unused_web_search,
            email_draft=email_draft,
            schedule=scheduler,
        )
        _interval, fire = scheduler.scheduled[0]

        await asyncio.to_thread(fire)
        await asyncio.to_thread(fire)

        self.assertEqual(len(drafted), 2)
        for draft in drafted:
            self.assertEqual(draft.report.summary, "Revenue rose 12%.")
            self.assertFalse(draft.sent)  # approval gate preserved - never auto-sent

    async def test_fired_reports_reflect_fresh_data_fetched_on_each_run_not_a_cached_snapshot(self) -> None:
        # asset_health's fetch_readings is a deterministic Python call, not
        # an LLM-selected tool (unlike general_data's fetch, which
        # FakeChatClient can't be made to invoke - see
        # test_images_are_empty_when_the_fetch_tool_is_never_invoked in
        # test_workflow.py), so it's the reliable way to prove each fire
        # re-fetches rather than replaying a snapshot captured at setup time
        scheduler = FakeScheduler()
        readings_calls: list[str] = []
        readings = AssetReadings(
            asset_id="ENG-001",
            asset_model="CFM56-7B26",
            readings=[Reading(parameter="egt_margin_c", value=56.0)],  # Normal
        )
        chat_client = FakeChatClient(
            response_text="s",
            structured_values={
                RouterOutput: RouterOutput(
                    topic="asset_health", asset_id="ENG-001", recurring=True, interval="daily"
                )
            },
        )

        def fetch_readings(asset_id: str) -> AssetReadings:
            readings_calls.append(asset_id)
            return readings

        await ask(
            "send me ENG-001's health status every day",
            chat_client=chat_client,
            fetch=unused_fetch,
            fetch_readings=fetch_readings,
            fetch_maintenance_history=unused_fetch_maintenance_history,
            retrieve_guidance=unused_retrieve_guidance,
            web_search=unused_web_search,
            email_draft=lambda r: EmailDraft(report=r),
            schedule=scheduler,
        )
        self.assertEqual(readings_calls, [])  # setup alone doesn't run the flow
        _interval, fire = scheduler.scheduled[0]

        await asyncio.to_thread(fire)
        await asyncio.to_thread(fire)

        self.assertEqual(readings_calls, ["ENG-001", "ENG-001"])

    async def test_scheduled_asset_health_fire_runs_the_full_asset_health_flow(self) -> None:
        scheduler = FakeScheduler()
        drafted: list[EmailDraft] = []
        readings = AssetReadings(
            asset_id="ENG-001",
            asset_model="CFM56-7B26",
            readings=[Reading(parameter="egt_margin_c", value=56.0)],  # Normal
        )
        chat_client = FakeChatClient(
            response_text="Everything looks normal.",
            structured_values={
                RouterOutput: RouterOutput(
                    topic="asset_health", asset_id="ENG-001", recurring=True, interval="weekly"
                )
            },
        )

        def email_draft(report: Report) -> EmailDraft:
            draft = EmailDraft(report=report)
            drafted.append(draft)
            return draft

        await ask(
            "send me ENG-001's health status every week",
            chat_client=chat_client,
            fetch=unused_fetch,
            fetch_readings=lambda asset_id: readings,
            fetch_maintenance_history=unused_fetch_maintenance_history,
            retrieve_guidance=unused_retrieve_guidance,
            web_search=unused_web_search,
            email_draft=email_draft,
            schedule=scheduler,
        )
        self.assertEqual(drafted, [])  # nothing fired yet
        _interval, fire = scheduler.scheduled[0]

        await asyncio.to_thread(fire)

        self.assertEqual(len(drafted), 1)
        self.assertEqual(len(drafted[0].report.verdicts), 1)
        self.assertEqual(drafted[0].report.verdicts[0].health, "Normal")


if __name__ == "__main__":
    unittest.main()
