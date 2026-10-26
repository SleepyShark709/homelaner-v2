(async () => {
  const play=window.__undefeatedPlay,c=play.character;
  return ['Hero_IdleFlying','Hero_FlyForwardLow','Hero_FlyForward','Hero_FlyLeft','Hero_FlyRight','Hero_FlyBack'].map(name=>{
    const g=c.groupFor(name); let max=0,count=0,worst='';
    for(const t of g?.targetedAnimations??[]){const keys=t.animation.getKeys(); if(keys.length<2)continue; const a=keys[0].value,b=keys[keys.length-1].value; let d=0; if(Array.isArray(a)) d=Math.max(...a.map((v,i)=>Math.abs(v-b[i]))); else if(typeof a==='number') d=Math.abs(a-b); if(d>max){max=d;worst=t.target.name||'';} count++;}
    return {name,channels:count,seamMax:+max.toFixed(5),worst};
  });
})()
