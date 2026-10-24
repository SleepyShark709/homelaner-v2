import assert from 'node:assert/strict';
import { test } from 'node:test';
import { OriginalPlayer } from '../src/play/OriginalPlayer.ts';

class FakeInput {
  down = new Set();
  presses = new Set();
  yaw = Math.PI;
  held(...keys) { return keys.some(key => this.down.has(key)); }
  pressed(key) { const value = this.presses.has(key); this.presses.delete(key); return value; }
  axis(positive, negative) { return Number(this.held(...positive)) - Number(this.held(...negative)); }
}
const ground = { heightAt: () => 0 };
const spatial = { nearby: () => [] };
const bounds = { min: [-500, -100, -500], max: [500, 500, 500] };
const step = (player, input, seconds, each) => {
  const count = Math.round(seconds * 120);
  for (let i = 0; i < count; i++) { player.update(1 / 120, input); each?.(i); }
};
function make() {
  const input = new FakeInput();
  const player = new OriginalPlayer([0, 0.02, 0], ground, spatial, bounds);
  return { input, player };
}

test('ground settle and walk direction follow original input axes', () => {
  const { input, player } = make();
  step(player, input, 0.5);
  assert.equal(player.grounded, true);
  input.down.add('KeyW');
  step(player, input, 1);
  assert.ok(player.position[2] < -4, `expected forward (-Z) movement, got ${player.position[2]}`);
  assert.ok(Math.hypot(player.velocity[0], player.velocity[2]) > 5);
  assert.equal(player.state, 'run');
});

test('ground Space jumps; airborne Space opens flight; flight Space exits', () => {
  const { input, player } = make();
  step(player, input, 0.3);
  input.presses.add('Space');
  player.update(1 / 120, input);
  assert.ok(player.velocity[1] > 0);
  assert.equal(player.flying, false);
  step(player, input, 0.2);
  assert.ok(player.position[1] > 0.2, `expected airborne, got ${player.position[1]}`);
  input.presses.add('Space');
  player.update(1 / 120, input);
  assert.equal(player.flying, true);
  assert.equal(player.state, 'hover');
  input.presses.add('Space');
  player.update(1 / 120, input);
  assert.equal(player.flying, false);
});

test('holding E on the ground charges flight after one second', () => {
  const { input, player } = make();
  step(player, input, 0.3);
  input.down.add('KeyE');
  let chargedAt = null;
  step(player, input, 1.2, (index) => { if (player.flying && chargedAt === null) chargedAt = index / 120; });
  assert.equal(player.flying, true);
  assert.ok(chargedAt >= 0.99 && chargedAt < 1.02, `charge fired at ${chargedAt}`);
  assert.equal(player.charge, 0);
});

test('sprint exceeds walk, Alt walk is slower, E/Q move vertically in flight', () => {
  const { input, player } = make();
  const distance = (keys) => {
    player.reset(); input.down.clear(); input.presses.clear();
    step(player, input, 0.3);
    for (const key of keys) input.down.add(key);
    step(player, input, 1);
    return Math.abs(player.position[2]);
  };
  const walked = distance(['KeyW']);
  const sprinted = distance(['KeyW', 'ShiftLeft']);
  assert.ok(sprinted > walked, `sprint ${sprinted} should exceed walk ${walked}`);
  const walkedSlow = distance(['KeyW', 'AltLeft']);
  assert.ok(walkedSlow < walked, `Alt walk ${walkedSlow} should be slower than walk ${walked}`);
  input.down.clear();
  player.reset(); step(player, input, 0.3);
  input.presses.add('Space'); player.update(1 / 120, input); step(player, input, 0.2);
  input.presses.add('Space'); player.update(1 / 120, input);
  assert.equal(player.flying, true);
  const startY = player.position[1];
  input.down.add('KeyE'); step(player, input, 0.5); input.down.delete('KeyE');
  assert.ok(player.position[1] > startY + 1, `E should ascend, got ${player.position[1] - startY}`);
  const highY = player.position[1];
  input.down.add('KeyQ'); step(player, input, 0.8); input.down.delete('KeyQ');
  assert.ok(player.position[1] < highY, 'Q should descend');
});

test('Shift only arms sprint when movement input is present', () => {
  const { input, player } = make();
  step(player, input, 0.3);
  input.down.add('ShiftLeft');
  step(player, input, 0.5);
  assert.equal(player.sprint, false);
  assert.ok(Math.hypot(player.velocity[0], player.velocity[2]) < 0.01);
  input.down.add('KeyW');
  step(player, input, 0.5);
  assert.equal(player.sprint, true);
  assert.ok(Math.hypot(player.velocity[0], player.velocity[2]) > 15);
  input.down.delete('ShiftLeft');
  step(player, input, 0.1);
  assert.equal(player.sprint, false);
});

test('dynamic vehicle/prop boxes block walking', () => {
  const { input, player } = make();
  player.setDynamicBoxes([{ id: 'preview-car', min: [-2, -1, -4], max: [2, 2, -2] }]);
  step(player, input, 0.3);
  input.down.add('KeyW');
  step(player, input, 2);
  assert.ok(player.position[2] > -1.9, `expected AABB block before -2m, got ${player.position[2]}`);
  assert.ok(player.velocity[2] >= -0.01, `expected forward velocity cleared, got ${player.velocity[2]}`);
});

test('R resets to the original spawn and clears flight', () => {
  const { input, player } = make();
  input.down.add('KeyE'); step(player, input, 1.2);
  assert.equal(player.flying, true);
  input.down.clear(); input.presses.add('KeyR'); player.update(1 / 120, input);
  assert.ok(Math.abs(player.position[0]) < 1e-9 && Math.abs(player.position[1] - 0.02) < 1e-9 && Math.abs(player.position[2]) < 1e-9, `reset position ${player.position}`);
  assert.equal(player.flying, false);
  assert.equal(player.velocity[1], 0);
});
