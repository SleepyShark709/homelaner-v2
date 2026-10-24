import { Scene } from '@babylonjs/core/scene';
import { TransformNode } from '@babylonjs/core/Meshes/transformNode';
import { LoadAssetContainerAsync } from '@babylonjs/core/Loading/sceneLoader';
import type { AssetContainer } from '@babylonjs/core/assetContainer';
import type { ShadowGenerator } from '@babylonjs/core/Lights/Shadows/shadowGenerator';
import type { MotionState, PlayerMotor } from './PlayerMotor';
import type { Vec3 } from './collision';

const CLIPS: Record<MotionState, string> = { idle: 'Hero_Idle', run: 'A_ThirdPersonRun', jump: 'Hero_IdleFlying', hover: 'Hero_IdleFlying', fly: 'Hero_FlyFastSprint' };
export class Character {
  readonly root: TransformNode;
  private container!: AssetContainer;
  private clip = '';
  private yaw = Math.PI;
  private action = '';
  constructor(readonly scene: Scene) { this.root = new TransformNode('player-visual', scene); this.root.scaling.setAll(1.05); }
  async load(shadows: ShadowGenerator): Promise<void> {
    this.container = await LoadAssetContainerAsync('/assets/character/hero.gltf', this.scene);
    this.container.addAllToScene();
    this.container.animationGroups.forEach(group => group.stop());
    this.container.skeletons.forEach(skeleton => skeleton.returnToRest());
    this.container.rootNodes.forEach(node => { node.parent = this.root; });
    this.container.meshes.filter(mesh => mesh.getTotalVertices() > 0).forEach(mesh => { mesh.isPickable = false; shadows.addShadowCaster(mesh); });
    for (const group of this.container.animationGroups) {
      for (const animation of group.targetedAnimations) {
        animation.animation.enableBlending = true;
        animation.animation.blendingSpeed = 0.15;
      }
    }
  }
  update(motor: PlayerMotor, dt: number): void {
    this.root.position.copyFromFloats(...motor.position);
    this.root.position.y += 0.026;
    const difference = Math.atan2(Math.sin(motor.heading - this.yaw), Math.cos(motor.heading - this.yaw));
    this.yaw += difference * Math.min(1, dt * 12);
    this.root.rotation.y = this.yaw;
    if (this.action) return;
    const clip = CLIPS[motor.state];
    if (clip !== this.clip) {
      this.container.animationGroups.forEach(group => group.stop());
      this.container.skeletons.forEach(skeleton => skeleton.returnToRest());
      this.container.animationGroups.find(group => group.name === clip)?.start(true);
      this.clip = clip;
    }
    const group = this.container.animationGroups.find(group => group.name === clip);
    if (group) group.speedRatio = motor.state === 'run' ? Math.max(0.7, Math.min(2.2, Math.hypot(motor.velocity[0], motor.velocity[2]) / 6)) : 1;
  }
  pause(paused: boolean): void {
    const group = this.container?.animationGroups.find(group => group.name === this.clip);
    if (paused) group?.pause(); else group?.play(!this.action);
  }
  playAction(name: string, speed: number): void {
    const group = this.container.animationGroups.find(item => item.name === name);
    if (!group) throw new Error(`原版动作缺失: ${name}`);
    this.container.animationGroups.forEach(item => item.stop());
    this.container.skeletons.forEach(skeleton => skeleton.returnToRest());
    this.action = name; this.clip = name; group.start(false, speed);
  }
  endAction(): void { this.action = ''; this.clip = ''; }
  eyes(): Vec3[] {
    const head = this.container.transformNodes.find(node => node.name === 'head');
    const position = head?.getAbsolutePosition();
    const x = position?.x ?? this.root.position.x, y = (position?.y ?? this.root.position.y + 1.55) + 0.10, z = position?.z ?? this.root.position.z;
    const sin = Math.sin(this.yaw), cos = Math.cos(this.yaw);
    return [-0.032, 0.032].map(side => [x + sin * 0.12 + cos * side, y, z + cos * 0.12 - sin * side] as Vec3);
  }
  dispose(): void { this.container?.dispose(); this.root.dispose(); }
}
