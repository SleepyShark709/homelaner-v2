#!/usr/bin/env python3
"""Inspect an exported lightmap DDS and test the mislabeled-BC6H hypothesis."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dds")
    parser.add_argument("--out", default="research/screenshots")
    args = parser.parse_args()
    source = Path(args.dds)
    data = source.read_bytes()
    header = data[:128]
    width = int.from_bytes(header[16:20], "little")
    height = int.from_bytes(header[12:16], "little")
    fourcc = header[84:88].decode("latin1")
    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    image = Image.open(source)
    image.convert("RGB").save(out / "lightmap-dxt5.png")
    bc6 = None
    try:
        import texture2ddecoder  # optional research dependency

        raw = texture2ddecoder.decode_bc6(data[128:], width, height)
        rgba = np.frombuffer(raw, dtype=np.uint8).reshape((height, width, 4)).astype(np.float32)
        rgb = rgba[..., :3] / 255.0
        lo, hi = np.percentile(rgb, 1), np.percentile(rgb, 99)
        stretched = np.clip((rgb - lo) / max(1e-6, hi - lo), 0, 1)
        Image.fromarray((np.power(stretched, 1 / 2.2) * 255).astype(np.uint8)).save(out / "lightmap-bc6.png")
        bc6 = "colour noise; see lightmap-bc6.png"
    except ImportError:
        bc6 = "texture2ddecoder not installed; BC6H check skipped"
    report = {
        "dds": str(source),
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "width": width,
        "height": height,
        "fourCC": fourcc,
        "dxt5Decode": "see lightmap-dxt5.png",
        "bc6hDecode": bc6,
    }
    (ROOT / "research/world-recovery/lightmap-dds-inspection.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
