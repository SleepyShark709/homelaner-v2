"""Export the actual BP_ManCitizen assets and blueprint-referenced combat clips.

Uses installed portable tools; reads the game pak only. UE shaders are simplified
to glTF PBR using original exported diffuse textures, not recreated exactly.
"""
import argparse
import json
import math
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
OLD = Path("C:/Users/Shark/OneDrive/文档/ChatGPT/homerlander/analysis")
CONTENT = ROOT / "research/exports/unpacked/UNDEFEATED/Content"
RAW = ROOT / "research/exports/citizen"
PUBLIC = ROOT / "public/assets/citizen"
COMBAT = ROOT / "research/exports/combat-animations"
TOOLS = ROOT / "tools/asset-pipeline"
PAK = Path("E:/SteamLibrary/steamapps/common/UNDEFEATED/UNDEFEATED/Content/Paks/UNDEFEATED-WindowsNoEditor.pak")
U = runpy.run_path(str(ROOT / "scripts/convert-original-animations.py"))
MONTAGES = ["Hero_Attack1_Montage", "Hero_Attack2_Montage", "Hero_Attack3_Montage", "Hero_Attack4_Montage",
            "Hero_LongLAttack_Montage", "Hero_LongRAttack_Montage", "Hero_BackHandSlash_Montage", "Hero_FlashKick_Montage",
            "Hero_Smash_Montage", "Hero_SuperPunch_Montage", "Hero_AirKick_L_Montage", "Hero_AirKick_R_Montage",
            "Hero_AirSuperKick_Montage", "Hero_AirAttackStart_Montage"]


