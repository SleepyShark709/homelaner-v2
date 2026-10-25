(async () => {
  const play = window.__undefeatedPlay;
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const key = (type, code) => window.dispatchEvent(new KeyboardEvent(type, { code, bubbles: true }));
  const citizen = play.population.actors.find(actor => actor.kind === 'citizen' && actor.alive);
  if (!citizen) throw new Error('no citizen');
  const camera = play.viewer.camera;
  const forward = camera.getTarget().subtract(camera.position); forward.y = 0; forward.normalize();
  const p = play.player.position;
  citizen.route = undefined;
  citizen.position = [p[0] + forward.x * 1.0, p[1], p[2] + forward.z * 1.0];
  citizen.alive = true; citizen.health = 35; citizen.defeatedTime = 0; citizen.root.setEnabled(true);
  play.population.place(citizen, Math.atan2(forward.x, forward.z));
  await wait(120);
  const before = { pos: citizen.position, min: citizen.min, max: citizen.max, root: citizen.root.position.asArray() };
  key('keydown', 'KeyJ'); await wait(80); key('keyup', 'KeyJ');
  await wait(900);
  return { before, after: { alive: citizen.alive, health: citizen.health, defeatedTime: citizen.defeatedTime, hits: play.combat.hits, clip: play.character.clip } };
})()
