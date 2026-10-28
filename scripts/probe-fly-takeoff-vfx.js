(async () => {
  const play=window.__undefeatedPlay; const wait=ms=>new Promise(r=>setTimeout(r,ms)); const key=(t,c)=>window.dispatchEvent(new KeyboardEvent(t,{code:c,bubbles:true}));
  for(let i=0;i<50&&!play.player.stats().grounded;i++)await wait(100); await wait(300);
  key('keydown','Space');await wait(70);key('keyup','Space');await wait(260);key('keydown','Space');await wait(70);key('keyup','Space');await wait(80);
  play.combat.effects.blasts.forEach(b=>{b.life=100;}); play.combat.effects.dust.forEach(d=>{d.life=100;});
  return {flying:play.player.flying,blasts:play.combat.effects.blasts.length,dust:play.combat.effects.dust.length};
})()
