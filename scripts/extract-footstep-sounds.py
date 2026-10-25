#!/usr/bin/env python3
"""Extract embedded Ogg payloads from cooked UE4 SoundWave .uexp files."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "public/assets/audio")
    parser.add_argument("--manifest", type=Path, default=ROOT / "research/world-recovery/footstep-sound-manifest.json")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    entries = []
    for uexp in sorted(args.input.rglob("*.uexp")):
        payload = uexp.read_bytes()
        offset = payload.find(b"OggS")
        if offset < 0:
            continue
        ogg = payload[offset:]
        target = args.output / f"{uexp.stem.lower()}.ogg"
        target.write_bytes(ogg)
        entries.append({
            "name": uexp.stem,
            "file": str(target.relative_to(ROOT)),
            "bytes": len(ogg),
            "oggOffsetInUexp": offset,
            "sha256": hashlib.sha256(ogg).hexdigest(),
            "source": str(uexp),
        })
    manifest = {
        "source": "cooked UNDEFEATED SoundWave .uexp files, embedded Ogg payload",
        "clipCount": len(entries),
        "clips": entries,
    }
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"clipCount": len(entries), "files": [item["name"] for item in entries]}, indent=2))


if __name__ == "__main__":
    main()
