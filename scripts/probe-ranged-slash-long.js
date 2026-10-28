(async () => {
  const play=window.__undefeatedPlay; const wait=ms=>new Promise(r=>setTimeout(r,ms));
  for(let i=0;i<50&&!play.player.stats().grounded;i++)await wait(100); await wait(300);
  play.population.actors.forEach(a=>{a.alive=false;});
  play.combat.begin('ranged',false); await wait(20);
  play.combat.effects.ranged.forEach(r=>{r.life=100;});
  return {count:play.combat.effects.ranged.length};
})()
