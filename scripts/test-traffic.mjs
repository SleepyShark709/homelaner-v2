import assert from 'node:assert/strict';
import { vehicleShouldHold } from '../src/game/traffic.ts';

const self = [0, 0, 0];
assert.equal(vehicleShouldHold(self, [0, 0, 5], [0, 0, 1]), true, 'vehicle directly ahead in range should hold');
assert.equal(vehicleShouldHold(self, [0, 0, 10], [0, 0, 1]), false, 'vehicle beyond gap should not hold');
assert.equal(vehicleShouldHold(self, [0, 0, -5], [0, 0, 1]), false, 'vehicle behind should not hold');
assert.equal(vehicleShouldHold(self, [5, 0, 5], [0, 0, 1]), false, 'lateral vehicle should not hold');
assert.equal(vehicleShouldHold(self, [0, 0, 0], [0, 0, 1]), false, 'same position is not a spacing target');
assert.equal(vehicleShouldHold(self, [0, 0, 4], [0, 0, 1], 5), true, 'player 4 m ahead should make the vehicle yield');
assert.equal(vehicleShouldHold(self, [0, 0, 6], [0, 0, 1], 5), false, 'player outside the 5 m yield window should not hold');
assert.equal(vehicleShouldHold(self, [0, 0, -4], [0, 0, 1], 5), false, 'player behind should not make the vehicle yield');
console.log('traffic tests pass');
