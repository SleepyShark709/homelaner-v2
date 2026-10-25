"""Append recovered locomotion PSAs to the original 93-joint hero glTF.

The base pipeline (convert-original-animations.py + attach-combat-animations.py)
already produced the 18-clip hero.gltf. This script only appends the seven
missing AnimBP locomotion clips without touching geometry/skin/material or the
existing animations.

Run:
  python scripts/append-locomotion-animations.py
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import runpy
import struct

ROOT = Path(__file__).resolve().parents[1]
U = runpy.run_path(str(ROOT / "scripts" / "convert-original-animations.py"))
MODEL = ROOT / "public/assets/character/hero.gltf"
BIN = ROOT / "public/assets/character/directional-animations.bin"
REPORT = ROOT / "research/exports/locomotion/directional-validation.json"
CLIPS = [
    ROOT / "research/exports/locomotion-directional/AdvancedLocomotionV2/Characters/Mannequin/ActionMaleAnimation/ALS_N_Walk_B.psa",
    ROOT / "research/exports/locomotion-directional/AdvancedLocomotionV2/Characters/Mannequin/ActionMaleAnimation/ALS_N_Walk_FL.psa",
    ROOT / "research/exports/locomotion-directional/AdvancedLocomotionV2/Characters/Mannequin/ActionMaleAnimation/ALS_N_Walk_FR.psa",
    ROOT / "research/exports/locomotion-directional/AdvancedLocomotionV2/Characters/Mannequin/ActionMaleAnimation/ALS_N_Run_B.psa",
    ROOT / "research/exports/locomotion-directional/AdvancedLocomotionV2/Characters/Mannequin/ActionMaleAnimation/ALS_N_Run_FL.psa",
    ROOT / "research/exports/locomotion-directional/AdvancedLocomotionV2/Characters/Mannequin/ActionMaleAnimation/ALS_N_Run_FR.psa",
]
EXPECTED_EXISTING = 18


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    model = json.loads(MODEL.read_text(encoding="utf-8"))
    existing = {animation["name"] for animation in model["animations"]}
    assert len(existing) >= EXPECTED_EXISTING, "Unexpected base animation count"
    missing = [path for path in CLIPS if path.stem not in existing]
    assert missing, "No new directional clips to append"
    new_names = [path.stem for path in missing]
    assert not (set(new_names) & existing), f"Locomotion clips already present: {set(new_names) & existing}"
    joints = model["skins"][0]["joints"]
    names = {model["nodes"][index]["name"].casefold(): index for index in joints}
    root_node = joints[0]
    binary = bytearray()
    buffer_index = len(model["buffers"])

    def accessor(values, kind: str) -> int:
        while len(binary) % 4:
            binary.append(0)
        component = "SCALAR" if kind == "SCALAR" else kind
        width = 1 if component == "SCALAR" else (3 if component == "VEC3" else 4)
        flat = [value for row in values for value in row]
        assert all(math.isfinite(value) for value in flat)
        blob = struct.pack("<" + "f" * len(flat), *flat)
        view = len(model["bufferViews"])
        model["bufferViews"].append(
            dict(buffer=buffer_index, byteOffset=len(binary), byteLength=len(blob), target=34962)
        )
        index = len(model["accessors"])
        entry = dict(
            bufferView=view,
            componentType=5126,
            count=len(values),
            type=component,
        )
        if component == "SCALAR":
            entry.update(min=[min(flat)], max=[max(flat)])
        else:
            entry.update(
                min=[min(row[axis] for row in values) for axis in range(width)],
                max=[max(row[axis] for row in values) for axis in range(width)],
            )
        model["accessors"].append(entry)
        binary.extend(blob)
        return index

    report = {"source": "UModel PSA + config; appendix script", "clips": []}
    for psa in missing:
        config = psa.with_suffix(".config")
        bones, infos, keys = U["read_psa"](psa)
        rotation_only, translations, forced, removed = U["read_config"](config)
        mapping = [(i, names[name.casefold()]) for i, name in enumerate(bones) if name.casefold() in names]
        assert len(mapping) == len(joints), f"{psa.name}: only {len(mapping)}/{len(joints)} joints mapped"
        assert len(infos) == 1
        info = infos[0]
        count, rate = info["frames"], info["rate"]
        times = [[frame / rate] for frame in range(count)]
        assert all(times[i + 1][0] > times[i][0] for i in range(count - 1))
        time_accessor = accessor(times, "SCALAR")
        animation = dict(name=info["name"], samplers=[], channels=[])
        for bone, node in mapping:
            flag = removed.get(f"{info['name']}.{bone}", "")
            if flag not in ("", "all", "trans", "rot"):
                raise ValueError(f"Unsupported removed track flag {flag}")
            rows = [keys[(info["first_frame"] + frame) * len(bones) + bone] for frame in range(count)]
            positions = [U["position"](row) for row in rows]
            rotations = [U["rotation"](row, node == root_node) for row in rows]
            for frame in range(1, len(rotations)):
                if sum(a * b for a, b in zip(rotations[frame - 1], rotations[frame])) < 0:
                    rotations[frame] = [-value for value in rotations[frame]]
            allow_translation = (
                (not rotation_only or bones[bone].casefold() in translations)
                and bones[bone].casefold() not in forced
            )
            for path, values, kind, enabled in (
                ("translation", positions, "VEC3", allow_translation and flag not in ("all", "trans")),
                ("rotation", rotations, "VEC4", flag not in ("all", "rot")),
            ):
                if not enabled:
                    continue
                sampler = len(animation["samplers"])
                animation["samplers"].append(
                    dict(input=time_accessor, output=accessor(values, kind), interpolation="LINEAR")
                )
                animation["channels"].append(dict(sampler=sampler, target=dict(node=node, path=path)))
        assert animation["channels"]
        model["animations"].append(animation)
        report["clips"].append(
            dict(
                name=info["name"],
                frames=count,
                rate=rate,
                durationSeconds=times[-1][0],
                channelCount=len(animation["channels"]),
                mappedJoints=len(mapping),
                source=psa.relative_to(ROOT).as_posix(),
                sourceSha256=digest(psa),
            )
        )

    BIN.write_bytes(binary)
    model["buffers"].append(dict(uri=BIN.name, byteLength=len(binary)))
    model.setdefault("asset", {}).setdefault("extras", {})["directionalAnimationAppend"] = {
        "clips": new_names,
        "source": "research/exports/locomotion",
        "note": "UModel PSA + config appended; not AnimBP blending yet",
    }
    MODEL.write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    report["outputGltfSha256"] = digest(MODEL)
    report["outputBufferSha256"] = digest(BIN)
    report["animationCount"] = len(model["animations"])
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"animationCount": len(model["animations"]), "clips": report["clips"]}, indent=2))


if __name__ == "__main__":
    main()

