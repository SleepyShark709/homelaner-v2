(async () => {
  const play = window.__undefeatedPlay;
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const key = (type, code) => window.dispatchEvent(new KeyboardEvent(type, { code, bubbles: true }));
  const c = play.character;
  const samples = [];
  let recording = false;
  const observer = play.viewer.scene.onAfterRenderObservable.add(() => {
    if (!recording) return;
    const groups = c.animations.filter(g => g.isPlaying && (g.weight ?? 1) > 0.01)
      .map(g => ({ name: g.name, weight: +(g.weight ?? 1).toFixed(3) }));
    const sum = groups.reduce((n, g) => n + g.weight, 0);
    samples.push({ t: performance.now(), clip: c.clip, state: play.player.state, fade: !!c.fade, sum: +sum.toFixed(3), groups });
  });
  const run = async (label, ms) => {
    samples.length = 0; recording = true;
    await wait(ms);
    recording = false;
    const clips = [...new Set(samples.map(s => s.clip))];
    const low = samples.filter(s => s.sum < 0.95);
    const high = samples.filter(s => s.sum > 1.05);
    const changes = samples.reduce((n, s, i) => i && s.clip !== samples[i - 1].clip ? n + 1 : n, 0);
    return { label, frames: samples.length, clips, changes, minSum: Math.min(...samples.map(s => s.sum)), maxSum: Math.max(...samples.map(s => s.sum)), lowFrames: low.length, highFrames: high.length, example: samples.slice(0, 8) };
  };
  key('keydown', 'KeyW'); key('keydown', 'KeyA');
  const diagonal = await run('WA diagonal run', 1600);
  key('keyup', 'KeyA'); key('keyup', 'KeyW');
  await wait(400);
  key('keydown', 'KeyJ'); await wait(80); key('keyup', 'KeyJ');
  await wait(500);
  key('keydown', 'KeyW');
  const afterAttack = await run('after attack -> W', 1400);
  key('keyup', 'KeyW');
  play.viewer.scene.onAfterRenderObservable.remove(observer);
  return { diagonal, afterAttack };
})()
