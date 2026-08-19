from __future__ import annotations

import re

from fabric_qa.classify import Verdict

# Matches asset-style identifiers (ENG-001) and work-order-style ones
# (WO-1003) as a backstop, independent of which specific asset/verdicts
# the caller happened to pass in.
_IDENTIFIER_PATTERN = re.compile(r"\b[A-Z]{2,6}-\d{3,6}\b", re.IGNORECASE)


def sanitize_query(raw_query: str, *, asset_id: str, verdicts: list[Verdict]) -> str:
    sanitized = re.sub(re.escape(asset_id), "", raw_query, flags=re.IGNORECASE)
    for verdict in verdicts:
        # digit-boundary lookaround: strip "4.9" as its own token, not as a
        # substring of an unrelated number like "14.9"
        value_pattern = rf"(?<!\d){re.escape(str(verdict.value))}(?!\d)"
        sanitized = re.sub(value_pattern, "", sanitized)
    sanitized = _IDENTIFIER_PATTERN.sub("", sanitized)
    return " ".join(sanitized.split())
