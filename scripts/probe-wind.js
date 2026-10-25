(async () => {
  const play = window.__undefeatedPlay;
  const event = (type, code) => window.dispatchEvent(new KeyboardEvent(type, { code, bubbles: true }));
  const tap = async code => { event('keydown', code); await new Promise(r => setTimeout(r, 70)); event('keyup', code); };
  const before = play.footsteps.flightWindActive;
  await tap('Space'); await new Promise(r => setTimeout(r, 250));
  await tap('Space'); await new Promise(r => setTimeout(r, 350));
  return { before, during: play.footsteps.flightWindActive, flying: play.player.flying };
})()
