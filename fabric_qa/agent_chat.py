from __future__ import annotations

from typing import Any

import agent_framework as af


class FakeChatClient:
    additional_properties: dict[str, Any] = {}

    def __init__(self, response_text: str = "fake summary", structured_value: Any = None) -> None:
        self._response_text = response_text
        self._structured_value = structured_value
        self.calls: list[Any] = []

    def get_response(self, messages: Any, *, stream: bool = False, client_kwargs: Any = None, **kwargs: Any) -> Any:
        self.calls.append(messages)
        options = kwargs.get("options") or {}
        wants_structured = bool(getattr(options, "response_format", None) or (
            isinstance(options, dict) and options.get("response_format")
        ))

        async def _response() -> af.ChatResponse[Any]:
            if wants_structured:
                return af.ChatResponse(
                    messages=[af.Message("assistant", ["{}"])],
                    response_id="fake",
                    value=self._structured_value,
                )
            return af.ChatResponse(
                messages=[af.Message("assistant", [self._response_text])],
                response_id="fake",
            )

        return _response()
