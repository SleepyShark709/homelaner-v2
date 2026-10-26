(async () => {
  const play=window.__undefeatedPlay; const wait=ms=>new Promise(r=>setTimeout(r,ms)); const key=(t,c)=>window.dispatchEvent(new KeyboardEvent(t,{code:c,bubbles:true}));
  for(let i=0;i<50&&!play.player.stats().grounded;i++)await wait(100); await wait(300);
  key('keydown','Space');await wait(80);key('keyup','Space');await wait(300);key('keydown','Space');await wait(80);key('keyup','Space');await wait(300);key('keydown','KeyW');
  const c=play.character; const nodes=c.container.transformNodes.slice(0,140); const prev=[],vels=nodes.map(()=>[]),acc=nodes.map(()=>[]); let lastYaw=c.root.rotation.y; const yawRates=[],yawAcc=[];
  const observer=play.viewer.scene.onAfterRenderObservable.add(()=>{
    nodes.forEach((n,i)=>{const p=n.getAbsolutePosition(),r=c.root.position;const v=[p.x-r.x,p.y-r.y,p.z-r.z];if(prev[i]){const d=Math.hypot(v[0]-prev[i][0],v[1]-prev[i][1],v[2]-prev[i][2]);vels[i].push(d);if(vels[i].length>1)acc[i].push(Math.abs(vels[i].at(-1)-vels[i].at(-2)));}prev[i]=v;});
    const yaw=c.root.rotation.y; const rate=Math.atan2(Math.sin(yaw-lastYaw),Math.cos(yaw-lastYaw)); yawRates.push(rate); if(yawRates.length>1)yawAcc.push(Math.abs(yawRates.at(-1)-yawRates.at(-2))); lastYaw=yaw;
  });
  await wait(1300); key('keyup','KeyW'); play.viewer.scene.onAfterRenderObservable.remove(observer);
  const top=acc.map((a,i)=>({name:nodes[i].name,max:a.length?Math.max(...a):0,avg:a.length?a.reduce((x,y)=>x+y,0)/a.length:0})).sort((a,b)=>b.max-a.max).slice(0,8);
  return {nodes:nodes.length,top,yawMaxRate:Math.max(...yawRates.map(Math.abs)),yawMaxAcc:Math.max(...yawAcc)};
})()
