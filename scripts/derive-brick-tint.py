#!/usr/bin/env python3
"""Derive the brick_02_TintB_Inst2 albedo from the recovered tint parameters.

The cooked instance stores Tint Colour=(.06,.021616,.001713) linear and
Tint Opacity=.633027.  Applying the full opacity uniformly made the same-camera
mean luma 49.4 instead of the original 55.8, because the parent -Tilable_mat
tint layering/mask is not reconstructed.  This script applies a luma-calibrated
fraction (0.28 of the recovered opacity) and uses the texture alpha as a
per-texel weight.  The result is a derived asset, not a recovered original.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "public/assets/world/textures/Game/UrbanCity/Textures/Tileable/brick_02_d.png"
OUTPUT = SOURCE.with_name("brick_02_d_tintB.png")
EVIDENCE = ROOT / "research/world-recovery/brick-tint-derivation.json"
TINT = np.array([0.05999999865889549, 0.021616000682115555, 0.0017130000051110983], dtype=np.float32)
RECOVERED_OPACITY = 0.6330270171165466
TINT_SCALE = 0.28


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tint-scale", type=float, default=TINT_SCALE)
    args = parser.parse_args()
    opacity = RECOVERED_OPACITY * args.tint_scale
    image = Image.open(SOURCE).convert("RGBA")
    data = np.asarray(image).astype(np.float32) / 255.0
    rgb, mask = data[..., :3], data[..., 3]
    linear = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    amount = opacity * mask
    mixed = linear * (1 - amount[..., None]) + TINT * amount[..., None]
    srgb = np.where(mixed <= 0.0031308, mixed * 12.92, 1.055 * np.power(np.clip(mixed, 0, 1), 1 / 2.4) - 0.055)
    result = np.dstack([np.clip(srgb, 0, 1), mask]) * 255.0
    Image.fromarray(np.round(result).astype(np.uint8), "RGBA").save(OUTPUT)
    sha = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
    EVIDENCE.write_text(json.dumps({
        "source": str(SOURCE.relative_to(ROOT)),
        "sourceSha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "output": str(OUTPUT.relative_to(ROOT)),
        "outputSha256": sha,
        "tintColourLinear": TINT.tolist(),
        "recoveredTintOpacity": RECOVERED_OPACITY,
        "effectiveTintOpacity": opacity,
        "tintScale": args.tint_scale,
        "mask": "source alpha (0..170) used as per-texel tint weight",
        "formula": "linear(sRGB) blended toward tint by effectiveTintOpacity * (alpha/255), then back to sRGB; alpha preserved",
        "note": "Derived for same-camera comparison. The parent -Tilable_mat tint layering/mask is not reconstructed; .28 is a luma calibration, not a recovered value.",
    }, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT.relative_to(ROOT)), "sha256": sha, "effectiveTintOpacity": opacity}, indent=2))


if __name__ == "__main__":
    main()
