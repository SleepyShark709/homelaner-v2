#!/usr/bin/env python3
"""Extract notify names from UModel animation property dumps."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "research/world-recovery/animation-notify-manifest.json"
SEARCH = [
    ROOT / "research/exports/locomotion",
    ROOT / "research/exports/locomotion-directional",
    ROOT / "research/exports/fly-directional",
    ROOT / "research/exports/jump-extra",
]
entries = []
for directory in SEARCH:
    for props in sorted(directory.rglob("*.props.txt")):
        text = props.read_text(encoding="utf-8", errors="replace")
        names = re.findall(r"NotifyName\s*=\s*([A-Za-z0-9_]+)", text)
        durations = re.findall(r"Duration\s*=\s*([0-9.+-]+)", text)
        entries.append({
            "clip": props.name.removesuffix(".props.txt"),
            "source": str(props.relative_to(ROOT)),
            "notifies": sorted(set(names)),
            "notifyCount": len(names),
            "note": "UModel props serialize TriggerTimeOffset (0) but not the absolute TriggerTime; absolute times require the AnimSequence notify array.",
        })
report = {
    "source": "UModel .props.txt animation dumps",
    "clipCount": len(entries),
    "notifyNames": sorted({name for entry in entries for name in entry["notifies"]}),
    "clips": entries,
}
OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"clipCount": len(entries), "notifyNames": report["notifyNames"]}, indent=2))
