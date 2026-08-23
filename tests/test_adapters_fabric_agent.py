from __future__ import annotations

import unittest

from fabric_qa.adapters.fabric_agent import FabricDataAgentPort


class FakeDataAgentClient:
    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.questions_asked: list[str] = []

    async def ask(self, question: str) -> str:
        self.questions_asked.append(question)
        return self._responses.pop(0)


class TestFabricDataAgentPortFetch(unittest.TestCase):
    def test_fetch_wraps_the_agents_text_reply_in_a_fabric_result(self) -> None:
        client = FakeDataAgentClient(["Revenue rose 12% quarter over quarter."])
        port = FabricDataAgentPort(client)

        result = port.fetch("What is our revenue trend?")

        self.assertEqual(result.data, "Revenue rose 12% quarter over quarter.")
        self.assertEqual(result.images, [])
        self.assertEqual(client.questions_asked, ["What is our revenue trend?"])


class TestFabricDataAgentPortFetchReadings(unittest.TestCase):
    def test_parses_bare_json_into_asset_readings(self) -> None:
        client = FakeDataAgentClient(
            [
                """{
                    "asset_model": "CFM56-7B26",
                    "readings": {"egt_margin_c": 12.0, "n1_pct": 91.3}
                }"""
            ]
        )
        port = FabricDataAgentPort(client)

        result = port.fetch_readings("ENG-001")

        self.assertEqual(result.asset_id, "ENG-001")
        self.assertEqual(result.asset_model, "CFM56-7B26")
        by_param = {r.parameter: r.value for r in result.readings}
        self.assertEqual(by_param, {"egt_margin_c": 12.0, "n1_pct": 91.3})

    def test_strips_a_markdown_json_fence_before_parsing(self) -> None:
        client = FakeDataAgentClient(
            ['```json\n{"asset_model": "GEnx-1B", "readings": {"n2_pct": 95.2}}\n```']
        )
        port = FabricDataAgentPort(client)

        result = port.fetch_readings("ENG-003")

        self.assertEqual(result.asset_model, "GEnx-1B")

    def test_retries_once_when_the_agent_replies_with_prose_instead_of_json(self) -> None:
        client = FakeDataAgentClient(
            [
                "There was a technical issue retrieving that data.",
                '{"asset_model": "CFM56-7B26", "readings": {"egt_margin_c": 40.0}}',
            ]
        )
        port = FabricDataAgentPort(client)

        result = port.fetch_readings("ENG-001")

        self.assertEqual(result.asset_model, "CFM56-7B26")
        self.assertEqual(len(client.questions_asked), 2)

    def test_raises_a_clear_error_after_exhausting_retries_on_unparseable_replies(self) -> None:
        client = FakeDataAgentClient(["not json", "still not json", "nope"])
        port = FabricDataAgentPort(client)

        with self.assertRaises(ValueError):
            port.fetch_readings("ENG-001")


class TestFabricDataAgentPortFetchMaintenanceHistory(unittest.TestCase):
    def test_parses_a_json_array_into_maintenance_records(self) -> None:
        client = FakeDataAgentClient(
            [
                """[
                    {"work_order_id": "WO-1001", "date": "2026-02-10",
                     "finding": "Routine borescope", "parts_replaced": null}
                ]"""
            ]
        )
        port = FabricDataAgentPort(client)

        records = port.fetch_maintenance_history("ENG-001")

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].work_order_id, "WO-1001")
        self.assertEqual(records[0].finding, "Routine borescope")

    def test_a_null_parts_replaced_becomes_an_empty_string_not_none(self) -> None:
        client = FakeDataAgentClient(
            ['[{"work_order_id": "WO-1", "date": "d", "finding": "f", "parts_replaced": null}]']
        )
        port = FabricDataAgentPort(client)

        records = port.fetch_maintenance_history("ENG-001")

        self.assertEqual(records[0].parts_replaced, "")


if __name__ == "__main__":
    unittest.main()
