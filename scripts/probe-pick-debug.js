(async () => {
  const play = window.__undefeatedPlay;
  await new Promise(r => setTimeout(r, 500));
  return {
    cameraName: play.viewer.camera?.name,
    activeCameraName: play.viewer.scene.activeCamera?.name,
    sameCamera: play.viewer.camera === play.viewer.scene.activeCamera,
    canvas: play.viewer.engine.getRenderingCanvas()?.getBoundingClientRect().toJSON(),
    render: [play.viewer.engine.getRenderWidth(), play.viewer.engine.getRenderHeight()],
    center: play.pick(640, 360),
    bottom: play.pick(640, 700),
    character: play.pick(640, 430),
  };
})()
