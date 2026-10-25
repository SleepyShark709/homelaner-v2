import { Scene } from '@babylonjs/core/scene';
import { TransformNode } from '@babylonjs/core/Meshes/transformNode';
import { Animation } from '@babylonjs/core/Animations/animation';
import { AnimationGroup } from '@babylonjs/core/Animations/animationGroup';
import { Quaternion, Vector3 } from '@babylonjs/core/Maths/math.vector';
import { LoadAssetContainerAsync } from '@babylonjs/core/Loading/sceneLoader';
import type { AssetContainer } from '@babylonjs/core/assetContainer';
import type { ShadowGenerator } from '@babylonjs/core/Lights/Shadows/shadowGenerator';
import type { MotionState } from './PlayerMotor';
import type { Vec3 } from './collision';

const CLIPS: Record<MotionState, string> = { idle: 'Hero_Idle', run: 'Hero_SprintRun', jump: 'Hero_JumpFall', hover: 'Hero_IdleFlying', fly: 'Hero_FlyForward' };
// Absolute source-time notify events decoded from the AnimSequences.
const FOOTSTEP_TIMES: Record<string, number[]> = {
  Hero_Walk: [0.332, 0.826],
  Hero_SprintRun: [0.264, 0.556],
  Hero_SprintSuper: [0.263, 0.550],
  Hero_Stopping_WalkRun: [0.463, 0.935],
  Hero_Stopping_Sprint: [0.948, 1.207],
  Hero_JumpLand: [0.067],
  Hero_JumpSpeed: [0.107],
  ALS_N_Walk_B: [0.036, 0.482],
  ALS_N_Walk_FL: [0.036, 0.482],
  ALS_N_Walk_FR: [0.036, 0.482],
  ALS_N_Run_B: [0.123, 0.379],
  ALS_N_Run_FL: [0.123, 0.379],
  ALS_N_Run_FR: [0.123, 0.379],
};
interface RetargetClip {
  duration: number;
  times: number[];
  root: { positions: number[][] };
  bones: Record<string, number[][]>;
}
interface RetargetFile { fps: number; clips: Record<string, RetargetClip> }

const normalizeBone = (name: string) => name.replace(/[^a-z0-9]/gi, '').toLowerCase();

export interface MotionSource { position: Vec3; velocity: Vec3; heading: number; state: MotionState; sprint?: boolean }
interface Crossfade {
  elapsed: number;
  duration: number;
  from: Map<AnimationGroup, number>;
  to: Map<AnimationGroup, number>;
}
export class Character {
  readonly root: TransformNode;
  private container!: AssetContainer;
  private animations: AnimationGroup[] = [];
  private aliases = new Map<string, string>();
  private clip = '';
  private yaw = Math.PI;
  private action = '';
  private transition: { name: string; remaining: number; next: string; holdUntilFall?: boolean; nextFade?: number } | null = null;
  private fade: Crossfade | null = null;
  private wasGrounded = true;
  private wasSprinting = false;
  private footstepLast = new Map<string, number>();
  onFootstep: ((clip: string) => void) | undefined;
  constructor(readonly scene: Scene) {
    this.root = new TransformNode('player-visual', scene);
    this.root.scaling.setAll(1.05);
    this.scene.onBeforeRenderObservable.add(() => {
      this.tickCrossfade(Math.min(this.scene.getEngine().getDeltaTime() / 1000, 0.05));
      this.emitFootsteps();
    });
  }

