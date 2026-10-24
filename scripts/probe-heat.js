/**
 * Browser probe: place the player near a citizen, hold Shift+E heat vision,
 * leave the keys held so the capture harness can screenshot the beam.
 * Usage:
 *   node scripts/capture-world.mjs --query='view=play&mode=free' --ready=play \
 *     --probe=scripts/probe-heat.js --shot=research/screenshots/play-heat-beam.jpg
 */
(async () => {
  const play = window.__undefeatedPlay;
  const citizen = play.population.actors.find(actor => actor.kind === 'citizen');
  if (!citizen) return { error: 'no citizen' };
  play.player.position = [citizen.position[0], citizen.position[1], citizen.position[2] + 5];
  play.player.velocity = [0, 0, 0];
  play.input.yaw = Math.atan2(citizen.position[0] - play.player.position[0], citizen.position[2] - play.player.position[2]);
  await new Promise(resolve => setTimeout(resolve, 400));
  window.dispatchEvent(new KeyboardEvent('keydown', { code: 'ShiftLeft', bubbles: true }));
  window.dispatchEvent(new KeyboardEvent('keydown', { code: 'KeyE', bubbles: true }));
  await new Promise(resolve => setTimeout(resolve, 900));
  return { active: play.combat.heatActive, health: citizen.health, alive: citizen.alive, flying: play.player.flying };
})()
