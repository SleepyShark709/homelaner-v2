(async () => {
  const play = window.__undefeatedPlay;
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const key = (type, code) => window.dispatchEvent(new KeyboardEvent(type, { code, bubbles: true }));
  const meshes = play.character.container.meshes.filter(m => m.getTotalVertices() > 0);
  let frames = 0, missing = 0, hidden = 0;
  const observer = play.viewer.scene.onAfterRenderObservable.add(() => {
    frames++;
    const active = new Set(play.viewer.scene.getActiveMeshes().data);
    for (const mesh of meshes) {
      if (!active.has(mesh) && mesh.isEnabled()) missing++;
      if (mesh.visibility < 0.99 || (mesh.material?.alpha ?? 1) < 0.99) hidden++;
    }
  });
  await wait(2000);
  key('keydown', 'KeyW'); await wait(1500); key('keyup', 'KeyW');
  key('keydown', 'Space'); await wait(80); key('keyup', 'Space'); await wait(200);
  key('keydown', 'Space'); await wait(80); key('keyup', 'Space'); await wait(200);
  key('keydown', 'KeyE'); await wait(700); key('keyup', 'KeyE'); await wait(500);
  play.viewer.scene.onAfterRenderObservable.remove(observer);
  return { meshes: meshes.length, frames, missing, hidden, alwaysSelect: meshes.every(m => m.alwaysSelectAsActiveMesh) };
})()
