(async () => {
  const play = window.__undefeatedPlay;
  if (!play) throw new Error('play debug hook missing');
  const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
  const key = (type, code) => window.dispatchEvent(new KeyboardEvent(type, { code, bubbles: true }));
  const state = () => ({
    action: play.combat.actionName,
    clip: play.character.clip,
    heat: play.combat.heatActive,
    projectiles: play.combat.projectiles?.length ?? -1,
    player: play.player.stats(),
    camera: play.viewer.camera.position.asArray(),
  });
  const start = state();
  key('keydown', 'KeyJ'); await wait(60); key('keyup', 'KeyJ'); await wait(120);
  const meleeActive = state();
  if (meleeActive.action !== '近战连击') throw new Error(`melee did not start: ${meleeActive.action}`);
  if (!/Hero_Attack[1-4]/.test(meleeActive.clip)) throw new Error(`unexpected melee clip ${meleeActive.clip}`);
  await wait(1200);
  const meleeFinished = state();
  if (meleeFinished.action !== '待命') throw new Error(`melee did not finish: ${meleeFinished.action}`);
  key('keydown', 'KeyK'); await wait(60); key('keyup', 'KeyK'); await wait(150);
  const rangedActive = state();
  if (rangedActive.action !== '远程攻击') throw new Error(`ranged did not start: ${rangedActive.action}`);
  await wait(500);
  const rangedLater = state();
  key('keydown', 'KeyE'); await wait(250);
  const charging = state();
  key('keyup', 'KeyE');
  if (charging.heat) throw new Error('heat vision must stay disabled in B1/B2 while E is ascend/charge');
  if (charging.player.charge <= 0) throw new Error('ground E did not charge');
  const boxes = play.collision.boxes;
  const cameraInside = boxes.some(box => play.viewer.camera.position.x > box.min[0] && play.viewer.camera.position.x < box.max[0] && play.viewer.camera.position.y > box.min[1] && play.viewer.camera.position.y < box.max[1] && play.viewer.camera.position.z > box.min[2] && play.viewer.camera.position.z < box.max[2]);
  return { start, meleeActive, meleeFinished, rangedActive, rangedLater, charging, cameraInside };
})()
