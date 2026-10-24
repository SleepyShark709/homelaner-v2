#!/usr/bin/env node
/**
 * Build a local population manifest whose citizens start at nearest recovered
 * BP_CharaSpawnPoint positions instead of the old prototype's hand-placed
 * citizen positions.
 *
 * What is recovered: spawn coordinates + actor names from the decoded
 * CitizenWayPoint map. What is still preview: the two-point patrol routes are a
 * nearest-neighbour convenience, not recovered citizen AI. Vehicles/props stay
 * on the old prototype placements, shifted by the same originUE offset.
 *
 * Usage:
 *   node tools/asset-pipeline/export-citizen-spawns.mjs
 */
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(import.meta.dirname, '../..');
const DECODED = path.join(ROOT, 'research/rea-audit/decoded-world/CitizenWayPoint.json');
const PREVIEW = path.join(ROOT, 'public/assets/population-manifest.json');
const OUT = path.join(ROOT, 'public/assets/world/population-original-citizens.json');
const EVIDENCE = path.join(ROOT, 'research/world-recovery/citizen-spawns-selection.json');
const ORIGIN = [-100, -550]; // originUE [-10000,-55000,0] cm -> metres
const TARGET = [-50, -548.63];
const RADIUS = 110;
const MIN_SPACING = 7;
const MAX_CITIZENS = 12;

const decoded = JSON.parse(fs.readFileSync(DECODED, 'utf8'));
const preview = JSON.parse(fs.readFileSync(PREVIEW, 'utf8'));
const prop = (entity, name) => entity?.Data ? Object.values(entity.Data).find(item => item?.Name === name) : undefined;
const vec = value => {
  const stack = [value];
  while (stack.length) {
    const item = stack.pop();
    if (!item || typeof item !== 'object') continue;
    if (item.X !== undefined || item.Y !== undefined || item.Z !== undefined) return [Number(item.X ?? 0), Number(item.Y ?? 0), Number(item.Z ?? 0)];
    for (const child of Object.values(item)) stack.push(child);
  }
  return null;
};

const spawns = [];
for (let index = 0; index < decoded.Exports.length; index++) {
  const entity = decoded.Exports[index];
  if (!String(entity.ObjectName).startsWith('BP_CharaSpawnPoint')) continue;
  const rootIndex = prop(entity, 'RootComponent')?.Value;
  const root = decoded.Exports[rootIndex];
  const ue = vec(prop(root, 'RelativeLocation'));
  if (!ue) continue;
  // Local frame -> restored world: world = local + originUE/100.
  const world = [ue[0] / 100 + ORIGIN[0], 0, ue[1] / 100 + ORIGIN[1]];
  const distance = Math.hypot(world[0] - TARGET[0], world[2] - TARGET[1]);
  if (distance > RADIUS) continue;
  spawns.push({ id: String(entity.ObjectName), ue, world, distance });
}
spawns.sort((a, b) => a.distance - b.distance);

const selected = [];
for (const spawn of spawns) {
  if (selected.length >= MAX_CITIZENS) break;
  if (selected.some(item => Math.hypot(item.world[0] - spawn.world[0], item.world[2] - spawn.world[2]) < MIN_SPACING)) continue;
  selected.push(spawn);
}
if (selected.length < 4) throw new Error(`Only ${selected.length} original spawn points selected`);

const citizenSpawns = selected.map((spawn, index) => ({
  id: `original-citizen-${index + 1}`,
  modelId: 'citizen',
  position: spawn.world,
  yaw: 0,
  routeId: `original-citizen-${index + 1}-route`,
  sourceActor: spawn.id,
  sourceUe: spawn.ue,
}));

const childPoints = [];
for (let index = 0; index < decoded.Exports.length; index++) {
  const entity = decoded.Exports[index];
  if (!String(entity.ObjectName).startsWith('BP_CharaChildWaypoint')) continue;
  const root = decoded.Exports[prop(entity, 'RootComponent')?.Value];
  const ue = vec(prop(root, 'RelativeLocation'));
  if (!ue) continue;
  childPoints.push({
    id: String(entity.ObjectName),
    parent: String(prop(entity, 'ParentWaypoint')?.Value ?? ''),
    ue,
    world: [ue[0] / 100 + ORIGIN[0], 0, ue[1] / 100 + ORIGIN[1]],
  });
}

