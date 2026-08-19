from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Topic = Literal["asset_health", "general_data"]


@dataclass
class RouterDecision:
    topic: Topic
    asset_id: str | None = None
    recurring: bool = False
    interval: str | None = None
