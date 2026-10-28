(async () => {
  const play=window.__undefeatedPlay; const wait=ms=>new Promise(r=>setTimeout(r,ms));
  for(let i=0;i<50&&!play.player.stats().grounded;i++)await wait(100); await wait(300);
  play.population.actors.forEach(a=>{a.alive=false;});
  play.combat.begin('ranged',false); try{play.combat.fire();}catch(e){return {err:String(e)}}
  await wait(80);
  const pr=play.combat.projectiles?.[0]; if(pr){pr.age=-100;const cam=play.viewer.camera;const f=cam.getTarget().subtract(cam.position);f.normalize();pr.position=cam.position.add(f.scale(4)).asArray();pr.mesh.position.copyFromFloats(...pr.position);}
  return {projectiles:play.combat.projectiles?.map(p=>({name:p.mesh.name,scale:p.mesh.scaling.asArray(),enabled:p.mesh.isEnabled()}))};
})()
