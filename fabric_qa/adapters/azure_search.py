from __future__ import annotations

import os
from typing import Iterable, Protocol

from azure.identity import ClientSecretCredential
from azure.search.documents import SearchClient

SEARCH_SCOPE = "https://search.azure.com/.default"


class GuidanceChunk(Protocol):
    def __getitem__(self, key: str) -> object: ...


class SearchDocumentsClient(Protocol):
    def search(self, *, search_text: str | None, filter: str, order_by: list[str]) -> Iterable[GuidanceChunk]: ...


class AzureSearchKnowledgeBasePort:
    """KnowledgeBasePort backed by the Azure AI Search guidance index (ADR 0008).

    retrieve() is called with an asset_model key, not a free-text query (see
    diagnosis.py's retrieve_guidance tool), so this does a filtered lookup on
    the asset_model field rather than a vector/hybrid query - there is no
    natural-language input to embed. The index still carries a content_vector
    field (populated at ingestion time by scripts/ingest_guidance.py) so
    hybrid retrieval can be turned on here later without a re-index, if the
    tool's contract grows to accept a fault-description query alongside the
    asset_model filter.

    Chunks for a model are concatenated in chunk_index order; today that's a
    single whole-document chunk per model per ADR 0008's "small manuals
    loaded whole" rule.
    """

    def __init__(self, client: SearchDocumentsClient) -> None:
        self._client = client

    @classmethod
    def from_env(cls) -> "AzureSearchKnowledgeBasePort":
        credential = ClientSecretCredential(
            tenant_id=os.environ["KB_TENANT_ID"],
            client_id=os.environ["KB_CLIENT_ID"],
            client_secret=os.environ["KB_CLIENT_SECRET"],
        )
        client = SearchClient(
            endpoint=os.environ["KB_SEARCH_ENDPOINT"],
            index_name=os.environ.get("KB_SEARCH_INDEX_NAME", "guidance"),
            credential=credential,
        )
        return cls(client=client)

    def retrieve(self, asset_model: str) -> str:
        results = self._client.search(
            search_text=None,
            filter=f"asset_model eq '{_escape_odata(asset_model)}'",
            order_by=["chunk_index asc"],
        )
        chunks = sorted(results, key=lambda chunk: int(chunk["chunk_index"]))  # type: ignore[arg-type]
        if not chunks:
            raise ValueError(f"no Guidance indexed in Azure AI Search for asset_model={asset_model!r}")
        return "\n\n".join(str(chunk["content"]) for chunk in chunks)


def _escape_odata(value: str) -> str:
    return value.replace("'", "''")
