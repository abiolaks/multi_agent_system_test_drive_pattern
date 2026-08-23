# Per-reading Health verdicts are code; Fault-Signature diagnosis is the LLM

Comparing each Reading against its Threshold to produce a per-reading Health verdict (Normal / Advisory / Alarm) is done in deterministic code, not by the LLM. The model receives the per-reading verdicts plus the retrieved Guidance and produces the Fault-Signature diagnosis and Recommendations. Exact numeric comparisons are error-prone for self-hosted 32B–70B models and health classification must be reliable, so per-reading classification lives in testable code; matching the multi-reading pattern to a Fault Signature and writing the narrative are the LLM's job.



## Known Limitation: Router-Dependent Enforcement

  This ADR's guarantee — that asset health status is always determined by
  `classify()`, never by LLM judgment — is enforced only within the Asset
  Health chain. It is not a property of the system as a whole; it holds
  conditional on the Router (ADR 0001) correctly classifying health-status
  requests into that chain.

  If a health-status request is misrouted, or phrased ambiguously enough
  that the Router sends it to the general Q&A chain instead, `classify()`
  is never called — that step exists only in the Asset Health chain, not
  as a shared/common step. The Q&A chain would hand raw readings to an
  LLM and let it answer in free text, which is exactly the outcome this
  ADR exists to prevent.

  **Mitigation (pick one, to be decided):**
  - Force a `classify()` call on any Q&A-chain data pull that touches a
    monitored asset's readings, before the LLM formats a response, or
  - Narrow the Q&A chain's scope so it never answers questions about a
    monitored asset's status directly — it redirects such requests into
    the Asset Health chain instead.

  **Consequence for testing:** Router accuracy on health-status-flavored
  phrasing (e.g. "how's engine 3 doing" vs. "what's the temperature trend
  for engine 3") must be evaluated as a safety property of this ADR, not
  just as a routing/UX quality metric.