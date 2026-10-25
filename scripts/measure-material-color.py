#!/usr/bin/env python3
"""Measure the same-camera facade stone region in the original and Web captures."""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageStat

ROOT = Path(__file__).resolve().parent.parent
ORIGINAL = ROOT / "research/runtime-observation/original-gameplay-start-final.png"
WEB = ROOT / "research/screenshots/building-clouds-tiling.jpg"
OUTPUT = ROOT / "research/world-recovery/material-color-samples.json"
BOX = (300, 130, 450, 500)


def load_original() -> Image.Image:
    image = Image.open(ORIGINAL).convert("RGB")
    # The capture includes a Windows title bar; align its content with the 1280x720 Web frame.
    return image.crop((0, 56, image.width, image.height)).resize((1280, 724), Image.LANCZOS)


def stats(image: Image.Image) -> dict[str, list[float]]:
    result = ImageStat.Stat(image.crop(BOX))
    return {
        "mean": [round(value, 1) for value in result.mean],
        "stddev": [round(value, 1) for value in result.stddev],
    }


def main() -> None:
    original = stats(load_original())
    web = stats(Image.open(WEB).convert("RGB").resize((1280, 724), Image.LANCZOS))
    output = {
        "sourceImages": {
            "original": str(ORIGINAL.relative_to(ROOT)),
            "web": str(WEB.relative_to(ROOT)),
        },
        "region": {"box": list(BOX), "description": "left facade pillar stone, excluding window glass and dark trim"},
        "means": {"original": original["mean"], "web": web["mean"]},
        "stddev": {"original": original["stddev"], "web": web["stddev"]},
        "deltaWebMinusOriginal": [round(w - o, 1) for w, o in zip(web["mean"], original["mean"])],
        "conclusion": "The Web stone is about 7 levels brighter and more red-biased (R-B=7.0) than the original neutral stone (R-B=1.8). Reducing the recovered TintB opacity would remove warmth but brighten it further, so the remaining gap is baked shadow/lightmap/grunge, not the base tint alone.",
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
