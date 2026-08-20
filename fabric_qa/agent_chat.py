from __future__ import annotations

from typing import Any

import agent_framework as af


class FakeChatClient:
    additional_properties: dict[str, Any] = {}

    def __init__(self, response_text: str = "fake summary") -> None:
        self._response_text = response_text
        self.calls: list[Any] = []

    def get_response(self, messages: Any, *, stream: bool = False, client_kwargs: Any = None, **kwargs: Any) -> Any:
        self.calls.append(messages)

        async def _response() -> af.ChatResponse[Any]:
            return af.ChatResponse(
                messages=[af.Message("assistant", [self._response_text])],
                response_id="fake",
            )

        return _response()
