(async () => {
  const play = window.__undefeatedPlay;
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const key = (type, code) => window.dispatchEvent(new KeyboardEvent(type, { code, bubbles: true }));
  const forward = play.viewer.camera.getTarget().subtract(play.viewer.camera.position);
  forward.y = 0; forward.normalize();
  const p = play.player.position;
  const citizens = play.population.actors.filter(a => a.kind === 'citizen' && a.alive);
  const place = (c, distance) => {
    c.route = undefined;
    c.position = [p[0] + forward.x * distance, p[1], p[2] + forward.z * distance];
    c.alive = true; c.health = 35; c.defeatedTime = 0; c.root.setEnabled(true);
    play.population.place(c, Math.atan2(forward.x, forward.z));
  };
  const rangedCitizen = citizens[0];
  place(rangedCitizen, 4);
  await wait(120);
  key('keydown', 'KeyK'); await wait(80); key('keyup', 'KeyK');
  await wait(1200);
  const ranged = { alive: rangedCitizen.alive, health: rangedCitizen.health, hits: play.combat.hits, clip: play.character.clip };
  const heatCitizen = citizens.find(c => c !== rangedCitizen && c.alive);
  place(heatCitizen, 3);
  await wait(120);
  key('keydown', 'ShiftLeft'); key('keydown', 'KeyE');
  await wait(1200);
  const heat = { alive: heatCitizen.alive, health: heatCitizen.health, hits: play.combat.hits, active: play.combat.heatActive };
  key('keyup', 'KeyE'); key('keyup', 'ShiftLeft');
  return { ranged, heat };
})()
