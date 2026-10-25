(async () => {
  const event = (type, code) => window.dispatchEvent(new KeyboardEvent(type, { code, bubbles: true }));
  event('keydown', 'Space');
  await new Promise(resolve => setTimeout(resolve, 80));
  event('keyup', 'Space');
  await new Promise(resolve => setTimeout(resolve, 2400));
  return { player: document.querySelector('canvas')?.dataset.player ?? '' };
})()
