/** Authored Web execution of the recovered startup contract, not a full UE World.
 * Load promises must resolve after geometry/visibility assembly, not fetch dispatch.
 * Adapters must honor AbortSignal and dispose partial work on abort; this module
 * cannot undo a renderer that mounts objects after its request was cancelled.
 */
export type StreamingBranch = 'resident' | 'city' | 'overlay' | 'conditional';
export interface LevelRequest {
  package: string;
  levelName: string;
  branch: StreamingBranch;
  signal: AbortSignal;
}
export interface LoadRequest extends LevelRequest {
  makeVisibleAfterLoad: true;
  shouldBlockOnLoad: false;
}
export interface UnloadRequest extends LevelRequest { shouldBlockOnUnload: false }
export interface OriginalStreamingAdapter {
  load(request: LoadRequest): Promise<void>;
  unload(request: UnloadRequest): Promise<void>;
}
export interface StreamingClock { delay(milliseconds: number, signal: AbortSignal): Promise<void> }
export interface StreamingSaveFlags { isFirstPlayerSpecialAction?: boolean }
/** Fresh save inference, not a loaded user save and not a complete new-game model.
 * HeroGameInstance /Exports/0/ScriptBytecode/93..103: invalid LoadGame result ->
 * CreateSaveGameObject(HeroGameSaveData_C), assign SaveData; only IsFirstStart=true.
 * HeroGameSaveData /Exports/0/LoadedProperties/29 declares this Blueprint bool;
 * /Exports/1 (CDO) has no override, direct parent is Engine.SaveGame and there
 * are no function exports. UE4.27 UObject zero initialization therefore gives
 * false. FBoolProperty.Value describes the property, NOT its instance value.
 * Evidence and source hashes: research/streaming-new-save-evidence.json.
 * https://dev.epicgames.com/documentation/en-us/unreal-engine/unreal-object-handling?application_version=4.27
 */
export function createOriginalNewSaveFlags(): StreamingSaveFlags {
  return { isFirstPlayerSpecialAction: false };
}
export interface StreamingSnapshot {
  phase: 'idle' | 'loading' | 'awaiting-save-state' | 'complete' | 'failed' | 'disposed';
  resident: 'idle' | 'loading' | 'ready' | 'failed';
  overlay: 'idle' | 'loading' | 'delay' | 'unloading' | 'complete' | 'failed';
  completedCitySteps: number;
  loadedPackages: readonly string[];
  failure?: string;
}
export type StreamingEvent =
  | { type: 'state'; snapshot: StreamingSnapshot }
  | { type: 'request' | 'completed'; operation: 'load' | 'unload'; request: LevelRequest }
  | { type: 'needs-save-state'; flag: 'isFirstPlayerSpecialAction' }
  | { type: 'failed'; branch: StreamingBranch; message: string }
  | { type: 'unknown-event'; event: string; reason: string };
export interface OriginalStreamingOptions {
  clock?: StreamingClock;
  /** Observer must not throw. Renderer actions belong in the adapter. */
  onEvent?: (event: StreamingEvent) => void;
}
interface Level { package: string; levelName: string }
interface Plan { resident: Level[]; city: Level[]; overlay: Level; meteor: Level; delay: number }

const delayClock: StreamingClock = {
  delay(milliseconds, signal) {
    return new Promise((resolve, reject) => {
      signal.throwIfAborted();
      const abort = () => { clearTimeout(timer); reject(signal.reason); };
      const timer = setTimeout(() => { signal.removeEventListener('abort', abort); resolve(); }, milliseconds);
      signal.addEventListener('abort', abort, { once: true });
    });
  },
};

function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Invalid streaming contract object');
  return value as Record<string, unknown>;
}
function array(value: unknown): unknown[] {
  if (!Array.isArray(value)) throw new Error('Invalid streaming contract array');
  return value;
}
function text(value: unknown): string {
  if (typeof value !== 'string' || !value) throw new Error('Invalid streaming contract string');
  return value;
}

