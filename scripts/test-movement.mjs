import assert from 'node:assert/strict';
import { PlayerMotor } from '../src/game/PlayerMotor.ts';
class Keys {
  yaw = Math.PI; down = new Set(); edges = new Set();
  held(...keys) { return keys.some(key => this.down.has(key)); }
  pressed(key) { const value = this.edges.has(key); this.edges.delete(key); return value; }
  axis(positive, negative) { return +this.held(...positive) - +this.held(...negative); }
  press(key) { this.down.add(key); this.edges.add(key); }
  clear() { this.down.clear(); this.edges.clear(); }
}
const floor = { id: 'ground', min: [-500, -5, -500], max: [500, 0, 500] };
const bounds = { min: [-400, 0, -400], max: [400, 100, 400] };
const motor = new PlayerMotor([0, .001, 0], [floor], bounds), input = new Keys();
const tick = (seconds, target = motor, keys = input) => { for (let i = 0; i < seconds * 120; i++) target.update(1 / 120, keys); };
tick(.1); assert.ok(motor.grounded); assert.ok(motor.position[1] >= 0);
input.press('KeyW'); tick(1); assert.ok(motor.position[2] < -7); assert.equal(motor.state, 'run');
input.clear(); tick(.3); assert.equal(motor.state, 'idle'); assert.equal(motor.velocity[2], 0);
input.press('Space'); tick(.15); assert.ok(motor.position[1] > 2); assert.equal(motor.flying, false);
input.clear(); input.press('Space'); tick(.1); assert.equal(motor.flying, true);
input.clear(); input.press('KeyW'); input.press('ShiftLeft'); tick(1); assert.equal(Math.round(Math.hypot(...motor.velocity)), 70);
input.clear(); tick(1); assert.equal(Math.round(Math.hypot(...motor.velocity)), 0); assert.equal(motor.state, 'hover');
const hoverHeight = motor.position[1]; input.press('KeyE'); tick(1); assert.equal(motor.position[1], hoverHeight, 'E heat vision must not ascend'); input.clear();
input.press('KeyF'); tick(5); assert.equal(motor.flying, false); assert.equal(motor.grounded, true);
input.clear(); input.press('KeyR'); tick(.1); assert.ok(Math.abs(motor.position[0]) < .01 && Math.abs(motor.position[2]) < .01);
const wall = { id: 'wall', min: [-50, 0, -12], max: [50, 100, -11] };
const boost = new PlayerMotor([0, 20, 0], [floor, wall], bounds); const boostKeys = new Keys();
boostKeys.press('KeyF'); boostKeys.press('KeyW'); boostKeys.press('ShiftLeft'); tick(2, boost, boostKeys);
assert.ok(boost.position[2] > -10.641 && boost.position[2] < -10.63); assert.equal(boost.velocity[2], 0);
const step = { id: 'curb', min: [-5, 0, -10], max: [5, .15, -2] };
const walker = new PlayerMotor([0, .001, 0], [floor, step], bounds); const walkKeys = new Keys();
walkKeys.press('KeyW'); tick(1, walker, walkKeys);
assert.ok(walker.position[2] < -5 && walker.position[1] > .149 && walker.position[1] < .16);
console.log('Movement integration passed: ground, run/brake, jump, second-jump flight, 70m/s boost, hover, landing, reset, high-speed wall.');


