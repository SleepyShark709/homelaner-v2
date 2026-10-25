(async () => {
  const play = window.__undefeatedPlay;
  const event = (type, code) => window.dispatchEvent(new KeyboardEvent(type, { code, bubbles: true }));
  event('keydown', 'KeyS');
  await new Promise(resolve => setTimeout(resolve, 900));
  const state = { clip: play.character.clip, player: play.player.stats() };
  event('keyup', 'KeyS');
  return state;
})()
