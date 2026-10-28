(async () => {
  const play=window.__undefeatedPlay; const wait=ms=>new Promise(r=>setTimeout(r,ms));
  for(let i=0;i<50&&!play.player.stats().grounded;i++)await wait(100); await wait(300);
  play.population.actors.forEach(a=>{a.alive=false;});
  play.combat.begin('ranged',false); await wait(25);
  play.combat.effects.fistSpawns.forEach(f=>{f.life=100;});
  play.combat.effects.fistFlashes.forEach(f=>{f.life=100;});
  return {fistSpawns:play.combat.effects.fistSpawns.length,fistMeshes:play.combat.effects.fistMeshes?.length,childMeshes:play.viewer.scene.meshes.filter(m=>m.name.includes('fist-cannon')).map(m=>({name:m.name,enabled:m.isEnabled(),pos:m.position.asArray(),scale:m.scaling.asArray()}))};
})()
