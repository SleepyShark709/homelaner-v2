(async () => {
  const play = window.__undefeatedPlay;
  const sounds = [];
  play.combat.onSound = kind => sounds.push(kind);
  const event = (type, code) => window.dispatchEvent(new KeyboardEvent(type, { code, bubbles: true }));
  event('keydown', 'ShiftLeft');
  event('keydown', 'KeyK'); await new Promise(r => setTimeout(r, 70)); event('keyup', 'KeyK');
  await new Promise(r => setTimeout(r, 120));
  event('keyup', 'ShiftLeft');
  return { sounds, clip: play.character.clip, action: play.combat.actionName };
})()

