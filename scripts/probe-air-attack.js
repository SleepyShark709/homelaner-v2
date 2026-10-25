(async () => {
  const play = window.__undefeatedPlay;
  const event = (type, code) => window.dispatchEvent(new KeyboardEvent(type, { code, bubbles: true }));
  event('keydown', 'Space'); await new Promise(r => setTimeout(r, 80)); event('keyup', 'Space');
  await new Promise(r => setTimeout(r, 250));
  event('keydown', 'Space'); await new Promise(r => setTimeout(r, 80)); event('keyup', 'Space');
  await new Promise(r => setTimeout(r, 250));
  event('keydown', 'KeyK'); await new Promise(r => setTimeout(r, 80)); event('keyup', 'KeyK');
  await new Promise(r => setTimeout(r, 120));
  return { clip: play.character.clip, player: play.player.stats() };
})()
