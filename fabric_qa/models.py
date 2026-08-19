from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fabric_qa.classify import Verdict


@dataclass
class Recommendation:
    fault_signature: str
    next_step: str
    citation: str


@dataclass
class MaintenanceRecord:
    work_order_id: str
    date: str
    finding: str
    parts_replaced: str


@dataclass
class DiagnosisResult:
    summary: str
    what_data_shows: str
    what_guidance_says: str
    combined_finding: str
    recommendation: Recommendation
    caveats: str


@dataclass
class Report:
    summary: str
    images: list[bytes] = field(default_factory=list)
    verdicts: list[Verdict] = field(default_factory=list)
    diagnosis: DiagnosisResult | None = None


@dataclass
class FabricResult:
    data: Any
    images: list[bytes] = field(default_factory=list)


@dataclass
class Reading:
    parameter: str
    value: float


@dataclass
class AssetReadings:
    asset_id: str
    asset_model: str
    readings: list[Reading]


@dataclass
class EmailDraft:
    report: Report
    sent: bool = False
