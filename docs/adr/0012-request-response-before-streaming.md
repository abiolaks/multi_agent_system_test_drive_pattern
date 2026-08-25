# Request/response for v1 UI, live event streaming deferred

The v1 web UI submits a question and waits for the final `Report`, rather than streaming live agent progress (router decision, tool calls, per-agent status) as it happens. `fabric_qa.workflow.ask()` currently returns only a completed `Report` with no event hooks, so streaming would require first instrumenting `workflow.py`/`orchestrator.py` to emit progress events through the run — real but deferrable work, and not needed to prove the chat flow end-to-end.

Streaming remains the intended direction once that instrumentation exists: an SSE endpoint (`/api/stream/{run_id}`) proxying typed events to an activity-feed/task-board UI, matching the pattern used by `maf_multi_agent_new/frontend`. Revisit this once request/response is working and the event shape `workflow.py` should emit has been designed.
