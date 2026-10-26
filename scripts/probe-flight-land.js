(async () => {
  const play=window.__undefeatedPlay; const wait=ms=>new Promise(r=>setTimeout(r,ms)); const key=(t,c)=>window.dispatchEvent(new KeyboardEvent(t,{code:c,bubbles:true}));
  for(let i=0;i<50&&!play.player.stats().grounded;i++)await wait(100); await wait(300);
  key('keydown','Space');await wait(80);key('keyup','Space');await wait(300);
  key('keydown','Space');await wait(80);key('keyup','Space');await wait(300);
  const flying={flying:play.player.flying,state:play.player.state,grounded:play.player.grounded};
  key('keydown','KeyE');await wait(700);key('keyup','KeyE');await wait(200);
  const ascended={y:play.player.position[1],flying:play.player.flying,state:play.player.state};
  key('keydown','KeyF');await wait(80);key('keyup','KeyF');await wait(3500);
  return {flying,ascended,landed:{y:play.player.position[1],flying:play.player.flying,grounded:play.player.grounded,state:play.player.state,clip:play.character.clip}};
})()
