(async () => {
  const play=window.__undefeatedPlay; const wait=ms=>new Promise(r=>setTimeout(r,ms));
  for(let i=0;i<50&&!play.player.stats().grounded;i++)await wait(100); await wait(300);
  play.population.actors.forEach(a=>{a.alive=false;});
  play.combat.begin('ranged',true); await wait(30);
  play.combat.effects.blasts.forEach(b=>{b.life=100;});
  return {clip:play.character.clip,count:play.combat.effects.blasts.length,sprites:play.viewer.scene.spriteManagers.map(m=>({name:m.name,count:m.sprites.length}))};
})()