  async load(shadows?: ShadowGenerator, skin: 'original' | 'homelander' = 'original'): Promise<void> {
    const url = skin === 'homelander' ? '/assets/character/homelander.glb' : '/assets/character/hero.gltf';
    this.container = await LoadAssetContainerAsync(url, this.scene);
    this.container.addAllToScene();
    this.container.animationGroups.forEach(group => group.stop());
    this.container.skeletons.forEach(skeleton => skeleton.returnToRest());
    this.container.rootNodes.forEach(node => { node.parent = this.root; });
    this.container.meshes.filter(mesh => mesh.getTotalVertices() > 0).forEach(mesh => {
      mesh.isPickable = false;
      // Skinned characters animate outside their rest-pose bounding box; Babylon
      // can cull the whole skinned mesh for a frame when the stale bounds leave
      // the frustum. Keep the hero active every frame to remove the visible
      // one-frame flicker/disappearance.
      mesh.alwaysSelectAsActiveMesh = true;
      // Do not enable receiveShadows on the skinned hero yet: the preview
      // 1024px shadow map has no character-specific bias/normalBias, so
      // self-shadow acne flickers across the body while running/attacking.
      // The hero still casts a stable shadow onto the world.
      shadows?.addShadowCaster(mesh);
      // M_ShadowTrim and the glasses are decorative coplanar overlays. Without
      // a polygon offset they z-fight against the body/lens at grazing angles,
      // which shows up as local flicker while running or after an attack.
      const material = mesh.material;
      if (material && /ShadowTrim|Sunglasses|GlassLens/i.test(material.name)) {
        material.zOffset = -1;
        material.zOffsetUnits = -1;
      }
    });
    if (skin === 'homelander') {
      await this.loadRetargetedAnimations();
    } else {
      this.animations = this.container.animationGroups;
      for (const group of this.animations) {
        for (const animation of group.targetedAnimations) {
          animation.animation.enableBlending = true;
          animation.animation.blendingSpeed = 0.15;
        }
      }
    }
  }

  /**
   * The Homelander GLB has its own rig but we deliberately do not use its
   * clips. homelander-retarget.json contains UNDEFEATED's original clips,
   * resampled onto the Homelander bones from the original rest-pose deltas.
   */
  private async loadRetargetedAnimations(): Promise<void> {
    const useRetarget = new URLSearchParams(location.search).get('retarget') === '1';
    if (!useRetarget) {
      // The Homelander GLB ships its own authored idle/walk/jog/sprint/fly/
      // punch/combo clips. They are mapped onto the original action names so
      // the gameplay state machine and right-button attack flow stay intact.
      // This avoids the arm deformation produced by retargeting the original
      // rig's very different rest pose onto this mesh.
      const aliases: Record<string, string> = {
        Hero_Idle: 'idle', Hero_IdleFlying: 'hover', Hero_FlyFastSprint: 'fly', A_ThirdPersonRun: 'jog',
        Hero_Attack1: 'punch', Hero_Attack2: 'combo_a', Hero_Attack3: 'combo_b', Hero_Attack4: 'casual_attack',
        Hero_LongFistForce_L: 'punch', Hero_LongFistForce_R: 'punch', Hero_BackHandSlash_New: 'combo_b',
        Hero_FlashKick: 'casual_attack', Hero_Smash_A: 'slam', Hero_SuperPunch: 'punch',
        Hero_AirKick_L: 'combo_a', Hero_AirKick_R: 'combo_b', Hero_AirSuperKick: 'slam', Hero_AirAttackStart: 'casual_attack',
      };
      this.animations = this.container.animationGroups;
      this.aliases = new Map(Object.entries(aliases));
      return;
    }
    // Experimental rest-relative retarget of the original clips. Kept behind
    // ?retarget=1 because the Homelander rest pose differs enough that the
    // arm chain deforms under locomotion.
    this.container.skeletons.forEach(skeleton => skeleton.bones.forEach(bone => bone.linkTransformNode(null)));
    const data = await fetch('/assets/character/homelander-retarget.json').then(response => {
      if (!response.ok) throw new Error(`Homelander retarget clips unavailable: ${response.status}`);
      return response.json() as Promise<RetargetFile>;
    });
    const skeleton = this.container.skeletons[0];
    if (!skeleton) throw new Error('Homelander skeleton missing');
    const bones = new Map(skeleton.bones.map(bone => [normalizeBone(bone.name), bone]));
    const rootBone = bones.get(normalizeBone('root.x'));
    const groups: AnimationGroup[] = [];
    for (const [name, clip] of Object.entries(data.clips)) {
      const group = new AnimationGroup(name, this.scene);
      for (const [boneName, rotations] of Object.entries(clip.bones)) {
        if (/twist/i.test(boneName)) continue;
        const bone = bones.get(normalizeBone(boneName));
        if (!bone) continue;
        const animation = new Animation(`${name}:${boneName}`, 'rotation', data.fps, Animation.ANIMATIONTYPE_VECTOR3, Animation.ANIMATIONLOOPMODE_CYCLE);
        animation.setKeys(clip.times.map((time, index) => {
          const value = rotations[index] ?? rotations[rotations.length - 1] ?? [0, 0, 0, 1];
          return { frame: time * data.fps, value: new Quaternion(value[0], value[1], value[2], value[3]).toEulerAngles() };
        }));
        animation.enableBlending = true;
        animation.blendingSpeed = 0.15;
        group.addTargetedAnimation(animation, bone);
      }
      if (rootBone && clip.root?.positions?.length) {
        const animation = new Animation(`${name}:root.position`, 'position', data.fps, Animation.ANIMATIONTYPE_VECTOR3, Animation.ANIMATIONLOOPMODE_CYCLE);
        animation.setKeys(clip.times.map((time, index) => {
          const value = clip.root.positions[index] ?? clip.root.positions[clip.root.positions.length - 1] ?? [0, 0, 0];
          return { frame: time * data.fps, value: new Vector3(value[0], value[1], value[2]) };
        }));
        group.addTargetedAnimation(animation, rootBone);
      }
      group.from = 0;
      group.to = clip.duration * data.fps;
      groups.push(group);
    }
    if (!groups.length) throw new Error('Homelander retarget produced no clips');
    // The GLB's own idle/walk/etc. clips are discarded; the original clips win.
    this.container.animationGroups.forEach(group => { group.stop(); group.dispose(); });
    this.container.animationGroups.length = 0;
    this.animations = groups;
  }

