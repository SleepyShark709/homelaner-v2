(async () => {
  const play=window.__undefeatedPlay; const wait=ms=>new Promise(r=>setTimeout(r,ms));
  for(let i=0;i<50&&!play.player.stats().grounded;i++)await wait(100); await wait(300);
  const p=play.player.position; const f=play.viewer.camera.getTarget().subtract(play.viewer.camera.position);f.normalize();
  play.combat.effects.impact([p[0]+f.x*2,p[1]+1.1,p[2]+f.z*2],true);
  play.combat.effects.blasts.forEach(b=>{b.life=100;});
  return {blasts:play.combat.effects.blasts.length};
})()
