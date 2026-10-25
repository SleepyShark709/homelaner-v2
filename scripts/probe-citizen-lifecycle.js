(async () => {
  const play = window.__undefeatedPlay;
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const citizen = play.population.actors.find(actor => actor.kind === 'citizen' && actor.alive);
  if (!citizen) throw new Error('no live citizen');
  const before = { alive: citizen.alive, health: citizen.health, remaining: play.population.remaining };
  const result = play.population.hit(citizen.id, { kind: 'melee', strong: false, damage: 50, direction: [0, 0, 1] }, 'baseline');
  const dead = { result, alive: citizen.alive, health: citizen.health, defeatedTime: citizen.defeatedTime };
  await wait(4000);
  const at4 = { alive: citizen.alive, defeatedTime: citizen.defeatedTime };
  await wait(9000);
  const at9 = { alive: citizen.alive, health: citizen.health, defeatedTime: citizen.defeatedTime, remaining: play.population.remaining };
  return { before, dead, at4, at9 };
})()

