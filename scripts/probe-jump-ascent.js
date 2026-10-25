(async () => {
  const play = window.__undefeatedPlay;
  const event = code => window.dispatchEvent(new KeyboardEvent('keydown', { code, key: code === 'Space' ? ' ' : code, bubbles: true }));
  event('Space');
  await new Promise(resolve => setTimeout(resolve, 80));
  window.dispatchEvent(new KeyboardEvent('keyup', { code: 'Space', key: ' ', bubbles: true }));
  await new Promise(resolve => setTimeout(resolve, 150));
  return { clip: play.character.clip, player: play.player.stats() };
})()

