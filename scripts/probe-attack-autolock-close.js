(async () => {
  const play = window.__undefeatedPlay;
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const key = (type, code) => window.dispatchEvent(new KeyboardEvent(type, { code, bubbles: true }));
  for (let i = 0; i < 50 && !play.player.stats().grounded; i++) await wait(100);
  await wait(300);
  const citizen = play.population.actors.find(a => a.kind === 'citizen' && a.alive);
  if (!citizen) throw new Error('no citizen');
  const forward = play.viewer.camera.getTarget().subtract(play.viewer.camera.position); forward.y = 0; forward.normalize();
  const p = play.player.position;
  citizen.route = undefined;
  citizen.position = [p[0] + forward.x * 3.5, p[1], p[2] + forward.z * 8];
  citizen.alive = true; citizen.health = 35; citizen.defeatedTime = 0; citizen.root.setEnabled(true);
  play.population.place(citizen, Math.atan2(forward.x, forward.z));
  await wait(150);
  const before = { player: play.player.stats().position, citizen: citizen.position, center: [(citizen.min[0]+citizen.max[0])/2,(citizen.min[2]+citizen.max[2])/2] };
  key('keydown', 'KeyJ'); await wait(80); key('keyup', 'KeyJ');
  await wait(900);
  const after = { player: play.player.stats().position, citizen: citizen.position, alive: citizen.alive, hits: play.combat.hits };
  const beforeDistance = Math.hypot(before.player[0]-before.center[0], before.player[2]-before.center[1]);
  const afterDistance = Math.hypot(after.player[0]-before.center[0], after.player[2]-before.center[1]);
  return { before, after, beforeDistance: +beforeDistance.toFixed(2), afterDistance: +afterDistance.toFixed(2) };
})()

