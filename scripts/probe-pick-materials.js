(async () => {
  const play = window.__undefeatedPlay;
  await new Promise(r => setTimeout(r, 500));
  const points = [[650, 70], [650, 90], [650, 120], [250, 220], [500, 650]];
  return Object.fromEntries(points.map(([x, y]) => [`${x},${y}`, play.pick(x, y)]));
})()
