export {};
const view = new URLSearchParams(location.search).get('view');
if (view === 'assets') {
  await import('./lab');
} else if (view === 'prototype') {
  await import('./play');
} else if (view === 'play' || view === 'play-original') {
  await import('./play-original');
} else {
  await import('./world');
}
