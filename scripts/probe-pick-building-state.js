(async () => {
  const play = window.__undefeatedPlay;
  const hit = play.pick(640, 360);
  const rows = play.viewer.scene.meshes
    .filter(m => /SM_MERGED_Building_2_01_9/i.test(m.name) && m.isVisible && m.isEnabled())
    .slice(0, 5)
    .map(m => ({
      name: m.name,
      pickable: m.isPickable,
      thin: m.thinInstanceCount ?? 0,
      thinPicking: m.thinInstanceEnablePicking ?? null,
      vertices: m.getTotalVertices?.(),
      center: m.getBoundingInfo?.()?.boundingBox?.centerWorld?.asArray?.(),
      min: m.getBoundingInfo?.()?.boundingBox?.minimumWorld?.asArray?.(),
      max: m.getBoundingInfo?.()?.boundingBox?.maximumWorld?.asArray?.(),
    }));
  return { hit, rows };
})()
