(async () => {
 const play=window.__undefeatedPlay,c=play.character;
 return ['Hero_StartSprint','Hero_Stopping_Sprint','Hero_Stopping_WalkRun','Hero_Attack1','Hero_JumpLand'].map(n=>{const g=c.groupFor(n);return{name:n,length:g?.getLength?.(),to:g?.to,fps:g?.targetedAnimations?.[0]?.animation?.framePerSecond}});
})()
