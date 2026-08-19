from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Verdict:
    parameter: str
    value: float
    health: str

    @property
    def is_abnormal(self) -> bool:
        return self.health != "Normal"


def classify(value: float, spec: dict) -> str:
    if _breaches(value, spec.get("alarm", {})):
        return "Alarm"
    if _breaches(value, spec.get("advisory", {})):
        return "Advisory"
    return "Normal"


def _breaches(value: float, bound: dict) -> bool:
    if "min" in bound and value < bound["min"]:
        return True
    if "max" in bound and value > bound["max"]:
        return True
    return False
