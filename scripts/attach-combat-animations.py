"""Append 14 verified original PSA clips and a notify timeline to the assembled hero.

Run after assemble-original-character.py. Re-running is idempotent: only this
script's appended animation blocks are replaced. Original geometry, materials,
accessory skins and four locomotion clips are unchanged.
"""
import copy
import hashlib
import json
import math
from pathlib import Path
import runpy
import struct

ROOT = Path(__file__).resolve().parents[1]
U = runpy.run_path(str(ROOT / "scripts/convert-original-animations.py"))
MODEL = ROOT / "public/assets/character/hero.gltf"
MANIFEST = ROOT / "research/exports/combat-animations/manifest.json"
SPEC = ROOT / "research/evidence/combat-spec.json"
BASE_CLIPS = {"Hero_Idle", "Hero_IdleFlying", "Hero_FlyFastSprint", "A_ThirdPersonRun"}
HIT_NAMES = {"StopAttackMove", "NormalLongAttack", "SpawnComboLongAttack", "SpawnSuperLongAttack", "SpawnAirLongAttack"}
FINISH_NAMES = {"FinishAction", "FinishLongAttack"}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def stable_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def main():
    model, manifest, spec = read(MODEL), read(MANIFEST), read(SPEC)
    extras = model["asset"].setdefault("extras", {})
    previous = extras.pop("combatAnimationAppend", None)
    if previous:
        for field, count in previous["baseCounts"].items():
            model[field] = model[field][:count]
    assert {a["name"] for a in model["animations"]} == BASE_CLIPS
    assert len(model["skins"][0]["joints"]) == 93
    assert [len(s["joints"]) for s in model["skins"]] == [93, 2, 2]
    preserved_fields = ("nodes", "skins", "meshes", "materials", "images", "textures", "scenes")
    preserved = {k: stable_hash(model.get(k)) for k in preserved_fields}
    locomotion = stable_hash(model["animations"])
    base_counts = {k: len(model[k]) for k in ("buffers", "bufferViews", "accessors", "animations")}
    input_model_hash = stable_hash(model)
    joints = model["skins"][0]["joints"]
    names = {model["nodes"][i]["name"].casefold(): i for i in joints}
    root_node = joints[0]
    binary, report_clips, timelines = bytearray(), [], []
    source_hashes = {str(MANIFEST.relative_to(ROOT)): U["digest"](MANIFEST), str(SPEC.relative_to(ROOT)): U["digest"](SPEC)}

    def add_accessor(rows, kind):
        while len(binary) % 4:
            binary.append(0)
        flat = [v for row in rows for v in row]
        assert all(math.isfinite(v) for v in flat)
        blob = struct.pack("<"+"f"*len(flat), *flat)
        view = len(model["bufferViews"])
        model["bufferViews"].append(dict(buffer=base_counts["buffers"], byteOffset=len(binary), byteLength=len(blob)))
        binary.extend(blob)
        accessor = dict(bufferView=view, componentType=5126, count=len(rows), type=kind)
        if kind == "SCALAR":
            accessor.update(min=[min(flat)], max=[max(flat)])
        result = len(model["accessors"])
        model["accessors"].append(accessor)
        return result

    sequence_lookup = {s["clips"][0]["name"]: (i, s) for i, s in enumerate(manifest["combatSequences"])}
    assert len(sequence_lookup) == 14 and len(spec["animations"]) == 14
    for specification in spec["animations"]:
        name = specification["psa_clip"]["name"]
        sequence_index, sequence = sequence_lookup[name]
        psa = ROOT / sequence["file"]
        config = psa.with_suffix(".config")
        assert U["digest"](psa) == sequence["sha256"]
        source_hashes[str(psa.relative_to(ROOT))] = U["digest"](psa)
        source_hashes[str(config.relative_to(ROOT))] = U["digest"](config)
        bones, infos, keys = U["read_psa"](psa)
        assert len(infos) == 1 and infos[0]["name"] == name
        info = infos[0]
        count, rate = info["frames"], info["rate"]
        # PSA K.Time=1 holds each sample for one frame. Keep the final pose for
        # its one-frame interval, so source tail notifies remain inside the clip.
        duration = count/rate
        times = [[frame/rate] for frame in range(count+1)]
        time_accessor = add_accessor(times, "SCALAR")
        rotation_only, translations, forced, removed = U["read_config"](config)
        mapping = [(i, names[n.casefold()]) for i, n in enumerate(bones) if n.casefold() in names]
        assert len(mapping) == len(joints)
        animation = dict(name=name, channels=[], samplers=[], extras=dict(sourcePsa=str(psa.relative_to(ROOT)),
                         terminalSampleHoldSeconds=1/rate, sourceFrames=count))
        tracks, ignored = {}, []
        max_local = 0
        for bone, node in mapping:
            flag = removed.get(f"{name}.{bone}", "")
            assert flag in ("", "all", "trans", "rot")
            rows = [keys[(info["first_frame"]+f)*len(bones)+bone] for f in range(count)]
            assert all(abs(row[7]-1) < 1e-6 for row in rows), "Unexpected PSA sample duration"
            positions = [U["position"](row) for row in rows]
            rotations = [U["rotation"](row, node == root_node) for row in rows]
            for f in range(1, count):
                if sum(a*b for a, b in zip(rotations[f-1], rotations[f])) < 0:
                    rotations[f] = [-v for v in rotations[f]]
            allowed = (not rotation_only or bones[bone].casefold() in translations) and bones[bone].casefold() not in forced
            for path, values, kind, enabled in (("translation", positions, "VEC3", allowed and flag not in ("all", "trans")),
                                                ("rotation", rotations, "VEC4", flag not in ("all", "rot"))):
                if not enabled:
                    continue
                values.append(values[-1][:])
                tracks[(node, path)] = values
                if path == "translation":
                    max_local = max(max_local, max(math.sqrt(sum(v*v for v in row)) for row in values))
                sampler = len(animation["samplers"])
                animation["samplers"].append(dict(input=time_accessor, output=add_accessor(values, kind), interpolation="LINEAR"))
                animation["channels"].append(dict(sampler=sampler, target=dict(node=node, path=path)))
            if flag:
                ignored.append(dict(bone=bones[bone], removed=flag))
        assert animation["channels"]
        world_min, world_max = [math.inf]*3, [-math.inf]*3
        for frame in range(count):
            pose = copy.deepcopy(model["nodes"])
            for (node, path), values in tracks.items():
                pose[node][path] = values[frame]
            world = U["world_matrices"](pose)
            for node in joints:
                for axis in range(3):
                    v = world[node][axis][3]
                    assert math.isfinite(v)
                    world_min[axis] = min(world_min[axis], v)
                    world_max[axis] = max(world_max[axis], v)
        assert max_local < 5 and max(abs(v) for v in world_min+world_max) < 10
        model["animations"].append(animation)

        raw_export_index, raw_export = next((i, e) for i, e in enumerate(sequence["decodedExports"])
                                            if e["name"] == name and "AnimSequence" in e["className"])
        data = raw_export["data"]
        source_scale = float(data.get("RateScale", 1))
        source_duration = float(data["SequenceLength"])
        assert abs(source_scale-specification["sequence_rate_scale"]) < 1e-6
        # UModel UnAnim4.cpp: Rate=NumFrames/SequenceLength*RateScale.
        assert abs(duration-source_duration/source_scale) < 1e-5
        notifies = []
        for notify_index, event in enumerate(data.get("Notifies", [])):
            assert event.get("LinkMethod", "EAnimLinkMethod::Absolute") == "EAnimLinkMethod::Absolute"
            source_time = float(event["LinkValue"])
            offset = float(event.get("TriggerTimeOffset", 0))
            source_event_duration = float(event.get("Duration", 0))
            time = (source_time+offset)/source_scale
            event_duration = source_event_duration/source_scale
            assert -1e-5 <= time <= duration+1e-5
            assert event_duration >= 0 and time+event_duration <= duration+1e-4
            notifies.append(dict(name=event.get("NotifyName") or event.get("NotifyStateClass") or event.get("Notify") or "unnamed",
                time=time, duration=event_duration, sourceTime=source_time, sourceDuration=source_event_duration,
                sourceTriggerOffset=offset, notifyObject=event.get("Notify"), notifyStateClass=event.get("NotifyStateClass"),
                sourcePointer=f"/combatSequences/{sequence_index}/decodedExports/{raw_export_index}/data/Notifies/{notify_index}"))
        notifies.sort(key=lambda e: e["time"])
        hits = [e for e in notifies if e["name"] in HIT_NAMES]
        finishes = [e for e in notifies if e["name"] in FINISH_NAMES]
        assert len(hits) <= 1
        playback_rate = {"Hero_FlashKick": 1.2, "Hero_SuperPunch": 0.75}.get(name, 1)
        hit = hits[0]["time"] if hits else None
        finish = finishes[0]["time"] if finishes else duration
        assert hit is None or 0 <= hit <= finish <= duration+1e-5
        timelines.append(dict(name=name, hit=hit, finish=finish, duration=duration, playbackRate=playback_rate,
            sourceRateScale=source_scale, sourceRateScaleAssumedDefault="RateScale" not in data,
            sourceDuration=source_duration, hitNotify=hits[0]["name"] if hits else None,
            finishNotify=finishes[0]["name"] if finishes else None, finishFallback=not bool(finishes),
            montage=specification["montage"], additionalRuntimeRate="AttackAnimRate and level multiplier where applicable; do not multiply sourceRateScale again",
            notifies=notifies))
        report_clips.append(dict(name=name, sourceFrames=count, outputKeys=count+1, fps=rate, duration=duration,
            mappedJoints=len(mapping), unmappedPsaBones=[n for n in bones if n.casefold() not in names],
            removedTracks=ignored, channels=len(animation["channels"]), maxLocalTranslationMeters=max_local,
            allFrameWorldJointBoundsMeters=dict(min=world_min, max=world_max), terminalSampleHoldSeconds=1/rate))

    model["buffers"].append(dict(uri="combat-animations.bin", byteLength=len(binary)))
    extras["combatAnimationAppend"] = dict(baseCounts=base_counts, count=14, version=1,
        timingUrl="/assets/character/combat-timings.json", terminalSamplePolicy="Hold last PSA sample for its one-frame duration")
    assert all(stable_hash(model.get(k)) == v for k, v in preserved.items())
    assert stable_hash(model["animations"][:4]) == locomotion
    assert len(model["animations"]) == 18
    # Independently decode the actual float32 payload before publication.
    buffers = [(MODEL.parent / b["uri"]).read_bytes() for b in model["buffers"][:-1]]+[bytes(binary)]
    quaternion_error = 0
    for view in model["bufferViews"]:
        assert view.get("byteOffset", 0)+view["byteLength"] <= len(buffers[view["buffer"]])
    for animation in model["animations"]:
        targets = set()
        for channel in animation["channels"]:
            target = (channel["target"]["node"], channel["target"]["path"])
            assert target not in targets and target[0] in joints
            targets.add(target)
            sampler = animation["samplers"][channel["sampler"]]
            times = U["read_accessor"](model, buffers, sampler["input"])
            values = U["read_accessor"](model, buffers, sampler["output"])
            assert len(times) == len(values)
            assert all(times[i][0] < times[i+1][0] for i in range(len(times)-1))
            assert all(math.isfinite(v) for row in values for v in row)
            if target[1] == "rotation":
                quaternion_error = max(quaternion_error, max(abs(sum(v*v for v in row)-1) for row in values))
    assert quaternion_error < 1e-6
    (MODEL.parent / "combat-animations.bin").write_bytes(binary)
    MODEL.write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    timing = dict(schemaVersion=1, modelUrl="/assets/character/hero.gltf", units="seconds on exported animation timeline",
        timeMapping="(sourceTime + triggerOffset) / sourceRateScale; wall time = timelineTime / runtimePlaybackRate",
        playbackRatePolicy="playbackRate is the default extra multiplier only; sourceRateScale is already baked into PSA",
        clips=timelines)
    timing_file = MODEL.parent / "combat-timings.json"
    timing_file.write_text(json.dumps(timing, ensure_ascii=False, indent=2), encoding="utf-8")
    report = dict(sourceFiles=source_hashes, inputBaseModelCanonicalSha256=input_model_hash,
        originalSceneAndGeometryHashes=preserved, preservedLocomotionCanonicalSha256=locomotion,
        clips=report_clips, checks=dict(mainJoints=93, accessorySkinJoints=[2, 2], totalAnimations=18,
        originalNodesSkinsMeshesMaterialsAndLocomotionPreserved=True, allSerializedKeysFinite=True,
        allInputTimesStrictlyIncreasing=True, noDuplicateAnimationTargets=True, bufferBoundsValid=True,
        allNotifiesWithinExportedDuration=True, maximumQuaternionSquaredNormError=quaternion_error),
        outputs={str(p.relative_to(ROOT)): U["digest"](p) for p in (MODEL, MODEL.parent / "combat-animations.bin", timing_file)},
        conversionSource="https://github.com/gildor2/UEViewer/blob/a0bfb468d42be831b126632fd8a0ae6b3614f981/Unreal/UnrealMesh/UnAnim4.cpp#L818",
        limitations=["Static mathematical verification, not original-game timing observation.",
        "Terminal last-pose hold preserves the last PSA sample duration; no additional motion poses are synthesized.",
        "Notification metadata alone does not implement collision, particles, montage blending or action cancellation."])
    (ROOT / "research/evidence/combat-animation-conversion.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(dict(model=str(MODEL), clips=[{k: c[k] for k in ("name", "hit", "finish", "duration", "playbackRate", "sourceRateScale")} for c in timelines],
                         checks=report["checks"]), indent=2))


if __name__ == "__main__":
    main()
