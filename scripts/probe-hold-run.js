(async () => {
  const play = window.__undefeatedPlay;
  const key = (type, code) => window.dispatchEvent(new KeyboardEvent(type, { code, bubbles: true }));
  key('keydown', 'KeyW');
  return { state: play.player.state, clip: play.character.clip };
})()