def execute(command, timeout=90):
    result = subprocess.run([str(x) for x in command], capture_output=True, timeout=timeout, cwd=ROOT,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        raise RuntimeError(result.stdout.decode(errors="replace")+result.stderr.decode(errors="replace"))
    return (result.stdout+result.stderr).decode(errors="replace")


def decode(source):
    with tempfile.TemporaryDirectory(prefix="undefeated-citizen-") as td:
        output = Path(td) / "asset.json"
        execute([TOOLS / "uasset-net472/UAssetGUI.exe", "tojson", source, output, "VER_UE4_27"])
        return json.loads(output.read_text(encoding="utf-8-sig"))


def import_path(doc, ref):
    if ref >= 0:
        return doc["Exports"][ref-1]["ObjectName"] if ref else None
    imp = doc["Imports"][-ref-1]
    outer = imp["OuterIndex"]
    return import_path(doc, outer)+"."+imp["ObjectName"] if outer else imp["ObjectName"]


def props(items, doc):
    result = {}
    for prop in items:
        value = prop.get("Value", prop.get("EnumValue"))
        if isinstance(value, list):
            value = [props(v.get("Value", []), doc) if isinstance(v.get("Value"), list)
                     else ({v.get("Name", "value"): v.get("Value", v.get("EnumValue"))}) for v in value]
        if "ObjectPropertyData" in prop.get("$type", ""):
            value = import_path(doc, value)
        result[prop.get("Name", "value")] = value
    return result


def export_asset(package, destination, animation=False):
    # Explicit package path avoids same-name sequences from the female citizen set.
    log = execute([TOOLS / "umodel.exe", "-export", "-game=ue4.27", "-psk" if animation else "-gltf", "-png",
                   "-path="+CONTENT.as_posix(), "-out="+destination.as_posix(), (CONTENT / package).as_posix()])
    checked_log = log if animation else log.replace("ERROR: glTF animation could be exported from mesh viewer only.", "")
    if "ERROR:" in checked_log:
        raise RuntimeError(log)
    destination.mkdir(parents=True, exist_ok=True)
    (destination / (Path(package).stem + ".export.log")).write_text(log, encoding="utf-8")
    return next(destination.rglob(Path(package).stem + (".psa" if animation else ".gltf")))


def publish_materials(source, output):
    doc = json.loads(source.read_text(encoding="utf-8"))
    output.mkdir(parents=True, exist_ok=True)
    for buffer in doc["buffers"]:
        shutil.copy2(source.parent / buffer["uri"], output / buffer["uri"])
    pngs = {p.stem.casefold(): p for p in (RAW / "mesh").rglob("*.png")}
    matfiles = {p.stem: p for p in (RAW / "mesh").rglob("*.mat")}
    propfiles = {p.name.removesuffix(".props.txt"): p for p in (RAW / "mesh").rglob("*.props.txt")}
    images, mappings = {}, []
    for material in doc["materials"]:
        name = material["name"]
        material["pbrMetallicRoughness"] = pbr = dict(baseColorFactor=[1, 1, 1, 1], metallicFactor=0, roughnessFactor=0.8)
        diffuse = None
        if name in matfiles:
            match = re.search(r"^Diffuse=(.+)$", matfiles[name].read_text(), re.M)
            if match:
                diffuse = match[1].strip()
        if name in propfiles:
            text = propfiles[name].read_text()
            match = re.search(r"Name=Color\s*\}.*?ParameterValue = \{ R=([\d.e-]+), G=([\d.e-]+), B=([\d.e-]+), A=([\d.e-]+)", text, re.S)
            if match:
                pbr["baseColorFactor"] = list(map(float, match.groups()))
        if name == "M_ShadowTrim":
            pbr["baseColorFactor"] = [0.006, 0.006, 0.006, 1]
        if diffuse and diffuse.casefold() in pngs:
            if diffuse not in images:
                file = pngs[diffuse.casefold()]
                (output / "textures").mkdir(exist_ok=True)
                shutil.copy2(file, output / "textures" / file.name)
                index = len(doc.setdefault("images", []))
                doc["images"].append(dict(uri="textures/"+file.name))
                doc.setdefault("textures", []).append(dict(source=index))
                images[diffuse] = index
            pbr["baseColorTexture"] = dict(index=images[diffuse])
        mappings.append(dict(material=name, sourceDiffuse=diffuse, textureConnected="baseColorTexture" in pbr,
                             baseColorFactor=pbr["baseColorFactor"]))
    out = output / "citizen-base.gltf"
    out.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    return out, mappings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--combat-only", action="store_true")
    args = parser.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    COMBAT.mkdir(parents=True, exist_ok=True)
    evidence = dict(source="Static UAssetAPI + official UModel exports, not runtime capture", citizen={}, combat=[])
    hero = json.loads((OLD / "decoded/HeroComponent.json").read_text(encoding="utf-8-sig"))
    actual_montages = {i["ObjectName"] for i in hero["Imports"] if i["ClassName"] == "AnimMontage"}
    assert set(MONTAGES) <= actual_montages
    # Decode references before deciding which raw sequences to export.
    sequences = set()
    for montage in MONTAGES:
        source = CONTENT / "-HeroGame/Player/Animations" / (montage+".uasset")
        doc = decode(source)
        refs = [import_path(doc, -(i+1)) for i, imp in enumerate(doc["Imports"]) if imp["ClassName"] == "AnimSequence"]
        sequence_packages = [r.split(".")[0].removeprefix("/Game/") for r in refs]
        sequences.update(sequence_packages)
        exported = [{"name": e["ObjectName"], "class": import_path(doc, e["ClassIndex"]), "data": props(e.get("Data", []), doc)} for e in doc["Exports"]]
        evidence["combat"].append(dict(montage=montage, sourceSha256=U["digest"](source), sequences=sequence_packages,
                                       decodedExports=exported))
    needed = [p for s in sequences for p in [s+".uasset", s+".uexp"] if not (CONTENT / p).exists()]
    if needed:
        command = [TOOLS / "bin/repak.exe", "unpack", PAK, "-o", ROOT / "research/exports/unpacked"]
        for path in needed:
            command += ["-i", "UNDEFEATED/Content/"+path]
        execute(command)
    exported_sequences = []
    for package in sorted(sequences):
        psa = export_asset(package+".uasset", COMBAT, True)
        bones, infos, keys = U["read_psa"](psa)
        raw_sequence = CONTENT / (package+".uasset")
        decoded_sequence = decode(raw_sequence)
        sequence_metadata = []
        retained = {"Notifies", "SequenceLength", "NumFrames", "RateScale", "AdditiveAnimType", "RefPoseType", "RefPoseSeq", "RefFrameIndex", "bEnableRootMotion"}
        for export in decoded_sequence["Exports"]:
            data = export.get("Data", [])
            if "AnimSequence" in import_path(decoded_sequence, export["ClassIndex"]):
                data = [p for p in data if p["Name"] in retained]
            sequence_metadata.append(dict(name=export["ObjectName"], className=import_path(decoded_sequence, export["ClassIndex"]),
                                          data=props(data, decoded_sequence)))
        exported_sequences.append(dict(package=package, file=str(psa.relative_to(ROOT)), sha256=U["digest"](psa),
            sourceAssetSha256=U["digest"](raw_sequence), decodedExports=sequence_metadata,
            bones=len(bones), clips=[dict(name=i["name"], frames=i["frames"], fps=i["rate"],
            lastKeySeconds=(i["frames"]-1)/i["rate"], nominalSeconds=i["frames"]/i["rate"]) for i in infos]))
    evidence["combatSequences"] = exported_sequences
    (COMBAT / "manifest.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Exported combat sequences:", len(exported_sequences))
    if args.combat_only:
        return

    bp_source = next((OLD / "extracted-systems").rglob("BP_ManCitizen.uasset"))
    anim_source = next((OLD / "extracted-systems").rglob("Citizen_AnimBP.uasset"))
    bp, anim = decode(bp_source), decode(anim_source)
    mesh_export = next(e for e in bp["Exports"] if e["ObjectName"] == "CharacterMesh0")
    mesh_ref = next(p["Value"] for p in mesh_export["Data"] if p["Name"] == "SkeletalMesh")
    mesh_package = import_path(bp, mesh_ref).split(".")[0].removeprefix("/Game/")
    execute([TOOLS / "bin/repak.exe", "unpack", PAK, "-o", ROOT / "research/exports/unpacked",
             "-i", "UNDEFEATED/Content/-HeroGame/Animations/Citizen/"])
    blend_source = CONTENT / "-HeroGame/Animations/Citizen/Citizen_MoveGround.uasset"
    blend = decode(blend_source)
    clips = ["Citizen_N_Idle_Pose", "Citizen_N_Walk_F", "Citizen_N_Run_F"]
    assert clips[0] in {i["ObjectName"] for i in anim["Imports"] if i["ClassName"] == "AnimSequence"}
    assert set(clips[1:]) <= {i["ObjectName"] for i in blend["Imports"] if i["ClassName"] == "AnimSequence"}
    mesh = export_asset(mesh_package+".uasset", RAW / "mesh")
    psas = [export_asset("-HeroGame/Animations/Citizen/"+name+".uasset", RAW / "animations", True) for name in clips]
    base, materials = publish_materials(mesh, RAW / "prepared")
    # Invoke the generic name-mapped converter with this mesh + these exact PSAs;
    # only its entry-point globals change in this process, never the source file.
    conversion_main = U["main"]
    conversion_main.__globals__["CLIPS"] = psas
    argv = sys.argv
    try:
        sys.argv = ["convert-original-animations.py", "--mesh", str(base), "--output", str(PUBLIC)]
        conversion_main()
    finally:
        sys.argv = argv
    published = PUBLIC / "citizen.gltf"
    (PUBLIC / "hero.gltf").replace(published)
    doc = json.loads(published.read_text(encoding="utf-8"))
    doc["asset"].setdefault("extras", {})["citizen"] = dict(sourceBlueprint="BP_ManCitizen", sourceMesh=mesh_package,
        forwardAxis="+Z", upAxis="+Y", units="meters", clips=clips,
        note="Original default body mesh and textures; idle pose only, additive breathing layer not combined; optional randomized hair/eyewear not assembled.")
    published.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    validation = json.loads((PUBLIC / "validation.json").read_text(encoding="utf-8"))
    validation["outputGltfSha256"] = U["digest"](published)
    (PUBLIC / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    positions = [doc["accessors"][p["attributes"]["POSITION"]] for p in doc["meshes"][0]["primitives"]]
    box = dict(min=[min(a["min"][k] for a in positions) for k in range(3)], max=[max(a["max"][k] for a in positions) for k in range(3)])
    buffers = [(PUBLIC / b["uri"]).read_bytes() for b in doc["buffers"]]
    deviations = {}
    quaternion_error = 0
    for animation in doc["animations"]:
        deviation, targets = 0, set()
        for channel in animation["channels"]:
            target = (channel["target"]["node"], channel["target"]["path"])
            assert target not in targets
            targets.add(target)
            sampler = animation["samplers"][channel["sampler"]]
            times = U["read_accessor"](doc, buffers, sampler["input"])
            values = U["read_accessor"](doc, buffers, sampler["output"])
            assert len(times) == len(values)
            assert all(times[i][0] < times[i+1][0] for i in range(len(times)-1))
            assert all(math.isfinite(v) for row in values for v in row)
            deviation = max(deviation, max(abs(x-y) for row in values for x, y in zip(row, values[0])))
            if target[1] == "rotation":
                quaternion_error = max(quaternion_error, max(abs(sum(v*v for v in row)-1) for row in values))
        deviations[animation["name"]] = deviation
    assert quaternion_error < 1e-6
    evidence["citizen"] = dict(blueprint=str(bp_source), blueprintSha256=U["digest"](bp_source),
        meshComponent=props(mesh_export["Data"], bp), animationBlueprint=str(anim_source), animationBlueprintSha256=U["digest"](anim_source),
        blendSpace=str(blend_source), blendSpaceSha256=U["digest"](blend_source),
        blendData=[dict(name=e["ObjectName"], data=props(e.get("Data", []), blend)) for e in blend["Exports"]],
        meshPackage=mesh_package, sourceMeshGltf=str(mesh), sourceMeshSha256=U["digest"](mesh),
        sourceCookedAssetSha256=U["digest"](CONTENT / (mesh_package+".uasset")),
        sourceCookedExportSha256=U["digest"](CONTENT / (mesh_package+".uexp")),
        materials=materials, output=str(published), sha256=U["digest"](published),
        joints=len(doc["skins"][0]["joints"]), forwardAxis="+Z", upAxis="+Y", units="meters", meshBounds=box,
        clips=validation["clips"], checks=dict(serializedAnimationFinite=True, uniqueTargets=True, monotonicTimes=True,
        matchingKeyCounts=True, maximumQuaternionSquaredNormError=quaternion_error, maximumDeviationFromFirstFrame=deviations),
        limitations=["Idle_Pose has 31 identical source frames; original additive breathing has not been combined.",
        "This sample uses the original default body mesh, not all randomized wardrobe/hair variants.", "Original textures connected to simplified PBR; UE material graphs and skin subsurface shading not reproduced."])
    (ROOT / "research/evidence/citizen-assets.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: evidence["citizen"][k] for k in ("output", "joints", "meshBounds")}, indent=2))


if __name__ == "__main__":
    main()
