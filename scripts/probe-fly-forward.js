(async () => {
  const event = (type, code) => window.dispatchEvent(new KeyboardEvent(type, { code, bubbles: true }));
  const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
  event('keydown', 'Space'); await wait(80); event('keyup', 'Space');
  await wait(240);
  event('keydown', 'Space'); await wait(80); event('keyup', 'Space');
  await wait(300);
  event('keydown', 'KeyW'); await wait(700); event('keyup', 'KeyW');
  return { player: document.querySelector('canvas')?.dataset.player ?? '' };
})()
