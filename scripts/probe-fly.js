(async () => {
  const event = (type, code) => window.dispatchEvent(new KeyboardEvent(type, { code, bubbles: true }));
  event('keydown', 'Space'); await new Promise(r => setTimeout(r, 80)); event('keyup', 'Space');
  await new Promise(r => setTimeout(r, 240));
  event('keydown', 'Space'); await new Promise(r => setTimeout(r, 80)); event('keyup', 'Space');
  await new Promise(r => setTimeout(r, 350));
  event('keydown', 'KeyE');
  await new Promise(r => setTimeout(r, 900));
  return { player: document.querySelector('canvas')?.dataset.player ?? '' };
})()
