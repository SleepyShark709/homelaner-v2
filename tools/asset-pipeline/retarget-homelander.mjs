#!/usr/bin/env node
/**
 * Retarget UNDEFEATED's original clips (Hero_Idle, attacks, etc.) onto the
 * user-supplied Homelander GLB skeleton. The original clips are sampled at
 * 24 fps; each mapped bone receives the world-space rotation delta from the
 * original rest pose, converted back to Homelander local rotation. Bone
 * translations stay at Homelander rest lengths except the pelvis/root motion.
 *
 * Output: public/assets/character/homelander-retarget.json
 */
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(import.meta.dirname, '../..');
const ORIGINAL = path.join(ROOT, 'public/assets/character/hero.gltf');
const HOMELANDER = path.join(ROOT, 'public/assets/character/homelander.glb');
const OUTPUT = path.join(ROOT, 'public/assets/character/homelander-retarget.json');
const FPS = 24;

function readGlb(file) {
  const buf = fs.readFileSync(file);
  let offset = 12, json = null, bin = null;
  while (offset < buf.length) {
    const length = buf.readUInt32LE(offset), type = buf.readUInt32LE(offset + 4);
    const data = buf.subarray(offset + 8, offset + 8 + length);
    if (type === 0x4e4f534a) json = JSON.parse(data.toString('utf8'));
    if (type === 0x004e4942) bin = data;
    offset += 8 + length;
  }
  return { json, buffers: [bin] };
}
function readGltf(file) {
  const dir = path.dirname(file);
  const json = JSON.parse(fs.readFileSync(file, 'utf8'));
  const buffers = (json.buffers ?? []).map(buffer => buffer.uri ? fs.readFileSync(path.join(dir, decodeURIComponent(buffer.uri))) : null);
  return { json, buffers };
}
function accessor(doc, index) {
  const a = doc.json.accessors[index];
  const view = doc.json.bufferViews[a.bufferView];
  const buffer = doc.buffers[view.buffer];
  const componentBytes = { 5126: 4, 5125: 4, 5123: 2, 5121: 1 }[a.componentType];
  const components = { SCALAR: 1, VEC2: 2, VEC3: 3, VEC4: 4, MAT4: 16 }[a.type];
  const stride = view.byteStride ?? componentBytes * components;
  const offset = (view.byteOffset ?? 0) + (a.byteOffset ?? 0);
  const out = new Float64Array(a.count * components);
  for (let i = 0; i < a.count; i++) {
    for (let c = 0; c < components; c++) {
      const at = offset + i * stride + c * componentBytes;
      out[i * components + c] = a.componentType === 5126 ? buffer.readFloatLE(at) : buffer.readUIntLE(at, componentBytes);
    }
  }
  return { values: out, count: a.count, components, max: a.max ?? null, min: a.min ?? null };
}

const Q = {
  id: [0, 0, 0, 1],
  mul(a, b) {
    const [ax, ay, az, aw] = a, [bx, by, bz, bw] = b;
    return [aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx, aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz];
  },
  inv(q) { return [-q[0], -q[1], -q[2], q[3]]; },
  norm(q) { const n = Math.hypot(...q) || 1; return q.map(v => v / n); },
  slerp(a, b, t) {
    let [bx, by, bz, bw] = b, dot = a[0] * bx + a[1] * by + a[2] * bz + a[3] * bw;
    if (dot < 0) { bx = -bx; by = -by; bz = -bz; bw = -bw; dot = -dot; }
    if (dot > 0.9995) return Q.norm([a[0] + (bx - a[0]) * t, a[1] + (by - a[1]) * t, a[2] + (bz - a[2]) * t, a[3] + (bw - a[3]) * t]);
    const theta = Math.acos(Math.max(-1, Math.min(1, dot))), sin = Math.sin(theta);
    const w1 = Math.sin((1 - t) * theta) / sin, w2 = Math.sin(t * theta) / sin;
    return Q.norm([a[0] * w1 + bx * w2, a[1] * w1 + by * w2, a[2] * w1 + bz * w2, a[3] * w1 + bw * w2]);
  },
  rotate(q, v) {
    const p = Q.mul(Q.mul(q, [v[0], v[1], v[2], 0]), Q.inv(q));
    return [p[0], p[1], p[2]];
  },
};

