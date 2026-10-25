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

const CLIPS: Record<MotionState, string> = { idle: 'Hero_Idle', run: 'Hero_SprintRun', jump: 'Hero_JumpFall', hover: 'Hero_IdleFlying', fly: 'Hero_FlyFastSprint' };
interface RetargetClip {
  duration: number;
  times: number[];
  root: { positions: number[][] };
  bones: Record<string, number[][]>;
}
interface RetargetFile { fps: number; clips: Record<string, RetargetClip> }

const normalizeBone = (name: string) => name.replace(/[^a-z0-9]/gi, '').toLowerCase();

export interface MotionSource { position: Vec3; velocity: Vec3; heading: number; state: MotionState }
export class Character {
  readonly root: TransformNode;
  private container!: AssetContainer;
  private animations: AnimationGroup[] = [];
  private aliases = new Map<string, string>();
  private clip = '';
  private yaw = Math.PI;
  private action = '';
  constructor(readonly scene: Scene) { this.root = new TransformNode('player-visual', scene); this.root.scaling.setAll(1.05); }

  async load(shadows?: ShadowGenerator, skin: 'original' | 'homelander' = 'original'): Promise<void> {
    const url = skin === 'homelander' ? '/assets/character/homelander.glb' : '/assets/character/hero.gltf';
    this.container = await LoadAssetContainerAsync(url, this.scene);
    this.container.addAllToScene();
    this.container.animationGroups.forEach(group => group.stop());
    this.container.skeletons.forEach(skeleton => skeleton.returnToRest());
    this.container.rootNodes.forEach(node => { node.parent = this.root; });
    this.container.meshes.filter(mesh => mesh.getTotalVertices() > 0).forEach(mesh => {
      mesh.isPickable = false;
      shadows?.addShadowCaster(mesh);
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

  update(motor: MotionSource, dt: number): void {
    this.root.position.copyFromFloats(...motor.position);
    this.root.position.y += 0.026;
    const difference = Math.atan2(Math.sin(motor.heading - this.yaw), Math.cos(motor.heading - this.yaw));
    this.yaw += difference * Math.min(1, dt * 12);
    this.root.rotation.y = this.yaw;
    if (this.action) return;
    const clip = CLIPS[motor.state];
    if (clip !== this.clip) {
      this.animations.forEach(group => group.stop());
      this.container.skeletons.forEach(skeleton => skeleton.returnToRest());
      this.groupFor(clip)?.start(true);
      this.clip = clip;
    }
    const group = this.groupFor(clip);
    if (group) group.speedRatio = motor.state === 'run' ? Math.max(0.7, Math.min(2.2, Math.hypot(motor.velocity[0], motor.velocity[2]) / 6)) : 1;
  }

  pause(paused: boolean): void {
    const group = this.groupFor(this.clip);
    if (paused) group?.pause(); else group?.play(!this.action);
  }

  playAction(name: string, speed: number): void {
    const group = this.groupFor(name);
    if (!group) throw new Error(`原版动作缺失: ${name}`);
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

  dispose(): void { this.animations.forEach(group => group.dispose()); this.animations = []; this.container?.dispose(); this.root.dispose(); }
}
