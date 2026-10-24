export {};
const view = new URLSearchParams(location.search).get('view');
if (view === 'assets') {
  await import('./lab');
} else if (view === 'prototype') {
  await import('./play');
} else {
  await import('./world');
}
