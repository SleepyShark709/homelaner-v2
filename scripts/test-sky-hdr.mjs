import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { RGBE_ReadHeader, RGBE_ReadPixels } from '@babylonjs/core/Misc/HighDynamicRange/hdr.js';

const root = path.resolve(import.meta.dirname,'..');
const evidence = JSON.parse(fs.readFileSync(path.join(root,'research/world-recovery/sky-recovery/sampling-evidence.json'),'utf8'));
const file = fs.readFileSync(path.join(root,'public',evidence.image.url));
const bytes = new Uint8Array(file.buffer,file.byteOffset,file.byteLength);
const header = RGBE_ReadHeader(bytes);
assert.equal(header.width,evidence.image.width); assert.equal(header.height,evidence.image.height);
// Exercise Babylon's actual loader decoder on the UModel flat RGBE file.
// Non-RLE payload and row orientation cannot be inferred from its RLE header.
const pixels = RGBE_ReadPixels(bytes,header);
for (const sample of evidence.image.pixelSamples) {
  const offset = (sample.y*header.width+sample.x)*3;
  assert.deepEqual(Array.from(pixels.subarray(offset,offset+3)),sample.linearRGB,
    `Original HDR row/channel identity changed at ${sample.x},${sample.y}`);
}
assert.ok(evidence.image.pixelSamples.some(sample=>sample.linearRGB.some(value=>value>1)),'No HDR-range fixture');
console.log('Babylon HDR decoder preserves all 6 original RGBE probes, top/bottom row identity and values above one.');
