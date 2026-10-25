(async () => {
  const play = window.__undefeatedPlay;
  const vehicle = play.population.actors.find(a => a.kind === 'vehicle' && a.alive);
  if (!vehicle) throw new Error('no vehicle');
  const attack = strong => ({ kind: 'ranged', strong, damage: 100, direction: [0, 0, 1] });
  const before = { alive: vehicle.alive, health: vehicle.health, bounds: [vehicle.min, vehicle.max] };
  const weak = play.population.hit(vehicle.id, attack(false), 'baseline');
  const afterWeak = { result: weak, alive: vehicle.alive, health: vehicle.health };
  const strong = play.population.hit(vehicle.id, attack(true), 'baseline');
  const afterStrong = { result: strong, alive: vehicle.alive, health: vehicle.health };
  return { before, afterWeak, afterStrong };
})()
