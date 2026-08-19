# Routing + sequential chaining (not one or the other)

The orchestrator classifies each request with an LLM router into one of two flows — Asset Health analysis or general data Q&A — plus an optional scheduling modifier, then runs a fixed sequential chain inside the chosen flow. Neither pattern alone suffices: one fixed chain would have to either always cross-reference thresholds (nonsense for general questions) or never (missing the point of asset health), so the router selects the chain and chaining executes it.

## Considered Options

- **Sequential chaining only** — rejected because the two flows differ in their middle steps (threshold cross-reference + recommendations), so a single fixed chain can't serve both.
- **LLM routing only** — routing just picks a handler; each handler still needs its steps run in order, so chaining is required inside anyway.
- **Open-ended agentic loop (ReAct)** — rejected because the system's capabilities are a small closed set (two flows + a scheduling modifier), so a bounded router is simpler and more predictable than unbounded tool selection.