  private groupFor(name: string): AnimationGroup | undefined {
    return this.animations.find(group => group.name === (this.aliases.get(name) ?? name));
  }

  /** Normalized 0..1 phase of the current dominant clip, used to start a
   * newly activated blend sample at the same gait phase instead of frame 0. */
  private currentPhase(): number {
    const group = this.groupFor(this.clip);
    const animatable = group?.animatables[0];
    if (!group || !animatable) return 0;
    const span = group.to - group.from;
    if (span <= 0) return 0;
    const frame = ((animatable.masterFrame - group.from) % span + span) % span;
    return frame / span;
  }

  private startAtPhase(group: AnimationGroup, ratio: number, phase: number): void {
    const span = group.to - group.from;
    group.start(true, ratio, group.from + Math.max(0, Math.min(0.999, phase)) * span);
  }

  private setFlyBlend(vertical: number, planar: number, velocityX: number, velocityZ: number): void {
    if (this.fade) return;
    // HeroABS_FlyingUpDonwAnim samples: FlyUp +2666, FastUp +6000,
    // FlyDown -1333/-3333, Tame -4000, FastDown -4666, BulletDive -6000 cm/s.
    if (vertical > 35) { this.setLoop('Hero_FlyFastUp'); return; }
    if (vertical > 13) { this.setLoop('Hero_FlyUp'); return; }
    if (vertical < -45) { this.setLoop('Hero_FlyBulletDive'); return; }
    if (vertical < -35) { this.setLoop('Hero_FlyFastDown'); return; }
    if (vertical < -13) { this.setLoop('Hero_FlyDown'); return; }
    if (planar <= 1) { this.setLoop('Hero_IdleFlying'); return; }
    const idleFlying = this.groupFor('Hero_IdleFlying');
    const low = this.groupFor('Hero_FlyForwardLow');
    const mid = this.groupFor('Hero_FlyForward');
    const fast = this.groupFor('Hero_FlyFastForward1');
    const left = this.groupFor('Hero_FlyLeft');
    const right = this.groupFor('Hero_FlyRight');
    const back = this.groupFor('Hero_FlyBack');
    if (!idleFlying || !low || !mid || !fast || !left || !right || !back) { this.setLoop('Hero_FlyForward'); return; }
    // HeroABS_FlyingMoveAnim samples: Y speed 0/1200/3000/4200/6000 cm/s.
    const speed = planar * 100;
    const forwardWeights = speed <= 0
      ? { idle: 1, low: 0, mid: 0, fast: 0 }
      : speed < 1200
        ? { idle: 1 - speed / 1200, low: speed / 1200, mid: 0, fast: 0 }
        : speed < 3000
          ? { idle: 0, low: 1 - (speed - 1200) / 1800, mid: (speed - 1200) / 1800, fast: 0 }
          : speed < 4200
            ? { idle: 0, low: 0, mid: 1, fast: 0 }
            : speed < 6000
              ? { idle: 0, low: 0, mid: 1 - (speed - 4200) / 1800, fast: (speed - 4200) / 1800 }
              : { idle: 0, low: 0, mid: 0, fast: 1 };
    const sin = Math.sin(this.yaw), cos = Math.cos(this.yaw);
    const localForward = velocityX * sin + velocityZ * cos;
    const localRight = velocityX * cos - velocityZ * sin;
    const angle = Math.atan2(-localRight, localForward) * 180 / Math.PI;
    const a = Math.abs(angle);
    // Side samples sit at +/-108 degrees, not +/-90.
    const direction = a <= 108
      ? angle >= 0
        ? { F: (108 - a) / 108, L: 0, R: a / 108, B: 0 }
        : { F: (108 - a) / 108, L: a / 108, R: 0, B: 0 }
      : angle >= 0
        ? { F: 0, L: 0, R: (180 - a) / 72, B: (a - 108) / 72 }
        : { F: 0, L: (180 - a) / 72, R: 0, B: (a - 108) / 72 };
    const combined: Array<[AnimationGroup, number, number]> = [
      [idleFlying, forwardWeights.idle * direction.F, 1],
      [low, forwardWeights.low * direction.F, Math.max(0.7, Math.min(1.4, speed / 1200))],
      [mid, forwardWeights.mid * direction.F, Math.max(0.7, Math.min(1.4, speed / 3000))],
      [fast, forwardWeights.fast * direction.F, Math.max(0.8, Math.min(1.5, speed / 6000))],
      [left, direction.L, Math.max(0.7, Math.min(1.4, speed / 3000))],
      [right, direction.R, Math.max(0.7, Math.min(1.4, speed / 3000))],
      [back, direction.B, Math.max(0.7, Math.min(1.4, speed / 3000))],
    ];
    const total = combined.reduce((sum, [, weight]) => sum + weight, 0);
    const phase = this.currentPhase();
    const active = new Set(combined.map(([group]) => group));
    this.animations.forEach(group => { if (!active.has(group)) group.stop(); });
    let dominant = 'Hero_FlyForward', dominantWeight = -1;
    for (const [group, weight, ratio] of combined) {
      const normalized = total > 0 ? weight / total : 0;
      if (normalized <= 0.001) {
        if (group.isPlaying) group.stop();
        group.weight = 0;
        group.setWeightForAllAnimatables(0);
        continue;
      }
      if (!group.isPlaying) this.startAtPhase(group, ratio, phase);
      group.weight = normalized;
      group.setWeightForAllAnimatables(normalized);
      group.speedRatio = ratio;
      if (normalized > dominantWeight) { dominantWeight = normalized; dominant = group.name; }
    }
    this.transition = null;
    this.action = '';
    this.clip = dominant;
  }

