"""Attach original hair/glasses at the socket decoded from the shipped skeleton.

Keeps all four source animations, the original 93-joint hero skin and each
accessory's original two-joint skin. No vertex data or animation is regenerated.
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import runpy
import shutil
import subprocess
import tempfile
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
UTIL = runpy.run_path(str(ROOT / "scripts/convert-original-animations.py"))


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def properties(export):
    result = {}
    for item in export.get("Data", []):
        value = item.get("Value")
        if item.get("StructType") in ("Vector", "Rotator"):
            value = {k: float(v) for k, v in value[0]["Value"].items() if k != "$type"}
        result[item["Name"]] = value
    return result


def ue_transform(props):
    """UE FRotator -> quaternion, then B R B^-1 for B(x,y,z)=(x,z,y)."""
    rot = props.get("RelativeRotation", {})
    pitch, yaw, roll = [math.radians(rot.get(k, 0))*0.5 for k in ("Pitch", "Yaw", "Roll")]
    sp, cp, sy, cy, sr, cr = math.sin(pitch), math.cos(pitch), math.sin(yaw), math.cos(yaw), math.sin(roll), math.cos(roll)
    q = [cr*sp*sy-sr*cp*cy, -cr*sp*cy-sr*cp*sy, cr*cp*sy-sr*sp*cy, cr*cp*cy+sr*sp*sy]
    loc = props.get("RelativeLocation", {})
    scale = props.get("RelativeScale", props.get("RelativeScale3D", {}))
    return dict(translation=[loc.get(k, 0)*0.01 for k in ("X", "Z", "Y")],
                rotation=[-q[0], -q[2], -q[1], q[3]],
                scale=[scale.get(k, 1) for k in ("X", "Z", "Y")])


def bounds(points):
    return dict(min=[min(p[i] for p in points) for i in range(3)], max=[max(p[i] for p in points) for i in range(3)])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--player-json", type=Path, default=ROOT / "research/exports/decoded/PlayerBP.json")
    parser.add_argument("--pak", type=Path, default=Path("E:/SteamLibrary/steamapps/common/UNDEFEATED/UNDEFEATED/Content/Paks/UNDEFEATED-WindowsNoEditor.pak"))
    args = parser.parse_args()
    output = ROOT / "public/assets/character"
    output.mkdir(parents=True, exist_ok=True)
    skeleton = ROOT / "research/exports/unpacked/UNDEFEATED/Content/Action_Male/Meshes/SKEL_Male.uasset"
    decoder = ROOT / "tools/asset-pipeline/uasset-net472/UAssetGUI.exe"
    if not args.player_json.exists():
        args.player_json.parent.mkdir(parents=True, exist_ok=True)
        unpacked = ROOT / "research/exports/unpacked"
        package = "UNDEFEATED/Content/-HeroGame/Player/PlayerBP"
        subprocess.run([str(ROOT / "tools/asset-pipeline/bin/repak.exe"), "unpack", str(args.pak), "-o", str(unpacked),
                        "-i", package + ".uasset", "-i", package + ".uexp"], check=True, capture_output=True,
                       timeout=120, creationflags=subprocess.CREATE_NO_WINDOW)
        subprocess.run([str(decoder), "tojson", str(unpacked / (package + ".uasset")), str(args.player_json), "VER_UE4_27"],
                       check=True, capture_output=True, timeout=60, creationflags=subprocess.CREATE_NO_WINDOW)
    with tempfile.TemporaryDirectory(prefix="undefeated-character-") as tmp:
        decoded = Path(tmp) / "skeleton.json"
        subprocess.run([str(decoder), "tojson", str(skeleton), str(decoded), "VER_UE4_27"],
                       check=True, capture_output=True, timeout=60, creationflags=subprocess.CREATE_NO_WINDOW)
        socket_data = read(decoded)
    sockets = [(i+1, e, properties(e)) for i, e in enumerate(socket_data["Exports"])
               if properties(e).get("SocketName") == "head_accessories"]
    assert len(sockets) == 1
    socket_export, socket_record, socket = sockets[0]
    player = read(args.player_json)
    exports = {e["ObjectName"]: (i+1, e, properties(e)) for i, e in enumerate(player["Exports"])}
    hero_component = exports["CharacterMesh0"][2]
    sources = {str(p): sha(p) for p in (args.player_json, skeleton, skeleton.with_suffix(".uexp"), decoder)}
    gltf = read(ROOT / "public/assets/animated/hero.gltf")
    original_nodes = copy.deepcopy(gltf["nodes"])
    original_skin = copy.deepcopy(gltf["skins"][0])
    original_animations = copy.deepcopy(gltf["animations"])
    head = next(i for i, n in enumerate(gltf["nodes"]) if n.get("name").casefold() == socket["BoneName"].casefold())
    socket_node = len(gltf["nodes"])
    gltf["nodes"].append(dict(name="head_accessories", **ue_transform(socket), children=[]))
    gltf["nodes"][head].setdefault("children", []).append(socket_node)

    def copy_resources(doc, folder, prefix):
        for key in ("buffers", "images"):
            for resource in doc.get(key, []):
                uri = resource.get("uri")
                if not uri or uri.startswith("data:"):
                    raise ValueError("Expected external resource")
                source = (folder / unquote(uri)).resolve()
                dest = (output / prefix / unquote(uri)).resolve()
                assert dest.is_relative_to(output.resolve())
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, dest)
                sources[str(source)] = sha(source)
                resource["uri"] = dest.relative_to(output).as_posix()

    sources[str(ROOT / "public/assets/animated/hero.gltf")] = sha(ROOT / "public/assets/animated/hero.gltf")
    copy_resources(gltf, ROOT / "public/assets/animated", "body")
    attachments = []
    for category, variable in (("hair", "SK_Hair"), ("sunglasses", "SK_Sunglasses")):
        scs = [(i+1, e, properties(e)) for i, e in enumerate(player["Exports"])
               if properties(e).get("InternalVariableName") == variable]
        assert len(scs) == 1
        scs_id, scs_export, scs_props = scs[0]
        assert scs_props["AttachToName"] == socket["SocketName"]
        assert scs_props["ParentComponentOrVariableName"] == "CharacterMesh0"
        component_export = player["Exports"][scs_props["ComponentTemplate"] - 1]
        component = properties(component_export)
        folder = ROOT / "public/assets/original" / category
        asset = folder / (category + ".gltf")
        part = read(asset)
        sources[str(asset)] = sha(asset)
        assert not part.get("animations") and not part.get("extensionsUsed")
        copy_resources(part, folder, category)
        keys = ["buffers", "bufferViews", "accessors", "images", "samplers", "textures", "materials", "meshes", "skins", "nodes"]
        offsets = {key: len(gltf.get(key, [])) for key in keys}
        for view in part.get("bufferViews", []):
            view["buffer"] += offsets["buffers"]
        for a in part.get("accessors", []):
            assert "sparse" not in a
            a["bufferView"] += offsets["bufferViews"]
        for image in part.get("images", []):
            if "bufferView" in image:
                image["bufferView"] += offsets["bufferViews"]
        for texture in part.get("textures", []):
            texture["source"] += offsets["images"]
            if "sampler" in texture:
                texture["sampler"] += offsets["samplers"]
        def adjust_texture_refs(value):
            if isinstance(value, dict):
                for name, item in value.items():
                    if name.endswith("Texture") and isinstance(item, dict) and "index" in item:
                        item["index"] += offsets["textures"]
                    else:
                        adjust_texture_refs(item)
            elif isinstance(value, list):
                for item in value:
                    adjust_texture_refs(item)
        for material in part["materials"]:
            adjust_texture_refs(material)
        for mesh in part["meshes"]:
            for primitive in mesh["primitives"]:
                for attr in primitive["attributes"]:
                    primitive["attributes"][attr] += offsets["accessors"]
                if "indices" in primitive:
                    primitive["indices"] += offsets["accessors"]
                if "material" in primitive:
                    primitive["material"] += offsets["materials"]
                assert "targets" not in primitive
        for skin in part["skins"]:
            skin["inverseBindMatrices"] += offsets["accessors"]
            skin["skeleton"] += offsets["nodes"]
            skin["joints"] = [i+offsets["nodes"] for i in skin["joints"]]
        for node in part["nodes"]:
            node["name"] = category + "/" + node["name"]
            for key in ("mesh", "skin"):
                if key in node:
                    node[key] += offsets[key + ("es" if key == "mesh" else "s")]
            if "children" in node:
                node["children"] = [i+offsets["nodes"] for i in node["children"]]
        roots = [i+offsets["nodes"] for i in part["scenes"][part.get("scene", 0)]["nodes"]]
        for key in keys:
            if part.get(key):
                gltf.setdefault(key, []).extend(part[key])
        component_node = len(gltf["nodes"])
        gltf["nodes"].append(dict(name=variable, **ue_transform(component), children=roots))
        gltf["nodes"][socket_node]["children"].append(component_node)
        attachments.append(dict(name=variable, scsExport=scs_id, scsName=scs_export["ObjectName"],
                                componentExport=scs_props["ComponentTemplate"], attachTo=scs_props["AttachToName"],
                                relativeTransform=ue_transform(component), retainedAccessorySkinJointCount=2,
                                componentNode=component_node, sourceAsset=component.get("SkeletalMesh")))

    # Preserve original skin/animation indices and original node transforms exactly.
    assert gltf["skins"][0] == original_skin and len(original_skin["joints"]) == 93
    assert gltf["animations"] == original_animations and len(original_animations) == 4
    for i, original in enumerate(original_nodes):
        for key in ("translation", "rotation", "scale", "matrix"):
            assert original.get(key) == gltf["nodes"][i].get(key)
    buffers = [(output / b["uri"]).read_bytes() for b in gltf["buffers"]]
    for b, blob in zip(gltf["buffers"], buffers):
        assert b["byteLength"] == len(blob)
    for view in gltf["bufferViews"]:
        assert view.get("byteOffset", 0)+view["byteLength"] <= len(buffers[view["buffer"]])
    read_accessor = UTIL["read_accessor"]
    position_indices = {p["attributes"]["POSITION"] for p in gltf["meshes"][0]["primitives"]}
    body_points = [p for a in position_indices for p in read_accessor(gltf, buffers, a)]
    body_bounds = bounds(body_points)
    world = UTIL["world_matrices"](gltf["nodes"])
    attach_world = world[socket_node]
    assembled_points, accessory_bounds = [], {}
    accessory_bind_error = 0
    for node_id, node in enumerate(gltf["nodes"]):
        if "mesh" not in node:
            continue
        points = [p for primitive in gltf["meshes"][node["mesh"]]["primitives"]
                  for p in read_accessor(gltf, buffers, primitive["attributes"]["POSITION"])]
        transformed = [[sum(world[node_id][axis][k]*v for k, v in enumerate((*p, 1))) for axis in range(3)] for p in points]
        assembled_points.extend(transformed)
        if node["mesh"]:
            accessory_bounds[node["name"]] = bounds(transformed)
            skin = gltf["skins"][node["skin"]]
            inverse_part = read_accessor(gltf, buffers, skin["inverseBindMatrices"])
            for i, joint in enumerate(skin["joints"]):
                product = UTIL["multiply"](world[joint], [[inverse_part[i][c*4+r] for c in range(4)] for r in range(4)])
                accessory_bind_error = max(accessory_bind_error, max(abs(product[r][c]-world[node_id][r][c]) for r in range(4) for c in range(4)))
    assert accessory_bind_error < 0.0001
    # Exact CPU skinning at first idle frame gives a useful (pose-specific) foot height.
    idle = next(a for a in gltf["animations"] if a["name"] == "Hero_Idle")
    pose = copy.deepcopy(gltf["nodes"])
    for channel in idle["channels"]:
        accessor = idle["samplers"][channel["sampler"]]["output"]
        pose[channel["target"]["node"]][channel["target"]["path"]] = list(read_accessor(gltf, buffers, accessor)[0])
    pose_world = UTIL["world_matrices"](pose)
    inverse = read_accessor(gltf, buffers, original_skin["inverseBindMatrices"])
    matrices = [UTIL["multiply"](pose_world[node], [[inverse[i][c*4+r] for c in range(4)] for r in range(4)])
                for i, node in enumerate(original_skin["joints"])]
    idle_y = []
    used = set()
    for primitive in gltf["meshes"][0]["primitives"]:
        attrs = primitive["attributes"]
        identity = (attrs["POSITION"], attrs["JOINTS_0"], attrs["WEIGHTS_0"])
        if identity in used:
            continue
        used.add(identity)
        positions, joints, weights = [read_accessor(gltf, buffers, a) for a in identity]
        weight_accessor = gltf["accessors"][identity[2]]
        if weight_accessor.get("normalized"):
            divisor = {5121: 255.0, 5123: 65535.0}[weight_accessor["componentType"]]
            weights = [[v/divisor for v in row] for row in weights]
        for p, js, ws in zip(positions, joints, weights):
            assert abs(sum(ws)-1) < 0.02
            idle_y.append(sum(w*sum(matrices[j][1][c]*v for c, v in enumerate((*p, 1))) for j, w in zip(js, ws)))
    assert all(math.isfinite(y) for y in idle_y)
    assert -0.5 < min(idle_y) < 0.5 and 1 < max(idle_y) < 3
    front_evidence = {}
    for side in ("l", "r"):
        foot, ball = [next(i for i, n in enumerate(gltf["nodes"]) if n.get("name") == name) for name in ("foot_"+side, "ball_"+side)]
        front_evidence[side] = [world[ball][axis][3]-world[foot][axis][3] for axis in range(3)]
    metadata = dict(forwardAxis="+Z", upAxis="+Y", units="meters", gameplayScaleApplied=False,
                    suggestedGameplayUniformScale=hero_component["RelativeScale3D"]["X"],
                    bindPoseBodyBoundsMeters=body_bounds, bindPoseSoleY=body_bounds["min"][1],
                    bindPoseAssembledBoundsMeters=bounds(assembled_points),
                    idleFirstFrameSoleY=min(idle_y), idleFirstFrameBodyTopY=max(idle_y),
                    originalCapsuleMeshOffsetApplied=False)
    gltf["asset"].setdefault("extras", {})["characterAssembly"] = metadata
    (output / "hero.gltf").write_text(json.dumps(gltf, ensure_ascii=False, indent=2), encoding="utf-8")
    evidence = dict(sourceFiles=sources, socketSource=dict(asset=str(skeleton), exportIndex=socket_export,
                    objectName=socket_record["ObjectName"], properties=socket), socketGltfTransform=ue_transform(socket),
                    socketBindWorldMatrix=attach_world, attachments=attachments,
                    accessoryBindBoundsMeters=accessory_bounds,
                    originalCharacterMeshTransform={k: hero_component[k] for k in ("RelativeLocation", "RelativeRotation", "RelativeScale3D")},
                    meshMetadata=metadata, forwardEvidenceToeMinusAnkleMeters=front_evidence,
                    checks=dict(original93JointSkinUnchanged=True, originalFourAnimationsUnchanged=True,
                                originalBoneTransformsUnchanged=True, totalSkins=len(gltf["skins"]), totalNodes=len(gltf["nodes"]),
                                bufferBoundsValid=True, allIdleSkinnedVertexHeightsFinite=True,
                                accessorySkinBindMaxError=accessory_bind_error),
                    output=str(output / "hero.gltf"), outputSha256=sha(output / "hero.gltf"),
                    limitations=["原材质由先前Web材质转换提供，此装配不重新调色。", "装配挂点来自静态资产；尚未复刻摘墨镜动画与手部挂点切换。", "脚底高度随动作变化，当前仅计算绑定姿势和待机第0帧，不是运行时全动作地面IK。"])
    (ROOT / "research/evidence/character-assembly.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(metadata, indent=2))
    print("output:", output / "hero.gltf")


if __name__ == "__main__":
    main()
