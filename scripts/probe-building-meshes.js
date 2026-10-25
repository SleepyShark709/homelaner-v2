(async () => {
  const play = window.__undefeatedPlay;
  const names = [];
  for (const mesh of play.viewer.scene.meshes) {
    if (mesh.name.toLowerCase().includes('building_2_01')) names.push(mesh.name);
  }
  return { count: names.length, names: names.slice(0, 30) };
})()
