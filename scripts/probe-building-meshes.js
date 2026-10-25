(async () => {
  const play = window.__undefeatedPlay;
  const meshes = play.viewer.scene.meshes.filter(m => /Building|MERGED|Window|brick|stone/i.test(m.name));
  return {
    total: meshes.length,
    rows: meshes.slice(0, 40).map(m => ({
      name: m.name,
      visible: m.isVisible,
      enabled: m.isEnabled(),
      pickable: m.isPickable,
      thin: m.thinInstanceCount ?? 0,
      vertices: m.getTotalVertices?.(),
      center: m.getBoundingInfo?.()?.boundingBox?.centerWorld?.asArray?.(),
    })),
  };
})()
