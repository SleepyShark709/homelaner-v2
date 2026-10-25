#!/usr/bin/env python3
"""Measure Rec.709 luma mean/std for screenshots."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image


def measure(path: Path) -> dict:
    image = Image.open(path).convert("RGB")
    pixels = np.asarray(image, dtype=np.float64)
    luma = 0.2126 * pixels[:, :, 0] + 0.7152 * pixels[:, :, 1] + 0.0722 * pixels[:, :, 2]
    return {
        "path": str(path),
        "width": image.width,
        "height": image.height,
        "mean": round(float(luma.mean()), 2),
        "std": round(float(luma.std()), 2),
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: measure-luma.py IMAGE [IMAGE...]")
    for argument in sys.argv[1:]:
        print(measure(Path(argument)))
