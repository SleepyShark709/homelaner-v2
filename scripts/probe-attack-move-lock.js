(async () => {
  const play=window.__undefeatedPlay; const wait=ms=>new Promise(r=>setTimeout(r,ms)); const key=(t,c)=>window.dispatchEvent(new KeyboardEvent(t,{code:c,bubbles:true}));
  for(let i=0;i<50&&!play.player.stats().grounded;i++)await wait(100); await wait(300);
  play.population.actors.forEach(a=>{a.alive=false;});
  key('keydown','KeyW'); await wait(700);
  const p0=[...play.player.position]; const v0=[...play.player.velocity];
  key('keydown','KeyJ'); await wait(80); key('keyup','KeyJ'); await wait(600);
  const p1=[...play.player.position]; const during={action:play.character.action,grounded:play.player.grounded,dx:+(p1[0]-p0[0]).toFixed(3),dz:+(p1[2]-p0[2]).toFixed(3),v:[...play.player.velocity]};
  await wait(1200); const p2=[...play.player.position];
  key('keyup','KeyW');
  return {v0,during,after:{clip:play.character.clip,dx:+(p2[0]-p1[0]).toFixed(2),dz:+(p2[2]-p1[2]).toFixed(2)}};
})()
