"""Create (or update) the `guidance` Azure AI Search index used by AzureSearchKnowledgeBasePort.

Requires the caller's identity to hold the "Search Service Contributor" role
on the target Search service (index schema management is a control-plane
operation - the app's own runtime identity only needs "Search Index Data
Reader", see docs/kb-setup.md).

Usage:
    KB_SEARCH_ENDPOINT=https://<service>.search.windows.net uv run python scripts/create_search_index.py
"""

from __future__ import annotations

import os

from azure.identity import AzureCliCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)

from fabric_qa.adapters.embeddings import EMBEDDING_DIMENSIONS

INDEX_NAME = os.environ.get("KB_SEARCH_INDEX_NAME", "guidance")
VECTOR_SEARCH_PROFILE = "guidance-vector-profile"
VECTOR_SEARCH_ALGORITHM = "guidance-hnsw"
SEMANTIC_CONFIG = "guidance-semantic-config"


def build_index() -> SearchIndex:
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SimpleField(name="asset_model", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SimpleField(name="chunk_index", type=SearchFieldDataType.Int32, filterable=True, sortable=True),
        SimpleField(name="source_file", type=SearchFieldDataType.String),
        SearchableField(name="section", type=SearchFieldDataType.String),
        SearchableField(name="content", type=SearchFieldDataType.String),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=EMBEDDING_DIMENSIONS,
            vector_search_profile_name=VECTOR_SEARCH_PROFILE,
        ),
    ]

    vector_search = VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name=VECTOR_SEARCH_ALGORITHM)],
        profiles=[
            VectorSearchProfile(
                name=VECTOR_SEARCH_PROFILE,
                algorithm_configuration_name=VECTOR_SEARCH_ALGORITHM,
            )
        ],
    )

    semantic_search = SemanticSearch(
        configurations=[
            SemanticConfiguration(
                name=SEMANTIC_CONFIG,
                prioritized_fields=SemanticPrioritizedFields(
                    title_field=SemanticField(field_name="section"),
                    content_fields=[SemanticField(field_name="content")],
                    keywords_fields=[SemanticField(field_name="asset_model")],
                ),
            )
        ]
    )

    return SearchIndex(
        name=INDEX_NAME,
        fields=fields,
        vector_search=vector_search,
        semantic_search=semantic_search,
    )


def main() -> None:
    endpoint = os.environ["KB_SEARCH_ENDPOINT"]
    client = SearchIndexClient(endpoint=endpoint, credential=AzureCliCredential())
    result = client.create_or_update_index(build_index())
    print(f"created/updated index {result.name!r} at {endpoint}")


if __name__ == "__main__":
    main()
