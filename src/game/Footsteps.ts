const FOOTSTEP_URLS = Array.from({ length: 8 }, (_, index) => {
  const number = index < 4 ? index + 1 : index + 2; // the pak has no Footstep05
  return `/assets/audio/footstep${String(number).padStart(2, '0')}.ogg`;
});
const SWING_URLS = Array.from({ length: 4 }, (_, index) => `/assets/audio/punch_swish${String(index + 1).padStart(2, '0')}.ogg`);
const IMPACT_URLS = ['/assets/audio/chain_d_impacts_0201.ogg', '/assets/audio/chain_d_impacts_0601.ogg'];

/**
 * Plays the recovered Footstep01..09 samples at the original animation notify
 * times. The Ogg payloads are extracted from the cooked SoundWave .uexp files;
 * they stay local and are not committed.
 */
export class Footsteps {
  private context: AudioContext | null = null;
  private gain: GainNode | null = null;
  private buffers: AudioBuffer[] = [];
  private swings: AudioBuffer[] = [];
  private impacts: AudioBuffer[] = [];
  private unlocked = false;

  constructor(private readonly enabled = true) {}

  private async loadBuffers(urls: string[]): Promise<AudioBuffer[]> {
    const loaded = await Promise.all(urls.map(async url => {
      try {
        const response = await fetch(url);
        if (!response.ok) return null;
        return await this.context!.decodeAudioData(await response.arrayBuffer());
      } catch {
        return null;
      }
    }));
    return loaded.filter((buffer): buffer is AudioBuffer => buffer !== null);
  }

  async load(): Promise<void> {
    if (!this.enabled) return;
    const AudioContextClass = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!AudioContextClass) return;
    this.context = new AudioContextClass();
    this.gain = this.context.createGain();
    this.gain.gain.value = 0.32;
    this.gain.connect(this.context.destination);
    [this.buffers, this.swings, this.impacts] = await Promise.all([
      this.loadBuffers(FOOTSTEP_URLS),
      this.loadBuffers(SWING_URLS),
      this.loadBuffers(IMPACT_URLS),
    ]);
  }

  private playBuffer(buffers: AudioBuffer[], volume = 1, duration?: number): void {
    if (!this.enabled || !this.context || !this.gain || buffers.length === 0) return;
    if (this.context.state === 'suspended') {
      if (!this.unlocked) {
        this.unlocked = true;
        void this.context.resume().catch(() => undefined);
      }
      return;
    }
    const source = this.context.createBufferSource();
    source.buffer = buffers[Math.floor(Math.random() * buffers.length)];
    const level = this.context.createGain();
    level.gain.value = volume;
    source.connect(level);
    level.connect(this.gain);
    source.start(0, 0, duration);
  }

  play(): void { this.playBuffer(this.buffers); }

  playSwing(): void { this.playBuffer(this.swings, 0.8); }

  playImpact(): void { this.playBuffer(this.impacts, 0.9, 0.22); }

  playDestruction(): void { this.playBuffer(this.impacts, 1); }

  dispose(): void {
    void this.context?.close().catch(() => undefined);
    this.context = null;
    this.gain = null;
    this.buffers = [];
    this.swings = [];
    this.impacts = [];
  }
}
