from __future__ import annotations

import unittest

from fabric_qa.fakes import FakeLLMPort
from fabric_qa.router import RouterDecision


class TestRouterDetection(unittest.TestCase):
    def test_router_decision_surfaces_recurring_schedule_and_interval(self) -> None:
        llm = FakeLLMPort(
            route_response=RouterDecision(topic="general_data", recurring=True, interval="weekly"),
        )

        decision = llm.route("send me this every week")

        self.assertTrue(decision.recurring)
        self.assertEqual(decision.interval, "weekly")

    def test_router_decision_defaults_to_one_off(self) -> None:
        llm = FakeLLMPort(route_response=RouterDecision(topic="general_data"))

        decision = llm.route("what is the health status of my assets?")

        self.assertFalse(decision.recurring)
        self.assertIsNone(decision.interval)


if __name__ == "__main__":
    unittest.main()
