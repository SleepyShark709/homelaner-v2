(async () => {
  const play = window.__undefeatedPlay;
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const key = (type, code) => window.dispatchEvent(new KeyboardEvent(type, { code, bubbles: true }));
  for (let i = 0; i < 50 && !play.player.stats().grounded; i++) await wait(100);
  await wait(300);
  key('keydown','Space'); await wait(80); key('keyup','Space'); await wait(300);
  key('keydown','Space'); await wait(80); key('keyup','Space'); await wait(300);
  key('keydown','KeyW');
  const rows=[]; let last=play.character.clip;
  const observer=play.viewer.scene.onAfterRenderObservable.add(()=>{
    const s=play.player.stats(); const c=play.viewer.camera;
    rows.push({clip:play.character.clip,y:+s.position[1].toFixed(3),px:+s.position[0].toFixed(3),pz:+s.position[2].toFixed(3),vx:+s.velocity[0].toFixed(2),vy:+s.velocity[1].toFixed(2),vz:+s.velocity[2].toFixed(2),cx:+c.position.x.toFixed(3),cy:+c.position.y.toFixed(3),cz:+c.position.z.toFixed(3),fade:!!play.character.fade,ratio:+(play.character.groupFor(play.character.clip)?.speedRatio??0).toFixed(2)});
  });
  await wait(2200);
  key('keyup','KeyW');
  play.viewer.scene.onAfterRenderObservable.remove(observer);
  const changes=rows.reduce((n,r,i)=>i&&r.clip!==rows[i-1].clip?n+1:n,0);
  return {frames:rows.length, clips:[...new Set(rows.map(r=>r.clip))], clipChanges:changes, sample:rows.slice(0,20), tail:rows.slice(-10)};
})()
