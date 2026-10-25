(async () => {
  const play = window.__undefeatedPlay;
  const event = (type, code) => window.dispatchEvent(new KeyboardEvent(type, { code, bubbles: true }));
  event('keydown', 'Space'); await new Promise(r => setTimeout(r, 70));
  event('keyup', 'Space');
  await new Promise(r => setTimeout(r, 1150));
  const c = play.character;
  const g = c.groupFor ? c.groupFor('ALS_N_Jump') : null;
  return { clip: c.clip, transition: c.transition, fade: c.fade ? { duration: c.fade.duration, elapsed: c.fade.elapsed } : null, jumpLength: g?.getLength?.(), player: play.player.stats() };
})()

