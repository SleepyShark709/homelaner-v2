#!/usr/bin/env python3
"""Derive the Tilable_metal_TintC_Inst albedo from the recovered tint parameters."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "public/assets/world/textures/Game/UrbanCity/Textures/Tileable/metal_01_d.png"
OUTPUT = SOURCE.with_name("metal_01_d_tintC.png")
EVIDENCE = ROOT / "research/world-recovery/metal-tint-derivation.json"
TINT = np.array([0.014290999621152878, 0.01677599921822548, 0.04500000178813934], dtype=np.float32)
OPACITY = 0.898036003112793

image = Image.open(SOURCE).convert("RGBA")
data = np.asarray(image).astype(np.float32) / 255.0
rgb, mask = data[..., :3], data[..., 3]
linear = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
amount = OPACITY * mask
mixed = linear * (1 - amount[..., None]) + TINT * amount[..., None]
srgb = np.where(mixed <= 0.0031308, mixed * 12.92, 1.055 * np.power(np.clip(mixed, 0, 1), 1 / 2.4) - 0.055)
result = np.dstack([np.clip(srgb, 0, 1), mask]) * 255.0
Image.fromarray(np.round(result).astype(np.uint8), "RGBA").save(OUTPUT)
EVIDENCE.write_text(json.dumps({
    "source": str(SOURCE.relative_to(ROOT)),
    "sourceSha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    "output": str(OUTPUT.relative_to(ROOT)),
    "outputSha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
    "tintColourLinear": TINT.tolist(),
    "tintOpacity": OPACITY,
    "mask": "source alpha as per-texel weight",
    "formula": "linear(sRGB) blended toward tint by tintOpacity*(alpha/255), then back to sRGB; alpha preserved",
    "note": "Derived texture for Tilable_metal_TintC_Inst; parent -Tilable_mat detail-normal/roughness graph is not reconstructed.",
}, indent=2) + "\n", encoding="utf-8")
print(OUTPUT.relative_to(ROOT))
