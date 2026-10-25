import { Vector3 } from '@babylonjs/core/Maths/math.vector';
import type { FreeCamera } from '@babylonjs/core/Cameras/freeCamera';
import type { Mesh } from '@babylonjs/core/Meshes/mesh';
import type { Scene } from '@babylonjs/core/scene';
import type { Character } from './Character';
import type { Input } from './Input';
import type { PlayerMotor } from './PlayerMotor';
import type { Population } from './Population';
import { Effects } from './Effects';
import { firstHit, sweep } from './collision';
import type { Obstacle, Vec3 } from './collision';
import { AttackTimeline, FREE_RULES, traceTargets } from './combat-rules';
import type { AttackKind, AttackSpec, ClipTiming, PlayMode } from './combat-rules';

interface Projectile { mesh: Mesh; position: Vec3; direction: Vec3; radius: number; age: number; strong: boolean; hitIds: Set<string> }
export class Combat {
  mode: PlayMode = 'free';
  destroyed = 0;
  hits = 0;
  heatActive = false;
  heatTarget = '';
  private readonly effects: Effects;
  private clips: ClipTiming[] = [];
  private timeline: AttackTimeline | null = null;
  private attackKind: AttackKind = 'melee';
  private strong = false;
  private queued: { kind: 'melee' | 'ranged'; strong: boolean } | null = null;
  private combo = 0;
  private rangedCombo = 0;
  private airAttackStarted = false;
  private idleTime = 0;
  private heatTick = 0;
  private readonly projectiles: Projectile[] = [];
  private readonly allowHeatVision: boolean;
  onImpact: (message: string) => void = () => {};
  constructor(scene: Scene, readonly input: Input, readonly motor: PlayerMotor, readonly character: Character, readonly population: Population, readonly camera: FreeCamera, readonly walls: Obstacle[], options: { heatVision?: boolean } = {}) { this.effects = new Effects(scene); this.allowHeatVision = options.heatVision ?? true; }
  async load(): Promise<void> {
    const response = await fetch('/assets/character/combat-timings.json');
    if (!response.ok) throw new Error('原版动作时间轴未生成');
    this.clips = (await response.json()).clips;
  }
  get actionName(): string { return this.heatActive ? '热视线' : this.timeline ? this.attackKind === 'melee' ? '近战连击' : this.strong ? '强力拳波' : '远程攻击' : '待命'; }
  get attacking(): boolean { return this.timeline !== null; }
  private aim(): Vec3 {
    const origin = this.camera.position.asArray() as Vec3;
    const delta = this.camera.getTarget().subtract(this.camera.position).normalize().scale(200).asArray() as Vec3;
    const hit = traceTargets(origin, delta, this.walls, this.population.actors);
    return origin.map((value, i) => value + delta[i] * (hit?.time ?? 1)) as Vec3;
  }
  private direction(origin: Vec3, target: Vec3): Vec3 { return Vector3.FromArray(target).subtract(Vector3.FromArray(origin)).normalize().asArray() as Vec3; }
  private origin(): Vec3 { return [this.motor.position[0], this.motor.position[1] + 1.25, this.motor.position[2]]; }
  private begin(kind: 'melee' | 'ranged', strong: boolean): void {
    this.strong = kind === 'ranged' && strong;
    let name: string;
    if (kind === 'melee' && (this.motor.flying || !this.motor.grounded)) {
      // Air melee uses the same AirAttack state entry as the ranged path.
      if (!this.airAttackStarted) {
        this.airAttackStarted = true;
        name = 'Hero_AirAttackStart';
      } else {
        name = ['Hero_AirKick_L', 'Hero_AirKick_R'][this.combo++ % 2];
      }
    } else if (kind === 'melee') { name = `Hero_Attack${this.combo % 4 + 1}`; this.combo++; }
    else if (this.strong) name = this.motor.flying || !this.motor.grounded ? 'Hero_AirSuperKick' : 'Hero_SuperPunch';
    else if (this.motor.flying || !this.motor.grounded) {
      if (!this.airAttackStarted) {
        // HeroAnimBP has a distinct Jump/Falling AirAttack state; its entry
        // montage is Hero_AirAttackStart with a StartAirAttack notify.
        this.airAttackStarted = true;
        name = 'Hero_AirAttackStart';
      } else {
        name = ['Hero_AirKick_L', 'Hero_AirKick_R'][this.rangedCombo++ % 2];
      }
    }
    else if (Math.hypot(this.motor.velocity[0], this.motor.velocity[2]) > 0.5) name = ['Hero_BackHandSlash_New', 'Hero_FlashKick', 'Hero_Smash_A'][this.rangedCombo++ % 3];
    else name = ['Hero_LongFistForce_L', 'Hero_LongFistForce_R'][this.rangedCombo++ % 2];
    const timing = this.clips.find(clip => clip.name === name);
    if (!timing) throw new Error(`动作时间轴缺失: ${name}`);
    this.attackKind = kind; this.timeline = new AttackTimeline(timing); this.idleTime = 0;
    this.motor.heading = this.input.yaw;
    this.character.playAction(name, timing.playbackRate);
  }
  update(dt: number): void {
    if (this.motor.grounded && !this.motor.flying) this.airAttackStarted = false;
    const melee = this.input.pressed('AttackMelee') || this.input.pressed('KeyJ');
    const ranged = this.input.pressed('AttackRanged') || this.input.pressed('KeyK');
    const strong = this.input.pressed('AttackStrong') || this.input.held('ShiftLeft', 'ShiftRight');
    this.heatActive = this.allowHeatVision && this.input.held('KeyE') && this.input.held('ShiftLeft', 'ShiftRight');
    if (this.heatActive) {
      if (this.timeline) { this.timeline = null; this.character.endAction(); }
      this.queued = null; this.motor.heading = this.input.yaw;
      this.heat(dt);
    } else {
      this.effects.heat(null); this.heatTick = 0; this.heatTarget = '';
      if (melee || ranged) {
        const kind = ranged ? 'ranged' : 'melee';
        if (this.timeline) this.queued = { kind, strong }; else this.begin(kind, strong);
      }
      if (this.timeline) {
        this.motor.heading = this.input.yaw;
        const result = this.timeline.step(dt);
        if (result.hit) this.fire();
        if (result.finished) {
          this.timeline = null; this.character.endAction();
          if (this.queued) { const queued = this.queued; this.queued = null; this.begin(queued.kind, queued.strong); }
        }
      } else {
        this.idleTime += dt;
        if (this.idleTime > (this.motor.flying ? 0.5 : 1)) { this.combo = 0; this.rangedCombo = 0; }
      }
    }
    this.updateProjectiles(dt); this.effects.update(dt);
  }
  private strike(id: string, attack: AttackSpec, point: Vec3): void {
    const actor = this.population.actors.find(item => item.id === id);
    const result = this.population.hit(id, attack, this.mode);
    this.effects.impact(point, result === 'destroyed' && actor?.kind !== 'citizen');
    if (result !== 'ignored') { this.hits++; this.population.alert(point); }
    if (result === 'destroyed') {
      this.destroyed++;
      this.onImpact(actor?.kind === 'citizen' ? '击倒路人' : actor?.kind === 'vehicle' ? '载具已摧毁' : '道具已摧毁');
    } else if (result === 'hit') this.onImpact('命中目标');
    else this.onImpact('基础交互：弱攻击不会破坏车辆或伤害路人');
  }
  private fire(): void {
    const origin = this.origin(), direction = this.direction(origin, this.aim());
    this.population.alert(origin);
    if (this.attackKind === 'melee') {
      const center: Vec3 = [origin[0] + direction[0] * 0.95, this.motor.position[1] + 0.3, origin[2] + direction[2] * 0.95];
      this.effects.impact([center[0], origin[1], center[2]]);
      for (const actor of this.population.actors.filter(item => item.alive)) {
        const closest = center.map((value, i) => Math.max(actor.min[i], Math.min(actor.max[i], value))) as Vec3;
        if (Math.hypot(...closest.map((value, i) => value - center[i])) > 2.56) continue;
        const target: Vec3 = [(actor.min[0] + actor.max[0]) / 2, (actor.min[1] + actor.max[1]) / 2, (actor.min[2] + actor.max[2]) / 2];
        const wall = firstHit(origin, target.map((value, i) => value - origin[i]) as Vec3, this.walls);
        if (!wall || wall.time > 0.99) this.strike(actor.id, { kind: 'melee', strong: false, damage: FREE_RULES.meleeDamage, direction }, target);
      }
    } else {
      if (this.projectiles.length >= 12) this.projectiles.shift()!.mesh.dispose();
      const mesh = this.effects.projectile(); mesh.position.copyFromFloats(...origin);
      this.projectiles.push({ mesh, position: origin, direction, age: 0, strong: this.strong, radius: this.strong ? (this.timeline?.timing.name === 'Hero_AirSuperKick' ? 5 : 15) : 2.56, hitIds: new Set() });
    }
  }
  private heat(dt: number): void {
    const eyes = this.character.eyes(), origin = eyes[0], target = this.aim();
    const delta = target.map((value, i) => value - origin[i]) as Vec3;
    const hit = traceTargets(origin, delta, this.walls, this.population.actors);
    const point = origin.map((value, i) => value + delta[i] * (hit?.time ?? 1)) as Vec3;
    this.effects.heat(eyes, point);
    this.heatTarget = hit?.target ? hit.id : '';
    this.heatTick -= dt;
    if (this.heatTick <= 0) {
      this.heatTick += FREE_RULES.heatInterval;
      if (hit?.target) this.strike(hit.id, { kind: 'heat', strong: false, damage: FREE_RULES.heatDamage, direction: this.direction(origin, point) }, point);
      else if (hit) this.effects.impact(point);
    }
  }
  private updateProjectiles(dt: number): void {
    for (let i = this.projectiles.length - 1; i >= 0; i--) {
      const projectile = this.projectiles[i]; projectile.age += dt;
      const delta = projectile.direction.map(value => value * 150 * dt) as Vec3;
      const wall = firstHit(projectile.position, delta, this.walls, [1, 1, 1]);
      for (const actor of this.population.actors.filter(item => item.alive && !projectile.hitIds.has(item.id))) {
        const hit = sweep(projectile.position, delta, actor, [projectile.radius, projectile.radius, projectile.radius]);
        // A projectile can start within an expanded target. Account for that explicitly.
        const inside = projectile.position.every((value, axis) => value >= actor.min[axis] - projectile.radius && value <= actor.max[axis] + projectile.radius);
        const time = inside ? 0 : hit?.time;
        if (time === undefined || (wall && time >= wall.time)) continue;
        const center: Vec3 = [(actor.min[0] + actor.max[0]) / 2, (actor.min[1] + actor.max[1]) / 2, (actor.min[2] + actor.max[2]) / 2];
        const obstructed = firstHit(projectile.position, center.map((value, axis) => value - projectile.position[axis]) as Vec3, this.walls);
        if (obstructed && obstructed.time < 0.99) continue;
        projectile.hitIds.add(actor.id);
        this.strike(actor.id, { kind: 'ranged', strong: projectile.strong, damage: FREE_RULES.rangedDamage, direction: projectile.direction }, center);
      }
      projectile.position = projectile.position.map((value, axis) => value + delta[axis] * (wall?.time ?? 1)) as Vec3;
      projectile.mesh.position.copyFromFloats(...projectile.position);
      projectile.mesh.setEnabled(projectile.age < 3.5);
      if (wall || projectile.age >= 4) { if (wall) this.effects.impact(projectile.position); projectile.mesh.dispose(); this.projectiles.splice(i, 1); }
    }
  }
  pause(): void { this.heatActive = false; this.heatTarget = ''; this.heatTick = 0; this.effects.heat(null); }
  reset(): void { this.pause(); this.timeline = null; this.queued = null; this.combo = this.rangedCombo = this.destroyed = this.hits = 0; this.character.endAction(); this.projectiles.forEach(projectile => projectile.mesh.dispose()); this.projectiles.length = 0; this.effects.reset(); }
  dispose(): void { this.reset(); this.effects.dispose(); }
}