function quatFromMatrix(m) {
  const m00 = m[0], m01 = m[4], m02 = m[8], m10 = m[1], m11 = m[5], m12 = m[9], m20 = m[2], m21 = m[6], m22 = m[10];
  const trace = m00 + m11 + m22;
  if (trace > 0) { const s = Math.sqrt(trace + 1) * 2; return [ (m21 - m12) / s, (m02 - m20) / s, (m10 - m01) / s, 0.25 * s ]; }
  if (m00 > m11 && m00 > m22) { const s = Math.sqrt(1 + m00 - m11 - m22) * 2; return [ 0.25 * s, (m01 + m10) / s, (m02 + m20) / s, (m21 - m12) / s ]; }
  if (m11 > m22) { const s = Math.sqrt(1 + m11 - m00 - m22) * 2; return [ (m01 + m10) / s, 0.25 * s, (m12 + m21) / s, (m02 - m20) / s ]; }
  const s = Math.sqrt(1 + m22 - m00 - m11) * 2; return [ (m02 + m20) / s, (m12 + m21) / s, 0.25 * s, (m10 - m01) / s ];
}

function local(node) {
  if (node.matrix) {
    const m = node.matrix;
    return { p: [m[12], m[13], m[14]], q: Q.norm(quatFromMatrix(m)) };
  }
  return { p: node.translation ?? [0, 0, 0], q: Q.norm(node.rotation ?? Q.id) };
}

const original = readGltf(ORIGINAL);
const homelander = readGlb(HOMELANDER);

function prepare(doc) {
  const nodes = doc.json.nodes ?? [];
  const parent = new Map();
  nodes.forEach((node, index) => (node.children ?? []).forEach(child => parent.set(child, index)));
  return { nodes, parent };
}
const O = prepare(original);
const H = prepare(homelander);

function worldRest(prep) {
  const cache = new Map();
  const build = index => {
    if (cache.has(index)) return cache.get(index);
    const node = prep.nodes[index];
    const own = local(node);
    const parentIndex = prep.parent.get(index);
    let result;
    if (parentIndex === undefined) result = { p: [...own.p], q: Q.norm(own.q) };
    else {
      const p = build(parentIndex);
      const r = Q.rotate(p.q, own.p);
      result = { p: [p.p[0] + r[0], p.p[1] + r[1], p.p[2] + r[2]], q: Q.mul(p.q, own.q) };
    }
    cache.set(index, result);
    return result;
  };
  return { cache, build };
}
const ORest = worldRest(O);
const HRest = worldRest(H);
const OSkin = original.json.skins[0];
const HSkin = homelander.json.skins[0];
const OJoints = OSkin.joints.map(index => O.nodes[index]);
const HJoints = HSkin.joints.map(index => H.nodes[index]);
const ORestWorld = OJoints.map((_, i) => ORest.build(OSkin.joints[i]));
const HRestWorld = HJoints.map((_, i) => HRest.build(HSkin.joints[i]));
const HIndexByName = new Map(HJoints.map((node, index) => [node.name, index]));
const ORestByName = new Map(OJoints.map((node, index) => [node.name, index]));

