(async () => {
  const play=window.__undefeatedPlay; const wait=ms=>new Promise(r=>setTimeout(r,ms));
  for(let i=0;i<50&&!play.player.stats().grounded;i++)await wait(100); await wait(6000);
  const boxes=play.collision?.boxes||[]; const actors=play.population.actors.filter(a=>a.alive); const p=play.player; const pp=p.position;
  const overlap=(a,b)=>a.min[0]<b.max[0]&&a.max[0]>b.min[0]&&a.min[2]<b.max[2]&&a.max[2]>b.min[2]&&a.min[1]<b.max[1]&&a.max[1]>b.min[1];
  let sunk=0,floating=0,wall=0,playerOverlap=0;const samples=[];
  for(const a of actors){const g=p.supportAt(a.position[0],a.position[2],a.position[1]);const dy=a.position[1]-g;if(dy<-0.15)sunk++;if(dy>0.25)floating++;const hit=boxes.some(b=>overlap(a,b));if(hit)wall++;const po=pp[0]>a.min[0]-0.35&&pp[0]<a.max[0]+0.35&&pp[2]>a.min[2]-0.35&&pp[2]<a.max[2]+0.35;if(po)playerOverlap++;if((hit||po)&&samples.length<6)samples.push({id:a.id,kind:a.kind,pos:a.position.map(v=>+v.toFixed(2)),wall:hit,playerOverlap:po});}
  return {actors:actors.length,sunk,floating,wall,playerOverlap,samples};
})()