const citizenRoutes = selected.map((spawn, index) => {
  const children = childPoints
    .map(point => ({ ...point, distance: Math.hypot(point.world[0] - spawn.world[0], point.world[2] - spawn.world[2]) }))
    .sort((a, b) => a.distance - b.distance);
  const nearest = children[0];
  if (!nearest || nearest.distance > 25) {
    return { id: `original-citizen-${index + 1}-route`, kind: 'citizen', points: [spawn.world], closed: false, routeSource: [] };
  }
  const points = [spawn.world, nearest.world];
  const source = [nearest.id];
  const sameParent = children.filter(point => point !== nearest && point.parent === nearest.parent);
  const next = sameParent[0] ?? children.find(point => point !== nearest && Math.hypot(point.world[0] - nearest.world[0], point.world[2] - nearest.world[2]) <= 25);
  if (next && next.distance <= 35) {
    points.push(next.world);
    source.push(next.id);
    const third = children.find(point => point !== nearest && point !== next && point.parent === next.parent && Math.hypot(point.world[0] - next.world[0], point.world[2] - next.world[2]) <= 25);
    if (third) { points.push(third.world); source.push(third.id); }
  }
  return { id: `original-citizen-${index + 1}-route`, kind: 'citizen', points, closed: false, routeSource: source };
});

const vehicleAndPropSpawns = preview.spawns
  .filter(spawn => spawn.modelId !== 'citizen')
  .map(spawn => ({ ...spawn, position: [spawn.position[0] + ORIGIN[0], spawn.position[1], spawn.position[2] + ORIGIN[1]] }));
const vehicleAndPropRoutes = preview.routes
  .filter(route => route.kind !== 'citizen' && route.kind !== 'citizen--1')
  .map(route => ({ ...route, points: route.points.map(point => [point[0] + ORIGIN[0], point[1], point[2] + ORIGIN[1]]) }))
  .filter(route => vehicleAndPropSpawns.some(spawn => spawn.routeId === route.id));

const manifest = {
  coordinateSystem: 'gltf-rh-y-up-meters',
  originUE: [0, 0, 0],
  models: preview.models,
  spawns: [...citizenSpawns, ...vehicleAndPropSpawns],
  routes: [...citizenRoutes, ...vehicleAndPropRoutes],
  notes: [
    'Citizen spawn positions are the nearest recovered BP_CharaSpawnPoint actors from CitizenWayPoint, converted with originUE [-10000,-55000,0] cm.',
    'Citizen patrol routes use the nearest recovered BP_CharaChildWaypoint positions (same parent where available); route order, traversal and citizen AI/state machine are still preview.',
    'Vehicle/prop placements and routes remain the previous prototype preview, shifted by the same originUE offset.',
  ],
};

fs.writeFileSync(OUT, `${JSON.stringify(manifest, null, 2)}\n`);
fs.writeFileSync(EVIDENCE, `${JSON.stringify({
  schemaVersion: 1,
  source: 'research/rea-audit/decoded-world/CitizenWayPoint.json',
  sourceSha256: 'F984545FB9127B94C8561202234748886568170AE64FF7BC631D14FE4D02F88F',
  originUEcm: [-10000, -55000, 0],
  targetWorld: TARGET,
  radius: RADIUS,
  minSpacing: MIN_SPACING,
  candidates: spawns.length,
  childCandidates: childPoints.length,
  selected: selected.map((spawn, index) => ({ id: `original-citizen-${index + 1}`, sourceActor: spawn.id, ue: spawn.ue, world: spawn.world, distance: spawn.distance, route: citizenRoutes[index] })),
  previewVehiclesProps: vehicleAndPropSpawns.length,
  caveats: manifest.notes,
}, null, 2)}\n`);
console.log(JSON.stringify({ output: path.relative(ROOT, OUT), evidence: path.relative(ROOT, EVIDENCE), candidates: spawns.length, childCandidates: childPoints.length, selected: selected.length, vehiclesProps: vehicleAndPropSpawns.length }, null, 1));
