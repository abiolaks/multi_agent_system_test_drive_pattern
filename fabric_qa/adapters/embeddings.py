from __future__ import annotations

import os
from typing import Protocol

DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIMENSIONS = 384


class Embedder(Protocol):
    def embed(self, text: str) -> list[float]: ...


class LocalEmbedder:
    # ADR 0004: self-host our own model rather than call a cloud model API,
    # so guidance content never leaves our infrastructure to be embedded.
    def __init__(self, model_name: str = DEFAULT_EMBEDDING_MODEL) -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)

    @classmethod
    def from_env(cls) -> "LocalEmbedder":
        return cls(model_name=os.environ.get("KB_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL))

    def embed(self, text: str) -> list[float]:
        return self._model.encode(text, normalize_embeddings=True).tolist()
