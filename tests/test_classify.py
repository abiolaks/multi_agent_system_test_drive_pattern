from __future__ import annotations

import unittest

from fabric_qa.classify import classify
from fabric_qa.thresholds import load_thresholds


def load_spec(asset_model: str, parameter: str) -> dict:
    return load_thresholds(asset_model)[parameter]


class TestClassify(unittest.TestCase):
    # egt_margin_c (CFM56-7B26): advisory min=40, alarm min=20 (low is bad)
    # values drawn from the real data/engine_readings.csv ENG-001 trend

    def test_egt_margin_within_normal_range_is_normal(self) -> None:
        spec = load_spec("CFM56-7B26", "egt_margin_c")
        self.assertEqual(classify(56.0, spec), "Normal")

    def test_egt_margin_below_advisory_floor_is_advisory(self) -> None:
        spec = load_spec("CFM56-7B26", "egt_margin_c")
        self.assertEqual(classify(35.0, spec), "Advisory")

    def test_egt_margin_below_alarm_floor_is_alarm(self) -> None:
        spec = load_spec("CFM56-7B26", "egt_margin_c")
        self.assertEqual(classify(14.0, spec), "Alarm")

    def test_boundary_exactly_at_advisory_floor_is_still_normal(self) -> None:
        spec = load_spec("CFM56-7B26", "egt_margin_c")
        self.assertEqual(classify(40.0, spec), "Normal")

    def test_boundary_exactly_at_alarm_floor_is_advisory_not_alarm(self) -> None:
        spec = load_spec("CFM56-7B26", "egt_margin_c")
        self.assertEqual(classify(20.0, spec), "Advisory")

    # vibration_n2_ips (GEnx-1B): advisory max=2.0, alarm max=4.0 (high is bad)
    # values drawn from the real data/engine_readings.csv ENG-003 trend

    def test_vibration_within_normal_range_is_normal(self) -> None:
        spec = load_spec("GEnx-1B", "vibration_n2_ips")
        self.assertEqual(classify(1.0, spec), "Normal")

    def test_vibration_above_advisory_ceiling_is_advisory(self) -> None:
        spec = load_spec("GEnx-1B", "vibration_n2_ips")
        self.assertEqual(classify(2.8, spec), "Advisory")

    def test_vibration_above_alarm_ceiling_is_alarm(self) -> None:
        spec = load_spec("GEnx-1B", "vibration_n2_ips")
        self.assertEqual(classify(4.9, spec), "Alarm")


if __name__ == "__main__":
    unittest.main()
