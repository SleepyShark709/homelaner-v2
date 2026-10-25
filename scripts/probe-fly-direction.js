(async () => {
  const play = window.__undefeatedPlay;
  const event = (type, code) => window.dispatchEvent(new KeyboardEvent(type, { code, bubbles: true }));
  const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
  const tap = async code => { event('keydown', code); await wait(70); event('keyup', code); };
  await tap('Space'); await wait(250);
  await tap('Space'); await wait(250);
  event('keydown', 'KeyD');
  await wait(800);
  const right = { clip: play.character.clip, player: play.player.stats() };
  event('keyup', 'KeyD');
  event('keydown', 'KeyS');
  await wait(800);
  const back = { clip: play.character.clip, player: play.player.stats() };
  event('keyup', 'KeyS');
  return { right, back };
})()
