(async () => {
  const play = window.__undefeatedPlay;
  const events = [];
  play.character.onFootstep = clip => events.push(clip);
  const event = (type, code) => window.dispatchEvent(new KeyboardEvent(type, { code, bubbles: true }));
  event('keydown', 'KeyW');
  await new Promise(resolve => setTimeout(resolve, 1400));
  event('keyup', 'KeyW');
  return { count: events.length, events, clip: play.character.clip, player: play.player.stats() };
})()
