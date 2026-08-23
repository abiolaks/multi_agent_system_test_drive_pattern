from __future__ import annotations

import os

from agent_framework_openai import OpenAIChatCompletionClient

DEFAULT_BASE_URL = "http://localhost:8000/v1"
DEFAULT_MODEL = "qwen3-32b-awq"


def build_vllm_chat_client() -> OpenAIChatCompletionClient:
    # ADR 0004: self-hosted model, so this points at our own vLLM server
    # rather than a cloud API. Must be OpenAIChatCompletionClient (targets
    # /v1/chat/completions) - OpenAIChatClient targets the newer Responses
    # API (/v1/responses), which vLLM's OpenAI-compatible server doesn't
    # implement.
    return OpenAIChatCompletionClient(
        model=os.environ.get("LLM_MODEL", DEFAULT_MODEL),
        base_url=os.environ.get("LLM_BASE_URL", DEFAULT_BASE_URL),
        api_key=os.environ.get("LLM_API_KEY", "not-needed"),
    )
