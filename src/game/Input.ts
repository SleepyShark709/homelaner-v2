export class Input {
  private readonly down = new Set<string>();
  private readonly presses = new Set<string>();
  private dragging = false;
  private lastX = 0;
  private lastY = 0;
  private dragDistance = 0;
  yaw = Math.PI;
  pitch = 0.14;
  active = false;
  onPause: () => void = () => {};
  private readonly abort = new AbortController();

  constructor(privateCanvas: HTMLCanvasElement) {
    const signal = this.abort.signal;
    window.addEventListener('keydown', event => {
      if (!this.active || /^(INPUT|TEXTAREA|SELECT)$/.test((event.target as HTMLElement)?.tagName)) return;
      if (['Space', 'ControlLeft', 'ControlRight', 'Tab', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(event.code)) event.preventDefault();
      if (!event.repeat) this.presses.add(event.code);
      if (!event.repeat && event.code === 'KeyK' && event.shiftKey) this.presses.add('AttackStrong');
      this.down.add(event.code);
      if (event.code === 'Escape') this.pause();
    }, { signal });
    window.addEventListener('keyup', event => this.down.delete(event.code), { signal });
    window.addEventListener('blur', () => this.pause(), { signal });
    document.addEventListener('visibilitychange', () => { if (document.hidden) this.pause(); }, { signal });
    privateCanvas.addEventListener('pointerdown', event => {
      if (!this.active) return;
      if (event.button === 2 || document.pointerLockElement) this.presses.add(event.button === 2 ? 'AttackRanged' : 'AttackMelee');
      if (event.button === 2 && event.shiftKey) this.presses.add('AttackStrong');
      this.dragging = true; this.dragDistance = 0; this.lastX = event.clientX; this.lastY = event.clientY;
      privateCanvas.setPointerCapture(event.pointerId);
    }, { signal });
    privateCanvas.addEventListener('pointermove', event => {
      if (!this.active || !this.dragging || document.pointerLockElement) return;
      this.dragDistance += Math.abs(event.clientX - this.lastX) + Math.abs(event.clientY - this.lastY);
      this.look(event.clientX - this.lastX, event.clientY - this.lastY);
      this.lastX = event.clientX; this.lastY = event.clientY;
    }, { signal });
    privateCanvas.addEventListener('pointerup', event => {
      if (this.active && this.dragging && this.dragDistance < 5 && event.button === 0 && !document.pointerLockElement) this.presses.add('AttackMelee');
      this.dragging = false;
    }, { signal });
    privateCanvas.addEventListener('pointercancel', () => { this.dragging = false; }, { signal });
    privateCanvas.addEventListener('contextmenu', event => event.preventDefault(), { signal });
    window.addEventListener('mousemove', event => {
      if (!this.active || document.pointerLockElement !== privateCanvas) return;
      this.look(event.movementX, event.movementY);
    }, { signal });
    document.addEventListener('pointerlockchange', () => {
      if (!document.pointerLockElement && this.active) this.pause();
    }, { signal });
  }
  private look(x: number, y: number): void { this.yaw -= x * 0.0025; this.pitch = Math.max(-0.75, Math.min(1.05, this.pitch + y * 0.0025)); }
  held(...keys: string[]): boolean { return keys.some(key => this.down.has(key)); }
  pressed(key: string): boolean { const value = this.presses.has(key); this.presses.delete(key); return value; }
  axis(positive: string[], negative: string[]): number { return Number(this.held(...positive)) - Number(this.held(...negative)); }
  clear(): void { this.down.clear(); this.presses.clear(); this.dragging = false; }
  pause(): void { this.clear(); if (this.active) { this.active = false; this.onPause(); } }
  dispose(): void { this.abort.abort(); this.clear(); }
}
