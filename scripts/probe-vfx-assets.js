(async () => {
  const play=window.__undefeatedPlay; const wait=ms=>new Promise(r=>setTimeout(r,ms));
  for(let i=0;i<50&&!play.player.stats().grounded;i++)await wait(100); await wait(300);
  const e=play.combat.effects; const p=play.player.position; const d=[0,0,-1];
  e.slash([p[0],p[1]+1.2,p[2]-1]); e.flyDust(p,[0,0,-10],true,0.2); e.startSprint(p); e.airShock([p[0],p[1]+1,p[2]-1]); e.attackWave([p[0],p[1]+1,p[2]-1]);
  e.fistCannon([p[0],p[1]+1,p[2]],d); e.rangedSlash([p[0],p[1]+1,p[2]],d); e.impact([p[0],p[1]+1,p[2]-1],true);
  await wait(80);
  return {managers:play.viewer.scene.spriteManagers.map(m=>({name:m.name,ready:m.texture.isReady(),count:m.sprites.length})),fistSpawns:e.fistSpawns.length,fistMeshes:e.fistMeshes.length};
})()
