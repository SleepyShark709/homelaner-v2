#!/usr/bin/env node
/** Report root-joint translation ranges for every animation in hero.gltf. */
import fs from 'node:fs';
import path from 'node:path';

const base = 'public/assets/character';
const gltf = JSON.parse(fs.readFileSync(path.join(base, 'hero.gltf'), 'utf8'));
const bins = gltf.buffers.map(buffer => buffer.uri ? fs.readFileSync(path.join(base, buffer.uri)) : null);
const accessor = index => {
  const item = gltf.accessors[index];
  const view = gltf.bufferViews[item.bufferView];
  const bin = bins[view.buffer];
  const width = { SCALAR: 1, VEC3: 3, VEC4: 4 }[item.type];
  const offset = (view.byteOffset ?? 0) + (item.byteOffset ?? 0);
  return Array.from({ length: item.count }, (_, row) => Array.from({ length: width }, (_, column) =>
    bin.readFloatLE(offset + (row * width + column) * 4)));
};
const root = gltf.skins[0].joints[0];
const clips = [];
for (const animation of gltf.animations) {
  const channel = animation.channels.find(item => item.target.node === root && item.target.path === 'translation');
  if (!channel) {
    clips.push({ name: animation.name, rootTranslationChannel: false });
    continue;
  }
  const frames = accessor(animation.samplers[channel.sampler].output);
  const min = [Infinity, Infinity, Infinity];
  const max = [-Infinity, -Infinity, -Infinity];
  for (const frame of frames) for (let axis = 0; axis < 3; axis++) {
    min[axis] = Math.min(min[axis], frame[axis]);
    max[axis] = Math.max(max[axis], frame[axis]);
  }
  clips.push({
    name: animation.name,
    rootTranslationChannel: true,
    frames: frames.length,
    range: max.map((value, axis) => +(value - min[axis]).toFixed(6)),
    net: max.map((value, axis) => +(value - frames[0][axis]).toFixed(6)),
  });
}
const moving = clips.filter(clip => clip.rootTranslationChannel && clip.range.some(value => value > 1e-6));
const report = {
  source: 'public/assets/character/hero.gltf',
  rootJoint: gltf.nodes[root].name,
  animationCount: clips.length,
  movingRootClips: moving.map(clip => clip.name),
  conclusion: moving.length
    ? 'Some clips carry root-joint translation; inspect before applying external movement.'
    : 'All converted clips have zero root-joint translation. Movement is driven by the external player motor; there is no clip root motion to extract for these animations.',
  clips,
};
fs.writeFileSync('research/world-recovery/root-motion-audit.json', JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify({ animationCount: report.animationCount, movingRootClips: report.movingRootClips }, null, 2));
