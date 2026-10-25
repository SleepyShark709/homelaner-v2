(async () => {
  const play = window.__undefeatedPlay;
  if (!play) throw new Error('play debug hook missing; open ?view=play&debug=1');
  const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
  const key = (type, code) => window.dispatchEvent(new KeyboardEvent(type, { code, bubbles: true }));
  const state = () => ({ stats: play.player.stats(), clip: play.character.clip, active: play.input.active });
  // The first frames after ?ready=play can still be resolving the terrain pose.
  for (let i = 0; i < 50 && !play.player.stats().grounded; i++) await wait(100);
  await wait(300);
  const start = state();
  if (!start.stats.grounded) throw new Error('player did not settle on terrain');
  if (start.clip !== 'Hero_Idle') throw new Error(`unexpected idle clip ${start.clip}`);
  key('keydown', 'KeyW'); await wait(2000);
  const walking = state();
  key('keyup', 'KeyW');
  if (Math.abs(walking.stats.position[2] - start.stats.position[2]) < 3) throw new Error('W did not move the player');
  if (walking.stats.state !== 'run' || walking.clip !== 'Hero_SprintRun') throw new Error(`walk state/animation mismatch: ${walking.stats.state}/${walking.clip}`);
  key('keydown', 'Space'); await wait(80); key('keyup', 'Space'); await wait(220);
  const jump = state();
  if (jump.stats.grounded || jump.stats.position[1] < start.stats.position[1] + 1) throw new Error('Space did not jump');
  if (!['Hero_JumpSpeed', 'Hero_JumpFallFast'].includes(jump.clip)) throw new Error(`unexpected jump clip ${jump.clip}`);
  key('keydown', 'Space'); await wait(80); key('keyup', 'Space'); await wait(220);
  const flying = state();
  if (!flying.stats.flying) throw new Error('airborne Space did not open flight');
  const flyClips = ['Hero_FlyUp', 'Hero_FlyDown', 'Hero_FlyFastDown', 'Hero_FlyForward', 'Hero_FlyForwardLow', 'Hero_IdleFlying'];
  if (!flyClips.includes(flying.clip)) throw new Error(`unexpected flight clip ${flying.clip}`);
  const flyY = flying.stats.position[1];
  key('keydown', 'KeyE'); await wait(700); key('keyup', 'KeyE');
  const ascended = state();
  if (ascended.stats.position[1] < flyY + 3) throw new Error('E did not ascend in flight');
  if (ascended.clip !== 'Hero_FlyUp') throw new Error(`E did not select Hero_FlyUp (${ascended.clip})`);
  key('keydown', 'KeyQ'); await wait(1800);
  const descended = state();
  key('keyup', 'KeyQ'); await wait(200);
  if (descended.stats.position[1] >= ascended.stats.position[1]) throw new Error('Q did not descend in flight');
  if (!['Hero_FlyDown', 'Hero_FlyFastDown', 'Hero_IdleFlying'].includes(descended.clip)) throw new Error(`Q did not select a fly-down/terminal clip (${descended.clip})`);
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





