(async () => {
  const play = window.__undefeatedPlay;
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const key = (type, code) => window.dispatchEvent(new KeyboardEvent(type, { code, bubbles: true }));
  const p = play.player.position;
  const camera = play.viewer.camera;
  const forward = camera.getTarget().subtract(camera.position); forward.y = 0; forward.normalize();
  const cx = p[0] + forward.x * 0.95, cz = p[2] + forward.z * 0.95;
  const dummy = {
    id: 'probe-citizen', kind: 'citizen', alive: true, health: 35,
    min: [cx - 0.45, p[1], cz - 0.45], max: [cx + 0.45, p[1] + 1.8, cz + 0.45],
    position: [cx, p[1], cz], root: { setEnabled() {}, rotation: { x: 0 } },
    entries: { animationGroups: [] }, velocity: [0, 0, 0], defeatedTime: 0,
  };
  play.population.actors.push(dummy);
  await wait(100);
  const before = { alive: dummy.alive, health: dummy.health, bounds: [dummy.min, dummy.max] };
  key('keydown', 'KeyJ'); await wait(80); key('keyup', 'KeyJ');
  await wait(800);
  return { before, after: { alive: dummy.alive, health: dummy.health, defeatedTime: dummy.defeatedTime, hits: play.combat.hits, clip: play.character.clip } };
})()