  private beginCrossfade(to: Map<AnimationGroup, number>, duration: number): void {
    const from = new Map<AnimationGroup, number>();
    for (const group of this.animations) {
      if (group.isPlaying && group.weight > 0.001) from.set(group, group.weight);
    }
    for (const group of to.keys()) {
      if (!group.isPlaying) group.start(true);
      group.weight = 0;
      group.setWeightForAllAnimatables(0);
    }
    this.fade = { elapsed: 0, duration: Math.max(0.01, duration), from, to };
  }

  private tickCrossfade(dt: number): void {
    const fade = this.fade;
    if (!fade) return;
    fade.elapsed += dt;
    const t = Math.min(1, fade.elapsed / fade.duration);
    const eased = t * t * (3 - 2 * t);
    const groups = new Set<AnimationGroup>([...fade.from.keys(), ...fade.to.keys()]);
    for (const group of groups) {
      const from = fade.from.get(group) ?? 0;
      const to = fade.to.get(group) ?? 0;
      const weight = from + (to - from) * eased;
      if (!group.isPlaying && weight > 0.001) group.start(true);
      group.weight = weight;
      group.setWeightForAllAnimatables(weight);
    }
    if (t >= 1) {
      for (const group of this.animations) {
        if (!fade.to.has(group)) group.stop();
      }
      for (const [group, weight] of fade.to) {
        group.weight = weight;
        group.setWeightForAllAnimatables(weight);
      }
      this.fade = null;
    }
  }

  private setLoop(name: string, fadeSeconds = 0.2): void {
    const group = this.groupFor(name);
    if (!group) return;
    if (this.clip === name && group.isPlaying && !this.fade) { this.transition = null; return; }
    group.start(true);
    this.beginCrossfade(new Map([[group, 1]]), fadeSeconds);
    this.transition = null;
    this.action = '';
    this.clip = name;
  }

