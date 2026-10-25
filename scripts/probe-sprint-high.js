(async () => {
  const play = window.__undefeatedPlay;
  const event = (type, code) => window.dispatchEvent(new KeyboardEvent(type, { code, bubbles: true }));
  event('keydown', 'ShiftLeft');
  event('keydown', 'KeyW');
  await new Promise(resolve => setTimeout(resolve, 1800));
  const state = { clip: play.character.clip, player: play.player.stats() };
  event('keyup', 'KeyW'); event('keyup', 'ShiftLeft');
  return state;
})()
