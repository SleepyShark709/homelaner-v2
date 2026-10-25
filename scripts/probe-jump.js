(async () => {
  const event = code => new KeyboardEvent('keydown', { code, key: code === 'Space' ? ' ' : code, bubbles: true });
  window.dispatchEvent(event('Space'));
  await new Promise(resolve => setTimeout(resolve, 260));
  return { held: 'Space', player: document.querySelector('canvas')?.dataset.player ?? '' };
})()
