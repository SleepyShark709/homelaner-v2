(async () => {
  const play = window.__undefeatedPlay;
  const rows = [];
  for (const mesh of play.viewer.scene.meshes) {
    if (!mesh.name.toLowerCase().includes('building_2_01')) continue;
    const material = mesh.material;
    rows.push({
      mesh: mesh.name,
      material: material?.name,
      albedo: material?.albedoColor ? [material.albedoColor.r, material.albedoColor.g, material.albedoColor.b] : null,
      texture: material?.albedoTexture?.name ?? null,
    });
  }
  return rows.slice(0, 40);
})()
