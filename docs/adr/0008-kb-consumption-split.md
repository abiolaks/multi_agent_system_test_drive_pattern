# Knowledge base is consumed two ways: extracted thresholds + indexed guidance

The knowledge base (Azure AI Search) serves two consumers differently. Numeric thresholds are pre-extracted from the PDFs into structured, queryable records for deterministic code comparison (never RAG'd). The narrative Fault-Signature guidance is chunked and indexed for hybrid retrieval (RAG) so the LLM can pull the relevant failure-mode section to ground its diagnosis and recommendations. Small per-model manuals may be loaded whole into context; fine-grained chunking is added only when a manual exceeds context.
