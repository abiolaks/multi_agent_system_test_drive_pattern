from __future__ import annotations

from typing import Callable, Protocol

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

# ADR 0003: in-process scheduler for the POV. Jobs live in memory only -
# lost on restart, duplicated across replicas - acceptable while proving
# the flow, but must be replaced with a durable scheduler (queue + worker,
# or a persistent job store) before production.

# "monthly" is approximated as 4 weeks, not a calendar month - fine for a
# POV, would need CronTrigger(day=1, ...) for calendar accuracy.
INTERVAL_TRIGGER_KWARGS: dict[str, dict[str, int]] = {
    "hourly": {"hours": 1},
    "daily": {"days": 1},
    "weekly": {"weeks": 1},
    "monthly": {"weeks": 4},
}


class JobScheduler(Protocol):
    def add_job(self, func: Callable[[], None], trigger: IntervalTrigger) -> object: ...


class APSchedulerPort:
    def __init__(self, scheduler: JobScheduler) -> None:
        self._scheduler = scheduler

    @classmethod
    def from_env(cls) -> "APSchedulerPort":
        scheduler = BackgroundScheduler()
        scheduler.start()
        return cls(scheduler)

    def schedule(self, interval: str, callback: Callable[[], None]) -> None:
        kwargs = INTERVAL_TRIGGER_KWARGS.get(interval.strip().lower())
        if kwargs is None:
            known = ", ".join(sorted(INTERVAL_TRIGGER_KWARGS))
            raise ValueError(f"unrecognized schedule interval {interval!r}; expected one of: {known}")
        self._scheduler.add_job(callback, IntervalTrigger(**kwargs))
