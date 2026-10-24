import { readFile, stat } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../public');
const fail = message => { throw new Error(message); };
const contained = target => target === root || target.startsWith(root + path.sep);
async function localFile(base, uri) {
  if (/^[a-z]+:/i.test(uri) || uri.startsWith('//')) fail(`External URI disallowed: ${uri}`);
  const result = path.resolve(uri.startsWith('/') ? root : base, decodeURIComponent(uri).replace(/^\//, ''));
  if (!contained(result)) fail(`Asset escapes public/: ${uri}`);
  await stat(result);
  return result;
}
const sizes = { 5120: 1, 5121: 1, 5122: 2, 5123: 2, 5125: 4, 5126: 4 };
const widths = { SCALAR: 1, VEC2: 2, VEC3: 3, VEC4: 4, MAT4: 16 };
const readers = { 5120: 'readInt8', 5121: 'readUInt8', 5122: 'readInt16LE', 5123: 'readUInt16LE', 5125: 'readUInt32LE', 5126: 'readFloatLE' };
const catalog = JSON.parse(await readFile(path.join(root, 'assets/original/catalog.json'), 'utf8'));
if (!Array.isArray(catalog) || !catalog.length) fail('No asset catalog entries');
if (process.argv.includes('--game')) {
  catalog.push({ id: 'assembled-character', url: '/assets/character/hero.gltf', sourcePackage: 'PlayerBP/head_accessories + original body' });
  const city = JSON.parse(await readFile(path.join(root, 'assets/city/manifest.json'), 'utf8'));
  if (city.coordinateSystem !== 'gltf-rh-y-up-meters') fail('City coordinate mismatch');
  const assetIds = new Set(city.assets.map(asset => asset.id));
  for (const item of city.objects) {
    if (!assetIds.has(item.assetId) || !item.sourceActor) fail(`Missing city source/reference: ${item.id}`);
    if (![...item.position, ...item.rotation, ...item.scale].every(Number.isFinite)) fail(`Nonfinite transform: ${item.id}`);
    if (Math.abs(Math.hypot(...item.rotation) - 1) > 0.002) fail(`Invalid city quaternion: ${item.id}`);
    if (item.scale.some(value => Math.abs(value) < 1e-8)) fail(`Zero scale: ${item.id}`);
  }
  for (const asset of city.assets) catalog.push({ ...asset, id: `city/${asset.id}`, sourcePackage: asset.sourcePackage ?? 'Recovered city mesh; see city-layout evidence' });
  console.log(`City: ${city.objects.length} source-attributed objects; transform and reference checks OK.`);
  const population = JSON.parse(await readFile(path.join(root, 'assets/population-manifest.json'), 'utf8'));
  if (population.coordinateSystem !== city.coordinateSystem || JSON.stringify(population.originUE) !== JSON.stringify(city.originUE)) fail('Population/city coordinate mismatch');
  const models = new Map(), routes = new Map(), spawnIds = new Set(), counts = { citizen: 0, vehicle: 0, prop: 0 };
  const point = value => Array.isArray(value) && value.length === 3 && value.every(Number.isFinite);
  const inDistrict = value => point(value) && [0, 2].every(axis => value[axis] >= city.bounds.min[axis] && value[axis] <= city.bounds.max[axis]);
  for (const model of population.models) {
    if (!model.id || models.has(model.id) || !(model.kind in counts)) fail('Missing/duplicate population model identity');
    if (!['+X', '+Z', '-Z'].includes(model.forwardAxis) || !Number.isFinite(model.groundOffset)) fail(`Invalid population axis/ground offset: ${model.id}`);
    if (!point(model.bounds?.min) || !point(model.bounds?.max) || model.bounds.min.some((v, i) => v > model.bounds.max[i])) fail(`Invalid population bounds: ${model.id}`);
    models.set(model.id, model);
    catalog.push({ ...model, id: `population/${model.id}`, sourcePackage: 'Original exported population model; see population-placement evidence',
      requiredClips: model.kind === 'citizen' ? ['Citizen_N_Idle_Pose', 'Citizen_N_Walk_F', 'Citizen_N_Run_F'] : [] });
  }
  for (const route of population.routes) {
    if (!route.id || routes.has(route.id) || !['citizen', 'vehicle'].includes(route.kind) || typeof route.closed !== 'boolean' || !route.provenance) fail('Invalid population route identity/provenance');
    if (!Array.isArray(route.points) || route.points.length < 2 || route.points.some(p => !inDistrict(p))) fail(`Invalid/outside population route: ${route.id}`);
    routes.set(route.id, route);
  }
  for (const spawn of population.spawns) {
    const model = models.get(spawn.modelId);
    if (!spawn.id || spawnIds.has(spawn.id) || !model || !inDistrict(spawn.position) || !Number.isFinite(spawn.yaw)) fail(`Invalid population spawn: ${spawn.id}`);
    if (spawn.routeId && (!routes.has(spawn.routeId) || routes.get(spawn.routeId).kind !== model.kind)) fail(`Population route/model mismatch: ${spawn.id}`);
    counts[model.kind]++; spawnIds.add(spawn.id);
  }
  if (counts.citizen < 8 || counts.vehicle < 3 || counts.prop < 3) fail(`Population incomplete: ${JSON.stringify(counts)}`);
  console.log(`Population: ${spawnIds.size} spawns (${counts.citizen} citizens, ${counts.vehicle} vehicles, ${counts.prop} props), ${routes.size} attributed browser routes; references and transforms OK.`);
}
const ids = new Set();
for (const entry of catalog) {
  if (!entry.id || ids.has(entry.id) || !entry.sourcePackage) fail('Missing/duplicate identity or source');
  ids.add(entry.id);
  const filename = await localFile(root, entry.url);
  const model = JSON.parse(await readFile(filename, 'utf8'));
  if (model.asset.version !== '2.0') fail(`Unsupported glTF: ${entry.id}`);
  for (const name of entry.requiredClips ?? []) if (!(model.animations ?? []).some(clip => clip.name === name)) fail(`Missing required animation ${name}: ${entry.id}`);
  const base = path.dirname(filename);
  const buffers = await Promise.all((model.buffers ?? []).map(async buffer => {
    const bytes = await readFile(await localFile(base, buffer.uri));
    if (bytes.length < buffer.byteLength) fail(`Truncated buffer: ${buffer.uri}`);
    return bytes;
  }));
  await Promise.all((model.images ?? []).filter(image => image.uri).map(image => localFile(base, image.uri)));
  function accessor(index) {
    const a = model.accessors[index];
    if (!a || a.sparse) fail(`Missing or unsupported sparse accessor ${index}`);
    const view = model.bufferViews[a.bufferView];
    const width = widths[a.type], size = sizes[a.componentType];
    if (!view || !size || !width || !Number.isInteger(a.count) || a.count <= 0) fail(`Invalid accessor ${index}`);
    const buffer = buffers[view.buffer];
    const start = (view.byteOffset ?? 0) + (a.byteOffset ?? 0);
    const stride = view.byteStride ?? size * width;
    const end = start + (a.count - 1) * stride + size * width;
    if (!buffer || end > buffer.length || end > (view.byteOffset ?? 0) + view.byteLength) fail(`Accessor ${index} exceeds buffer bounds`);
    const values = new Array(a.count * width);
    for (let row = 0; row < a.count; row++) for (let col = 0; col < width; col++) {
      const value = buffer[readers[a.componentType]](start + row * stride + col * size);
      if (!Number.isFinite(value)) fail(`Nonfinite accessor ${index}`);
      values[row * width + col] = value;
    }
    return { ...a, values, width };
  }
  for (let index = 0; index < model.accessors.length; index++) accessor(index);
  let triangles = 0;
  for (const node of model.nodes ?? []) {
    if (node.mesh === undefined) continue;
    const skin = node.skin === undefined ? null : model.skins[node.skin];
    for (const primitive of model.meshes[node.mesh].primitives) {
      const position = accessor(primitive.attributes.POSITION);
      if (primitive.indices !== undefined) {
        const indices = accessor(primitive.indices);
        if (indices.values.some(value => value < 0 || value >= position.count)) fail('Mesh index outside vertex range');
        triangles += Math.floor(indices.count / 3);
      }
      if (skin && primitive.attributes.JOINTS_0 !== undefined) {
        const joints = accessor(primitive.attributes.JOINTS_0);
        if (joints.values.some(value => value >= skin.joints.length)) fail('Joint index outside skin range');
        const weights = accessor(primitive.attributes.WEIGHTS_0);
        const divisor = weights.normalized ? ({ 5121: 255, 5123: 65535 }[weights.componentType] ?? 1) : 1;
        for (let i = 0; i < weights.values.length; i += 4) {
          const sum = weights.values.slice(i, i + 4).reduce((a, b) => a + b, 0) / divisor;
          if (Math.abs(sum - 1) > 0.025) fail(`Unnormalized skin weights: ${sum}`);
        }
      }
    }
  }
  for (const skin of model.skins ?? []) {
    if (skin.joints.some(joint => !model.nodes[joint])) fail('Missing bone node');
    if (skin.inverseBindMatrices !== undefined && accessor(skin.inverseBindMatrices).count !== skin.joints.length) fail('Bind matrix count mismatch');
  }
  for (const clip of model.animations ?? []) for (const channel of clip.channels) {
    if (!model.nodes[channel.target.node]) fail(`Missing animation target in ${clip.name}`);
    const sampler = clip.samplers[channel.sampler];
    const input = accessor(sampler.input), output = accessor(sampler.output);
    if (input.values.some((value, index, array) => value < 0 || (index > 0 && value <= array[index - 1]))) fail(`Nonmonotonic times in ${clip.name}`);
    if (output.count !== input.count * (sampler.interpolation === 'CUBICSPLINE' ? 3 : 1)) fail(`Key count mismatch in ${clip.name}`);
    if (channel.target.path === 'rotation') for (let i = 0; i < output.values.length; i += 4) {
      const length = Math.hypot(...output.values.slice(i, i + 4));
      if (Math.abs(length - 1) > 0.002) fail(`Non-unit quaternion in ${clip.name}`);
    }
  }
  console.log(`${entry.id}: ${triangles.toLocaleString()} triangles, ${(model.skins ?? []).reduce((sum, skin) => sum + skin.joints.length, 0)} joints, ${model.animations?.length ?? 0} clips; references, buffers and skin/animation data OK`);
}
console.log(`Validated ${catalog.length} original assets.`);
