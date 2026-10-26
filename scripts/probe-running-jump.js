(async () => {
  const play = window.__undefeatedPlay;
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const key = (type, code) => window.dispatchEvent(new KeyboardEvent(type, { code, bubbles: true }));
  for (let i = 0; i < 50 && !play.player.stats().grounded; i++) await wait(100);
  await wait(300);
  key('keydown', 'KeyW'); await wait(700);
  const c = play.character; const samples = []; let recording = true;
  const observer = play.viewer.scene.onAfterRenderObservable.add(() => {
    if (!recording) return;
    samples.push({ clip:c.clip, grounded:play.player.grounded, fade:!!c.fade, active:c.animations.filter(g=>g.isPlaying&&(g.weight??1)>0.01).map(g=>g.name), y:+play.player.position[1].toFixed(2) });
  });
  key('keydown','Space'); await wait(80); key('keyup','Space');
  for (let i = 0; i < 140 && (!play.player.grounded || samples.length < 10); i++) await wait(20);
  recording = false; key('keyup','KeyW'); play.viewer.scene.onAfterRenderObservable.remove(observer);
  return { frames:samples.length, clips:[...new Set(samples.map(s=>s.clip))], emptyFrames:samples.filter(s=>s.active.length===0).length, maxY:Math.max(...samples.map(s=>s.y)) };
})()
