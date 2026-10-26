(async () => {
  const play=window.__undefeatedPlay; const wait=ms=>new Promise(r=>setTimeout(r,ms));
  for(let i=0;i<50&&!play.player.stats().grounded;i++)await wait(100); await wait(300);
  play.population.actors.forEach(a=>{a.alive=false;});
  const f=play.viewer.camera.getTarget().subtract(play.viewer.camera.position);f.y=0;f.normalize();const p=play.player.position;const center=[p[0]+f.x*4,p[1],p[2]+f.z*4];
  const d={id:'reticle-dummy',kind:'citizen',alive:true,health:35,min:[center[0]-.4,center[1],center[2]-.4],max:[center[0]+.4,center[1]+1.8,center[2]+.4],position:center,root:{setEnabled(){},rotation:{x:0},position:{copyFromFloats(){}}},entries:{animationGroups:[]},velocity:[0,0,0],defeatedTime:0};play.population.actors.push(d);
  await wait(300); const e=document.getElementById('lock-reticle'),dist=document.getElementById('lock-distance');
  const on={hidden:e.hidden,left:e.style.left,top:e.style.top,distance:dist.textContent};
  d.alive=false; await wait(300); const off={hidden:e.hidden}; return {on,off};
})()
