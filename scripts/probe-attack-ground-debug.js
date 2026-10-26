(async () => {
  const play = window.__undefeatedPlay;
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const key = (type, code) => window.dispatchEvent(new KeyboardEvent(type, { code, bubbles: true }));
  for (let i = 0; i < 50 && !play.player.stats().grounded; i++) await wait(100);
  await wait(300);
  const forward = play.viewer.camera.getTarget().subtract(play.viewer.camera.position); forward.y=0; forward.normalize();
  const p=play.player.position;
  const c=play.population.actors.find(a=>a.kind==='citizen'&&a.alive); c.route=undefined; c.position=[p[0]+forward.x*4,p[1],p[2]+forward.z*4]; c.alive=true;c.health=35;c.defeatedTime=0;c.root.setEnabled(true); play.population.place(c,Math.atan2(forward.x,forward.z));
  await wait(150);
  key('keydown','KeyJ'); await wait(80); key('keyup','KeyJ'); await wait(2400);
  const s=play.player.stats(); const x=s.position[0],z=s.position[2],y=s.position[1]; const p2=play.player;
  return {stats:s, flying:s.flying, grounded:s.grounded, state:s.state, clip:play.character.clip, action:play.character.action, support:p2.supportAt(x,z,y), terrain:p2.ground.heightAt(x,z), floor:p2.surfaces?.topAt(x,z,y,0.75) };
})()
