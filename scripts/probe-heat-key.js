(async () => {
  const play = window.__undefeatedPlay;
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const key = (type, code) => window.dispatchEvent(new KeyboardEvent(type, { code, bubbles: true }));
  for (let i = 0; i < 50 && !play.player.stats().grounded; i++) await wait(100);
  await wait(300);
  key('keydown', 'KeyH'); await wait(350);
  const h = { heat: play.combat.heatActive, action: play.combat.actionName, charge: play.player.charge };
  key('keyup', 'KeyH'); await wait(200);
  key('keydown', 'KeyE'); await wait(350);
  const e = { heat: play.combat.heatActive, charge: play.player.charge, flying: play.player.flying };
  key('keyup', 'KeyE');
  return { h, e };
})()
