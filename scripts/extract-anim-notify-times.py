#!/usr/bin/env python3
"""Extract absolute AnimNotify times from decoded UAssetGUI AnimSequence JSON."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=ROOT / "research/rea-audit/decoded/Animations")
    parser.add_argument("--output", type=Path, default=ROOT / "research/world-recovery/notify-times.json")
    args = parser.parse_args()
    clips = {}
    for path in sorted(args.input.glob("*.json")):
        rows = extract(path)
        if rows:
            clips[path.stem] = rows
    report = {
        "source": "decoded UAssetGUI AnimSequence JSON",
        "note": "AnimNotifyEvent.LinkValue is the absolute sequence time; EndLink.LinkValue is the end time.",
        "clipCount": len(clips),
        "notifyCount": sum(len(rows) for rows in clips.values()),
        "notifyNames": sorted({row["notify"] for rows in clips.values() for row in rows}),
        "clips": clips,
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("clipCount", "notifyCount", "notifyNames")}, indent=2))


if __name__ == "__main__":
    main()
