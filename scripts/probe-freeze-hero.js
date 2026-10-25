(async () => {
  const play = window.__undefeatedPlay;
  const wait = ms => new Promise(r => setTimeout(r, ms));
  play.player.velocity = [0, 0, 0];
  play.character.animations.forEach(group => group.pause());
  await wait(400);
  return { clip: play.character.clip, paused: play.character.animations.filter(g => !g.isPlaying).length };
})()
