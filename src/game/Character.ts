import { Scene } from '@babylonjs/core/scene';
import { TransformNode } from '@babylonjs/core/Meshes/transformNode';
import { Mesh } from '@babylonjs/core/Meshes/mesh';
import { VertexData } from '@babylonjs/core/Meshes/mesh.vertexData';
import { CreatePlane } from '@babylonjs/core/Meshes/Builders/planeBuilder';
import { StandardMaterial } from '@babylonjs/core/Materials/standardMaterial';
import { Color3 } from '@babylonjs/core/Maths/math.color';
import { LoadAssetContainerAsync } from '@babylonjs/core/Loading/sceneLoader';
import type { AssetContainer } from '@babylonjs/core/assetContainer';
import type { ShadowGenerator } from '@babylonjs/core/Lights/Shadows/shadowGenerator';
import type { MotionState } from './PlayerMotor';
import type { Vec3 } from './collision';

const CLIPS: Record<MotionState, string> = { idle: 'Hero_Idle', run: 'A_ThirdPersonRun', jump: 'Hero_IdleFlying', hover: 'Hero_IdleFlying', fly: 'Hero_FlyFastSprint' };
export interface MotionSource { position: Vec3; velocity: Vec3; heading: number; state: MotionState }
export class Character {
  readonly root: TransformNode;
  private container!: AssetContainer;
  private clip = '';
  private yaw = Math.PI;
  private action = '';
  private extras: Mesh[] = [];
  private cape?: Mesh;
  constructor(readonly scene: Scene) { this.root = new TransformNode('player-visual', scene); this.root.scaling.setAll(1.05); }
  async load(shadows?: ShadowGenerator, skin: 'original' | 'homelander' = 'original'): Promise<void> {
    this.container = await LoadAssetContainerAsync('/assets/character/hero.gltf', this.scene);
    this.container.addAllToScene();
    this.container.animationGroups.forEach(group => group.stop());
    this.container.skeletons.forEach(skeleton => skeleton.returnToRest());
    this.container.rootNodes.forEach(node => { node.parent = this.root; });
    this.container.meshes.filter(mesh => mesh.getTotalVertices() > 0).forEach(mesh => { mesh.isPickable = false; shadows?.addShadowCaster(mesh); });
    if (skin === 'homelander') this.homelanderStyle(shadows);
    for (const group of this.container.animationGroups) {
      for (const animation of group.targetedAnimations) {
        animation.animation.enableBlending = true;
        animation.animation.blendingSpeed = 0.15;
      }
    }
  }
  private homelanderStyle(shadows?: ShadowGenerator): void {
    const recolor = (materialName: string, color: Color3) => {
      for (const mesh of this.container.meshes) {
        if (mesh.material?.name !== materialName) continue;
        const source = mesh.material;
        const material = source.clone(`${source.name}-homelander-${mesh.name}`) as unknown as { albedoColor?: Color3; diffuseColor?: Color3 };
        mesh.material = material as never;
        material.albedoColor?.copyFrom(color);
        material.diffuseColor?.copyFrom(color);
      }
    };
    for (const mesh of this.container.meshes) {
      if (mesh.material?.name !== 'MI_Clothes_Contemporary_AllBlack') continue;
      const color = /primitive4$/.test(mesh.name) ? new Color3(0.62, 0.03, 0.035) : new Color3(0.05, 0.16, 0.46);
      const material = mesh.material.clone(`${mesh.material.name}-homelander-${mesh.name}`) as unknown as { albedoColor?: Color3; diffuseColor?: Color3 };
      mesh.material = material as never;
      material.albedoColor?.copyFrom(color);
      material.diffuseColor?.copyFrom(color);
    }
    recolor('MI_Body_asian', new Color3(0.93, 0.76, 0.64));
    recolor('MI_Hair_Black', new Color3(0.88, 0.68, 0.28));
    for (const mesh of this.container.meshes) {
      if (/sunglasses/i.test(mesh.name)) mesh.setEnabled(false);
    }
    const spine = this.container.transformNodes.find(node => node.name === 'spine_03') ?? this.root;
    const capeMaterial = new StandardMaterial('homelander-cape-mat', this.scene);
    capeMaterial.diffuseColor = new Color3(0.72, 0.035, 0.045);
    capeMaterial.emissiveColor = new Color3(0.12, 0.008, 0.01);
    capeMaterial.backFaceCulling = false;
    const cape = new Mesh('homelander-cape', this.scene);
    const rows = [1.5, 1.05, 0.6, 0.32];
    const widths = [0.36, 0.44, 0.49, 0.52];
    const depths = [-0.16, -0.2, -0.28, -0.24];
    const positions: number[] = [], uvs: number[] = [], indices: number[] = [];
    for (let row = 0; row < rows.length; row++) {
      for (let col = 0; col < 3; col++) {
        positions.push((col - 1) * widths[row], rows[row], depths[row]);
        uvs.push(col / 2, row / (rows.length - 1));
      }
    }
    for (let row = 0; row < rows.length - 1; row++) {
      const base = row * 3, next = base + 3;
      indices.push(base, next, next + 1, base, next + 1, base + 1, base + 1, next + 1, next + 2, base + 1, next + 2, base + 2);
    }
    const normals: number[] = [];
    VertexData.ComputeNormals(positions, indices, normals);
    const vertexData = new VertexData();
    vertexData.positions = positions; vertexData.indices = indices; vertexData.uvs = uvs; vertexData.normals = normals;
    vertexData.applyToMesh(cape);
    cape.material = capeMaterial;
    cape.parent = this.root;
    cape.isPickable = false;
    this.cape = cape;
    shadows?.addShadowCaster(cape);
    this.extras.push(cape);
    const emblemMaterial = new StandardMaterial('homelander-emblem-mat', this.scene);
    emblemMaterial.diffuseColor = new Color3(0.95, 0.72, 0.18);
    emblemMaterial.backFaceCulling = false;
    const emblem = CreatePlane('homelander-emblem', { width: 0.24, height: 0.13, sideOrientation: Mesh.DOUBLESIDE }, this.scene);
    emblem.material = emblemMaterial;
    emblem.parent = spine;
    emblem.position.set(0, 0.22, 0.16);
    emblem.isPickable = false;
    this.extras.push(emblem);
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
  dispose(): void { this.extras.forEach(mesh => mesh.dispose()); this.extras = []; this.container?.dispose(); this.root.dispose(); }
}
