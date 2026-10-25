(async () => {
  const event = (type, code) => window.dispatchEvent(new KeyboardEvent(type, { code, bubbles: true }));
  event('keydown', 'KeyW');
  await new Promise(resolve => setTimeout(resolve, 1200));
  event('keyup', 'KeyW');
  await new Promise(resolve => setTimeout(resolve, 240));
  return { player: document.querySelector('canvas')?.dataset.player ?? '' };
})()
