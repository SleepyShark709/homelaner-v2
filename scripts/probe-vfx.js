(async () => {
  const play = window.__undefeatedPlay;
  const wait = ms => new Promise(r => setTimeout(r, ms));
  for (let i = 0; i < 50 && !play.player.stats().grounded; i++) await wait(100);
  await wait(300);
  play.player.velocity = [0, 0, 30];
  for (let i = 0; i < 6; i++) { play.combat.update(0.08); await wait(30); }
  return { speed: play.player.stats().speed, activeMeshes: play.viewer.scene.meshes.filter(m => m.name.includes('speed-streak')).length };
})()
