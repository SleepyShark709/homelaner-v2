(async () => {
  const play = window.__undefeatedPlay;
  const event = (type, code) => window.dispatchEvent(new KeyboardEvent(type, { code, bubbles: true }));
  event('keydown', 'Space'); await new Promise(r => setTimeout(r, 70));
  event('keyup', 'Space');
  await new Promise(r => setTimeout(r, 950));
  return { clip: play.character.clip, player: play.player.stats() };
})()