/** Reject an incomplete/changed contract rather than silently invent loading order. */
function parsePlan(raw: unknown): Plan {
  const manifest = object(raw), baseline = object(manifest.baseline);
  if (manifest.schemaVersion !== 1) throw new Error('Unsupported streaming contract version');
  const registrations = array(manifest.mapRegistrations).map(object);
  const registered = (name: string): Level => {
    const matches = registrations.filter(r => text(r.package).split('/').at(-1) === name);
    if (matches.length !== 1) throw new Error(`Missing/ambiguous streaming registration: ${name}`);
    return { levelName: name, package: text(matches[0].package) };
  };
  // The raw World table is the ordering evidence. This is request order only;
  // Unreal's AlwaysLoaded completion timing was not recovered.
  const always = registrations.filter(r => r.class === 'LevelStreamingAlwaysLoaded').map(r => registered(text(r.package).split('/').at(-1)!));
  const expectedAlways = array(baseline.alwaysLoadedLevelNames);
  if (JSON.stringify(always.map(x => x.levelName)) !== JSON.stringify(expectedAlways)) throw new Error('AlwaysLoaded table order mismatch');
  const sequence = array(manifest.startupSequence).map(object);
  const expected = ['DownTown', 'Park', 'FinancialDistrict', 'CommercialArea', 'IndustrialArea', 'Beach',
    'Slam', 'ResidentialArea1', 'ResidentialArea2', 'ResidentialArea3', 'Coast', 'DynamicProps'];
  if (JSON.stringify(sequence.map(s => s.levelName)) !== JSON.stringify(expected)) throw new Error('Unverified startup chain');
  const city = sequence.map((s, i) => {
    if (s.makeVisibleAfterLoad !== true || s.shouldBlockOnLoad !== false) throw new Error('Unsupported original load flags');
    if (i < sequence.length - 1 && s.onCompletedResumeOffset !== object(sequence[i + 1].evidence).offset) throw new Error('Broken latent completion edge');
    const level = registered(text(s.levelName));
    if (level.package !== s.package) throw new Error('Startup package identity mismatch');
    return level;
  });
  const overlay = object(manifest.transitionOverlay);
  if (overlay.levelName !== 'LoadLevel' || overlay.onLoadedDelaySeconds !== 1) throw new Error('Unverified transition overlay contract');
  const condition = array(manifest.conditionalLevels).map(object).find(c => c.levelName === 'EnelightMeteor');
  if (!condition || condition.condition !== 'HeroGameInstance.SaveData.IsFirstPlayerSpecialAction == true') throw new Error('Unverified meteor condition');
  const mainPackage = text(object(manifest.entry).package);
  if (mainPackage !== '/Game/-HeroGame/Maps/MainLevel') throw new Error('Only recovered MainLevel startup is supported');
  return { resident: [{ levelName: 'MainLevel', package: mainPackage }, ...always], city,
    overlay: registered('LoadLevel'), meteor: registered('EnelightMeteor'), delay: 1000 };
}

export class OriginalStreaming {
  private readonly plan: Plan;
  private readonly adapter: OriginalStreamingAdapter;
  private readonly clock: StreamingClock;
  private readonly observer?: (event: StreamingEvent) => void;
  private readonly abort = new AbortController();
  private readonly loaded = new Set<string>();
  private state: Omit<StreamingSnapshot, 'loadedPackages'> = { phase: 'idle', resident: 'idle', overlay: 'idle', completedCitySteps: 0 };
  private flags: StreamingSaveFlags = {};
  private residentTask?: Promise<StreamingSnapshot>;
  private startupTask?: Promise<StreamingSnapshot>;
  private overlayTask?: Promise<void>;
  private conditionalTask?: Promise<void>;

  static fromManifest(raw: unknown, adapter: OriginalStreamingAdapter, options: OriginalStreamingOptions = {}): OriginalStreaming {
    return new OriginalStreaming(parsePlan(raw), adapter, options);
  }
  private constructor(plan: Plan, adapter: OriginalStreamingAdapter, options: OriginalStreamingOptions) {
    this.plan = plan; this.adapter = adapter; this.clock = options.clock ?? delayClock; this.observer = options.onEvent;
  }
  getSnapshot(): StreamingSnapshot { return { ...this.state, loadedPackages: [...this.loaded] }; }
  private emit(event: StreamingEvent): void { this.observer?.(event); }
  private publish(): void { this.emit({ type: 'state', snapshot: this.getSnapshot() }); }
  private live(): boolean { return !this.abort.signal.aborted; }

  private async load(level: Level, branch: StreamingBranch): Promise<void> {
    this.abort.signal.throwIfAborted();
    const request: LoadRequest = { ...level, branch, signal: this.abort.signal, makeVisibleAfterLoad: true, shouldBlockOnLoad: false };
    this.emit({ type: 'request', operation: 'load', request });
    this.abort.signal.throwIfAborted();
    await this.adapter.load(request);
    this.abort.signal.throwIfAborted();
    this.loaded.add(level.package);
    this.emit({ type: 'completed', operation: 'load', request });
  }
  private fail(branch: StreamingBranch, error: unknown): void {
    if (!this.live()) return;
    const message = error instanceof Error ? error.message : String(error);
    if (branch === 'resident') this.state.resident = 'failed';
    else if (branch === 'overlay') this.state.overlay = 'failed';
    else this.state.phase = 'failed';
    this.state.failure = message;
    this.emit({ type: 'failed', branch, message }); this.publish();
  }

