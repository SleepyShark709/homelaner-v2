(async () => {
  const play = window.__undefeatedPlay;
  const rows = play.viewer.scene.meshes
    .filter(m => /MERGED_Building|hero|Character|SK_|SKM|head|torso/i.test(m.name))
    .slice(0, 30)
    .map(m => ({
      name: m.name,
      isPickable: m.isPickable,
      isVisible: m.isVisible,
      enabled: m.isEnabled(),
      thin: m.thinInstanceCount ?? 0,
      thinPicking: m.thinInstanceEnablePicking ?? null,
      vertices: m.getTotalVertices?.(),
      bounds: m.getBoundingInfo?.()?.boundingBox?.extendSize?.asArray?.(),
    }));
  return rows;
})()
