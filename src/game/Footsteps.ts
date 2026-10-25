const FOOTSTEP_URLS = Array.from({ length: 8 }, (_, index) => {
  const number = index < 4 ? index + 1 : index + 2; // the pak has no Footstep05
  return `/assets/audio/footstep${String(number).padStart(2, '0')}.ogg`;
});
const SWING_URLS = Array.from({ length: 4 }, (_, index) => `/assets/audio/punch_swish${String(index + 1).padStart(2, '0')}.ogg`);
const IMPACT_URLS = ['/assets/audio/chain_d_impacts_0201.ogg', '/assets/audio/chain_d_impacts_0601.ogg'];
const HEAVY_URLS = Array.from({ length: 5 }, (_, index) => `/assets/audio/cannonexplode0${index + 1}_stereo.ogg`);
const WHOOSH_URLS = Array.from({ length: 4 }, (_, index) => `/assets/audio/sweetener_whooshf0${index + 1}.ogg`);
const WIND_URL = '/assets/audio/flourish03.ogg';

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
  private heavies: AudioBuffer[] = [];
  private whooshes: AudioBuffer[] = [];
  private wind: AudioBuffer | null = null;
  private windSource: AudioBufferSourceNode | null = null;
  private windGain: GainNode | null = null;

  get flightWindActive(): boolean { return this.windSource !== null; }
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
    [this.heavies, this.whooshes] = await Promise.all([
      this.loadBuffers(HEAVY_URLS),
      this.loadBuffers(WHOOSH_URLS),
    ]);
    this.wind = (await this.loadBuffers([WIND_URL]))[0] ?? null;
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

  playHeavy(): void {
    this.playBuffer(this.swings, 0.55);
    this.playBuffer(this.heavies, 0.85);
  }

  playWhoosh(): void {
    this.playBuffer(this.whooshes, 0.75);
    this.playBuffer(this.swings, 0.5);
  }

  setFlightWind(active: boolean, intensity: number): void {
    if (!this.enabled || !this.context || !this.gain || !this.wind) return;
    if (active && !this.windSource) {
      this.windSource = this.context.createBufferSource();
      this.windSource.buffer = this.wind;
      this.windSource.loop = true;
      this.windSource.playbackRate.value = 1.2;
      this.windGain = this.context.createGain();
      this.windGain.gain.value = 0;
      this.windSource.connect(this.windGain);
      this.windGain.connect(this.gain);
      this.windSource.start();
    }
    if (this.windGain) {
      const level = active ? Math.min(0.35, 0.08 + Math.max(0, intensity) * 0.35) : 0;
      this.windGain.gain.setTargetAtTime(level, this.context.currentTime, 0.12);
    }
    if (!active && this.windSource) {
      const source = this.windSource;
      this.windSource = null;
      this.windGain = null;
      setTimeout(() => { try { source.stop(); source.disconnect(); } catch { /* already stopped */ } }, 350);
    }
  }

  dispose(): void {
    void this.context?.close().catch(() => undefined);
    this.context = null;
    this.gain = null;
    this.buffers = [];
    this.swings = [];
    this.impacts = [];
    this.heavies = [];
    this.whooshes = [];
    this.wind = null;
    this.windSource = null;
    this.windGain = null;
  }
}
