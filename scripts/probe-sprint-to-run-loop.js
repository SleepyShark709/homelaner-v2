(async () => {
  const play = window.__undefeatedPlay;
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const key = (type, code) => window.dispatchEvent(new KeyboardEvent(type, { code, bubbles: true }));
  for (let i = 0; i < 50 && !play.player.stats().grounded; i++) await wait(100);
  await wait(300);
  key('keydown', 'KeyW'); await wait(900);
  key('keydown', 'ShiftLeft'); await wait(1600);
  key('keyup', 'ShiftLeft'); await wait(900);
  const c = play.character, g = c.groupFor('Hero_SprintRun'); const samples = [];
  for (let i = 0; i < 120; i++) { samples.push({ t: Math.round(performance.now()), speed: +play.player.stats().speed.toFixed(1), frame: +(g?.animatables?.[0]?.masterFrame ?? -1).toFixed(1), ratio: +(g?.speedRatio ?? -1).toFixed(2), weight: +(g?.weight ?? -1).toFixed(2), length: +((g?.getLength?.() ?? 0)).toFixed(3), clip: c.clip }); await wait(20); }
  key('keyup', 'KeyW');
  const wraps = []; for (let i=1;i<samples.length;i++) if(samples[i].frame<samples[i-1].frame-5) wraps.push({t:samples[i].t,prev:samples[i-1].frame,frame:samples[i].frame,dt:samples[i].t-samples[i-1].t});
  return {length:g?.getLength?.(),to:g?.to,samples:samples.slice(0,40),wraps};
})()
