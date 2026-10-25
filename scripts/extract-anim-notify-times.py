#!/usr/bin/env python3
"""Extract absolute AnimNotify times from decoded UAssetGUI AnimSequence JSON."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = [
    ROOT / "research/rea-audit/decoded/Animations/Hero_StartSprint.json",
    ROOT / "research/rea-audit/decoded/Animations/Hero_Stopping_Sprint.json",
]
OUTPUT = ROOT / "research/world-recovery/notify-times.json"


def extract(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    for export in data.get("Exports", []):
        for prop in export.get("Data", []) or []:
            if prop.get("Name") != "Notifies":
                continue
            for event in prop.get("Value", []) or []:
                fields = {item.get("Name"): item.get("Value") for item in event.get("Value", []) or []}
                end = {item.get("Name"): item.get("Value") for item in fields.get("EndLink", []) or []}
                rows.append({
                    "notify": fields.get("NotifyName"),
                    "time": fields.get("LinkValue"),
                    "end": end.get("LinkValue"),
                    "duration": fields.get("Duration"),
                    "track": fields.get("TrackIndex"),
                })
    return rows


report = {
    "source": "decoded UAssetGUI AnimSequence JSON",
    "note": "AnimNotifyEvent.LinkValue is the absolute sequence time; EndLink.LinkValue is the end time.",
    "clips": {path.stem: extract(path) for path in SOURCES},
}
OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2))
