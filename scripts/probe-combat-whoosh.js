(async () => {
  const play = window.__undefeatedPlay;
  const sounds = [];
  play.combat.onSound = kind => sounds.push(kind);
  const event = (type, code) => window.dispatchEvent(new KeyboardEvent(type, { code, bubbles: true }));
  const tap = async code => { event('keydown', code); await new Promise(r => setTimeout(r, 70)); event('keyup', code); };
  await tap('Space'); await new Promise(r => setTimeout(r, 250));
  await tap('Space'); await new Promise(r => setTimeout(r, 250));
  await tap('KeyJ'); await new Promise(r => setTimeout(r, 120));
  return { sounds, clip: play.character.clip, action: play.combat.actionName };
})()
