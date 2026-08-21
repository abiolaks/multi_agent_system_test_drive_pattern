from __future__ import annotations

from typing import Any

import agent_framework as af


class FakeChatClient:
    additional_properties: dict[str, Any] = {}

    def __init__(
        self,
        response_text: str = "fake summary",
        structured_value: Any = None,
        structured_values: dict[type, Any] | None = None,
    ) -> None:
        self._response_text = response_text
        self._structured_value = structured_value
        # keyed by the requested response_format type - lets a single fake
        # client serve multiple Agents in one workflow that each request a
        # different structured shape (e.g. router vs diagnosis)
        self._structured_values = structured_values or {}
        self.calls: list[Any] = []

    def get_response(self, messages: Any, *, stream: bool = False, client_kwargs: Any = None, **kwargs: Any) -> Any:
        self.calls.append(messages)
        options = kwargs.get("options") or {}
        response_format = getattr(options, "response_format", None) or (
            options.get("response_format") if isinstance(options, dict) else None
        )

        async def _response() -> af.ChatResponse[Any]:
            if response_format is not None:
                value = self._structured_values.get(response_format, self._structured_value)
                return af.ChatResponse(
                    messages=[af.Message("assistant", ["{}"])],
                    response_id="fake",
                    value=value,
                )
            return af.ChatResponse(
                messages=[af.Message("assistant", [self._response_text])],
                response_id="fake",
            )

        return _response()
