import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { OriginalStreaming, createOriginalNewSaveFlags } from '../src/world/OriginalStreaming.ts';

const manifest = JSON.parse(readFileSync(new URL('../public/assets/world/streaming-manifest.json', import.meta.url), 'utf8'));
const flush = async () => { for (let i = 0; i < 12; i++) await Promise.resolve(); };
function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
function harness() {
  const calls = [], delays = [], events = [];
  const adapter = {
    load(request) { const pending = deferred(); calls.push({ operation: 'load', request, ...pending }); return pending.promise; },
    unload(request) { const pending = deferred(); calls.push({ operation: 'unload', request, ...pending }); return pending.promise; },
  };
  const clock = { delay(milliseconds, signal) { const pending = deferred(); delays.push({ milliseconds, signal, ...pending }); return pending.promise; } };
  const stream = OriginalStreaming.fromManifest(manifest, adapter, { clock, onEvent: e => events.push(e) });
  return { stream, calls, delays, events };
}
async function completeCity(h) {
  for (const step of manifest.startupSequence) {
    const call = h.calls.at(-1);
    assert.equal(call.request.branch, 'city'); assert.equal(call.request.levelName, step.levelName);
    call.resolve(); await flush();
  }
}

test('resident requests preserve raw World table order without serializing completion', async () => {
  const h = harness(), work = h.stream.prepareResidentWorld();
  await assert.rejects(h.stream.beginPlay(), /Resident preparation is loading/);
  assert.equal(h.calls.length, 1); assert.equal(h.calls[0].request.levelName, 'MainLevel');
  h.calls[0].resolve(); await flush();
  assert.deepEqual(h.calls.slice(1).map(c => c.request.levelName), manifest.baseline.alwaysLoadedLevelNames);
  h.calls.slice(1).reverse().forEach(c => c.resolve());
  assert.equal((await work).resident, 'ready');
  await h.stream.prepareResidentWorld(); assert.equal(h.calls.length, 5);
  h.stream.dispose();
});

test('failed resident assembly cannot begin the original startup chain', async () => {
  const h = harness(), work = h.stream.prepareResidentWorld();
  h.calls[0].reject(new Error('persistent world failed'));
  assert.equal((await work).resident, 'failed');
  await assert.rejects(h.stream.beginPlay(), /Resident preparation is failed/);
  assert.equal(h.calls.length, 1);
  h.stream.dispose();
});

test('fresh-save flags are explicit, isolated and limited to the recovered condition', () => {
  const first = createOriginalNewSaveFlags(), second = createOriginalNewSaveFlags();
  assert.deepEqual(first, { isFirstPlayerSpecialAction: false });
  first.isFirstPlayerSpecialAction = true;
  assert.equal(second.isFirstPlayerSpecialAction, false);
});

test('each city level waits for actual completion; overlay delay starts only after its own completion', async () => {
  const h = harness(), work = h.stream.beginPlay({ isFirstPlayerSpecialAction: false });
  assert.deepEqual(h.calls.map(c => c.request.levelName), ['LoadLevel', 'DownTown']);
  await flush(); assert.equal(h.calls.length, 2); assert.equal(h.delays.length, 0);
  const overlay = h.calls[0];
  await completeCity(h);
  assert.equal((await work).phase, 'complete');
  assert.equal(h.stream.getSnapshot().overlay, 'loading');
  assert.equal(h.calls.some(c => c.request.levelName === 'EnelightMeteor'), false);
  overlay.resolve(); await flush();
  assert.equal(h.delays.length, 1); assert.equal(h.delays[0].milliseconds, 1000);
  assert.equal(h.calls.some(c => c.operation === 'unload'), false);
  h.delays[0].resolve(); await flush();
  const unload = h.calls.at(-1);
  assert.equal(unload.operation, 'unload'); assert.equal(unload.request.levelName, 'LoadLevel');
  unload.resolve(); await h.stream.waitForOverlay();
  assert.equal(h.stream.getSnapshot().overlay, 'complete');
  assert.equal(h.stream.getSnapshot().loadedPackages.some(p => p.endsWith('/LoadLevel')), false);
  assert.equal(h.stream.getSnapshot().completedCitySteps, 12);
  h.stream.dispose();
});

test('overlay can finish while first city level is still loading', async () => {
  const h = harness(); h.stream.beginPlay();
  h.calls[0].resolve(); await flush(); h.delays[0].resolve(); await flush();
  h.calls.at(-1).resolve(); await h.stream.waitForOverlay();
  assert.equal(h.stream.getSnapshot().completedCitySteps, 0);
  assert.equal(h.stream.getSnapshot().overlay, 'complete');
  h.stream.dispose(); h.calls[1].resolve(); await flush();
});

test('unknown save flag pauses conditional branch; true loads meteor once and waits', async () => {
  const h = harness(), work = h.stream.beginPlay();
  await completeCity(h);
  assert.equal((await work).phase, 'awaiting-save-state');
  assert.equal(h.events.filter(e => e.type === 'needs-save-state').length, 1);
  const resume = h.stream.setSaveFlags({ isFirstPlayerSpecialAction: true });
  assert.equal(h.calls.at(-1).request.levelName, 'EnelightMeteor');
  assert.equal(h.stream.getSnapshot().phase, 'loading');
  await h.stream.setSaveFlags({ isFirstPlayerSpecialAction: true });
  assert.equal(h.calls.filter(c => c.request.levelName === 'EnelightMeteor').length, 1);
  h.calls.at(-1).resolve(); assert.equal((await resume).phase, 'complete');
  h.stream.dispose(); h.calls[0].resolve(); await flush();
});

test('city failure halts the completion chain and does not guess retries', async () => {
  const h = harness(), work = h.stream.beginPlay({ isFirstPlayerSpecialAction: false });
  h.calls[1].reject(new Error('geometry assembly failed'));
  assert.equal((await work).phase, 'failed');
  assert.match(h.stream.getSnapshot().failure, /geometry assembly failed/);
  await h.stream.beginPlay(); assert.equal(h.calls.length, 2);
  h.stream.dispose(); h.calls[0].resolve(); await flush();
});

test('dispose aborts shared signal and ignores late loads and timer completion', async () => {
  const h = harness(), work = h.stream.beginPlay({ isFirstPlayerSpecialAction: true });
  h.calls[0].resolve(); await flush();
  h.stream.dispose();
  const eventCount = h.events.length;
  assert.equal(h.calls.every(c => c.request.signal.aborted), true);
  h.calls[1].resolve(); h.delays[0].resolve(); await work; await h.stream.waitForOverlay();
  assert.equal(h.calls.length, 2); assert.equal(h.events.length, eventCount);
  assert.equal(h.stream.getSnapshot().phase, 'disposed');
  assert.equal(h.stream.getSnapshot().completedCitySteps, 0);
  await h.stream.beginPlay(); await h.stream.prepareResidentWorld(); await h.stream.setSaveFlags({ isFirstPlayerSpecialAction: true });
  assert.equal(h.calls.length, 2);
});

test('unknown events never cause level loads; malformed latent edges are rejected', () => {
  const h = harness();
  for (const event of ['boss', 'story', 'tutorial', 'challenge', 'distance']) {
    assert.equal(h.stream.requestEvent(event).status, 'unknown');
  }
  assert.equal(h.calls.length, 0);
  const bad = structuredClone(manifest); bad.startupSequence[0].onCompletedResumeOffset++;
  assert.throws(() => OriginalStreaming.fromManifest(bad, { load: async () => {}, unload: async () => {} }), /latent completion/);
  h.stream.dispose();
});
