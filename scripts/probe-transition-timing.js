(async () => {
  const play = window.__undefeatedPlay;
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const key = (type, code) => window.dispatchEvent(new KeyboardEvent(type, { code, bubbles: true }));
  for (let i = 0; i < 50 && !play.player.stats().grounded; i++) await wait(100);
  await wait(300);
  key('keydown','KeyW'); await wait(700);
  const start = performance.now(); const changes=[];
  let last=play.character.clip; const observer=play.viewer.scene.onAfterRenderObservable.add(()=>{const c=play.character.clip;if(c!==last){changes.push({t:Math.round(performance.now()-start),clip:c});last=c;}});
  key('keydown','ShiftLeft'); await wait(1200);
  key('keyup','ShiftLeft'); key('keyup','KeyW'); await wait(1000);
  play.viewer.scene.onAfterRenderObservable.remove(observer);
  return changes;
})()
