const FOOTSTEP_URLS = Array.from({ length: 8 }, (_, index) => {
  const number = index < 4 ? index + 1 : index + 2; // the pak has no Footstep05
  return `/assets/audio/footstep${String(number).padStart(2, '0')}.ogg`;
});

/**
 * Plays the recovered Footstep01..09 samples at the original animation notify
 * times. The Ogg payloads are extracted from the cooked SoundWave .uexp files;
 * they stay local and are not committed.
 */
export class Footsteps {
  private context: AudioContext | null = null;
  private gain: GainNode | null = null;
  private buffers: AudioBuffer[] = [];
  private unlocked = false;

  constructor(private readonly enabled = true) {}

  async load(): Promise<void> {
    if (!this.enabled) return;
    const AudioContextClass = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!AudioContextClass) return;
    this.context = new AudioContextClass();
    this.gain = this.context.createGain();
    this.gain.gain.value = 0.32;
    this.gain.connect(this.context.destination);
    const loaded = await Promise.all(FOOTSTEP_URLS.map(async url => {
      try {
        const response = await fetch(url);
        if (!response.ok) return null;
        return await this.context!.decodeAudioData(await response.arrayBuffer());
      } catch {
        return null;
      }
    }));
    this.buffers = loaded.filter((buffer): buffer is AudioBuffer => buffer !== null);
  }

  play(): void {
    if (!this.enabled || !this.context || !this.gain || this.buffers.length === 0) return;
    if (this.context.state === 'suspended') {
      if (!this.unlocked) {
        this.unlocked = true;
        void this.context.resume().catch(() => undefined);
      }
      return;
    }
    const source = this.context.createBufferSource();
    source.buffer = this.buffers[Math.floor(Math.random() * this.buffers.length)];
    source.connect(this.gain);
    source.start();
  }

  dispose(): void {
    void this.context?.close().catch(() => undefined);
    this.context = null;
    this.gain = null;
    this.buffers = [];
  }
}
