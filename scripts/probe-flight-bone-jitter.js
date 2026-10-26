(async () => {
  const play=window.__undefeatedPlay; const wait=ms=>new Promise(r=>setTimeout(r,ms)); const key=(t,c)=>window.dispatchEvent(new KeyboardEvent(t,{code:c,bubbles:true}));
  for(let i=0;i<50&&!play.player.stats().grounded;i++)await wait(100); await wait(300);
  key('keydown','Space');await wait(80);key('keyup','Space');await wait(300);key('keydown','Space');await wait(80);key('keyup','Space');await wait(300);key('keydown','KeyW');
  const c=play.character; const head=c.container.transformNodes.find(n=>/head/i.test(n.name));
  const rows=[]; const observer=play.viewer.scene.onAfterRenderObservable.add(()=>{const p=head.getAbsolutePosition();const r=c.root.position;rows.push({hx:p.x-r.x,hy:p.y-r.y,hz:p.z-r.z,cy:play.viewer.camera.position.y,clip:c.clip});});
  await wait(1500); key('keyup','KeyW'); play.viewer.scene.onAfterRenderObservable.remove(observer);
  const local=rows.map(r=>[r.hx,r.hy,r.hz]);
  const d1=[],d2=[]; for(let i=1;i<local.length;i++){d1.push(Math.hypot(local[i][0]-local[i-1][0],local[i][1]-local[i-1][1],local[i][2]-local[i-1][2]));}
  for(let i=1;i<d1.length;i++)d2.push(Math.abs(d1[i]-d1[i-1]));
  return {frames:rows.length,clips:[...new Set(rows.map(r=>r.clip))],headLocalMin:[Math.min(...local.map(v=>v[0])),Math.min(...local.map(v=>v[1])),Math.min(...local.map(v=>v[2]))],headLocalMax:[Math.max(...local.map(v=>v[0])),Math.max(...local.map(v=>v[1])),Math.max(...local.map(v=>v[2]))],d1max:Math.max(...d1),d2max:Math.max(...d2)};
})()
