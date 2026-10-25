(async () => {
  const play = window.__undefeatedPlay;
  const event = (type, code) => window.dispatchEvent(new KeyboardEvent(type, { code, bubbles: true }));
  const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
  const tap = async code => { event('keydown', code); await wait(70); event('keyup', code); };
  await tap('Space'); await wait(250);
  await tap('Space'); await wait(250);
  await tap('KeyK'); await wait(120);
  const first = { clip: play.character.clip, player: play.player.stats() };
  await wait(750);
  await tap('KeyK'); await wait(120);
  const second = { clip: play.character.clip, player: play.player.stats() };
  return { first, second };
})()
