#!/usr/bin/env python3
"""Connect evidence-proven fixed texture samples to material channels.

Only materials whose cooked shader resource table and PS sample usage identify
the texture role are listed here. The generated material manifest intentionally
does not guess roles from texture file names; this post-pass adds the few roles
that the DXBC evidence proves.

Run after restore-world-materials / restore-evidenced-shaders:
  python tools/asset-pipeline/restore-texture-sample-materials.py
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "public/assets/world/material-manifest.json"
OUT = ROOT / "research/world-recovery/material-shader-recovery/texture-sample-recovery.json"

RECOVERIES = [
    {
        "material": "/Game/UrbanCity/Materials/Tileable/Concrete_Tile_mat",
        "decoded": ROOT / "research/rea-audit/decoded-world-assets/UNDEFEATED/Content/UrbanCity/Materials/Tileable/Concrete_Tile_mat.json",
        "shader_dir": ROOT / "research/world-recovery/material-shader-recovery/Concrete_Tile_mat",
        "shader": "shader-0-ps_5_0.asm",
        "textures": {
            "baseColor": "/Game/UrbanCity/Textures/Tileable/Concrete_Tile_A",
            "normal": "/Game/UrbanCity/Textures/Tileable/Concrete_Tile_N",
            "compact": "/Game/UrbanCity/Textures/Tileable/Concrete_Tile_C",
        },
        # The PS samples t9 (A) into the material Color product and writes it
        # to o2, t8 (N) into the normal reconstruction written to o1.
        "shader_evidence": [
            "sample_b_indexable(texture2d)(float,float,float,float) r3.xy, v3.xyxx, t8.xyzw",
            "sample_b_indexable(texture2d)(float,float,float,float) r4.xyz, v3.xyxx, t9.xyzw",
            "mul_sat r4.xyz, r4.xyzx, cb3[3].xyzx",
            "mad o1.xyz, r0.xyzx, l(0.500000, 0.500000, 0.500000, 0.000000)",
            "mov o2.xyz, r4.xyzx",
        ],
    }
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def texture_url(package: str) -> str:
    assert package.startswith("/Game/")
    return "/assets/world/textures/" + package[1:] + ".png"


def verify_binding(shader_dir: Path, shader_file: str, defaults: dict[int, str]) -> dict[int, str]:
    index = json.loads((shader_dir / "index.json").read_text(encoding="utf-8"))
    uniforms = json.loads((shader_dir / "uniforms.json").read_text(encoding="utf-8"))
    shader = next(item for item in index["shaders"] if Path(item["assemblyFile"]).name == shader_file)
    groups: dict[int, list[dict]] = {}
    for bind in shader["resourceTable"]["textureBindings"]:
        groups.setdefault(bind["constantBuffer"], []).append(bind)
    expected = list(range(0, 2 * len(uniforms["textureParameters2D"]), 2))
    candidates = [binds for binds in groups.values() if sorted({b["resourceIndex"] for b in binds}) == expected]
    assert len(candidates) == 1, f"texture binding group is not unique for {shader_file}"
    mapping = {}
    for bind in candidates[0]:
        parameter = uniforms["textureParameters2D"][bind["resourceIndex"] // 2]
        mapping[bind["bindIndex"]] = parameter["defaultTextureObject"]
    assert mapping == defaults, f"unexpected texture binding map: {mapping}"
    return mapping


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    evidence = {
        "schemaVersion": 1,
        "method": "cooked material CachedExpressionData + D3D11 resource table + DXBC PS sample usage",
        "source": "UAssetAPI decoded package, UModel extracted material shader map; not REA native decompilation",
        "manifestBeforeSha256": sha256(MANIFEST),
        "materials": [],
        "unresolved": [
            "Compact (Concrete_Tile_C) is bound by the original PS but its channel packing is not established; it is not bound as ORM.",
            "Original shader UV transforms, detail normal and fog/lighting are not reconstructed.",
        ],
    }
    for recovery in RECOVERIES:
        material_key = recovery["material"]
        record = manifest["materials"].get(material_key)
        if record is None:
            raise SystemExit(f"material missing: {material_key}")
        defaults = {8: recovery["textures"]["normal"], 9: recovery["textures"]["baseColor"], 10: recovery["textures"]["compact"]}
        mapping = verify_binding(recovery["shader_dir"], recovery["shader"], defaults)
        shader_path = recovery["shader_dir"] / recovery["shader"]
        text = shader_path.read_text(encoding="utf-8")
        for line in recovery["shader_evidence"]:
            assert line in text, f"shader evidence missing: {line}"
        decoded_text = recovery["decoded"].read_text(encoding="utf-8")
        for package in recovery["textures"].values():
            assert package in decoded_text, f"decoded material does not reference {package}"
        for role in ("baseColor", "normal"):
            package = recovery["textures"][role]
            url = texture_url(package)
            assert (ROOT / "public" / url.lstrip("/")).exists(), f"texture not published: {url}"
            if role == "baseColor":
                channel = {
                    "texturePackage": package,
                    "url": url,
                    "colorSpace": "srgb",
                    "channel": "rgb",
                    "texCoord": 0,
                    "sourceParameter": "MaterialExpressionTextureSample (fixed reference)",
                    "mappingBasis": "DXBC t9 sample multiplied by material Color and written to base-color target; cooked material did not serialize a BaseColor input",
                    "uvMappingStatus": "mesh UV0 projection; original shader UV math not reconstructed",
                }
            else:
                channel = {
                    "texturePackage": package,
                    "url": url,
                    "colorSpace": "linear",
                    "channel": "rgb",
                    "texCoord": 0,
                    "sourceParameter": "MaterialExpressionTextureSample_0",
                    "mappingBasis": "DXBC t8 normal decode; cooked material serialized Normal input to the same texture",
                    "uvMappingStatus": "mesh UV0 projection; original shader UV math not reconstructed",
                    "normalConvention": "directx",
                }
            record.setdefault("channels", {})[role] = channel
        record["textureSampleRecovery"] = {
            "method": evidence["method"],
            "shader": str(shader_path.relative_to(ROOT)).replace("\\", "/"),
            "shaderSha256": sha256(shader_path),
            "textureBindings": {f"t{bind}": package for bind, package in sorted(mapping.items())},
            "connected": ["baseColor", "normal"],
            "notConnected": ["compact"],
        }
        evidence["materials"].append(
            {
                "material": material_key,
                "connected": ["baseColor", "normal"],
                "textures": {role: recovery["textures"][role] for role in ("baseColor", "normal")},
                "shader": str(shader_path.relative_to(ROOT)).replace("\\", "/"),
                "shaderSha256": sha256(shader_path),
            }
        )
        print(f"connected {material_key}: baseColor={recovery['textures']['baseColor']} normal={recovery['textures']['normal']}")
    evidence["manifestAfterSha256"] = hashlib.sha256(json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")).hexdigest()
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
