(async () => {
  const play = window.__undefeatedPlay;
  const event = (type, code) => window.dispatchEvent(new KeyboardEvent(type, { code, bubbles: true }));
  event('keydown', 'Space');
  await new Promise(resolve => setTimeout(resolve, 80));
  event('keyup', 'Space');
  await new Promise(resolve => setTimeout(resolve, 120));
  return { clip: play.character.clip, player: play.player.stats() };
})()
