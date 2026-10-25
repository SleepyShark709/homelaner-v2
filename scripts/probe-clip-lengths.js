(async () => {
  const play = window.__undefeatedPlay;
  const c = play.character;
  return ['Hero_Idle','Hero_Walk','Hero_SprintRun','Hero_SprintSuper'].map(name => {
    const g = c.groupFor(name);
    const a = g?.targetedAnimations?.[0]?.animation;
    const keys = a?.getKeys?.() ?? [];
    return { name, from: g?.from, to: g?.to, length: g?.getLength?.(), speedRatio: g?.speedRatio, animFrom: a?.from, animTo: a?.to, fps: a?.framePerSecond, keys: keys.length, firstKey: keys[0]?.frame, lastKey: keys[keys.length-1]?.frame, animatables: g?.animatables?.length };
  });
})()