const mapping = new Map();
const mapBone = (h, o) => { if (HIndexByName.has(h) && ORestByName.has(o)) mapping.set(HIndexByName.get(h), ORestByName.get(o)); };
mapBone('root.x', 'pelvis');
for (const i of ['01', '02', '03']) mapBone(`spine_${i}.x`, `spine_${i}`);
mapBone('neck.x', 'neck_01');
mapBone('head.x', 'head');
for (const [hs, os] of [['l', 'l'], ['r', 'r']]) {
  // Homelander's "shoulder" bone carries the upper-arm weights; it has no
  // separate clavicle bone. Map it to the original upper arm, and leave the
  // small arm_stretch helper at rest.
  mapBone(`shoulder.${hs}`, `upperarm_${os}`);
  mapBone(`arm_twist.${hs}`, `upperarm_twist_01_${os}`);
  mapBone(`forearm_stretch.${hs}`, `lowerarm_${os}`);
  mapBone(`forearm_twist.${hs}`, `lowerarm_twist_01_${os}`);
  mapBone(`hand.${hs}`, `hand_${os}`);
  for (const [base, o] of [['index', 'index'], ['middle', 'middle'], ['pinky', 'pinky'], ['ring', 'ring']]) {
    mapBone(`${base}1_base.${hs}`, `${o}_01_${os}`);
    mapBone(`${base}1.${hs}`, `${o}_02_${os}`);
    mapBone(`${base}2.${hs}`, `${o}_03_${os}`);
    mapBone(`${base}3.${hs}`, `${o}_03_${os}_end`);
  }
  mapBone(`thumb1.${hs}`, `thumb_01_${os}`);
  mapBone(`thumb2.${hs}`, `thumb_02_${os}`);
  mapBone(`thumb3.${hs}`, `thumb_03_${os}`);
  mapBone(`thigh_stretch.${hs}`, `thigh_${os}`);
  mapBone(`leg_stretch.${hs}`, `calf_${os}`);
  mapBone(`foot.${hs}`, `foot_${os}`);
  mapBone(`toes_01.${hs}`, `ball_${os}`);
  mapBone(`thigh_twist.${hs}`, `thigh_twist_01_${os}`);
  mapBone(`leg_twist.${hs}`, `calf_twist_01_${os}`);
}
const unmapped = HJoints.map((node, index) => mapping.has(index) ? null : node.name).filter(Boolean);

function channelsForClip(clip) {
  const rotation = new Map(), translation = new Map();
  for (const channel of clip.channels) {
    const sampler = clip.samplers[channel.sampler];
    const times = accessor(original, sampler.input).values;
    const values = accessor(original, sampler.output).values;
    if (channel.target.path === 'rotation') rotation.set(channel.target.node, { times, values });
    if (channel.target.path === 'translation') translation.set(channel.target.node, { times, values });
  }
  return { rotation, translation };
}
function sample(channel, time, components, fallback) {
  if (!channel) return fallback;
  const { times, values } = channel;
  if (time <= times[0]) return Array.from(values.slice(0, components));
  if (time >= times[times.length - 1]) { const base = (times.length - 1) * components; return Array.from(values.slice(base, base + components)); }
  let low = 0, high = times.length - 1;
  while (high - low > 1) { const mid = (low + high) >> 1; if (times[mid] <= time) low = mid; else high = mid; }
  const t = (time - times[low]) / (times[high] - times[low] || 1);
  if (components === 4) {
    const a = Array.from(values.slice(low * 4, low * 4 + 4)), b = Array.from(values.slice(high * 4, high * 4 + 4));
    return Q.slerp(Q.norm(a), Q.norm(b), t);
  }
  const a = values.slice(low * 3, low * 3 + 3), b = values.slice(high * 3, high * 3 + 3);
  return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
}

function topo(nodes, parent) {
  const order = [];
  const visit = index => { const p = parent.get(index); if (p !== undefined) visit(p); if (!order.includes(index)) order.push(index); };
  nodes.forEach((_, index) => visit(index));
  return order;
}
const OOrder = topo(O.nodes, O.parent);
const HOrder = topo(H.nodes, H.parent);
const OPelvisIndex = OJoints.findIndex(node => node.name === 'pelvis');
const HPelvisIndex = HJoints.findIndex(node => node.name === 'root.x');
const HRootLocal = local(HJoints[HPelvisIndex]);
const ORestPelvis = ORestWorld[OPelvisIndex];

