(async () => {
  const play = window.__undefeatedPlay;
  const materials = {};
  for (const mesh of play.viewer.scene.meshes) {
    if (!mesh.name.toLowerCase().includes('building_2_01')) continue;
    const material = mesh.material;
    const name = material?.name ?? 'none';
    materials[name] ??= {
      count: 0,
      texture: material?.albedoTexture?.name ?? null,
      albedo: material?.albedoColor ? [material.albedoColor.r, material.albedoColor.g, material.albedoColor.b] : null,
    };
    materials[name].count++;
  }
  return materials;
})()
