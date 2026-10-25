import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve('.');
const gltfPath = path.join(root, 'public/assets/character/hero.gltf');
const gltf = JSON.parse(fs.readFileSync(gltfPath, 'utf8'));
const buffers = gltf.buffers.map((buffer) => {
  if (buffer.uri?.startsWith('data:')) return Buffer.from(buffer.uri.split(',')[1], 'base64');
  return fs.readFileSync(path.join(path.dirname(gltfPath), buffer.uri));
});

function accessorData(index) {
  const accessor = gltf.accessors[index];
  const view = gltf.bufferViews[accessor.bufferView];
  const components = { SCALAR: 1, VEC3: 3, VEC4: 4 }[accessor.type];
  const stride = view.byteStride ?? components * 4;
  const offset = (view.byteOffset ?? 0) + (accessor.byteOffset ?? 0);
  const data = new Float32Array(accessor.count * components);
  for (let i = 0; i < accessor.count; i++) {
    for (let c = 0; c < components; c++) data[i * components + c] = buffers[view.buffer].readFloatLE(offset + i * stride + c * 4);
  }
  return { data, components, count: accessor.count };
}

const report = {
  source: 'public/assets/character/hero.gltf',
  animationCount: gltf.animations.length,
  clips: [],
  failures: [],
};

for (const animation of gltf.animations) {
  const channels = animation.channels.map((channel) => {
    const sampler = animation.samplers[channel.sampler];
    const time = accessorData(sampler.input);
    const value = accessorData(sampler.output);
    const values = [];
    let maxQuaternionNormError = 0;
    let nonFinite = 0;
    for (let i = 0; i < value.count; i++) {
      const row = Array.from(value.data.slice(i * value.components, (i + 1) * value.components));
      if (row.some((item) => !Number.isFinite(item))) nonFinite++;
      if (channel.target.path === 'rotation') {
        const norm = Math.hypot(...row);
        maxQuaternionNormError = Math.max(maxQuaternionNormError, Math.abs(norm - 1));
      }
      values.push(row);
    }
    return {
      node: gltf.nodes[channel.target.node]?.name ?? String(channel.target.node),
      target: channel.target.path,
      frames: time.count,
      duration: time.data[time.count - 1],
      maxQuaternionNormError,
      nonFinite,
      first: values[0],
      last: values[values.length - 1],
    };
  });
  const joints = new Set(channels.filter((channel) => channel.target === 'rotation').map((channel) => channel.node));
  const duration = Math.max(...channels.map((channel) => channel.duration));
  const loopDelta = Math.max(...channels
    .filter((channel) => channel.target === 'rotation')
    .map((channel) => {
      const dot = Math.abs(channel.first.reduce((sum, item, index) => sum + item * channel.last[index], 0));
      return (2 * Math.acos(Math.min(1, dot)) * 180) / Math.PI;
    }));
  const nonFinite = channels.reduce((sum, channel) => sum + channel.nonFinite, 0);
  const maxQuaternionNormError = Math.max(...channels.map((channel) => channel.maxQuaternionNormError));
  const loop = /Idle|Walk|Run|Sprint|Fall|Fly|Flying/i.test(animation.name);
  const clip = {
    name: animation.name,
    durationSeconds: duration,
    rotationJoints: joints.size,
    channels: channels.length,
    maxQuaternionNormError,
    nonFinite,
    loop,
    firstLastRotationDeltaDegrees: loopDelta,
  };
  report.clips.push(clip);
  if (joints.size < 68) report.failures.push(`${animation.name}: rotation joints ${joints.size} < 68 (below PSA-mapped set)`);
  if (joints.size > 93) report.failures.push(`${animation.name}: rotation joints ${joints.size} > 93`);
  if (maxQuaternionNormError > 1e-5) report.failures.push(`${animation.name}: quaternion norm error ${maxQuaternionNormError}`);
  if (nonFinite) report.failures.push(`${animation.name}: ${nonFinite} non-finite values`);
}

report.failures = [...new Set(report.failures)];
fs.writeFileSync(path.join(root, 'research/world-recovery/locomotion-frame-validation.json'), `${JSON.stringify(report, null, 2)}\n`);
console.log(JSON.stringify({ animationCount: report.animationCount, failures: report.failures, clips: report.clips.map(({ name, durationSeconds, rotationJoints, maxQuaternionNormError }) => ({ name, durationSeconds, rotationJoints, maxQuaternionNormError })) }, null, 2));
