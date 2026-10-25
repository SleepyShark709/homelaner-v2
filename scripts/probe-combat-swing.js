(async () => {
  const play = window.__undefeatedPlay;
  let swings = 0;
  play.combat.onSound = kind => { if (kind === 'swing') swings++; };
  const event = (type, code) => window.dispatchEvent(new KeyboardEvent(type, { code, bubbles: true }));
  event('keydown', 'KeyJ'); await new Promise(r => setTimeout(r, 70)); event('keyup', 'KeyJ');
  await new Promise(r => setTimeout(r, 120));
  return { swings, clip: play.character.clip, action: play.combat.actionName };
})()
