(async () => {
  const play=window.__undefeatedPlay; const wait=ms=>new Promise(r=>setTimeout(r,ms));
  for(let i=0;i<50&&!play.player.stats().grounded;i++)await wait(100); await wait(300);
  play.population.actors.forEach(a=>{a.alive=false;});
  const c=play.combat; let ok=true,err=''; try{c.begin('ranged',false);}catch(e){ok=false;err=String(e);}
  await wait(45);
  return {ok,err,clip:play.character.clip,sprites:play.viewer.scene.spriteManagers.map(m=>({name:m.name,count:m.sprites.length}))};
})()
