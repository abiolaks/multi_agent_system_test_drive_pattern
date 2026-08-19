from __future__ import annotations

import unittest

from fabric_qa.fakes import FakeEmailPort, FakeFabricPort, FakeLLMPort, FakeSchedulerPort
from fabric_qa.models import AssetReadings, FabricResult, Reading
from fabric_qa.orchestrator import ask
from fabric_qa.router import RouterDecision
from tests.test_ask import make_ports


class TestSchedulingSetup(unittest.TestCase):
    def test_recurring_request_with_interval_registers_the_schedule(self) -> None:
        scheduler = FakeSchedulerPort()
        ports = make_ports(
            llm=FakeLLMPort(route_response=RouterDecision(topic="general_data", recurring=True, interval="weekly")),
            scheduler=scheduler,
        )

        report = ask("send me this every week", ports)

        self.assertEqual(len(scheduler.scheduled), 1)
        interval, _callback = scheduler.scheduled[0]
        self.assertEqual(interval, "weekly")
        self.assertIn("weekly", report.summary.lower())

    def test_recurring_request_without_an_interval_asks_for_day_and_time_instead_of_scheduling(self) -> None:
        scheduler = FakeSchedulerPort()
        ports = make_ports(
            llm=FakeLLMPort(route_response=RouterDecision(topic="general_data", recurring=True, interval=None)),
            scheduler=scheduler,
        )

        report = ask("send me this regularly", ports)

        self.assertEqual(scheduler.scheduled, [])
        self.assertIn("day", report.summary.lower())
        self.assertIn("time", report.summary.lower())

    def test_scheduling_setup_itself_is_not_drafted_as_an_email(self) -> None:
        # the setup acknowledgment/clarification isn't a Scheduled Report -
        # AC3 scopes the draft-approval gate to "each Scheduled Report",
        # meaning what fires later, not the scheduling request/response itself
        email = FakeEmailPort()
        ports = make_ports(
            llm=FakeLLMPort(route_response=RouterDecision(topic="general_data", recurring=True, interval="weekly")),
            email=email,
        )

        ask("send me this every week", ports)

        self.assertEqual(email.drafted, [])

    def test_a_non_recurring_request_never_touches_the_scheduler(self) -> None:
        scheduler = FakeSchedulerPort()
        ports = make_ports(scheduler=scheduler)

        ask("how did revenue trend this quarter?", ports)

        self.assertEqual(scheduler.scheduled, [])

    def test_recurring_asset_health_request_without_a_resolved_asset_id_fails_fast_at_setup(self) -> None:
        # must fail here, not on fire - a fire has no caller to surface a
        # crash to, so a bad request should never be confirmed as scheduled
        scheduler = FakeSchedulerPort()
        ports = make_ports(
            llm=FakeLLMPort(
                route_response=RouterDecision(
                    topic="asset_health", asset_id=None, recurring=True, interval="weekly",
                ),
            ),
            scheduler=scheduler,
        )

        with self.assertRaises(ValueError):
            ask("email me my engines' health every week", ports)

        self.assertEqual(scheduler.scheduled, [])


class TestScheduledFires(unittest.TestCase):
    def test_each_fire_re_runs_the_flow_and_drafts_a_fresh_report(self) -> None:
        scheduler = FakeSchedulerPort()
        email = FakeEmailPort()
        fabric = FakeFabricPort(FabricResult(data={"revenue": [100, 112]}))
        llm = FakeLLMPort(
            response="Revenue rose 12%.",
            route_response=RouterDecision(topic="general_data", recurring=True, interval="weekly"),
        )
        ports = make_ports(llm=llm, fabric=fabric, email=email, scheduler=scheduler)

        ask("send me revenue every week", ports)
        _interval, fire = scheduler.scheduled[0]

        fire()
        fire()

        self.assertEqual(len(email.drafted), 2)
        for draft in email.drafted:
            self.assertEqual(draft.report.summary, "Revenue rose 12%.")
        self.assertEqual(email.sent, [])  # approval gate preserved - never auto-sent

    def test_fired_reports_reflect_fresh_data_fetched_on_each_run_not_a_cached_snapshot(self) -> None:
        # a Scheduled Report must re-fetch on each fire, not replay a
        # snapshot captured at setup time
        scheduler = FakeSchedulerPort()
        fabric = FakeFabricPort(FabricResult(data={"revenue": [100]}))
        ports = make_ports(
            llm=FakeLLMPort(route_response=RouterDecision(topic="general_data", recurring=True, interval="daily")),
            fabric=fabric,
            scheduler=scheduler,
        )

        ask("send me revenue every day", ports)
        self.assertEqual(fabric.calls, [])  # setup alone doesn't run the flow

        _interval, fire = scheduler.scheduled[0]
        fire()
        fire()

        self.assertEqual(fabric.calls, ["send me revenue every day", "send me revenue every day"])

    def test_scheduled_asset_health_fire_runs_the_full_asset_health_flow(self) -> None:
        readings = AssetReadings(
            asset_id="ENG-001",
            asset_model="CFM56-7B26",
            readings=[Reading(parameter="egt_margin_c", value=56.0)],  # Normal
        )
        scheduler = FakeSchedulerPort()
        email = FakeEmailPort()
        ports = make_ports(
            llm=FakeLLMPort(
                route_response=RouterDecision(
                    topic="asset_health", asset_id="ENG-001", recurring=True, interval="weekly",
                ),
            ),
            fabric=FakeFabricPort(readings_result=readings),
            email=email,
            scheduler=scheduler,
        )

        ask("send me ENG-001's health status every week", ports)
        self.assertEqual(email.drafted, [])  # nothing fired yet

        _interval, fire = scheduler.scheduled[0]
        fire()

        self.assertEqual(len(email.drafted), 1)
        self.assertEqual(len(email.drafted[0].report.verdicts), 1)


if __name__ == "__main__":
    unittest.main()
