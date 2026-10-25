(async () => {
  const play = window.__undefeatedPlay;
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const key = (type, code) => window.dispatchEvent(new KeyboardEvent(type, { code, bubbles: true }));
  for (let i = 0; i < 50 && !play.player.stats().grounded; i++) await wait(100);
  await wait(300);
  const c = play.character;
  const gait = /^(Hero_Idle|Hero_Walk|Hero_SprintRun|Hero_SprintSuper|ALS_N_)/;
  const samples = []; let recording = true;
  const observer = play.viewer.scene.onAfterRenderObservable.add(() => {
    if (!recording) return;
    const active = c.animations.filter(g => gait.test(g.name) && g.isPlaying && (g.weight ?? 1) > 0.01).map(g => g.name);
    samples.push({ t: Math.round(performance.now()), fade: !!c.fade, active, clip: c.clip, speed: +play.player.stats().speed.toFixed(1) });
  });
  key('keydown', 'KeyW'); await wait(1200);
  key('keydown', 'ShiftLeft'); await wait(1200);
  key('keyup', 'ShiftLeft'); await wait(1000);
  key('keyup', 'KeyW'); await wait(300);
  recording = false; play.viewer.scene.onAfterRenderObservable.remove(observer);
  const violations = samples.filter(s => !s.fade && s.active.length > 1);
  return {
    frames: samples.length,
    maxActiveWithFadeFalse: Math.max(...samples.filter(s => !s.fade).map(s => s.active.length)),
    violations: violations.slice(0, 10),
    clips: [...new Set(samples.map(s => s.clip))],
    peakSpeed: Math.max(...samples.map(s => s.speed)),
    final: samples.slice(-4),
  };
})()