  /** Web bootstrap boundary, not evidence that UE serializes AlwaysLoaded loads.
   * Mount MainLevel, then request the four resident levels in original table order
   * concurrently. Caller decides when to invoke BeginPlay after this barrier.
   */
  prepareResidentWorld(): Promise<StreamingSnapshot> {
    if (!this.live()) return Promise.resolve(this.getSnapshot());
    return this.residentTask ??= (async () => {
      this.state.resident = 'loading'; this.publish();
      try {
        await this.load(this.plan.resident[0], 'resident');
        await Promise.all(this.plan.resident.slice(1).map(level => this.load(level, 'resident')));
        if (this.live()) { this.state.resident = 'ready'; this.publish(); }
      } catch (error) { this.fail('resident', error); }
      return this.getSnapshot();
    })();
  }

  /** Starts the two independent BeginPlay latent paths exactly once.
   * If prepareResidentWorld was used, it must succeed first. An idle resident
   * phase allows an external owner that already mounted the persistent world;
   * this is an integration precondition, not a simulated UE readiness check.
   */
  beginPlay(flags: StreamingSaveFlags = {}): Promise<StreamingSnapshot> {
    if (!this.live()) return Promise.resolve(this.getSnapshot());
    if (this.startupTask) return this.startupTask;
    if (this.state.resident === 'loading' || this.state.resident === 'failed') {
      return Promise.reject(new Error(`Resident preparation is ${this.state.resident}; BeginPlay cannot start`));
    }
    this.flags = { ...flags };
    this.startupTask = (async () => {
      this.state.phase = 'loading'; this.publish();
      this.overlayTask = this.runOverlay();
      try {
        for (const level of this.plan.city) {
          await this.load(level, 'city');
          this.state.completedCitySteps++; this.publish();
        }
        await this.finishConditional();
      } catch (error) { this.fail('city', error); }
      return this.getSnapshot();
    })();
    return this.startupTask;
  }
  private async runOverlay(): Promise<void> {
    try {
      this.state.overlay = 'loading'; this.publish();
      await this.load(this.plan.overlay, 'overlay');
      this.state.overlay = 'delay'; this.publish();
      await this.clock.delay(this.plan.delay, this.abort.signal);
      this.abort.signal.throwIfAborted();
      this.state.overlay = 'unloading'; this.publish();
      const request: UnloadRequest = { ...this.plan.overlay, branch: 'overlay', signal: this.abort.signal, shouldBlockOnUnload: false };
      this.emit({ type: 'request', operation: 'unload', request });
      this.abort.signal.throwIfAborted();
      await this.adapter.unload(request);
      this.abort.signal.throwIfAborted();
      this.loaded.delete(request.package);
      this.emit({ type: 'completed', operation: 'unload', request });
      this.state.overlay = 'complete'; this.publish();
    } catch (error) { this.fail('overlay', error); }
  }
  private async finishConditional(): Promise<void> {
    if (!this.live() || this.state.phase === 'failed' || this.state.phase === 'complete') return;
    if (this.conditionalTask) return this.conditionalTask;
    if (typeof this.flags.isFirstPlayerSpecialAction !== 'boolean') {
      this.state.phase = 'awaiting-save-state'; this.publish();
      this.emit({ type: 'needs-save-state', flag: 'isFirstPlayerSpecialAction' }); return;
    }
    this.conditionalTask = (async () => {
      try {
        this.state.phase = 'loading'; this.publish();
        if (this.flags.isFirstPlayerSpecialAction) await this.load(this.plan.meteor, 'conditional');
        if (this.live()) { this.state.phase = 'complete'; this.publish(); }
      } catch (error) { this.fail('conditional', error); }
    })();
    return this.conditionalTask;
  }
  async setSaveFlags(flags: StreamingSaveFlags): Promise<StreamingSnapshot> {
    if (!this.live()) return this.getSnapshot();
    this.flags = { ...this.flags, ...flags };
    if (this.state.phase === 'awaiting-save-state') await this.finishConditional();
    return this.getSnapshot();
  }
  waitForOverlay(): Promise<void> { return this.overlayTask ?? Promise.resolve(); }
  /** These events have partial source contracts but no implemented execution. */
  requestEvent(event: string): { status: 'unknown'; reason: string } {
    const reason = 'Only MainLevel startup is executable. Tutorial, story, challenge, boss, reset, and distance streaming are not implemented by this module.';
    if (this.live()) this.emit({ type: 'unknown-event', event, reason });
    return { status: 'unknown', reason };
  }
  /** Stops timers, all subsequent requests, and all late completion publications.
   * Scene ownership remains with the adapter/caller; dispose existing geometry there.
   */
  dispose(): void {
    if (!this.live()) return;
    this.abort.abort(new Error('Original streaming disposed'));
    this.state.phase = 'disposed'; this.publish();
  }
}
