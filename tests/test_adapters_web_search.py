from __future__ import annotations

import unittest

import httpx

from fabric_qa.adapters.web_search import BRAVE_SEARCH_URL, BraveWebSearchPort


def make_port(handler) -> BraveWebSearchPort:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return BraveWebSearchPort(client=client, api_key="test-key")


class TestBraveWebSearchPort(unittest.TestCase):
    def test_search_sends_the_query_and_api_key_to_brave(self) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"web": {"results": []}})

        port = make_port(handler)
        port.search("engine EGT margin erosion causes")

        self.assertEqual(len(captured), 1)
        request = captured[0]
        self.assertEqual(str(request.url).split("?")[0], BRAVE_SEARCH_URL)
        self.assertEqual(request.url.params["q"], "engine EGT margin erosion causes")
        self.assertEqual(request.headers["X-Subscription-Token"], "test-key")

    def test_search_formats_results_as_readable_text(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "web": {
                        "results": [
                            {"title": "Hot section erosion causes", "url": "https://example.com/1", "description": "D1"},
                            {"title": "EGT margin decline", "url": "https://example.com/2", "description": "D2"},
                        ]
                    }
                },
            )

        port = make_port(handler)

        result = port.search("engine EGT margin erosion causes")

        self.assertIn("Hot section erosion causes", result)
        self.assertIn("https://example.com/1", result)
        self.assertIn("D1", result)
        self.assertIn("EGT margin decline", result)

    def test_search_returns_a_clear_message_when_there_are_no_results(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"web": {"results": []}})

        port = make_port(handler)

        result = port.search("some obscure query")

        self.assertEqual(result, "No web results found.")

    def test_search_raises_on_a_non_2xx_response(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, json={"error": "unauthorized"})

        port = make_port(handler)

        with self.assertRaises(httpx.HTTPStatusError):
            port.search("query")


if __name__ == "__main__":
    unittest.main()
