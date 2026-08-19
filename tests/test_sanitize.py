from __future__ import annotations

import unittest

from fabric_qa.classify import Verdict
from fabric_qa.sanitize import sanitize_query


class TestSanitizeQuery(unittest.TestCase):
    def test_strips_the_asset_id(self) -> None:
        sanitized = sanitize_query(
            "what is the health status of ENG-001?",
            asset_id="ENG-001",
            verdicts=[],
        )
        self.assertNotIn("ENG-001", sanitized)

    def test_asset_id_match_is_case_insensitive(self) -> None:
        sanitized = sanitize_query(
            "eng-001 EGT margin causes",
            asset_id="ENG-001",
            verdicts=[],
        )
        self.assertNotIn("eng-001", sanitized.lower())

    def test_strips_reading_values(self) -> None:
        sanitized = sanitize_query(
            "EGT margin 14.0 probable causes",
            asset_id="ENG-001",
            verdicts=[Verdict(parameter="egt_margin_c", value=14.0, health="Alarm")],
        )
        self.assertNotIn("14.0", sanitized)

    def test_identifier_backstop_catches_lowercase_tokens_too(self) -> None:
        sanitized = sanitize_query(
            "contact eng-003 support",
            asset_id="ENG-999",  # unrelated to the id in the query text
            verdicts=[],
        )
        self.assertNotIn("eng-003", sanitized.lower())

    def test_stripping_a_reading_value_does_not_corrupt_an_unrelated_larger_number(self) -> None:
        sanitized = sanitize_query(
            "vibration trend over 14.9 flight hours",
            asset_id="ENG-003",
            verdicts=[Verdict(parameter="vibration_n2_ips", value=4.9, health="Alarm")],
        )
        self.assertIn("14.9", sanitized)

    def test_strips_identifier_shaped_tokens_even_when_not_passed_explicitly(self) -> None:
        # a work-order id embedded in the raw query, e.g. copied in from
        # maintenance history text, must be stripped even though it was
        # never passed as asset_id or a verdict - the backstop pattern
        # catches identifier-shaped tokens regardless of source
        sanitized = sanitize_query(
            "recurrence after WO-1003 trim balance",
            asset_id="ENG-003",
            verdicts=[],
        )
        self.assertNotIn("WO-1003", sanitized)

    def test_backstop_catches_a_raw_asset_id_the_question_mentions_that_differs_from_the_resolved_one(self) -> None:
        # the resolved (canonical) asset_id may differ from what the user's
        # question literally said - exact-match stripping alone would miss
        # this, so the identifier-pattern backstop is what actually protects it
        sanitized = sanitize_query(
            "what is the health status of ENG-003?",
            asset_id="ENG-003-CANONICAL",
            verdicts=[],
        )
        self.assertNotIn("ENG-003", sanitized)

    def test_preserves_generic_domain_terms(self) -> None:
        sanitized = sanitize_query(
            "egt_margin_c probable causes",
            asset_id="ENG-001",
            verdicts=[],
        )
        self.assertEqual(sanitized, "egt_margin_c probable causes")

    def test_preserves_asset_model_since_it_is_generic_equipment_type_not_identifying_data(self) -> None:
        sanitized = sanitize_query(
            "CFM56-7B26 hot section erosion probable causes",
            asset_id="ENG-001",
            verdicts=[],
        )
        self.assertIn("CFM56-7B26", sanitized)

    def test_guardrail_no_sensitive_token_survives_across_a_batch_of_realistic_queries(self) -> None:
        sensitive_tokens = ["ENG-001", "ENG-002", "ENG-003", "WO-1003", "14.0", "4.9"]
        raw_queries = [
            "what is the health status of ENG-001? egt_margin_c probable causes",
            "ENG-002 all readings normal",
            "ENG-003 vibration_n2_ips 4.9 recurrence after WO-1003",
            "EGT margin 14.0 hot section erosion",
        ]
        verdicts = [
            Verdict(parameter="egt_margin_c", value=14.0, health="Alarm"),
            Verdict(parameter="vibration_n2_ips", value=4.9, health="Alarm"),
        ]

        for raw_query in raw_queries:
            sanitized = sanitize_query(raw_query, asset_id="ENG-003", verdicts=verdicts)
            for token in sensitive_tokens:
                self.assertNotIn(token, sanitized, f"{token!r} leaked in sanitized query: {sanitized!r}")


if __name__ == "__main__":
    unittest.main()
