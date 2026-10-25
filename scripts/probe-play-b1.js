(async () => {
  const play = window.__undefeatedPlay;
  if (!play) throw new Error('play debug hook missing; open ?view=play&debug=1');
  const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
  const key = (type, code) => window.dispatchEvent(new KeyboardEvent(type, { code, bubbles: true }));
  const state = () => ({ stats: play.player.stats(), clip: play.character.clip, active: play.input.active });
  const start = state();
  if (!start.stats.grounded) throw new Error('player did not settle on terrain');
  if (start.clip !== 'Hero_Idle') throw new Error(`unexpected idle clip ${start.clip}`);
  key('keydown', 'KeyW'); await wait(1600);
  const walking = state();
  key('keyup', 'KeyW');
  if (Math.abs(walking.stats.position[2] - start.stats.position[2]) < 3) throw new Error('W did not move the player');
  if (walking.stats.state !== 'run' || walking.clip !== 'Hero_SprintRun') throw new Error(`walk state/animation mismatch: ${walking.stats.state}/${walking.clip}`);
  key('keydown', 'Space'); await wait(80); key('keyup', 'Space'); await wait(220);
  const jump = state();
  if (jump.stats.grounded || jump.stats.position[1] < start.stats.position[1] + 1) throw new Error('Space did not jump');
  key('keydown', 'Space'); await wait(80); key('keyup', 'Space'); await wait(220);
  const flying = state();
  if (!flying.stats.flying) throw new Error('airborne Space did not open flight');
  const flyY = flying.stats.position[1];
  key('keydown', 'KeyE'); await wait(700); key('keyup', 'KeyE');
  const ascended = state();
  if (ascended.stats.position[1] < flyY + 3) throw new Error('E did not ascend in flight');
  key('keydown', 'KeyQ'); await wait(1800); key('keyup', 'KeyQ');
  const descended = state();
  if (descended.stats.position[1] >= ascended.stats.position[1]) throw new Error('Q did not descend in flight');
  key('keydown', 'Space'); await wait(80); key('keyup', 'Space'); await wait(250);
  const exited = state();
  if (exited.stats.flying) throw new Error('flight Space did not exit flight');
  return {
    start, walking, jump, flying, ascended, descended, exited,
    evidence: {
      walkDistance: Math.abs(walking.stats.position[2] - start.stats.position[2]),
      jumpHeight: jump.stats.position[1] - start.stats.position[1],
      ascendDelta: ascended.stats.position[1] - flyY,
      descendDelta: descended.stats.position[1] - ascended.stats.position[1],
    },
  };
})()

