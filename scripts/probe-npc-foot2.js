(async () => {
  const play=window.__undefeatedPlay; const wait=ms=>new Promise(r=>setTimeout(r,ms));
  for(let i=0;i<50&&!play.player.stats().grounded;i++)await wait(100); await wait(500);
  const a=play.population.actors.find(a=>a.alive); const meshes=a.root.getChildMeshes(); const m=meshes.find(x=>x.skeleton);
  if(!m)return {meshCount:meshes.length,names:meshes.map(x=>x.name).slice(0,10),skelMeshes:a.entries.skeletons?.[0]?.meshes?.length};
  const wm=m.getWorldMatrix().m; const tf=v=>wm[1]*v.x+wm[5]*v.y+wm[9]*v.z+wm[13]; const feet=(m.skeleton.bones||[]).filter(b=>/foot|toe|ball/i.test(b.name)); let min=Infinity;for(const b of feet)min=Math.min(min,tf(b.getAbsolutePosition()));const g=play.player.supportAt(a.position[0],a.position[2],a.position[1]);return {mesh:m.name,skel:m.skeleton.name,feet:feet.length,footY:+min.toFixed(2),ground:+g.toFixed(2),pen:+(min-g).toFixed(2),rootY:+a.root.position.y.toFixed(2),offset:a.model.groundOffset};
})()
