(async () => {
  const play=window.__undefeatedPlay; const wait=ms=>new Promise(r=>setTimeout(r,ms)); const key=(t,c)=>window.dispatchEvent(new KeyboardEvent(t,{code:c,bubbles:true}));
  for(let i=0;i<50&&!play.player.stats().grounded;i++)await wait(100); await wait(300);
  const c=play.population.actors.find(a=>a.kind==='citizen'&&a.alive); if(!c)return {noCitizen:true};
  const p=play.player.position; const yaw=play.input.yaw; const fx=Math.sin(yaw), fz=Math.cos(yaw);
  c.route=undefined; c.fleeTime=0; c.position=[p[0]+fx*2,p[1],p[2]+fz*2]; c.root.setEnabled(true); play.population.place(c,yaw+Math.PI);
  await wait(200); key('keydown','KeyW'); await wait(1500); key('keyup','KeyW');
  const q=play.player.position; const d=Math.hypot(c.position[0]-q[0],c.position[2]-q[2]);
  return {start:2.0,endDist:+d.toFixed(2),player:q.map(v=>+v.toFixed(2)),npc:c.position.map(v=>+v.toFixed(2)),npcMin:c.min.map(v=>+v.toFixed(2)),npcMax:c.max.map(v=>+v.toFixed(2))};
})()
