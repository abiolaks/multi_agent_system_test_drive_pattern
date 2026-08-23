"""Index data/guidance/*.md into the Azure AI Search `guidance` index.

Each file is one Asset Model's Fault Isolation Manual excerpt. Per ADR 0008,
small manuals are indexed whole (one chunk); this only splits on chunk size
if a manual grows past EMBEDDING_MODEL's practical input length, so today
every file produces exactly one chunk_index=0 document.

Requires the caller's identity to hold "Search Index Data Contributor" on
the target Search service (see docs/kb-setup.md).

Usage:
    KB_SEARCH_ENDPOINT=https://<service>.search.windows.net uv run python scripts/ingest_guidance.py
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from azure.identity import AzureCliCredential
from azure.search.documents import SearchClient

from fabric_qa.adapters.embeddings import LocalEmbedder

GUIDANCE_DIR = Path(__file__).resolve().parent.parent / "data" / "guidance"
FILENAME_SUFFIX = "_FIM.md"


def asset_model_for(path: Path) -> str:
    if not path.name.endswith(FILENAME_SUFFIX):
        raise ValueError(f"expected guidance filename to end with {FILENAME_SUFFIX!r}, got {path.name!r}")
    return path.name[: -len(FILENAME_SUFFIX)]


def section_for(content: str) -> str:
    match = re.search(r"^##\s+(.+)$", content, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def build_document(path: Path, embedder: LocalEmbedder) -> dict:
    content = path.read_text()
    asset_model = asset_model_for(path)
    return {
        "id": f"{asset_model}-0",
        "asset_model": asset_model,
        "chunk_index": 0,
        "source_file": path.name,
        "section": section_for(content),
        "content": content,
        "content_vector": embedder.embed(content),
    }


def main() -> None:
    endpoint = os.environ["KB_SEARCH_ENDPOINT"]
    index_name = os.environ.get("KB_SEARCH_INDEX_NAME", "guidance")
    client = SearchClient(endpoint=endpoint, index_name=index_name, credential=AzureCliCredential())
    embedder = LocalEmbedder.from_env()

    paths = sorted(GUIDANCE_DIR.glob(f"*{FILENAME_SUFFIX}"))
    if not paths:
        raise SystemExit(f"no guidance files found under {GUIDANCE_DIR}")

    documents = [build_document(path, embedder) for path in paths]
    result = client.merge_or_upload_documents(documents=documents)
    for outcome in result:
        status = "ok" if outcome.succeeded else f"FAILED: {outcome.error_message}"
        print(f"{outcome.key}: {status}")


if __name__ == "__main__":
    main()
