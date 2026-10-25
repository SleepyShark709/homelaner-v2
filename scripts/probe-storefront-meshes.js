(async () => {
  const play = window.__undefeatedPlay;
  const p = [-3.6, 2, 76];
  const rows = play.viewer.scene.meshes
    .filter(m => {
      if (!m.isVisible || !m.isEnabled() || (m.getTotalVertices?.() ?? 0) === 0) return false;
      const b = m.getBoundingInfo().boundingBox;
      const min = b.minimumWorld, max = b.maximumWorld;
      return p[0] >= min.x - 2 && p[0] <= max.x + 2 && p[1] >= min.y - 1 && p[1] <= max.y + 1 && p[2] >= min.z - 2 && p[2] <= max.z + 2;
    })
    .slice(0, 25)
    .map(m => ({
      name: m.name,
      pickable: m.isPickable,
      thin: m.thinInstanceCount ?? 0,
      thinPicking: m.thinInstanceEnablePicking ?? null,
      material: m.material?.name,
      vertices: m.getTotalVertices?.(),
      min: m.getBoundingInfo().boundingBox.minimumWorld.asArray(),
      max: m.getBoundingInfo().boundingBox.maximumWorld.asArray(),
    }));
  return rows;
})()
