#!/usr/bin/env python3
"""Extract HeroAnimBP state-machine transitions and crossfade timings."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "research/rea-audit/decoded/hero-anim/HeroAnimBP.json"
OUTPUT = ROOT / "research/world-recovery/animbp-transition-timing.json"


def fields(items):
    return {item.get("Name"): item.get("Value") for item in items or []}


def collect_transition_groups(node, groups):
    if isinstance(node, list):
        if node and isinstance(node[0], dict) and node[0].get("StructType") == "AnimationTransitionBetweenStates":
            groups.append(node)
        else:
            for item in node:
                collect_transition_groups(item, groups)
    elif isinstance(node, dict):
        for value in node.values():
            collect_transition_groups(value, groups)


data = json.loads(SOURCE.read_text(encoding="utf-8"))
export = next(item for item in data["Exports"] if item["ObjectName"] == "HeroAnimBP_C")
baked = next(item for item in export["Data"] if item["Name"] == "BakedStateMachines")
machines = []
for raw in baked["Value"]:
    machine = fields(raw["Value"])
    machines.append({
        "name": machine.get("MachineName"),
        "initialState": machine.get("InitialState"),
        "states": [fields(state["Value"]).get("StateName") for state in machine.get("States", [])],
    })
groups = []
collect_transition_groups(export, groups)
# Flying has a single state and no transitions, so the three serialized
# transition arrays map to Default/Ground/Jump-Falling in machine order.
for index, group in enumerate(groups):
    transitions = []
    for raw in group:
        item = fields(raw["Value"])
        transitions.append({
            "previousState": item.get("PreviousState"),
            "nextState": item.get("NextState"),
            "crossfadeSeconds": item.get("CrossfadeDuration"),
            "blendMode": item.get("BlendMode"),
            "logicType": item.get("LogicType"),
        })
    machine = machines[index] if index < len(machines) else {"name": f"machine{index}", "states": []}
    for transition in transitions:
        states = machine["states"]
        transition["previousName"] = states[transition["previousState"]] if transition["previousState"] < len(states) else None
        transition["nextName"] = states[transition["nextState"]] if transition["nextState"] < len(states) else None
    groups[index] = {"machine": machine["name"], "states": machine["states"], "transitions": transitions}

report = {
    "source": "research/rea-audit/decoded/hero-anim/HeroAnimBP.json",
    "note": "CrossfadeDuration is seconds; BlendMode is HermiteCubic in every recovered transition.",
    "machines": machines,
    "groups": [
        {
            "machine": machine["name"],
            "states": machine["states"],
            "transitions": [],
        }
        for machine in machines
    ],
}
for index, group in enumerate(groups):
    report["groups"][index]["transitions"] = group["transitions"]
# Flying has one state and no serialized transitions.
report["groups"] = [group for group in report["groups"] if group["transitions"]]
OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps({
    "machines": [machine["name"] for machine in machines],
    "groups": [{"machine": group["machine"], "count": len(group["transitions"])} for group in report["groups"]],
}, indent=2))
