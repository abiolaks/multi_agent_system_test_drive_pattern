# Knowledge base setup (Azure AI Search)

Implements ADR 0008: an Azure AI Search index (`guidance`) holding one
searchable document per Asset Model's Fault Isolation Manual excerpt, with a
`content_vector` field populated so hybrid retrieval is available once
`retrieve_guidance` grows past a plain asset_model lookup. Thresholds are
NOT in this index (ADR 0007) - they stay in `data/thresholds/*.json`.

Two identities are involved:

- **your own az login identity** — used once to create the index schema and
  ingest documents (control-plane + write access)
- **the app's service principal** (`KB_CLIENT_ID`/`KB_CLIENT_SECRET`) — used
  at runtime by `AzureSearchKnowledgeBasePort`, read-only

## 1. Re-authenticate

The session's az CLI token has expired:

```bash
az login --tenant 7085725b-f01d-4d02-ad1c-b1a8a6f44106 --scope "https://management.core.windows.net//.default"
```

## 2. Provision the Search service

```bash
RESOURCE_GROUP=<your existing resource group>
LOCATION=<its region, e.g. eastus>
SEARCH_SERVICE=<name, e.g. fabric-qa-guidance>

az provider register --namespace Microsoft.Search   # idempotent, safe to re-run

az search service create \
  --name "$SEARCH_SERVICE" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --sku basic

SEARCH_SERVICE_ID=$(az search service show \
  --name "$SEARCH_SERVICE" --resource-group "$RESOURCE_GROUP" --query id -o tsv)

SEARCH_ENDPOINT="https://${SEARCH_SERVICE}.search.windows.net"
```

`basic` is enough for a POV-scale index (2 documents today). Optional
hardening: disable API-key auth so only AAD/RBAC can reach the service —
check `az search service update --help` for the current flag name in your
az cli version (it's evolved across releases); look for something like
`--auth-options aadOrApiKey --aad-auth-failure-mode http403`, or set
"Disable local authentication" in the portal's Keys blade.

## 3. Create the app registration for the runtime identity

```bash
APP_ID=$(az ad app create --display-name "fabric-qa-kb-search" --query appId -o tsv)
az ad sp create --id "$APP_ID"
KB_CLIENT_SECRET=$(az ad app credential reset --id "$APP_ID" --years 1 --query password -o tsv)
```

Save `$APP_ID` as `KB_CLIENT_ID` and `$KB_CLIENT_SECRET` as `KB_CLIENT_SECRET`
in `.env` (copy from `.env.example`). `KB_TENANT_ID` is
`7085725b-f01d-4d02-ad1c-b1a8a6f44106`.

## 4. Role assignments

```bash
# your own identity: needed to create the index and ingest documents (once)
MY_OBJECT_ID=$(az ad signed-in-user show --query id -o tsv)
az role assignment create --assignee "$MY_OBJECT_ID" --role "Search Service Contributor" --scope "$SEARCH_SERVICE_ID"
az role assignment create --assignee "$MY_OBJECT_ID" --role "Search Index Data Contributor" --scope "$SEARCH_SERVICE_ID"

# the app's runtime identity: read-only, this is all AzureSearchKnowledgeBasePort needs
APP_SP_ID=$(az ad sp show --id "$APP_ID" --query id -o tsv)
az role assignment create --assignee "$APP_SP_ID" --role "Search Index Data Reader" --scope "$SEARCH_SERVICE_ID"
```

RBAC role assignments can take a few minutes to propagate.

## 5. Create the index and ingest guidance

```bash
export KB_SEARCH_ENDPOINT="$SEARCH_ENDPOINT"

uv run python scripts/create_search_index.py   # uses your az login (Search Service Contributor)
uv run python scripts/ingest_guidance.py       # uses your az login (Search Index Data Contributor)
```

`ingest_guidance.py` downloads and runs `BAAI/bge-small-en-v1.5` locally
(via `sentence-transformers`, CPU is fine at this size) to embed each
guidance file's full content — see `fabric_qa/adapters/embeddings.py`. Re-run
it whenever a guidance `.md` file changes; it's an idempotent upsert keyed
on `asset_model`.

## 6. Wire up the app

Fill in `.env` from `.env.example`'s `KB_*` block with the runtime service
principal's credentials and the endpoint from step 2, then construct the
port the same way `GraphEmailPort.from_env()` is used:

```python
from fabric_qa.adapters.azure_search import AzureSearchKnowledgeBasePort

knowledge_base = AzureSearchKnowledgeBasePort.from_env()
```

## Adding a new Asset Model's guidance

1. Drop `data/guidance/<AssetModel>_FIM.md`.
2. Re-run `uv run python scripts/ingest_guidance.py`.

No index or code changes needed as long as the manual is small enough to
load whole (ADR 0008). If a manual grows past that, chunking logic will need
to move from "1 chunk per file" to a real splitter in `ingest_guidance.py`.
