(async () => {
  const play = window.__undefeatedPlay;
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const key = (type, code) => window.dispatchEvent(new KeyboardEvent(type, { code, bubbles: true }));
  for (let i = 0; i < 50 && !play.player.stats().grounded; i++) await wait(100);
  await wait(300);

  key('keydown', 'KeyH'); await wait(300);
  const heatH = { active: play.combat.heatActive, action: play.combat.actionName, charge: play.player.charge };
  key('keyup', 'KeyH'); await wait(150);
  key('keydown', 'KeyE'); await wait(300);
  const heatE = { active: play.combat.heatActive, charge: play.player.charge };
  key('keyup', 'KeyE'); await wait(200);

  key('keydown', 'KeyW'); await wait(900);
  const gait = { clip: play.character.clip, speed: play.player.stats().speed };
  key('keyup', 'KeyW'); await wait(300);

  const citizen = play.population.actors.find(a => a.kind === 'citizen' && a.alive);
  const forward = play.viewer.camera.getTarget().subtract(play.viewer.camera.position); forward.y = 0; forward.normalize();
  const p = play.player.position;
  citizen.route = undefined;
  citizen.position = [p[0] + forward.x * 4, p[1], p[2] + forward.z * 4];
  citizen.alive = true; citizen.health = 35; citizen.defeatedTime = 0; citizen.root.setEnabled(true);
  play.population.place(citizen, Math.atan2(forward.x, forward.z));
  await wait(150);
  const beforeDistance = Math.hypot(play.player.position[0] - citizen.position[0], play.player.position[2] - citizen.position[2]);
  key('keydown', 'KeyJ'); await wait(80); key('keyup', 'KeyJ'); await wait(900);
  const attack = { alive: citizen.alive, hits: play.combat.hits, beforeDistance: +beforeDistance.toFixed(2), afterDistance: +Math.hypot(play.player.position[0] - citizen.position[0], play.player.position[2] - citizen.position[2]).toFixed(2) };

  play.player.velocity = [0, 0, 30];
  play.combat.update(0.08); play.combat.update(0.08);
  await wait(80);
  const vfx = { streakMeshes: play.viewer.scene.meshes.filter(m => m.name.includes('speed-streak')).length };

  return { heatH, heatE, gait, attack, vfx };
})()
