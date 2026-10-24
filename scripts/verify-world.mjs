import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const root = path.resolve(import.meta.dirname, '..');
const publicRoot = path.join(root, 'public');
const read = file => JSON.parse(fs.readFileSync(file, 'utf8').replace(/^\uFEFF/, ''));
const source = name => path.join(publicRoot, 'assets/world', name);
const geometry = read(source('geometry-manifest.json'));
const material = read(source('material-manifest.json'));
const terrain = read(source('terrain-manifest.json'));
const terrainMaterial = read(source('terrain-material-manifest.json'));
const streaming = read(source('streaming-manifest.json'));
const sky = read(source('sky-material-manifest.json'));
const files = new Set();
function exists(url, base = publicRoot) {
  assert.equal(typeof url, 'string');
  assert.ok(!url.includes('://') && !url.startsWith('data:'), `Unexpected external asset: ${url}`);
  const file = path.resolve(url.startsWith('/') ? publicRoot : base, url.startsWith('/') ? url.slice(1) : url);
  assert.ok(file.startsWith(publicRoot + path.sep), `Asset escapes public folder: ${url}`);
  assert.ok(fs.statSync(file).isFile(), `Missing asset: ${url}`);
  files.add(file); return file;
}
let gltfCount = 0, glbCount = 0;
for (const asset of [...geometry.assets, ...terrain.assets]) {
  const file = exists(asset.url);
  if (file.endsWith('.gltf')) {
    const doc = read(file); gltfCount++;
    for (const buffer of doc.buffers ?? []) {
      const bin = exists(buffer.uri, path.dirname(file));
      assert.ok(fs.statSync(bin).size >= buffer.byteLength, `Short glTF buffer: ${bin}`);
    }
    for (const image of doc.images ?? []) if (image.uri) exists(image.uri, path.dirname(file));
    for (const mesh of doc.meshes ?? []) for (const primitive of mesh.primitives) {
      assert.ok(doc.accessors[primitive.attributes.POSITION]?.count > 0, `Missing positions: ${asset.id}`);
      assert.ok(doc.accessors[primitive.indices]?.count > 0, `Missing indices: ${asset.id}`);
    }
  } else {
    const data = fs.readFileSync(file); glbCount++;
    assert.equal(data.toString('ascii', 0, 4), 'glTF'); assert.equal(data.readUInt32LE(4), 2);
    assert.equal(data.readUInt32LE(8), data.length);
  }
  if (asset.highQualityUrl) exists(asset.highQualityUrl);
}
const ids = new Set(geometry.assets.map(asset => asset.id));
assert.equal(ids.size, geometry.assets.length, 'Duplicate geometry asset IDs');
let objectCount = 0;
for (const level of geometry.levels) for (const object of level.objects) {
  objectCount++; assert.ok(ids.has(object.assetId), `Unknown asset ${object.assetId}`);
  for (const value of [...object.position, ...object.rotation, ...object.scale]) assert.ok(Number.isFinite(value), `Invalid transform: ${object.id}`);
  assert.ok(Math.abs(Math.hypot(...object.rotation) - 1) < 1e-4, `Invalid quaternion: ${object.id}`);
  for (const slot of object.materialOverrides ?? []) {
    if (slot.material) assert.ok(material.materials[slot.material.package], `Missing override material ${slot.material.package}`);
  }
}
for (const asset of geometry.assets) for (const slot of asset.sourceMaterialSlots ?? []) {
  if (slot.material) assert.ok(material.materials[slot.material.package], `Missing source material ${slot.material.package}`);
}
for (const record of Object.values(material.materials)) {
  for (const channel of Object.values(record.channels ?? {})) if (channel?.url) exists(channel.url);
  if (record.packedPBR?.url) exists(record.packedPBR.url);
  if (record.packedOpacity?.url) exists(record.packedOpacity.url);
  for (const texture of Object.values(record.shaderRecovery?.textures ?? {})) {
    exists(texture.url);
    assert.ok(['linear','srgb'].includes(texture.colorSpace), `Unknown recovered texture color space: ${record.sourcePackage}`);
  }
  if (record.shaderRecovery?.kind === 'world-triplanar') {
    for (const texture of Object.values(record.shaderRecovery.textures)) exists(texture.url);
    assert.ok(record.shaderRecovery.worldScaleUEcmNegative.every(value => Number.isFinite(value) && value < 0));
    assert.ok(['r','g','b','a'].includes(record.shaderRecovery.textures.roughness.channel));
  }
}
for (const [sourceMaterial, recipe] of Object.entries(sky.materials)) {
  assert.ok(material.materials[sourceMaterial], `Missing sky source material: ${sourceMaterial}`);
  const file = exists(recipe.texture.url);
  assert.equal(crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex'), recipe.source.textureSha256);
  assert.equal(recipe.texture.colorSpace,'linear'); assert.deepEqual(recipe.uvScale,[1,2]);
  assert.ok([...recipe.tint,...recipe.selectionColor,recipe.contrast,recipe.brightness,recipe.opacity].every(Number.isFinite));
}
assert.equal(streaming.baseline.packages.length, 17);
assert.equal(streaming.startupSequence.length, 12);
for (const name of streaming.baseline.packages) assert.ok(geometry.levels.some(level => level.package === name), `Missing startup level ${name}`);
assert.equal(geometry.coordinateSystem, terrain.coordinateSystem);
assert.deepEqual(geometry.originUE, terrain.originUE);
assert.equal(terrain.objects.length, 144);
assert.equal(terrainMaterial.objects.length, terrain.objects.length);
for (const layer of Object.values(terrainMaterial.layers)) {
  exists(layer.albedo.url); exists(layer.normal.url);
  assert.equal(layer.albedo.colorSpace, 'srgb');
}
for (const recipe of terrainMaterial.objects) {
  assert.ok(terrain.objects.some(object => object.id === recipe.id), `Unknown terrain material ${recipe.id}`);
  exists(recipe.weightmap.url); exists(recipe.heightNormal.url);
  assert.equal(recipe.meshPositionXZContainsSectionBase, false);
  assert.equal(recipe.weightmap.width, 128); assert.equal(recipe.weightmap.height, 128);
  for (const channel of Object.values(recipe.weightmap.channels)) assert.ok([0, 1, 2, 3].includes(channel));
  for (let i = 0; i < 2; i++) assert.ok(Math.abs(recipe.textureUVOffset[i] - recipe.sectionBaseUE[i] * recipe.textureUVScale[i]) < 1e-8);
}
const result = { generatedAt:new Date().toISOString(), geometryAssets:geometry.assets.length,
  levels:geometry.levels.length, renderedObjectRecords:objectCount, terrainBlocks:terrain.objects.length,
  gltfFiles:gltfCount, glbFiles:glbCount, localFilesVerified:files.size,
  manifestSHA256: Object.fromEntries(['geometry-manifest.json','material-manifest.json','terrain-manifest.json','terrain-material-manifest.json','streaming-manifest.json','sky-material-manifest.json'].map(name=>[name,crypto.createHash('sha256').update(fs.readFileSync(source(name))).digest('hex')])),
  scope:'Manifest, local-resource and runtime-binding integration checks; not original-game behavior equivalence.' };
fs.mkdirSync(path.join(root,'research/world-recovery'),{recursive:true});
fs.writeFileSync(path.join(root,'research/world-recovery/runtime-asset-validation.json'),JSON.stringify(result,null,2));
console.log(JSON.stringify(result,null,2));
