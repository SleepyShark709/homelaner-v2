import { Engine } from '@babylonjs/core/Engines/engine';
import { Scene } from '@babylonjs/core/scene';
import { ArcRotateCamera } from '@babylonjs/core/Cameras/arcRotateCamera';
import { Vector3 } from '@babylonjs/core/Maths/math.vector';
import { Color3, Color4 } from '@babylonjs/core/Maths/math.color';
import { HemisphericLight } from '@babylonjs/core/Lights/hemisphericLight';
import { DirectionalLight } from '@babylonjs/core/Lights/directionalLight';
import { MeshBuilder } from '@babylonjs/core/Meshes/meshBuilder';
import { StandardMaterial } from '@babylonjs/core/Materials/standardMaterial';
import { TransformNode } from '@babylonjs/core/Meshes/transformNode';
import { LoadAssetContainerAsync } from '@babylonjs/core/Loading/sceneLoader';
import { SkeletonViewer } from '@babylonjs/core/Debug/skeletonViewer';
import { registerBuiltInLoaders } from '@babylonjs/loaders/dynamic';
import type { AssetContainer } from '@babylonjs/core/assetContainer';
import type { AnimationGroup } from '@babylonjs/core/Animations/animationGroup';
import type { AbstractMesh } from '@babylonjs/core/Meshes/abstractMesh';
import type { Mesh } from '@babylonjs/core/Meshes/mesh';
import type { AssetEntry, AssetStats } from './types';

registerBuiltInLoaders();

export class AssetLab {
  readonly engine: Engine;
  readonly scene: Scene;
  readonly camera: ArcRotateCamera;
  private container?: AssetContainer;
  private root?: TransformNode;
  private floor?: Mesh;
  private grid?: Mesh;
  private skeletons: SkeletonViewer[] = [];
  private animation?: AnimationGroup;
  private request = 0;
  private radius = 3;
  private center = Vector3.Zero();
  private skeletonEnabled = false;
  private wireframeEnabled = false;
  private autoRotate = false;
  private readonly resize = () => this.engine.resize();

  constructor(canvas: HTMLCanvasElement) {
    this.engine = new Engine(canvas, true, { preserveDrawingBuffer: true, stencil: true });
    this.engine.setHardwareScalingLevel(Math.max(1, window.devicePixelRatio / 1.5));
    this.scene = new Scene(this.engine);
    this.scene.clearColor = Color4.FromHexString('#e6eae5ff');
    this.scene.ambientColor = new Color3(0.18, 0.18, 0.18);
    this.camera = new ArcRotateCamera('inspection-camera', Math.PI / 2.5, 1.25, 5, new Vector3(0, 1, 0), this.scene);
    this.camera.attachControl(canvas, true);
    this.camera.lowerBetaLimit = 0.08;
    this.camera.upperBetaLimit = Math.PI / 2 + 0.08;
    this.camera.wheelDeltaPercentage = 0.01;
    this.camera.pinchDeltaPercentage = 0.01;
    this.camera.minZ = 0.01;
    const fill = new HemisphericLight('sky-fill', new Vector3(0, 1, 0), this.scene);
    fill.intensity = 1.45;
    fill.groundColor = new Color3(0.46, 0.49, 0.47);
    const key = new DirectionalLight('key-light', new Vector3(-0.5, -1, 0.5), this.scene);
    key.intensity = 2.1;
    this.engine.runRenderLoop(() => {
      if (document.hidden) return;
      if (this.autoRotate) this.camera.alpha += Math.min(this.engine.getDeltaTime(), 50) * 0.00015;
      this.scene.render();
    });
    window.addEventListener('resize', this.resize);
  }

