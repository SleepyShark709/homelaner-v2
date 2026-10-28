(async () => {
  const play=window.__undefeatedPlay; const wait=ms=>new Promise(r=>setTimeout(r,ms)); const key=(t,c)=>window.dispatchEvent(new KeyboardEvent(t,{code:c,bubbles:true}));
  for(let i=0;i<50&&!play.player.stats().grounded;i++)await wait(100); await wait(300);
  const measureStop=async(maxMs)=>{const p0=[...play.player.position];const t0=performance.now();let dist=0,prev=[...p0];for(let i=0;i<maxMs/20;i++){await wait(20);const p=play.player.position;dist+=Math.hypot(p[0]-prev[0],p[2]-prev[2]);prev=[...p];if(play.player.stats().speed<0.4)break;}return{ms:Math.round(performance.now()-t0),distance:+dist.toFixed(2)};};
  key('keydown','KeyW'); await wait(1600); const runSpeed=play.player.stats().speed; key('keyup','KeyW');
  const run=await measureStop(3000);
  key('keydown','KeyR'); await wait(80); key('keyup','KeyR'); await wait(400);
  key('keydown','Space');await wait(80);key('keyup','Space');await wait(300);key('keydown','Space');await wait(80);key('keyup','Space');await wait(300);
  key('keydown','KeyW'); await wait(2000); const flySpeed=play.player.stats().speed; key('keyup','KeyW');
  const fly=await measureStop(4000);
  return {runSpeed,flySpeed,run,fly};
})()
