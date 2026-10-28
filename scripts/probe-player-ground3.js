(async () => {
  const play=window.__undefeatedPlay; const wait=ms=>new Promise(r=>setTimeout(r,ms)); const key=(t,c)=>window.dispatchEvent(new KeyboardEvent(t,{code:c,bubbles:true}));
  for(let i=0;i<50&&!play.player.stats().grounded;i++)await wait(100); await wait(300);
  const sample=async(label)=>{const c=play.character;const sk=c.container.skeletons?.[0];const mesh=sk?.meshes?.[0]||c.container.meshes?.find(m=>m.skeleton);const wm=mesh.getWorldMatrix().m;const tf=v=>({y:wm[1]*v.x+wm[5]*v.y+wm[9]*v.z+wm[13]});const feet=(sk?.bones||[]).filter(b=>/foot|toe|ball/i.test(b.name));let min=Infinity;for(let i=0;i<50;i++){for(const b of feet)min=Math.min(min,tf(b.getAbsolutePosition()).y);await wait(16);}const p=play.player.position;const g=play.player.supportAt(p[0],p[2],p[1]);return {label,min:+min.toFixed(3),ground:+g.toFixed(3),pen:+(min-g).toFixed(3)};};
  const idle=await sample('idle'); key('keydown','KeyW'); await wait(300); const run=await sample('run'); key('keyup','KeyW'); return {idle,run};
})()
