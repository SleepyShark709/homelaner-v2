#!/usr/bin/env node
/**
 * Build an optional population manifest that keeps the preview citizen
 * placements but replaces their patrol routes with nearest recovered
 * BP_CharaChildWaypoint positions (same parent where available).
 *
 * Usage: node tools/asset-pipeline/export-preview-waypoint-routes.mjs
 */
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(import.meta.dirname, '../..');
const DECODED = path.join(ROOT, 'research/rea-audit/decoded-world/CitizenWayPoint.json');
const PREVIEW = path.join(ROOT, 'public/assets/population-manifest.json');
const OUT = path.join(ROOT, 'public/assets/world/population-waypoint-routes.json');
const EVIDENCE = path.join(ROOT, 'research/world-recovery/preview-waypoint-routes.json');
const ORIGIN = [-100, -550];
const decoded = JSON.parse(fs.readFileSync(DECODED, 'utf8'));
const preview = JSON.parse(fs.readFileSync(PREVIEW, 'utf8'));
const prop = (entity, name) => entity?.Data ? Object.values(entity.Data).find(item => item?.Name === name) : undefined;
const vec = value => {
  const stack = [value];
  while (stack.length) {
    const item = stack.pop();
    if (!item || typeof item !== 'object') continue;
    if (item.X !== undefined || item.Y !== undefined) return [Number(item.X ?? 0), Number(item.Y ?? 0)];
    for (const child of Object.values(item)) stack.push(child);
  }
  return null;
};
const shift = point => [point[0] + ORIGIN[0], point[1], point[2] + ORIGIN[1]];

const children = [];
for (let index = 0; index < decoded.Exports.length; index++) {
  const entity = decoded.Exports[index];
  if (!String(entity.ObjectName).startsWith('BP_CharaChildWaypoint')) continue;
  const root = decoded.Exports[prop(entity, 'RootComponent')?.Value];
  const ue = vec(prop(root, 'RelativeLocation'));
  if (!ue) continue;
  children.push({
    id: String(entity.ObjectName),
    parent: String(prop(entity, 'ParentWaypoint')?.Value ?? ''),
    world: [ue[0] / 100 + ORIGIN[0], 0, ue[1] / 100 + ORIGIN[1]],
  });
}

const previewRoutes = new Map(preview.routes.map(route => [route.id, route]));
const citizenSpawns = preview.spawns.filter(spawn => spawn.modelId === 'citizen');
const usedChildren = new Set();
const routes = [];
const mappings = [];
for (const spawn of citizenSpawns) {
  const world = shift(spawn.position);
  const nearest = children
    .map(child => ({ ...child, distance: Math.hypot(child.world[0] - world[0], child.world[2] - world[2]) }))
    .sort((a, b) => a.distance - b.distance)[0];
  let points;
  let source;
  if (nearest && nearest.distance <= 30) {
    points = [world, nearest.world];
    source = [nearest.id];
    const next = children
      .filter(child => child !== nearest && child.parent === nearest.parent)
      .map(child => ({ ...child, distance: Math.hypot(child.world[0] - nearest.world[0], child.world[2] - nearest.world[2]) }))
      .sort((a, b) => a.distance - b.distance)[0];
    if (next && next.distance <= 30) { points.push(next.world); source.push(next.id); }
    source.forEach(id => usedChildren.add(id));
  } else {
    const fallback = previewRoutes.get(spawn.routeId);
    points = fallback ? fallback.points.map(shift) : [world];
    source = [];
  }
  routes.push({ id: spawn.routeId, kind: 'citizen', points, closed: false, routeSource: source });
  mappings.push({ spawn: spawn.id, world, nearestChild: nearest?.id ?? null, nearestDistance: nearest?.distance ?? null, routeSource: source });
}

const vehicleAndPropSpawns = preview.spawns
  .filter(spawn => spawn.modelId !== 'citizen')
  .map(spawn => ({ ...spawn, position: shift(spawn.position) }));
const vehicleAndPropRoutes = preview.routes
  .filter(route => route.kind !== 'citizen' && route.kind !== 'citizen--1')
  .map(route => ({ ...route, points: route.points.map(shift) }))
  .filter(route => vehicleAndPropSpawns.some(spawn => spawn.routeId === route.id));

const manifest = {
  coordinateSystem: 'gltf-rh-y-up-meters',
  originUE: [0, 0, 0],
  models: preview.models,
  spawns: [...citizenSpawns.map(spawn => ({ ...spawn, position: shift(spawn.position) })), ...vehicleAndPropSpawns],
  routes: [...routes, ...vehicleAndPropRoutes],
  notes: [
    'Preview citizen placements are retained; patrol routes are replaced by nearest recovered BP_CharaChildWaypoint positions (same parent where available).',
    'Route order/traversal and citizen AI/state machine are still preview, not recovered.',
    'Vehicle/prop placements and routes remain the previous prototype preview shifted by originUE.',
  ],
};
fs.writeFileSync(OUT, `${JSON.stringify(manifest, null, 2)}\n`);
fs.writeFileSync(EVIDENCE, `${JSON.stringify({
  schemaVersion: 1,
  source: 'research/rea-audit/decoded-world/CitizenWayPoint.json',
  preview: 'public/assets/population-manifest.json',
  originUEcm: [-10000, -55000, 0],
  childCandidates: children.length,
  citizens: citizenSpawns.length,
  usedChildren: usedChildren.size,
  mappings,
  caveats: manifest.notes,
}, null, 2)}\n`);
console.log(JSON.stringify({ output: path.relative(ROOT, OUT), evidence: path.relative(ROOT, EVIDENCE), children: children.length, citizens: citizenSpawns.length, usedChildren: usedChildren.size, vehiclesProps: vehicleAndPropSpawns.length }, null, 1));
