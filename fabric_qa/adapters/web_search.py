from __future__ import annotations

import os

import httpx

BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"
DEFAULT_RESULT_COUNT = 5


class BraveWebSearchPort:
    """WebSearchPort backed by the Brave Search API (raw results, not
    Brave's "Answers" product - ADR 0004 keeps synthesis on our own
    self-hosted model, this adapter only fetches grounding snippets).

    ADR 0006: the query reaching this adapter must already be sanitized
    - that's enforced at the tool boundary in diagnosis.py's
    make_web_search_tool, before this class is ever called. This class
    does no sanitization itself and trusts the query it's given.
    """

    def __init__(self, client: httpx.Client, api_key: str) -> None:
        self._client = client
        self._api_key = api_key

    @classmethod
    def from_env(cls) -> "BraveWebSearchPort":
        return cls(client=httpx.Client(timeout=10.0), api_key=os.environ["WEB_SEARCH_API_KEY"])

    def search(self, query: str) -> str:
        response = self._client.get(
            BRAVE_SEARCH_URL,
            params={"q": query, "count": DEFAULT_RESULT_COUNT},
            headers={"X-Subscription-Token": self._api_key, "Accept": "application/json"},
        )
        response.raise_for_status()
        results = response.json().get("web", {}).get("results", [])
        if not results:
            return "No web results found."
        return "\n\n".join(_format_result(result) for result in results)


def _format_result(result: dict) -> str:
    title = result.get("title", "")
    url = result.get("url", "")
    description = result.get("description", "")
    return f"{title}\n{url}\n{description}"
