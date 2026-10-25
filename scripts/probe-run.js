(async () => {
  const event = code => new KeyboardEvent('keydown', { code, key: code === 'KeyW' ? 'w' : code, bubbles: true });
  window.dispatchEvent(event('KeyW'));
  await new Promise(resolve => setTimeout(resolve, 1600));
  return { held: 'KeyW', player: document.querySelector('canvas')?.dataset.player ?? '' };
})()

