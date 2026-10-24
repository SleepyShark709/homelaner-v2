import { Scene } from '@babylonjs/core/scene';
import { TransformNode } from '@babylonjs/core/Meshes/transformNode';
import { Quaternion, Vector3 } from '@babylonjs/core/Maths/math.vector';
import { LoadAssetContainerAsync } from '@babylonjs/core/Loading/sceneLoader';
import type { AbstractMesh } from '@babylonjs/core/Meshes/abstractMesh';
import type { AssetContainer } from '@babylonjs/core/assetContainer';
import type { Bounds, Obstacle, Vec3 } from './collision';

export interface CityAsset { id: string; url: string; kind: 'building' | 'road' | 'prop' }
export interface CityObject { id: string; assetId: string; position: Vec3; rotation: [number, number, number, number]; scale: Vec3; sourceActor: string }
export interface CityManifest {
  coordinateSystem: 'gltf-rh-y-up-meters'; name?: string; originUE: Vec3; spawn: Vec3;
  bounds: Bounds; assets: CityAsset[]; objects: CityObject[]; notes: string[]; groundY?: number;
  collisionBoxes?: Obstacle[];
}
export class World {
  readonly obstacles: Obstacle[] = [];
  readonly visibleMeshes: AbstractMesh[] = [];
  private readonly containers: AssetContainer[] = [];
  manifest!: CityManifest;
  constructor(readonly scene: Scene) {}
  async load(onProgress: (message: string) => void): Promise<void> {
    const response = await fetch('/assets/city/manifest.json');
    if (!response.ok) throw new Error('原版街区清单尚未生成');
    this.manifest = await response.json() as CityManifest;
    if (this.manifest.coordinateSystem !== 'gltf-rh-y-up-meters') throw new Error('街区坐标系不匹配');
    for (const [index, asset] of this.manifest.assets.entries()) {
      onProgress(`载入原版街区 ${index + 1}/${this.manifest.assets.length} · ${asset.id}`);
      const container = await LoadAssetContainerAsync(asset.url, this.scene);
      container.meshes.forEach(mesh => { mesh.receiveShadows = true; });
      container.materials.forEach(material => material.freeze());
      this.containers.push(container);
      for (const object of this.manifest.objects.filter(item => item.assetId === asset.id)) {
        const instance = container.instantiateModelsToScene(name => `${object.id}/${name}`, false, { doNotInstantiate: false });
        const root = new TransformNode(object.id, this.scene);
        root.position.copyFromFloats(...object.position);
        root.scaling.copyFromFloats(...object.scale);
        root.rotationQuaternion = Quaternion.FromArray(object.rotation);
        for (const node of instance.rootNodes) node.parent = root;
        const meshes = root.getChildMeshes().filter(mesh => mesh.getTotalVertices() > 0);
        for (const mesh of meshes) {
          mesh.computeWorldMatrix(true);
          mesh.isPickable = false;
          mesh.freezeWorldMatrix();
          this.visibleMeshes.push(mesh);
        }
        if (asset.kind === 'building') {
          const min = new Vector3(Infinity, Infinity, Infinity), max = new Vector3(-Infinity, -Infinity, -Infinity);
          for (const mesh of meshes) {
            const box = mesh.getBoundingInfo().boundingBox;
            min.minimizeInPlace(box.minimumWorld); max.maximizeInPlace(box.maximumWorld);
          }
          if (Number.isFinite(min.x)) this.obstacles.push({ id: object.id, min: min.asArray() as Vec3, max: max.asArray() as Vec3 });
        }
      }
    }
    const ground = this.manifest.groundY ?? this.manifest.bounds.min[1];
    this.obstacles.push(...(this.manifest.collisionBoxes ?? []));
    this.obstacles.push({ id: 'district-ground-proxy', min: [this.manifest.bounds.min[0] - 10, ground - 5, this.manifest.bounds.min[2] - 10], max: [this.manifest.bounds.max[0] + 10, ground, this.manifest.bounds.max[2] + 10] });
  }
  dispose(): void { this.containers.forEach(container => container.dispose()); }
}