const clips = {};
for (const clip of original.json.animations ?? []) {
  const duration = Math.max(...clip.samplers.map(sampler => accessor(original, sampler.input).max?.[0] ?? 0));
  const frameCount = Math.max(1, Math.ceil(duration * FPS));
  const times = Array.from({ length: frameCount + 1 }, (_, i) => Math.min(duration, i / FPS));
  const { rotation, translation } = channelsForClip(clip);
  const boneTracks = new Map();
  for (const [hIndex] of mapping) boneTracks.set(hIndex, []);
  const rootPositions = [];
  for (const time of times) {
    const oLocalQ = new Map(), oLocalP = new Map();
    for (let index = 0; index < O.nodes.length; index++) {
      const base = local(O.nodes[index]);
      oLocalQ.set(index, Q.norm(sample(rotation.get(index), time, 4, base.q)));
      oLocalP.set(index, sample(translation.get(index), time, 3, base.p));
    }
    const oWorldQ = new Map(), oWorldP = new Map();
    for (const index of OOrder) {
      const p = O.parent.get(index);
      const q = oLocalQ.get(index), pos = oLocalP.get(index);
      if (p === undefined) { oWorldQ.set(index, q); oWorldP.set(index, [...pos]); }
      else {
        const r = Q.rotate(oWorldQ.get(p), pos);
        oWorldQ.set(index, Q.mul(oWorldQ.get(p), q));
        oWorldP.set(index, [oWorldP.get(p)[0] + r[0], oWorldP.get(p)[1] + r[1], oWorldP.get(p)[2] + r[2]]);
      }
    }
    const oPelvis = oWorldP.get(OSkin.joints[OPelvisIndex]);
    const deltaPos = [oPelvis[0] - ORestPelvis.p[0], oPelvis[1] - ORestPelvis.p[1], oPelvis[2] - ORestPelvis.p[2]];
    rootPositions.push([HRootLocal.p[0] + deltaPos[0], HRootLocal.p[1] + deltaPos[1], HRootLocal.p[2] + deltaPos[2]]);

    const hWorldQ = new Map();
    for (const index of HOrder) {
      const hNode = H.nodes[index];
      const hBase = local(hNode);
      const p = H.parent.get(index);
      const rest = HRest.build(index);
      const hIndex = HJoints.findIndex(node => node === hNode);
      let worldQ = rest.q;
      if (hIndex >= 0) {
        const oIndex = mapping.get(hIndex);
        if (oIndex !== undefined) {
          const originalWorld = oWorldQ.get(OSkin.joints[oIndex]);
          // The Homelander rest pose is a T-pose while the original rest is
          // A-pose. Transfer absolute world orientation for the arm/finger
          // chain (otherwise the arms stay horizontal during locomotion), but
          // use a rest-relative delta for the spine/root/legs so the whole
          // body does not inherit the original 90-degree bone roll.
          if (/^shoulder/.test(HJoints[hIndex].name)) {
            worldQ = originalWorld;
          } else {
            const delta = Q.mul(originalWorld, Q.inv(ORestWorld[oIndex].q));
            worldQ = Q.mul(delta, rest.q);
          }
        }
      }
      hWorldQ.set(index, worldQ);
      if (hIndex >= 0 && mapping.has(hIndex)) {
        const parentWorld = p === undefined ? Q.id : (hWorldQ.get(p) ?? HRest.build(p).q);
        const localQ = Q.mul(Q.inv(parentWorld), worldQ);
        boneTracks.get(hIndex).push(localQ);
      }
    }
  }
  clips[clip.name] = {
    duration,
    times,
    root: { positions: rootPositions },
    bones: Object.fromEntries([...boneTracks].map(([hIndex, rotations]) => [HJoints[hIndex].name, rotations])),
  };
}

fs.writeFileSync(OUTPUT, JSON.stringify({ schemaVersion: 1, source: 'UNDEFEATED hero.gltf', target: 'homelander.glb', fps: FPS, mapped: mapping.size, unmapped, clips }));
console.log(JSON.stringify({ output: path.relative(ROOT, OUTPUT), bytes: fs.statSync(OUTPUT).size, clips: Object.keys(clips), mapped: mapping.size, unmapped }, null, 1));
