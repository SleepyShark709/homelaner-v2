(async () => {
  const play = window.__undefeatedPlay;
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const key = (type, code) => window.dispatchEvent(new KeyboardEvent(type, { code, bubbles: true }));
  for (let i = 0; i < 50 && !play.player.stats().grounded; i++) await wait(100);
  await wait(300);
  key('keydown', 'KeyW'); key('keydown', 'ShiftLeft'); await wait(2400);
  const peak = play.player.stats().speed;
  key('keyup', 'KeyW'); key('keyup', 'ShiftLeft');
  const clips = new Set(); const samples = [];
  for (let i = 0; i < 120; i++) { const s = { t: Math.round(performance.now()), speed: +play.player.stats().speed.toFixed(1), clip: play.character.clip, action: play.character.action }; samples.push(s); clips.add(s.clip); await wait(20); }
  return { peak, clips: [...clips], stopSamples: samples.filter(s => s.clip.includes('Stopping')).slice(0, 8), tail: samples.slice(-5) };
})()
