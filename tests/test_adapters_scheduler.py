from __future__ import annotations

import unittest

from apscheduler.triggers.interval import IntervalTrigger

from fabric_qa.adapters.scheduler import APSchedulerPort


class FakeJobScheduler:
    def __init__(self) -> None:
        self.jobs: list[tuple[object, IntervalTrigger]] = []

    def add_job(self, func, trigger):
        self.jobs.append((func, trigger))


class TestAPSchedulerPort(unittest.TestCase):
    def test_schedule_registers_a_job_with_a_matching_interval_trigger(self) -> None:
        scheduler = FakeJobScheduler()
        port = APSchedulerPort(scheduler)
        callback = lambda: None  # noqa: E731

        port.schedule("daily", callback)

        self.assertEqual(len(scheduler.jobs), 1)
        func, trigger = scheduler.jobs[0]
        self.assertIs(func, callback)
        self.assertIsInstance(trigger, IntervalTrigger)
        self.assertEqual(trigger.interval_length, 24 * 60 * 60)

    def test_schedule_is_case_and_whitespace_insensitive(self) -> None:
        scheduler = FakeJobScheduler()
        port = APSchedulerPort(scheduler)

        port.schedule("  Weekly  ", lambda: None)

        self.assertEqual(len(scheduler.jobs), 1)
        _func, trigger = scheduler.jobs[0]
        self.assertEqual(trigger.interval_length, 7 * 24 * 60 * 60)

    def test_schedule_raises_a_clear_error_for_an_unrecognized_interval(self) -> None:
        scheduler = FakeJobScheduler()
        port = APSchedulerPort(scheduler)

        with self.assertRaises(ValueError):
            port.schedule("fortnightly", lambda: None)

        self.assertEqual(scheduler.jobs, [])


if __name__ == "__main__":
    unittest.main()
