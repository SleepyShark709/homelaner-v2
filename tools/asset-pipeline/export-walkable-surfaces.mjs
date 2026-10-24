#!/usr/bin/env node
/**
 * Export walkable flat floor meshes (plaza/brick floors) as world-space AABB
 * top surfaces. The playable controller samples these in addition to the
 * Landscape heightfield; original collision is still not PhysX.
 *
 * Usage: node tools/asset-pipeline/export-walkable-surfaces.mjs
 */
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(import.meta.dirname, '../..');
const GEOMETRY = path.join(ROOT, 'public/assets/world/geometry-manifest.json');
const OUT = path.join(ROOT, 'public/assets/world/walkable-surfaces.json');
const geometry = JSON.parse(fs.readFileSync(GEOMETRY, 'utf8'));

const rotate = (v, q) => {
  const [x, y, z, w] = q;
  const ix = w * v[0] + y * v[2] - z * v[1];
  const iy = w * v[1] + z * v[0] - x * v[2];
  const iz = w * v[2] + x * v[1] - y * v[0];
  const iw = -x * v[0] - y * v[1] - z * v[2];
  return [
    ix * w + iw * -x + iy * -z - iz * -y,
    iy * w + iw * -y + iz * -x - ix * -z,
    iz * w + iw * -z + ix * -y - iy * -x,
  ];
};
const assets = new Map(geometry.assets.map(asset => [asset.id, asset]));
const surfaces = [];
for (const level of geometry.levels) {
  for (const object of level.objects) {
    const asset = assets.get(object.assetId);
    if (!asset || !/\/Mesh\/Floor\//i.test(asset.sourcePackage)) continue;
    const b = asset.bounds;
    if (!b) continue;
    const min = [Infinity, Infinity, Infinity], max = [-Infinity, -Infinity, -Infinity];
    for (const x of [b.min[0], b.max[0]]) for (const y of [b.min[1], b.max[1]]) for (const z of [b.min[2], b.max[2]]) {
      const p = rotate([x * object.scale[0], y * object.scale[1], z * object.scale[2]], object.rotation);
      for (let i = 0; i < 3; i++) {
        const value = p[i] + object.position[i];
        min[i] = Math.min(min[i], value);
        max[i] = Math.max(max[i], value);
      }
    }
    const area = (max[0] - min[0]) * (max[2] - min[2]);
    if (max[1] - min[1] > 1.5 || area < 20) continue;
    surfaces.push({
      id: object.id,
      level: level.id,
      source: object.source?.actor ?? object.id,
      asset: asset.sourcePackage,
      material: asset.sourceMaterialSlots?.[0]?.material?.reference ?? null,
      minX: min[0], maxX: max[0], minZ: min[2], maxZ: max[2],
      top: max[1], bottom: min[1], area,
    });
  }
}
fs.writeFileSync(OUT, `${JSON.stringify({ schemaVersion: 1, status: 'authored-walkable-floor-aabb-proxy', source: 'geometry-manifest objects whose asset package is /Mesh/Floor/', surfaces }, null, 2)}\n`);
console.log(JSON.stringify({ output: path.relative(ROOT, OUT), surfaces: surfaces.length, byLevel: surfaces.reduce((m, s) => { m[s.level] = (m[s.level] ?? 0) + 1; return m; }, {}) }, null, 1));
