import { firstHit } from './collision.ts';
import type { Obstacle, Vec3 } from './collision';

export type TargetKind = 'citizen' | 'vehicle' | 'prop';
export type AttackKind = 'melee' | 'ranged' | 'heat';
export type PlayMode = 'baseline' | 'free';
export interface Damageable extends Obstacle { kind: TargetKind; alive: boolean; health: number }
export interface AttackSpec { kind: AttackKind; strong: boolean; damage: number; direction: Vec3 }
export interface ClipTiming { name: string; hit: number | null; finish: number; duration: number; playbackRate: number; sourceRateScale: number }

// Free-mode health/damage are deliberately new browser rules, not recovered UE values.
export const FREE_RULES = { citizenHealth: 35, vehicleHealth: 100, propHealth: 30, meleeDamage: 50, rangedDamage: 100, heatDamage: 12, heatInterval: 0.1 };
export function canDamage(mode: PlayMode, target: Damageable, attack: AttackSpec): boolean {
  if (!target.alive) return false;
  if (mode === 'free') return true;
  return target.kind === 'vehicle' && attack.strong;
}
export function applyDamage(mode: PlayMode, target: Damageable, attack: AttackSpec): 'ignored' | 'hit' | 'destroyed' {
  if (!canDamage(mode, target, attack)) return 'ignored';
  target.health = mode === 'baseline' ? 0 : Math.max(0, target.health - attack.damage);
  if (target.health === 0) { target.alive = false; return 'destroyed'; }
  return 'hit';
}
export function traceTargets(origin: Vec3, delta: Vec3, walls: Obstacle[], targets: Damageable[], half: Vec3 = [0, 0, 0]): { id: string; time: number; target: boolean } | null {
  const wall = firstHit(origin, delta, walls, half);
  const target = firstHit(origin, delta, targets.filter(item => item.alive), half);
  if (target && (!wall || target.time < wall.time)) return { id: target.id, time: target.time, target: true };
  return wall ? { id: wall.id, time: wall.time, target: false } : null;
}
export class AttackTimeline {
  elapsed = 0;
  hitSent = false;
  finished = false;
  readonly timing: ClipTiming;
  constructor(timing: ClipTiming) { this.timing = timing; }
  step(dt: number): { hit: boolean; finished: boolean } {
    if (this.finished) return { hit: false, finished: true };
    this.elapsed += dt * this.timing.playbackRate;
    const hit = !this.hitSent && this.timing.hit !== null && this.elapsed >= this.timing.hit;
    if (hit) this.hitSent = true;
    this.finished = this.elapsed >= this.timing.finish;
    return { hit, finished: this.finished };
  }
}