  /**
   * 2D speed/direction subset of HeroABS_MoveGround. The recovered ALS
   * Walk/Run B/FL/FR samples are blended with the forward Hero clips; the real
   * axis values, sample positions and AnimBP transition rules are still open.
   */
  private setGroundBlend(speed: number, velocityX: number, velocityZ: number): void {
    if (this.fade) return;
    const names = {
      idle: 'Hero_Idle',
      walkF: 'Hero_Walk', walkFL: 'ALS_N_Walk_FL', walkFR: 'ALS_N_Walk_FR', walkB: 'ALS_N_Walk_B',
      runF: 'Hero_SprintRun', superF: 'Hero_SprintSuper', runFL: 'ALS_N_Run_FL', runFR: 'ALS_N_Run_FR', runB: 'ALS_N_Run_B',
    } as const;
    const groups = Object.fromEntries(Object.entries(names).map(([key, name]) => [key, this.groupFor(name)])) as Record<keyof typeof names, AnimationGroup | undefined>;
    const idle = groups.idle, walkF = groups.walkF, runF = groups.runF;
    if (!idle || !walkF || !runF) return;
    const speedWeights = speed <= 3
      ? { idle: Math.max(0, 1 - (speed - 0.15) / 2.85), walk: Math.min(1, Math.max(0, (speed - 0.15) / 2.85)), run: 0, super: 0 }
      : speed < 8.5
        ? { idle: 0, walk: 1 - (speed - 3) / 5.5, run: (speed - 3) / 5.5, super: 0 }
        : speed < 16.75
          ? { idle: 0, walk: 0, run: 1 - (speed - 8.5) / 8.25, super: (speed - 8.5) / 8.25 }
          : { idle: 0, walk: 0, run: 0, super: 1 };
    let dir = { F: 1, FL: 0, FR: 0, B: 0 };
    if (speed > 0.15) {
      const sin = Math.sin(this.yaw), cos = Math.cos(this.yaw);
      const localForward = velocityX * sin + velocityZ * cos;
      const localRight = velocityX * cos - velocityZ * sin;
      const angle = Math.atan2(-localRight, localForward) * 180 / Math.PI;
      const a = Math.abs(angle);
      if (a <= 90) {
        dir = angle >= 0
          ? { F: (90 - a) / 90, FL: 0, FR: a / 90, B: 0 }
          : { F: (90 - a) / 90, FL: a / 90, FR: 0, B: 0 };
      } else {
        dir = angle >= 0
          ? { F: 0, FL: 0, FR: (180 - a) / 90, B: (a - 90) / 90 }
          : { F: 0, FL: (180 - a) / 90, FR: 0, B: (a - 90) / 90 };
      }
    }
    const combined: Array<[AnimationGroup | undefined, number, number]> = [
      [idle, speedWeights.idle, 1],
      [groups.walkF, speedWeights.walk * dir.F, Math.max(0.6, Math.min(1.5, speed / 3))],
      [groups.walkFL, speedWeights.walk * dir.FL, Math.max(0.6, Math.min(1.5, speed / 3))],
      [groups.walkFR, speedWeights.walk * dir.FR, Math.max(0.6, Math.min(1.5, speed / 3))],
      [groups.walkB, speedWeights.walk * dir.B, Math.max(0.6, Math.min(1.5, speed / 3))],
      [groups.runF, speedWeights.run * dir.F, Math.max(0.7, Math.min(2.2, speed / 8.5))],
      [groups.superF, speedWeights.super * dir.F, Math.max(0.8, Math.min(1.5, speed / 22.25))],
      [groups.runFL, (speedWeights.run + speedWeights.super) * dir.FL, Math.max(0.7, Math.min(2.2, speed / 8.5))],
      [groups.runFR, (speedWeights.run + speedWeights.super) * dir.FR, Math.max(0.7, Math.min(2.2, speed / 8.5))],
      [groups.runB, (speedWeights.run + speedWeights.super) * dir.B, Math.max(0.7, Math.min(2.2, speed / 8.5))],
    ];
    const total = combined.reduce((sum, [, weight]) => sum + weight, 0);
    const phase = this.currentPhase();
    let dominant = 'Hero_Idle', dominantWeight = -1;
    const ground = new Set(combined.map(([group]) => group).filter((group): group is AnimationGroup => !!group));
    this.animations.forEach(group => { if (!ground.has(group)) group.stop(); });
    for (const [group, weight, ratio] of combined) {
      if (!group) continue;
      const normalized = total > 0 ? weight / total : 0;
      if (normalized <= 0.001) {
        if (group.isPlaying) group.stop();
        group.weight = 0;
        group.setWeightForAllAnimatables(0);
        continue;
      }
      if (!group.isPlaying) this.startAtPhase(group, ratio, phase);
      group.weight = normalized;
      group.setWeightForAllAnimatables(normalized);
      group.speedRatio = ratio;
      if (normalized > dominantWeight) { dominantWeight = normalized; dominant = group.name; }
    }
    this.transition = null;
    this.action = '';
    this.clip = dominant;
  }

