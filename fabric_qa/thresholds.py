from __future__ import annotations

import json
from pathlib import Path

THRESHOLDS_DIR = Path(__file__).resolve().parent.parent / "data" / "thresholds"


def load_thresholds(asset_model: str) -> dict[str, dict]:
    data = json.loads((THRESHOLDS_DIR / f"{asset_model}.json").read_text())
    return {param["name"]: param for param in data["parameters"]}