  async load(entry: AssetEntry): Promise<AssetStats | null> {
    const request = ++this.request;
    const loaded = await LoadAssetContainerAsync(entry.url, this.scene);
    if (request !== this.request) {
      loaded.dispose();
      return null;
    }
    this.skeletons.forEach(viewer => viewer.dispose());
    this.skeletons = [];
    this.animation = undefined;
    this.container?.dispose();
    this.root?.dispose();
    this.container = loaded;
    loaded.addAllToScene();
    loaded.animationGroups.forEach(group => group.stop());
    loaded.skeletons.forEach(skeleton => skeleton.returnToRest());
    this.root = new TransformNode('asset-display-root', this.scene);
    loaded.rootNodes.forEach(node => {
      if (node instanceof TransformNode) node.parent = this.root!;
    });
    const meshes = loaded.meshes.filter(mesh => mesh.getTotalVertices() > 0);
    meshes.forEach(mesh => mesh.computeWorldMatrix(true));
    const bounds = this.bounds(meshes);
    const size = bounds.max.subtract(bounds.min);
    this.root.position.set(-(bounds.min.x + bounds.max.x) / 2, -bounds.min.y, -(bounds.min.z + bounds.max.z) / 2);
    this.center = new Vector3(0, size.y / 2, 0);
    this.radius = Math.max(size.length() * 1.5, 0.5);
    this.makeGround(Math.max(size.x, size.y, size.z, 1));
    this.resetCamera();
    loaded.skeletons.forEach(skeleton => {
      const mesh = meshes.find(item => item.skeleton === skeleton);
      if (mesh) {
        const viewer = new SkeletonViewer(skeleton, mesh, this.scene, true, 2);
        viewer.color = Color3.FromHexString('#ff4a1d');
        viewer.isEnabled = this.skeletonEnabled;
        this.skeletons.push(viewer);
      }
    });
    this.setWireframe(this.wireframeEnabled);
    return {
      meshes: meshes.length,
      triangles: meshes.reduce((sum, mesh) => sum + Math.floor(mesh.getTotalIndices() / 3), 0),
      bones: loaded.skeletons.reduce((sum, skeleton) => sum + skeleton.bones.length, 0),
      animations: loaded.animationGroups.map(group => group.name),
      height: size.y,
      materials: loaded.materials.length,
    };
  }

  play(index: number, speed = 1): void {
    this.container?.animationGroups.forEach(group => group.stop());
    // Clips omit some translation/IK tracks; restore the original pose before switching.
    this.container?.skeletons.forEach(skeleton => skeleton.returnToRest());
    this.animation = this.container?.animationGroups[index];
    this.animation?.start(true, speed);
  }

  setPlaying(playing: boolean): void {
    if (playing) this.animation?.play(true);
    else this.animation?.pause();
  }

  setSpeed(speed: number): void {
    if (this.animation) this.animation.speedRatio = speed;
  }

  setSkeleton(enabled: boolean): void {
    this.skeletonEnabled = enabled;
    this.skeletons.forEach(viewer => { viewer.isEnabled = enabled; });
  }

  setWireframe(enabled: boolean): void {
    this.wireframeEnabled = enabled;
    this.container?.materials.forEach(material => { material.wireframe = enabled; });
  }

  setAutoRotate(enabled: boolean): void { this.autoRotate = enabled; }

  resetCamera(): void {
    this.camera.setTarget(this.center);
    this.camera.alpha = Math.PI / 2.5;
    this.camera.beta = 1.25;
    this.camera.radius = this.radius;
    this.camera.lowerRadiusLimit = this.radius * 0.13;
    this.camera.upperRadiusLimit = this.radius * 6;
    this.camera.maxZ = this.radius * 30;
    this.camera.panningSensibility = 1800 / Math.max(1, this.radius / 4);
  }

  private bounds(meshes: AbstractMesh[]): { min: Vector3; max: Vector3 } {
    const min = new Vector3(Infinity, Infinity, Infinity);
    const max = new Vector3(-Infinity, -Infinity, -Infinity);
    for (const mesh of meshes) {
      const box = mesh.getBoundingInfo().boundingBox;
      min.minimizeInPlace(box.minimumWorld);
      max.maximizeInPlace(box.maximumWorld);
    }
    if (!Number.isFinite(min.x)) throw new Error('该资产没有可显示的网格');
    return { min, max };
  }

  private makeGround(size: number): void {
    this.floor?.dispose(false, true);
    this.grid?.dispose();
    const width = size * 5;
    this.floor = MeshBuilder.CreateGround('inspection-ground', { width, height: width }, this.scene);
    this.floor.position.y = -0.015;
    const mat = new StandardMaterial('ground-material', this.scene);
    mat.diffuseColor = Color3.FromHexString('#dce2db');
    mat.disableLighting = true;
    mat.emissiveColor = Color3.FromHexString('#dce2db');
    mat.specularColor = Color3.Black();
    this.floor.material = mat;
    const step = 10 ** Math.floor(Math.log10(size));
    const lines: Vector3[][] = [];
    const extent = Math.ceil(width / step / 2) * step;
    for (let offset = -extent; offset <= extent + step / 2; offset += step) {
      lines.push([new Vector3(offset, -0.01, -extent), new Vector3(offset, -0.01, extent)]);
      lines.push([new Vector3(-extent, -0.01, offset), new Vector3(extent, -0.01, offset)]);
    }
    const grid = MeshBuilder.CreateLineSystem('scale-grid', { lines }, this.scene);
    grid.color = Color3.FromHexString('#bdc9bf');
    grid.isPickable = false;
    this.grid = grid;
  }

  dispose(): void {
    ++this.request;
    window.removeEventListener('resize', this.resize);
    this.scene.dispose();
    this.engine.dispose();
  }
}