  private setOneShot(name: string, next: string, entryFade = 0.2, nextFade = 0.2): void {
    const group = this.groupFor(name);
    if (!group) { this.setLoop(next); return; }
    group.start(false);
    this.beginCrossfade(new Map([[group, 1]]), entryFade);
    this.action = '';
    this.clip = name;
    this.transition = { name, remaining: Math.max(0.05, group.getLength()), next, nextFade };
  }

  update(motor: MotionSource, dt: number): void {
    this.root.position.copyFromFloats(...motor.position);
    this.root.position.y += 0.026;
    const difference = Math.atan2(Math.sin(motor.heading - this.yaw), Math.cos(motor.heading - this.yaw));
    this.yaw += difference * Math.min(1, dt * 12);
    this.root.rotation.y = this.yaw;
    const grounded = motor.state === 'idle' || motor.state === 'run';
    const planarSpeed = Math.hypot(motor.velocity[0], motor.velocity[2]);
    const wasSprinting = this.wasSprinting;
    this.wasSprinting = motor.sprint === true;
    const landed = !this.wasGrounded && grounded;
    const tookOff = this.wasGrounded && !grounded;
    this.wasGrounded = grounded;
    if (this.action) return;
    if (landed) {
      const next = planarSpeed < 0.2 ? 'Hero_Idle' : planarSpeed < 4 ? 'Hero_Walk' : 'Hero_SprintRun';
      // Recovered Falling/Landing chain: entry ~0.1 s, Landing->Ground 0.25 s.
      this.setOneShot('Hero_JumpLand', next, 0.1, 0.25);
      return;
    }
    if (this.transition) {
      this.transition.remaining -= dt;
      if (this.transition.remaining > 0) return;
      if (this.transition.holdUntilFall && !grounded) {
        if (motor.state === 'hover' || motor.state === 'fly') {
          this.transition = null;
          return;
        }
        if (motor.velocity[1] > 0.2) {
          // Hold the last JumpSpeed frame through the ascent; the fall loop
          // must not start while the player is still moving upward.
          const group = this.groupFor(this.transition.name);
          if (group) {
            group.goToFrame(group.to);
            group.pause();
          }
          this.transition.remaining = 0.1;
          return;
        }
      }
      const next = this.transition.next;
      const nextFade = this.transition.nextFade ?? 0.2;
      this.transition = null;
      this.setLoop(next, nextFade);
      return;
    }
    if (tookOff && motor.state === 'jump') {
      // Walk/standing takeoff uses the ALS jump sample; running takeoff keeps
      // the game-specific Hero_JumpSpeed sample.
      this.setOneShot(planarSpeed < 4 ? 'ALS_N_Jump' : 'Hero_JumpSpeed', 'Hero_JumpFall', 0.2, 0.55);
      const created = this.transition as { holdUntilFall?: boolean } | null;
      if (created) created.holdUntilFall = true;
      return;
    }
    if (!grounded) {
      const vertical = motor.velocity[1];
      let desired: string;
      if (motor.state === 'jump') {
        // HeroABS_JumpFallLoop has a low-air fast sample and a slower fall
        // JumpFallLoop samples put JumpFallFast at the high-speed -5000 cm/s
        // band, while a normal ~9 m/s jump fall belongs to JumpFall.
        desired = vertical < -35 ? 'Hero_JumpFallFast' : 'Hero_JumpFall';
      } else if (motor.state === 'hover' || motor.state === 'fly') {
        this.setFlyBlend(vertical, planarSpeed, motor.velocity[0], motor.velocity[2]);
        return;
      } else {
        desired = CLIPS[motor.state];
      }
      if (this.clip !== desired) this.setLoop(desired);
      const group = this.groupFor(desired);
      if (group) group.speedRatio = 1;
      return;
    }
    const desired = planarSpeed < 0.15 ? 'Hero_Idle' : planarSpeed < 4 ? 'Hero_Walk' : 'Hero_SprintRun';
    const walkLike = this.clip === 'Hero_Walk' || this.clip.startsWith('ALS_N_Walk');
    const runLike = this.clip === 'Hero_SprintRun' || this.clip.startsWith('ALS_N_Run');
    if (!wasSprinting && motor.sprint === true && runLike && planarSpeed < 25) {
      // Shift pressed while already running: re-enter the recovered StartSprint
      // state instead of silently raising the speed ceiling.
      this.setOneShot('Hero_StartSprint', 'Hero_SprintRun');
      return;
    }
    if (this.clip !== desired) {
      if (desired === 'Hero_SprintRun' && (this.clip === 'Hero_Idle' || walkLike)) {
        if (motor.sprint === true) this.setOneShot('Hero_StartSprint', desired);
        else this.setGroundBlend(planarSpeed, motor.velocity[0], motor.velocity[2]);
      } else if ((desired === 'Hero_Idle' || desired === 'Hero_Walk') && runLike) {
        const exitFade = wasSprinting && desired === 'Hero_Idle' ? 0.25 : 0.2;
        this.setOneShot(wasSprinting ? 'Hero_Stopping_Sprint' : 'Hero_Stopping_WalkRun', desired, 0.2, exitFade);
      } else if (desired === 'Hero_Idle' && this.clip === 'Hero_Walk') {
        this.setOneShot('Hero_Stopping_WalkRun', desired);
      } else {
        this.setGroundBlend(planarSpeed, motor.velocity[0], motor.velocity[2]);
      }
      return;
    }
    this.setGroundBlend(planarSpeed, motor.velocity[0], motor.velocity[2]);
  }

