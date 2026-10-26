(async () => {
  const play=window.__undefeatedPlay; const wait=ms=>new Promise(r=>setTimeout(r,ms)); const key=(t,c)=>window.dispatchEvent(new KeyboardEvent(t,{code:c,bubbles:true}));
  for(let i=0;i<50&&!play.player.stats().grounded;i++)await wait(100); await wait(300);
  const f=play.viewer.camera.getTarget().subtract(play.viewer.camera.position);f.y=0;f.normalize();const p=play.player.position;
  const c=play.population.actors.find(a=>a.kind==='citizen'&&a.alive);c.route=undefined;c.position=[p[0]+f.x*4,p[1],p[2]+f.z*4];c.alive=true;c.health=35;c.defeatedTime=0;c.root.setEnabled(true);play.population.place(c,Math.atan2(f.x,f.z));
  await wait(100); key('keydown','KeyJ');await wait(80);key('keyup','KeyJ');await wait(1200);
  const afterAttack={grounded:play.player.grounded,clip:play.character.clip};
  key('keydown','Space');await wait(150);key('keyup','Space');await wait(120);
  const jump={grounded:play.player.grounded,y:play.player.position[1],clip:play.character.clip,state:play.player.state};
  return {afterAttack,jump};
})()
