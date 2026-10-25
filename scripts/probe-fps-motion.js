(async () => {
  const play = window.__undefeatedPlay;
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const key = (type, code) => window.dispatchEvent(new KeyboardEvent(type, { code, bubbles: true }));
  const engine = play.viewer.scene.getEngine();
  const measure = async (label, ms) => {
    await wait(500);
    const start = performance.now(); let frames = 0; let maxDt = 0; let last = start;
    await new Promise(resolve => {
      const observer = play.viewer.scene.onAfterRenderObservable.add(() => {
        const now = performance.now(); frames++; maxDt = Math.max(maxDt, now - last); last = now;
        if (now - start >= ms) { play.viewer.scene.onAfterRenderObservable.remove(observer); resolve(); }
      });
    });
    return { label, frames, seconds: +((performance.now() - start) / 1000).toFixed(2), fps: +(frames / ((performance.now() - start) / 1000)).toFixed(1), engineFps: +engine.getFps().toFixed(1), maxFrameMs: +maxDt.toFixed(1) };
  };
  const idle = await measure('idle', 1500);
  key('keydown', 'KeyW'); key('keydown', 'KeyA');
  const diagonal = await measure('WA run', 1800);
  key('keyup', 'KeyA'); key('keyup', 'KeyW'); await wait(300);
  key('keydown', 'KeyJ'); await wait(80); key('keyup', 'KeyJ'); await wait(700);
  key('keydown', 'KeyW');
  const afterAttack = await measure('after attack W', 1600);
  key('keyup', 'KeyW');
  return { idle, diagonal, afterAttack };
})()
