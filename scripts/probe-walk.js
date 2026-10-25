(async () => {
  const key = (type, code) => window.dispatchEvent(new KeyboardEvent(type, { code, bubbles: true }));
  key('keydown', 'AltLeft');
  key('keydown', 'KeyW');
  await new Promise(resolve => setTimeout(resolve, 1100));
  return { held: 'AltLeft+KeyW', player: document.querySelector('canvas')?.dataset.player ?? '' };
})()
