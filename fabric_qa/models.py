from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Report:
    summary: str
    images: list[bytes] = field(default_factory=list)


@dataclass
class FabricResult:
    data: Any
    images: list[bytes] = field(default_factory=list)


@dataclass
class EmailDraft:
    report: Report
    sent: bool = False
