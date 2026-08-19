from __future__ import annotations

import unittest

from fabric_qa.classify import classify
from fabric_qa.thresholds import load_thresholds


class TestLoadThresholds(unittest.TestCase):
    def test_load_thresholds_indexes_full_spec_by_parameter_name(self) -> None:
        thresholds = load_thresholds("CFM56-7B26")

        self.assertEqual(
            thresholds["egt_margin_c"],
            {"name": "egt_margin_c", "unit": "C",
             "advisory": {"min": 40}, "alarm": {"min": 20}},
        )

    def test_load_thresholds_output_is_directly_usable_by_classify(self) -> None:
        thresholds = load_thresholds("GEnx-1B")

        self.assertEqual(classify(4.9, thresholds["vibration_n2_ips"]), "Alarm")


if __name__ == "__main__":
    unittest.main()
