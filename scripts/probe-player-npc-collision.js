(async () => {
  const play=window.__undefeatedPlay; const wait=ms=>new Promise(r=>setTimeout(r,ms)); const key=(t,c)=>window.dispatchEvent(new KeyboardEvent(t,{code:c,bubbles:true}));
  for(let i=0;i<50&&!play.player.stats().grounded;i++)await wait(100); await wait(300);
  const cam=play.viewer.camera;const f=cam.getTarget().subtract(cam.position);f.y=0;f.normalize();const p=play.player.position;
  const c=play.population.actors.find(a=>a.kind==='citizen'&&a.alive); if(!c)return {noCitizen:true};
  c.route=undefined; c.fleeTime=0; c.position=[p[0]+f.x*2.5,p[1],p[2]+f.z*2.5]; c.root.setEnabled(true); play.population.place(c,Math.atan2(-f.x,-f.z));
  await wait(200);
  const startDist=Math.hypot(c.position[0]-p[0],c.position[2]-p[2]); key('keydown','KeyW'); await wait(1300); key('keyup','KeyW');
  const q=play.player.position; const endDist=Math.hypot(c.position[0]-q[0],c.position[2]-q[2]);
  const overlap=q[0]>c.min[0]-0.25&&q[0]<c.max[0]+0.25&&q[2]>c.min[2]-0.25&&q[2]<c.max[2]+0.25;
  return {startDist:+startDist.toFixed(2),endDist:+endDist.toFixed(2),overlap,player:q.map(v=>+v.toFixed(2)),npc:c.position.map(v=>+v.toFixed(2))};
})()
