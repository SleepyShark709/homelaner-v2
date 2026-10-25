(async () => {
  const play = window.__undefeatedPlay;
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const key = (type, code) => window.dispatchEvent(new KeyboardEvent(type, { code, bubbles: true }));
  const c = play.character;
  const samples = [];
  let recording = true;
  const observer = play.viewer.scene.onAfterRenderObservable.add(() => {
    if (!recording) return;
    samples.push({ t: Math.round(performance.now()), clip: c.clip, action: c.action, fade: !!c.fade, groups: c.animations.filter(g => g.isPlaying && (g.weight ?? 1) > 0.01).map(g => `${g.name}:${(g.weight ?? 1).toFixed(2)}`) });
  });
  key('keydown', 'KeyJ'); await wait(80); key('keyup', 'KeyJ');
  await wait(650);
  key('keydown', 'KeyW');
  await wait(900);
  key('keyup', 'KeyW'); recording = false;
  play.viewer.scene.onAfterRenderObservable.remove(observer);
  const fades = samples.filter(s => s.fade);
  const changes = samples.filter((s, i) => i && s.clip !== samples[i - 1].clip);
  return { frames: samples.length, fades: fades.slice(0, 12), changeCount: changes.length, changes: changes.slice(0, 12), aroundFade: samples.filter(s => s.fade || s.action).slice(0, 16) };
})()
