(async () => {
  const play = window.__undefeatedPlay;
  const scene = play.viewer.scene;
  const meshes = scene.meshes.filter(m => m.isVisible && m.isEnabled() && (m.getTotalVertices?.() ?? 0) > 0);
  return {
    visibleCount: meshes.length,
    sample: meshes.slice(0, 25).map(m => ({
      name: m.name,
      thin: m.thinInstanceCount ?? 0,
      pickable: m.isPickable,
      center: m.getBoundingInfo().boundingBox.centerWorld.asArray(),
    })),
  };
})()
