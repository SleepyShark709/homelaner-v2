(async () => {
  const play = window.__undefeatedPlay;
  const heroRoot = play.character.root;
  const meshes = play.character.container.meshes.filter(m => m.getTotalVertices() > 0);
  const descendants = heroRoot.getChildMeshes(false);
  const materials = new Map();
  for (const m of meshes) {
    const mat = m.material;
    if (!mat) continue;
    materials.set(mat.uniqueId, {
      name: mat.name, alpha: mat.alpha, needAlphaBlending: mat.needAlphaBlending?.(),
      needAlphaTesting: mat.needAlphaTesting?.(), transparencyMode: mat.transparencyMode,
      backFaceCulling: mat.backFaceCulling, zOffset: mat.zOffset,
    });
  }
  const renderList = play.shadows?.getShadowMap?.()?.renderList ?? [];
  return {
    heroMeshes: meshes.length,
    descendants: descendants.length,
    duplicateNames: meshes.map(m => m.name).filter((n, i, a) => a.indexOf(n) !== i),
    meshes: meshes.map(m => ({ name: m.name, parent: m.parent?.name, visibility: m.visibility, isVisible: m.isVisible, enabled: m.isEnabled(), alwaysActive: m.alwaysSelectAsActiveMesh, material: m.material?.name, zOffset: m.material?.zOffset })),
    materials: [...materials.values()],
    shadowRenderList: renderList.length,
    shadowHeroCasters: renderList.filter(m => heroRoot.getChildMeshes(false).includes(m)).length,
    skeletonCount: play.character.container.skeletons.length,
  };
})()
