(async () => {
  const play = window.__undefeatedPlay;
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const key = (type, code) => window.dispatchEvent(new KeyboardEvent(type, { code, bubbles: true }));
  const samples = [];
  const sample = label => samples.push({ label, position: play.player.stats().position, grounded: play.player.grounded, state: play.player.state });
  await wait(300); sample('start');
  key('keydown', 'KeyW'); await wait(2500); sample('walk-2.5s'); key('keyup', 'KeyW');
  key('keydown', 'KeyA'); await wait(1200); sample('left-1.2s'); key('keyup', 'KeyA');
  key('keydown', 'KeyS'); await wait(1800); sample('back-1.8s'); key('keyup', 'KeyS');
  key('keydown', 'KeyD'); await wait(1200); sample('right-1.2s'); key('keyup', 'KeyD');
  key('keydown', 'Space'); await wait(90); key('keyup', 'Space'); await wait(500); sample('jump');
  key('keydown', 'Space'); await wait(90); key('keyup', 'Space'); await wait(500); sample('fly');
  key('keydown', 'KeyE'); await wait(800); key('keyup', 'KeyE'); sample('ascend');
  key('keydown', 'KeyQ'); await wait(1800); key('keyup', 'KeyQ'); sample('descend');
  key('keydown', 'KeyF'); await wait(4000); key('keyup', 'KeyF'); sample('land');
  const minimumY = Math.min(...samples.map(s => s.position[1]));
  const ungroundedStable = samples.filter(s => !['jump','fly','ascend','descend'].includes(s.label)).every(s => s.grounded);
  return { samples, minimumY, ungroundedStable };
})()

