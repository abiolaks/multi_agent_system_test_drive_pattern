from __future__ import annotations

import re

from fabric_qa.classify import Verdict

# Matches asset-style identifiers (ENG-001) and work-order-style ones
# (WO-1003) as a backstop, independent of which specific asset/verdicts
# the caller happened to pass in.
_IDENTIFIER_PATTERN = re.compile(r"\b[A-Z]{2,6}-\d{3,6}\b")


def sanitize_query(raw_query: str, *, asset_id: str, verdicts: list[Verdict]) -> str:
    sanitized = re.sub(re.escape(asset_id), "", raw_query, flags=re.IGNORECASE)
    for verdict in verdicts:
        sanitized = re.sub(re.escape(str(verdict.value)), "", sanitized)
    sanitized = _IDENTIFIER_PATTERN.sub("", sanitized)
    return " ".join(sanitized.split())
