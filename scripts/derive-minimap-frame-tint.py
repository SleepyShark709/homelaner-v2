#!/usr/bin/env python3
"""Recolor the recovered minimap frame alpha to the start-state red."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "public/assets/world/minimap/frame-tint.png"
OUTPUT = ROOT / "public/assets/world/minimap/frame-tint-red.png"
EVIDENCE = ROOT / "research/world-recovery/minimap-frame-tint.json"
RGB = (178, 28, 20)

image = Image.open(SOURCE).convert("RGBA")
data = np.asarray(image)
out = np.zeros_like(data)
out[..., 0], out[..., 1], out[..., 2] = RGB
out[..., 3] = data[..., 3]
Image.fromarray(out, "RGBA").save(OUTPUT)
EVIDENCE.write_text(json.dumps({
    "source": str(SOURCE.relative_to(ROOT)),
    "sourceSha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    "output": str(OUTPUT.relative_to(ROOT)),
    "outputSha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
    "rgb": RGB,
    "method": "preserve recovered frame alpha, replace RGB with start-state red",
    "evidence": "The original gameplay-start capture (research/runtime-observation/original-gameplay-start-final.png) shows the red anger/alert minimap frame; the green/brown frame-tint.png does not match that state.",
}, indent=2) + "\n", encoding="utf-8")
print(OUTPUT.relative_to(ROOT))
