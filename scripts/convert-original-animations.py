"""Merge UModel PSA clips into the ORIGINAL UModel glTF skeleton (stdlib only).

This is specific to UModel's MIRROR_MESH=1 PSA exporter, not arbitrary ActorX.
See docs/animation-conversion.md for provenance, transforms and limitations.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import shutil
import struct
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_COMMIT = "a0bfb468d42be831b126632fd8a0ae6b3614f981"
CLIPS = [
    "-HeroGame/Player/Animations/Hero_Idle.psa",
    "-HeroGame/Player/Animations/Hero_IdleFlying.psa",
    "-HeroGame/Player/Animations/Hero_FlyFastSprint.psa",
    "Action_Male/Animations/A_ThirdPersonRun.psa",
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text(raw):
    return raw.split(b"\0", 1)[0].decode("utf-8")


def read_psa(path):
    data, chunks, offset = path.read_bytes(), {}, 0
    while offset < len(data):
        if offset + 32 > len(data):
            raise ValueError("Truncated PSA header")
        name, version, size, count = struct.unpack_from("<20sIii", data, offset)
        offset += 32
        name = text(name)
        if size < 0 or count < 0 or offset + size * count > len(data) or name in chunks:
            raise ValueError(f"Invalid PSA chunk {name}")
        chunks[name] = (size, count, data[offset:offset + size * count])
        offset += size * count
    if chunks["BONENAMES"][0] != 120 or chunks["ANIMINFO"][0] != 168 or chunks["ANIMKEYS"][0] != 32:
        raise ValueError("Unsupported PSA structure sizes")
    if chunks.get("SCALEKEYS", (0, 0))[1]:
        raise ValueError("Scale animation is not implemented; refusing silent loss")
    bones = [text(chunks["BONENAMES"][2][i * 120:i * 120 + 64]) for i in range(chunks["BONENAMES"][1])]
    if len(set(n.casefold() for n in bones)) != len(bones):
        raise ValueError("Duplicate bone names")
    infos = []
    for info in struct.iter_unpack("<64s64s4i3f3i", chunks["ANIMINFO"][2]):
        infos.append(dict(name=text(info[0]), total_bones=info[2], rate=info[8], first_frame=info[10], frames=info[11]))
    keys = list(struct.iter_unpack("<8f", chunks["ANIMKEYS"][2]))
    if any(not math.isfinite(v) for key in keys for v in key):
        raise ValueError("Nonfinite source animation")
    for info in infos:
        if info["total_bones"] != len(bones) or info["frames"] < 1 or info["rate"] <= 0:
            raise ValueError("Invalid animation metadata")
        if (info["first_frame"] + info["frames"]) * len(bones) > len(keys):
            raise ValueError("Animation exceeds key buffer")
    return bones, infos, keys


def read_config(path):
    sections, section = {}, None
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith((";", "#")):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
            sections[section] = []
        elif section:
            sections[section].append(line)
    unknown = set(sections) - {"AnimSet", "UseTranslationBoneNames", "ForceMeshTranslationBoneNames", "RemoveTracks"}
    if unknown:
        raise ValueError(f"Unsupported configuration sections: {unknown}")
    rotation_only = "bAnimRotationOnly=1" in sections.get("AnimSet", [])
    translations = {x.casefold() for x in sections.get("UseTranslationBoneNames", [])}
    forced_mesh = {x.casefold() for x in sections.get("ForceMeshTranslationBoneNames", [])}
    removed = dict(line.split("=", 1) for line in sections.get("RemoveTracks", []))
    return rotation_only, translations, forced_mesh, removed


def position(key):
    # Undo ExportPsk's mirror, then ExportGLTF::TransformPosition.
    return [key[0] * 0.01, key[2] * 0.01, -key[1] * 0.01]


def rotation(key, root):
    # Undo PSA Y/W mirroring, then swap Y/Z, then root conjugation.
    q = [key[3], key[5], -key[4], -key[6]]
    if root:
        q[:3] = [-x for x in q[:3]]
    length = math.sqrt(sum(x * x for x in q))
    if length < 1e-8:
        raise ValueError("Zero quaternion")
    return [x / length for x in q]


def matrix(node):
    if "matrix" in node:
        a = node["matrix"]
        return [[a[c * 4 + r] for c in range(4)] for r in range(4)]
    x, y, z, w = node.get("rotation", [0, 0, 0, 1])
    t = node.get("translation", [0, 0, 0])
    s = node.get("scale", [1, 1, 1])
    m = [[1-2*y*y-2*z*z, 2*x*y-2*z*w, 2*x*z+2*y*w, t[0]],
         [2*x*y+2*z*w, 1-2*x*x-2*z*z, 2*y*z-2*x*w, t[1]],
         [2*x*z-2*y*w, 2*y*z+2*x*w, 1-2*x*x-2*y*y, t[2]],
         [0, 0, 0, 1]]
    for r in range(3):
        for c in range(3):
            m[r][c] *= s[c]
    return m


def multiply(a, b):
    return [[sum(a[r][k]*b[k][c] for k in range(4)) for c in range(4)] for r in range(4)]


def world_matrices(nodes):
    parents = {child: i for i, n in enumerate(nodes) for child in n.get("children", [])}
    cache = {}
    def visit(i):
        if i not in cache:
            local = matrix(nodes[i])
            cache[i] = multiply(visit(parents[i]), local) if i in parents else local
        return cache[i]
    return [visit(i) for i in range(len(nodes))]


def read_accessor(gltf, buffers, index):
    a = gltf["accessors"][index]
    view = gltf["bufferViews"][a["bufferView"]]
    n = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}[a["type"]]
    fmt = {5121: "B", 5123: "H", 5125: "I", 5126: "f"}[a["componentType"]]
    size = struct.calcsize("<" + fmt * n)
    offset = view.get("byteOffset", 0) + a.get("byteOffset", 0)
    return [struct.unpack_from("<" + fmt*n, buffers[view["buffer"]], offset+i*view.get("byteStride", size)) for i in range(a["count"])]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mesh", type=Path, default=ROOT / "public/assets/original/hero/hero.gltf")
    parser.add_argument("--output", type=Path, default=ROOT / "public/assets/animated")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    gltf = json.loads(args.mesh.read_text(encoding="utf-8"))
    if gltf.get("animations"):
        raise ValueError("Input already contains animations")
    buffers = []
    source_files = {str(args.mesh.relative_to(ROOT)): digest(args.mesh)}
    for collection in (gltf["buffers"], gltf.get("images", [])):
        for resource in collection:
            uri = resource.get("uri")
            if not uri or uri.startswith("data:"):
                raise ValueError("Expected external resource URI")
            source = (args.mesh.parent / unquote(uri)).resolve()
            target = (args.output / unquote(uri)).resolve()
            if not target.is_relative_to(args.output.resolve()):
                raise ValueError("Resource escapes output directory")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            source_files[str(source.relative_to(ROOT))] = digest(source)
            if collection is gltf["buffers"]:
                buffers.append(source.read_bytes())
    joints = gltf["skins"][0]["joints"]
    names = {gltf["nodes"][i]["name"].casefold(): i for i in joints}
    if len(names) != len(joints):
        raise ValueError("Duplicate mesh bone names")
    root_node = joints[0]
    inverse = read_accessor(gltf, buffers, gltf["skins"][0]["inverseBindMatrices"])
    world = world_matrices(gltf["nodes"])
    bind_error = 0
    for i, node in enumerate(joints):
        inv = [[inverse[i][c*4+r] for c in range(4)] for r in range(4)]
        product = multiply(world[node], inv)
        bind_error = max(bind_error, max(abs(product[r][c] - int(r == c)) for r in range(4) for c in range(4)))
    if bind_error > 0.001:
        raise ValueError(f"Bind matrix mismatch: {bind_error}")
    output = bytearray()
    anim_buffer = len(gltf["buffers"])
    def accessor(values, kind):
        while len(output) % 4:
            output.append(0)
        width = {"SCALAR": 1, "VEC3": 3, "VEC4": 4}[kind]
        flat = [v for row in values for v in row]
        if not all(math.isfinite(v) for v in flat):
            raise ValueError("Nonfinite output")
        blob = struct.pack("<" + "f"*len(flat), *flat)
        view = len(gltf["bufferViews"])
        gltf["bufferViews"].append(dict(buffer=anim_buffer, byteOffset=len(output), byteLength=len(blob)))
        output.extend(blob)
        a = dict(bufferView=view, componentType=5126, count=len(values), type=kind)
        if kind == "SCALAR":
            a.update(min=[min(flat)], max=[max(flat)])
        index = len(gltf["accessors"])
        gltf["accessors"].append(a)
        return index
    gltf["animations"] = []
    report = dict(upstreamCommit=UPSTREAM_COMMIT, sourceFiles=source_files, meshJointCount=len(joints),
                  bindMatrixMaxIdentityError=bind_error, clips=[], validation="numeric; browser visual QA still required")
    for relative in CLIPS:
        psa = ROOT / "research/exports/animations" / relative
        config = psa.with_suffix(".config")
        source_files[str(psa.relative_to(ROOT))] = digest(psa)
        source_files[str(config.relative_to(ROOT))] = digest(config)
        bones, infos, keys = read_psa(psa)
        rotation_only, translations, forced, removed = read_config(config)
        mapping = [(i, names[n.casefold()]) for i, n in enumerate(bones) if n.casefold() in names]
        if len(mapping) != len(joints):
            raise ValueError("Not every mesh joint mapped by name")
        for info in infos:
            count, rate = info["frames"], info["rate"]
            times = [[f/rate] for f in range(count)]
            assert all(times[i+1][0] > times[i][0] for i in range(count-1))
            time_accessor = accessor(times, "SCALAR")
            animation = dict(name=info["name"], samplers=[], channels=[])
            tracks = {}
            ignored, max_local, root_travel = [], 0, 0
            for bone, node in mapping:
                flag = removed.get(f"{info['name']}.{bone}", "")
                if flag not in ("", "all", "trans", "rot"):
                    raise ValueError(f"Unsupported removed track flag {flag}")
                rows = [keys[(info["first_frame"]+f)*len(bones)+bone] for f in range(count)]
                pos = [position(row) for row in rows]
                rot = [rotation(row, node == root_node) for row in rows]
                # q and -q represent the same rotation; preserve the shortest interpolation arc.
                for i in range(1, len(rot)):
                    if sum(x*y for x,y in zip(rot[i-1], rot[i])) < 0:
                        rot[i] = [-v for v in rot[i]]
                allow_translation = (not rotation_only or bones[bone].casefold() in translations) and bones[bone].casefold() not in forced
                for path, values, kind, enabled in (("translation", pos, "VEC3", allow_translation and flag not in ("all", "trans")),
                                                    ("rotation", rot, "VEC4", flag not in ("all", "rot"))):
                    if not enabled:
                        continue
                    tracks[(node, path)] = values
                    if path == "translation":
                        max_local = max(max_local, max(math.sqrt(sum(v*v for v in p)) for p in values))
                        if node == root_node:
                            root_travel = max(math.dist(values[0], p) for p in values)
                    sampler = len(animation["samplers"])
                    animation["samplers"].append(dict(input=time_accessor, output=accessor(values, kind), interpolation="LINEAR"))
                    animation["channels"].append(dict(sampler=sampler, target=dict(node=node, path=path)))
                if flag:
                    ignored.append(dict(bone=bones[bone], removed=flag))
            # Evaluate every frame of the actual joint hierarchy, with omitted tracks at bind pose.
            world_min, world_max = [math.inf]*3, [-math.inf]*3
            for frame in range(count):
                nodes = copy.deepcopy(gltf["nodes"])
                for (node, path), values in tracks.items():
                    nodes[node][path] = values[frame]
                transforms = world_matrices(nodes)
                for node in joints:
                    for axis in range(3):
                        v = transforms[node][axis][3]
                        if not math.isfinite(v):
                            raise ValueError("Nonfinite world transform")
                        world_min[axis] = min(world_min[axis], v)
                        world_max[axis] = max(world_max[axis], v)
            if max_local > 5 or max(abs(v) for v in world_min + world_max) > 10:
                raise ValueError("Suspicious humanoid translation scale; inspect conversion")
            gltf["animations"].append(animation)
            report["clips"].append(dict(name=info["name"], frames=count, rate=rate, durationSeconds=times[-1][0],
                psaBoneCount=len(bones), mappedJoints=len(mapping), unmappedPsaBones=[n for n in bones if n.casefold() not in names],
                channelCount=len(animation["channels"]), removedMeshTracks=ignored, rotationOnlyConfig=rotation_only,
                maximumLocalTranslationMeters=max_local, rootTravelMeters=root_travel,
                allFrameJointBoundsMeters=dict(min=world_min, max=world_max),
                finiteKeys=True, monotonicTimes=True, quaternionNormalized=True))
    (args.output / "animations.bin").write_bytes(output)
    gltf["buffers"].append(dict(uri="animations.bin", byteLength=len(output)))
    gltf.setdefault("asset", {}).setdefault("extras", {})["animationConversion"] = "UModel PSA + config; see validation.json"
    (args.output / "hero.gltf").write_text(json.dumps(gltf, ensure_ascii=False, indent=2), encoding="utf-8")
    report["outputGltfSha256"] = digest(args.output / "hero.gltf")
    report["outputAnimationBufferSha256"] = digest(args.output / "animations.bin")
    (args.output / "validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output / "hero.gltf"), "bindError": bind_error, "clips": [{k: c[k] for k in ("name", "frames", "durationSeconds", "channelCount")} for c in report["clips"]]}, indent=2))


if __name__ == "__main__":
    main()
