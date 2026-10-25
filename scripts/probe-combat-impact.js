(async () => {
  const play = window.__undefeatedPlay;
  const [x, y, z] = play.player.position;
  play.population.actors.push({
    id: 'probe-target', kind: 'prop', alive: true, health: 999,
    min: [x - 1.2, y - 0.5, z - 1.8], max: [x + 1.2, y + 2, z + 1.8],
  });
  play.population.hit = () => 'hit';
  let impacts = 0;
  play.combat.onSound = kind => { if (kind === 'impact') impacts++; };
  const event = (type, code) => window.dispatchEvent(new KeyboardEvent(type, { code, bubbles: true }));
  event('keydown', 'KeyJ'); await new Promise(r => setTimeout(r, 70)); event('keyup', 'KeyJ');
  await new Promise(r => setTimeout(r, 650));
  return { impacts, clip: play.character.clip, hits: play.combat.hits };
})()
