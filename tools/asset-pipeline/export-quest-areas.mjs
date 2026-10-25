#!/usr/bin/env node
/**
 * Export recovered quest-area trigger components (FireQuest_BP / MatQuest_BP)
 * as world-space marker positions. Quest completion logic is not recovered.
 */
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(import.meta.dirname, '../..');
const MAIN = path.join(ROOT, 'research/exports/city-decoded/MainLevel.json');
const OUT = path.join(ROOT, 'public/assets/world/quest-areas.json');
const EVIDENCE = path.join(ROOT, 'research/world-recovery/quest-areas.json');
const json = JSON.parse(fs.readFileSync(MAIN, 'utf8'));
const prop = (entity, name) => (Array.isArray(entity?.Data) ? entity.Data : Object.values(entity?.Data ?? {})).find(item => item?.Name === name);
const num = value => typeof value === 'number' ? value : Number.parseFloat(String(value ?? '0')) || 0;
const vec = value => {
  const stack = [value];
  while (stack.length) {
    const item = stack.pop();
    if (!item || typeof item !== 'object') continue;
    if (item.X !== undefined || item.Y !== undefined || item.Z !== undefined) return [num(item.X), num(item.Y), num(item.Z)];
    for (const child of Object.values(item)) stack.push(child);
  }
  return null;
};
const areas = [];
for (const actor of json.Exports) {
  const match = /^(FireQuest_BP|MatQuest_BP)/.exec(String(actor.ObjectName));
  if (!match) continue;
  const kind = match[1] === 'FireQuest_BP' ? 'fire' : 'material';
  const rootPointer = prop(actor, 'RootComponent')?.Value ?? prop(actor, 'DefaultSceneRoot')?.Value;
  const root = typeof rootPointer === 'number' ? json.Exports[rootPointer] : null;
  const rootLocation = vec(prop(root, 'RelativeLocation')) ?? [0, 0, 0];
  const triggerPointer = prop(actor, 'Sphere_0')?.Value ?? prop(actor, 'Box')?.Value;
  const trigger = typeof triggerPointer === 'number' ? json.Exports[triggerPointer] : null;
  if (!root || !trigger) continue;
  const radius = num(prop(trigger, 'SphereRadius')?.Value) / 100;
  const extent = vec(prop(trigger, 'BoxExtent')?.Value);
  // The instance component often omits inherited shape properties. FireQuest_BP's
  // class default is SphereRadius=5000 cm; MatQuest_BP uses BoxExtent=(450,450,32) cm.
  const defaultRadius = kind === 'fire' ? 50 : 4.5;
  const markerRadius = Math.max(radius, extent ? Math.max(...extent.map(Math.abs)) / 100 : 0, defaultRadius);
  areas.push({
    id: String(actor.ObjectName),
    kind,
    position: [rootLocation[0] / 100, rootLocation[2] / 100, rootLocation[1] / 100],
    radius: markerRadius,
    component: String(trigger.ObjectName),
  });
}
fs.writeFileSync(OUT, `${JSON.stringify({ schemaVersion: 1, status: 'recovered-trigger-components-position-only', source: 'MainLevel.json FireQuest_BP/MatQuest_BP components', areas }, null, 2)}\n`);
fs.writeFileSync(EVIDENCE, `${JSON.stringify({ schemaVersion: 1, source: 'research/exports/city-decoded/MainLevel.json', areas: areas.map(area => ({ ...area, note: 'trigger position recovered; quest completion/state machine not recovered' })) }, null, 2)}\n`);
console.log(JSON.stringify({ output: path.relative(ROOT, OUT), areas: areas.length, kinds: areas.reduce((m, a) => { m[a.kind] = (m[a.kind] ?? 0) + 1; return m; }, {}) }, null, 1));
