(async () => {
  const play = window.__undefeatedPlay;
  const event = (type, code) => window.dispatchEvent(new KeyboardEvent(type, { code, bubbles: true }));
  const tap = async code => { event('keydown', code); await new Promise(r => setTimeout(r, 70)); event('keyup', code); };
  await tap('Space'); await new Promise(r => setTimeout(r, 250));
  await tap('Space'); await new Promise(r => setTimeout(r, 250));
  event('keydown', 'KeyE');
  await new Promise(r => setTimeout(r, 1800));
  const state = { clip: play.character.clip, player: play.player.stats() };
  event('keyup', 'KeyE');
  return state;
})()
