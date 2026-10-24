(async () => {
  const play = window.__undefeatedPlay;
  if (!play) throw new Error('play debug hook missing');
  const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
  const key = (type, code) => window.dispatchEvent(new KeyboardEvent(type, { code, bubbles: true }));
  const vehicles = play.population.actors.filter(actor => actor.kind === 'vehicle');
  const citizens = play.population.actors.filter(actor => actor.kind === 'citizen');
  if (vehicles.length === 0) throw new Error('preview vehicles missing');
  const nearest = vehicles.map(vehicle => ({ vehicle, distance: Math.hypot(vehicle.position[0] - play.player.position[0], vehicle.position[2] - play.player.position[2]) })).sort((a, b) => a.distance - b.distance)[0];
  play.input.yaw = Math.atan2(nearest.vehicle.position[0] - play.player.position[0], nearest.vehicle.position[2] - play.player.position[2]);
  await wait(120);
  const before = { remaining: play.population.remaining, hits: play.combat.hits, destroyed: play.combat.destroyed, vehicleAlive: nearest.vehicle.alive, distance: nearest.distance };
  play.input.down.add('ShiftLeft');
  key('keydown', 'KeyK'); await wait(80); key('keyup', 'KeyK');
  await wait(2600);
  play.input.down.delete('ShiftLeft');
  const after = { remaining: play.population.remaining, hits: play.combat.hits, destroyed: play.combat.destroyed, vehicleAlive: nearest.vehicle.alive, action: play.combat.actionName, projectiles: play.combat.projectiles.length };
  return { actors: play.population.actors.length, citizens: citizens.length, vehicles: vehicles.length, before, after };
})()
