(async () => {
  const play = window.__undefeatedPlay;
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const key = (type, code) => window.dispatchEvent(new KeyboardEvent(type, { code, bubbles: true }));
  for (let i = 0; i < 50 && !play.player.stats().grounded; i++) await wait(100);
  await wait(300);
  play.population.actors.forEach(a => { a.alive = false; });
  const forward = play.viewer.camera.getTarget().subtract(play.viewer.camera.position); forward.y = 0; forward.normalize();
  const p0 = [...play.player.position];
  const center = [p0[0] + forward.x * 6, p0[1], p0[2] + forward.z * 6];
  const dummy = { id:'dummy', kind:'citizen', alive:true, health:35, min:[center[0]-0.4,center[1],center[2]-0.4], max:[center[0]+0.4,center[1]+1.8,center[2]+0.4], position:[...center], root:{setEnabled(){},rotation:{x:0},position:{copyFromFloats(){}}}, entries:{animationGroups:[]}, velocity:[0,0,0], defeatedTime:0 };
  play.population.actors.push(dummy);
  await wait(100);
  const beforePlayer = [...play.player.position];
  key('keydown','KeyJ'); await wait(80); key('keyup','KeyJ'); await wait(300);
  const afterPlayer = [...play.player.position];
  const distance = (a,b) => Math.hypot(a[0]-b[0],a[2]-b[2]);
  return { beforeDistance:+distance(beforePlayer,center).toFixed(2), afterDistanceToInitialCenter:+distance(afterPlayer,center).toFixed(2), afterPlayer, center, alive:dummy.alive, hits:play.combat.hits };
})()
