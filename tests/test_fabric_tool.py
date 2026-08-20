from __future__ import annotations

import unittest

from fabric_qa.fabric_tool import make_fetch_fabric_data
from fabric_qa.models import FabricResult


class TestMakeFetchFabricData(unittest.TestCase):
    def test_calls_fetch_and_captures_the_result(self) -> None:
        captured: list[FabricResult] = []
        result = FabricResult(data="revenue rose 12%", images=[b"chart-bytes"])

        def fetch(question: str) -> FabricResult:
            self.assertEqual(question, "how did revenue trend?")
            return result

        fetch_fabric_data = make_fetch_fabric_data(fetch, captured)

        text = fetch_fabric_data("how did revenue trend?")

        self.assertEqual(text, "revenue rose 12%")
        self.assertEqual(captured, [result])

    def test_stringifies_non_string_data(self) -> None:
        captured: list[FabricResult] = []

        def fetch(question: str) -> FabricResult:
            return FabricResult(data={"revenue": [100, 112]})

        fetch_fabric_data = make_fetch_fabric_data(fetch, captured)

        text = fetch_fabric_data("q")

        self.assertEqual(text, "{'revenue': [100, 112]}")

    def test_multiple_calls_each_get_captured(self) -> None:
        captured: list[FabricResult] = []
        results = [FabricResult(data="first"), FabricResult(data="second")]

        def fetch(question: str) -> FabricResult:
            return results.pop(0)

        fetch_fabric_data = make_fetch_fabric_data(fetch, captured)

        fetch_fabric_data("q1")
        fetch_fabric_data("q2")

        self.assertEqual([r.data for r in captured], ["first", "second"])


if __name__ == "__main__":
    unittest.main()
