#!/usr/bin/env node
/**
 * Export recovered MainLevel crosswalk / traffic-light mesh placements as
 * marker positions. Signal timing and BP_TrafficSystem behavior are not
 * recovered.
 */
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(import.meta.dirname, '../..');
const GEOMETRY = path.join(ROOT, 'public/assets/world/geometry-manifest.json');
const OUT = path.join(ROOT, 'public/assets/world/traffic-markers.json');
const EVIDENCE = path.join(ROOT, 'research/world-recovery/traffic-markers.json');
const json = JSON.parse(fs.readFileSync(GEOMETRY, 'utf8'));
const assets = new Map(json.assets.map(asset => [asset.id, asset]));
const markers = [];
for (const level of json.levels) {
  for (const object of level.objects) {
    const asset = assets.get(object.assetId);
    if (!asset) continue;
    const pkg = String(asset.sourcePackage).split('/').pop();
    const kind = pkg === 'CrossWalk' ? 'crosswalk' : pkg === 'TrafficLight' ? 'traffic' : '';
    if (!kind) continue;
    markers.push({ id: `${level.id}:${object.id}`, level: level.id, kind, position: object.position.map(value => Math.round(value * 100) / 100) });
  }
}
fs.writeFileSync(OUT, `${JSON.stringify({ schemaVersion: 1, status: 'recovered-mesh-placements', source: 'geometry-manifest CrossWalk/TrafficLight objects', markers }, null, 2)}\n`);
fs.writeFileSync(EVIDENCE, `${JSON.stringify({ schemaVersion: 1, source: 'public/assets/world/geometry-manifest.json', markers: markers.map(marker => ({ ...marker, note: 'mesh placement recovered; signal timing/BP_TrafficSystem behavior not recovered' })) }, null, 2)}\n`);
console.log(JSON.stringify({ output: path.relative(ROOT, OUT), markers: markers.length, kinds: markers.reduce((m, item) => { m[item.kind] = (m[item.kind] ?? 0) + 1; return m; }, {}) }, null, 1));
