(async () => {
  const play=window.__undefeatedPlay; const wait=ms=>new Promise(r=>setTimeout(r,ms)); const key=(t,c)=>window.dispatchEvent(new KeyboardEvent(t,{code:c,bubbles:true}));
  for(let i=0;i<50&&!play.player.stats().grounded;i++)await wait(100); await wait(300);
  key('keydown','Space');await wait(80);key('keyup','Space');await wait(300);key('keydown','Space');await wait(80);key('keyup','Space');await wait(500);
  return {flying:play.player.flying,sprites:play.viewer.scene.spriteManagers.map(m=>({name:m.name,count:m.sprites.length,ready:m.texture.isReady()}))};
})()
