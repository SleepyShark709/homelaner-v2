(async () => {
  const play = window.__undefeatedPlay;
  const all = play.viewer.scene.meshes.filter(m => /Building|MERGED|Window|brick|stone/i.test(m.name) && m.isVisible && m.isEnabled() && (m.getTotalVertices?.() ?? 0) > 0);
  return {
    total: all.length,
    rows: all.slice(0, 30).map(m => ({
      name: m.name,
      pickable: m.isPickable,
      thin: m.thinInstanceCount ?? 0,
      vertices: m.getTotalVertices?.(),
      center: m.getBoundingInfo?.()?.boundingBox?.centerWorld?.asArray?.(),
    })),
  };
})()