  pause(paused: boolean): void {
    const group = this.groupFor(this.clip);
    if (paused) group?.pause(); else group?.play(!this.action);
  }

  playAction(name: string, speed: number): void {
    const group = this.groupFor(name);
    if (!group) throw new Error(`閸樼喓澧楅崝銊ょ稊缂傚搫銇? ${name}`);
    this.animations.forEach(item => item.stop());
    this.container.skeletons.forEach(skeleton => skeleton.returnToRest());
    this.action = name; this.clip = name; group.start(false, speed);
  }

  endAction(): void { this.action = ''; this.clip = ''; }

  eyes(): Vec3[] {
    const head = this.container.transformNodes.find(node => normalizeBone(node.name) === normalizeBone('head') || normalizeBone(node.name) === normalizeBone('head.x'));
    const position = head?.getAbsolutePosition();
    const x = position?.x ?? this.root.position.x, y = (position?.y ?? this.root.position.y + 1.55) + 0.10, z = position?.z ?? this.root.position.z;
    const sin = Math.sin(this.yaw), cos = Math.cos(this.yaw);
    return [-0.032, 0.032].map(side => [x + sin * 0.12 + cos * side, y, z + cos * 0.12 - sin * side] as Vec3);
  }

  private emitFootsteps(): void {
    if (!this.onFootstep || !this.clip) return;
    const times = FOOTSTEP_TIMES[this.clip];
    if (!times) return;
    const group = this.animations.find(item => item.name === this.clip);
    const animation = group?.targetedAnimations[0]?.animation;
    const animatable = group?.animatables[0];
    if (!group?.isPlaying || !animation || !animatable || (group.weight ?? 1) < 0.2) return;
    const fps = animation.framePerSecond || 30;
    const time = animatable.masterFrame / fps;
    let last = this.footstepLast.get(this.clip) ?? 0;
    if (time + 0.05 < last) last = 0;
    for (const notify of times) {
      if (notify > last && notify <= time) this.onFootstep(this.clip);
    }
    this.footstepLast.set(this.clip, time);
  }

  dispose(): void { this.animations.forEach(group => group.dispose()); this.animations = []; this.container?.dispose(); this.root.dispose(); }
}



