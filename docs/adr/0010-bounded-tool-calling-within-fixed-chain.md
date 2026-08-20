# Bounded per-node tool-calling within the fixed chain (scoped exception to ADR 0001)

ADR 0001 fixes the top-level shape — an LLM router picks Flow A (asset health) or Flow B (general data), then a fixed Python-controlled chain runs inside it — and rejects an open-ended agentic loop because the system's capabilities are a small, closed set. That top-level shape is unchanged by this decision.

Within two specific chain steps, the Diagnosis Agent (Flow A, abnormal-verdict branch) and the general-data Agent (Flow B) are each given a small, fixed `tools=[...]` list (Fabric Data Agent MCP, Knowledge Base, sanitized web search) and decide for themselves whether and how to call them, per issue #1's own "Tools" bullet: *"the LLM-callable tools are the Fabric Data Agent (MCP), the Knowledge Base, and sanitized web search."* This is bounded tool selection inside one already-fixed node, not the system-wide unbounded tool selection ADR 0001 rejected — the router still decides which flow runs, and the chain's sequence of steps (fetch → classify → conditional diagnose → email) is still fixed Python control flow via the workflow graph, not something either Agent can reorder or skip.

ADR 0002 (health is code) is unaffected: `classify()` runs as a deterministic workflow step before either Agent is ever invoked, outside both Agents' tool access entirely. Neither Agent has a tool that could substitute for it.

## Considered Options

- **Deterministic pre-fetch only, no agent tool-calling** — Python explicitly calls Fabric/KB/web-search in fixed order and hands the results to the Agent as context; the LLM only narrates. Rejected: doesn't honor issue #1's "LLM-callable tools" language, and is a smaller migration than the team decided to take on.
- **Full Facilitator/dispatcher pattern** (a planning agent dynamically decomposing the request into tasks for N specialist agents via a task-board) — rejected: voids ADR 0001 rather than scoping an exception to it, meaningfully weakens the ADR 0002 guarantee (nothing structurally stops a "specialist" from reasoning over raw readings itself), and serializes several more LLM round-trips per request through a single self-hosted 24GB-GPU model than the fixed two-flow shape does.
