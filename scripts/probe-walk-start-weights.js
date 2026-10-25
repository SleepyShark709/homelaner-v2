(async () => {
  const play = window.__undefeatedPlay;
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const key = (type, code) => window.dispatchEvent(new KeyboardEvent(type, { code, bubbles: true }));
  for (let i = 0; i < 50 && !play.player.stats().grounded; i++) await wait(100);
  await wait(300);
  const c = play.character; const samples = []; let recording = true;
  const observer = play.viewer.scene.onAfterRenderObservable.add(() => {
    if (!recording) return;
    samples.push({ t: Math.round(performance.now()), clip: c.clip, fade: !!c.fade, speed: +play.player.stats().speed.toFixed(1), active: c.animations.filter(g => g.isPlaying && (g.weight ?? 1) > 0.01).map(g => `${g.name}:${(g.weight ?? 1).toFixed(2)}:${(g.speedRatio ?? 1).toFixed(2)}`) });
  });
  key('keydown', 'KeyW'); await wait(1800); recording = false; key('keyup', 'KeyW');
  play.viewer.scene.onAfterRenderObservable.remove(observer);
  return { frames: samples.length, start: samples.slice(0, 35), middle: samples.slice(35, 55) };
})()
