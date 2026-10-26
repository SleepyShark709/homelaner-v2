(async () => {
  const play = window.__undefeatedPlay;
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const key = (type, code) => window.dispatchEvent(new KeyboardEvent(type, { code, bubbles: true }));
  for (let i = 0; i < 50 && !play.player.stats().grounded; i++) await wait(100);
  await wait(300);
  key('keydown','KeyW'); await wait(700); key('keydown','ShiftLeft');
  const rows=[];
  for(let i=0;i<40;i++){const s=play.player.stats();rows.push({t:i*50,speed:+s.speed.toFixed(1),clip:play.character.clip,sprint:play.player.sprint,blocked:play.player.sprintBlocked});await wait(50);}
  key('keyup','ShiftLeft'); key('keyup','KeyW');
  return rows;
})()
