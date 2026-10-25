(async () => {
  const play = window.__undefeatedPlay;
  const event = (type, code) => window.dispatchEvent(new KeyboardEvent(type, { code, bubbles: true }));
  event('keydown', 'ShiftLeft');
  event('keydown', 'KeyW');
  await new Promise(resolve => setTimeout(resolve, 1600));
  return { clip: play.character.clip, player: play.player.stats() };
})()
