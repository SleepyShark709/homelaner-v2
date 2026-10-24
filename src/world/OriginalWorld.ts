import { Engine } from '@babylonjs/core/Engines/engine';
import { Scene } from '@babylonjs/core/scene';
import { FreeCamera } from '@babylonjs/core/Cameras/freeCamera';
import { Vector3, Quaternion, Matrix } from '@babylonjs/core/Maths/math.vector';
import { Color3, Color4 } from '@babylonjs/core/Maths/math.color';
import { HemisphericLight } from '@babylonjs/core/Lights/hemisphericLight';
import { DirectionalLight } from '@babylonjs/core/Lights/directionalLight';
import { LoadAssetContainerAsync } from '@babylonjs/core/Loading/sceneLoader';
import { Mesh } from '@babylonjs/core/Meshes/mesh';
import { TransformNode } from '@babylonjs/core/Meshes/transformNode';
import { Material } from '@babylonjs/core/Materials/material';
import { MultiMaterial } from '@babylonjs/core/Materials/multiMaterial';
import type { AssetContainer } from '@babylonjs/core/assetContainer';
import '@babylonjs/core/Meshes/thinInstanceMesh';
import { registerBuiltInLoaders } from '@babylonjs/loaders/dynamic';
import { OriginalMaterials } from './OriginalMaterials';
import { OriginalStreaming, createOriginalNewSaveFlags, type StreamingEvent } from './OriginalStreaming';
import type { SkyMaterialManifest } from './RecoveredSurfacePlugins';
import { OriginalTerrainMaterials, type TerrainMaterialManifest } from './terrain-material';
import { explicitlyHidden, resolveMaterialPackage, sourceObjectCount } from './types';
import type { Bounds, GeometryManifest, OriginalAsset, OriginalObject, MaterialManifest, TerrainManifest, StreamingManifest, V3 } from './types';

registerBuiltInLoaders();
export interface WorldStats {
  objects: number; terrain: number; assets: number; failedAssets: number;
  hidden: number; ambiguousMaterials: number; unknownMaterials: number;
  textureFailures: number; fps: number; draws: number; position: V3;
}
async function json<T>(url: string): Promise<T> {
  const response = await fetch(url, { cache: 'no-cache' });
  if (!response.ok) throw new Error(`${url} 读取失败 (${response.status})`);
  return await response.json() as T;
}

export class OriginalWorld {
  readonly engine: Engine;
  readonly scene: Scene;
  readonly camera: FreeCamera;
  manifest!: GeometryManifest;
  materials!: OriginalMaterials;
  terrainManifest?: TerrainManifest;
  streamingManifest!: StreamingManifest;
  private terrainMaterials?: OriginalTerrainMaterials;
  private assets = new Map<string, OriginalAsset>();
  private containers = new Map<string, Promise<AssetContainer>>();
  private variants = new Map<string, Mesh[]>();
  private materialBindings = new WeakMap<OriginalObject, string>();
  private streaming?: OriginalStreaming;
  private streamNodes = new Map<string, {nodes: TransformNode[]; count: number}>();
  private regionNodes: TransformNode[] = [];
  private terrainNodes: TransformNode[] = [];
  private regionMaterials: MultiMaterial[] = [];
  private terrainLoaded = false;
  private loading = false;
  private disposed = false;
  private generation = 0;
  private lastBounds?: Bounds;
  private fast = false;
  private movementSpeed = 4;
  private highQuality = false;
  private terrainHighQuality = false;
  private failures = new Map<string, string>();
  private stats = { objects: 0, terrain: 0, assets: 0, hidden: 0, ambiguousMaterials: 0 };
  onStats: (value: WorldStats) => void = () => {};
  onProgress: (message: string, done: number, total: number) => void = () => {};
  onStreaming: (event: StreamingEvent) => void = () => {};
  private resize = () => this.engine.resize();
  private key = (event: KeyboardEvent) => {
    if (event.code === 'ShiftLeft' || event.code === 'ShiftRight') this.fast = event.type === 'keydown';
  };
  private blur = () => { this.fast = false; };

  constructor(readonly canvas: HTMLCanvasElement) {
    this.engine = new Engine(canvas, true, { stencil: true, preserveDrawingBuffer: true });
    this.engine.setHardwareScalingLevel(Math.max(1, window.devicePixelRatio / 1.5));
    this.scene = new Scene(this.engine);
    this.scene.useRightHandedSystem = true;
    this.scene.skipPointerMovePicking = true;
    this.scene.clearColor = new Color4(.69, .78, .82, 1);
    // Preview illumination only; original sky capture, lightmaps, exposure and
    // volumetric scattering are not silently replaced by a claimed equivalent.
    const fill = new HemisphericLight('preview-fill', Vector3.Up(), this.scene);
    fill.intensity = .75;
    fill.groundColor = new Color3(.23, .25, .27);
    const sun = new DirectionalLight('source-sun-direction', new Vector3(.374, -.75, -.544), this.scene);
    sun.intensity = 5;
    this.scene.imageProcessingConfiguration.toneMappingEnabled = true;
    this.scene.imageProcessingConfiguration.toneMappingType = 1;
    this.camera = new FreeCamera('world-inspection-camera', new Vector3(0, 100, 0), this.scene);
    // The original sky hemisphere has a 50 km radius. Inspection cameras away
    // from its center must not clip the far side of that recovered geometry.
    this.camera.minZ = .25; this.camera.maxZ = 100000; this.camera.fov = .9;
    this.camera.speed = this.movementSpeed; this.camera.inertia = .55;
    this.camera.angularSensibility = 1800;
    this.camera.keysUp = [87]; this.camera.keysDown = [83];
    this.camera.keysLeft = [65]; this.camera.keysRight = [68];
    this.camera.keysUpward = [69, 32]; this.camera.keysDownward = [81];
    this.camera.attachControl(canvas, true);
    window.addEventListener('resize', this.resize);
    window.addEventListener('keydown', this.key);
    window.addEventListener('keyup', this.key);
    window.addEventListener('blur', this.blur);
    let timer = 0;
    this.engine.runRenderLoop(() => {
      if (this.disposed || document.hidden || this.loading) return;
      this.camera.speed = this.movementSpeed * (this.fast ? 4 : 1);
      this.scene.render();
      timer += this.engine.getDeltaTime();
      if (timer > 250) {
        timer = 0;
        this.onStats({ ...this.stats, failedAssets: this.failures.size,
          unknownMaterials: this.materials?.unknownMaterials.size ?? 0,
          textureFailures: this.materials?.textureFailures.size ?? 0,
          fps: this.engine.getFps(), draws: this.scene.getActiveMeshes().length,
          position: this.camera.position.asArray() as V3 });
      }
    });
  }

  async load(): Promise<void> {
    const [geometry, materials, terrain, terrainMaterials, streaming, sky] = await Promise.all([
      json<GeometryManifest>('/assets/world/geometry-manifest.json'),
      json<MaterialManifest>('/assets/world/material-manifest.json'),
      json<TerrainManifest>('/assets/world/terrain-manifest.json').catch(() => undefined),
      json<TerrainMaterialManifest>('/assets/world/terrain-material-manifest.json'),
      json<StreamingManifest>('/assets/world/streaming-manifest.json'),
      json<SkyMaterialManifest>('/assets/world/sky-material-manifest.json'),
    ]);
    if (geometry.coordinateSystem !== 'gltf-rh-y-up-meters' || geometry.originUE.some(value => value !== 0)) {
      throw new Error('原世界坐标合同不匹配，停止装配');
    }
    if (terrain && (terrain.coordinateSystem !== geometry.coordinateSystem || terrain.originUE.some((v, i) => v !== geometry.originUE[i]))) {
      throw new Error('地形与关卡原点不一致，停止装配');
    }
    this.manifest = geometry;
    const available = new Set(geometry.levels.map(level => level.package));
    if (streaming.baseline.packages.some(name => !available.has(name))) throw new Error('原启动关卡存在未恢复的地图');
    this.streamingManifest = streaming;
    this.materials = new OriginalMaterials(this.scene, materials, sky);
    this.terrainMaterials = new OriginalTerrainMaterials(this.scene, terrainMaterials, this.materials.textureFailures);
    this.terrainManifest = terrain;
    geometry.assets.forEach(asset => this.assets.set(asset.id, asset));
    terrain?.assets.forEach(asset => this.assets.set(asset.id, asset));
  }

  private container(asset: OriginalAsset): Promise<AssetContainer> {
    let promise = this.containers.get(asset.id);
    if (!promise) {
      promise = LoadAssetContainerAsync(asset.url, this.scene).then(container => {
        container.animationGroups.forEach(group => group.stop());
        container.meshes.forEach(mesh => { mesh.isPickable = false; mesh.computeWorldMatrix(true); });
        return container;
      }).catch(error => {
        this.failures.set(asset.id, String(error));
        this.containers.delete(asset.id);
        throw error;
      });
      this.containers.set(asset.id, promise);
    }
    return promise;
  }

  private material(source: Material | null, asset: OriginalAsset, object: OriginalObject): Material {
    if (source instanceof MultiMaterial) {
      const replacement = new MultiMaterial(`${object.id}/slots`, this.scene);
      replacement.subMaterials = source.subMaterials.map(value => this.material(value, asset, object));
      this.regionMaterials.push(replacement);
      return replacement;
    }
    const pointers: string[] = source?.metadata?.gltf?.pointers ?? [];
    const indexPointer = pointers.find(value => /^\/materials\/\d+$/.test(value));
    const index = indexPointer ? Number(indexPointer.split('/').pop()) : asset.gltfMaterials?.find(item => item.name === source?.name)?.materialIndex;
    const resolved = index === undefined ? { package: null, ambiguous: false } : resolveMaterialPackage(asset, index, object.materialOverrides);
    return this.materials.get(resolved.package);
  }

  private variant(asset: OriginalAsset, object: OriginalObject, sources: Mesh[], terrain: boolean): Mesh[] {
    const key = `${asset.id}|${this.materialBindingKey(asset, object)}|${terrain}`;
    const cached = this.variants.get(key);
    if (cached) return cached;
    const groups = new Map<string, Mesh[]>();
    for (const source of sources) {
      const sourceWorld = source.computeWorldMatrix(true).clone();
      const clone = source.clone(`${asset.id}/material-template`, null, true)!;
      // Scene inspection uses the original reference pose. Bake the skin once
      // into a private geometry, keeping the source skeleton/animation untouched.
      // Thousands of per-instance skeleton clones otherwise stall the all-map view.
      if (clone.skeleton) {
        clone.makeGeometryUnique(); clone.skeleton.prepare(true);
        clone.applySkeleton(clone.skeleton); clone.skeleton = null;
        clone.numBoneInfluencers = 0;
      }
      clone.parent = null;
      clone.position.setAll(0); clone.scaling.setAll(1); clone.rotation.setAll(0); clone.rotationQuaternion = Quaternion.Identity();
      clone.setPreTransformMatrix(sourceWorld);
      clone.material = terrain ? this.terrainMaterials?.get(object.id) ?? this.materials.get(null) : this.material(source.material, asset, object);
      clone.computeWorldMatrix(true);
      const groupKey = `${clone.material.uniqueId}|${clone.getVerticesDataKinds().sort().join(',')}`;
      const group = groups.get(groupKey) ?? []; group.push(clone); groups.set(groupKey, group);
    }
    const result: Mesh[] = [];
    for (const group of groups.values()) {
      let mesh: Mesh;
      if (group.length > 1) {
        const merged = Mesh.MergeMeshes(group, true, true, undefined, false, false);
        if (!merged) throw new Error(`同材质几何合并失败：${asset.id}`);
        mesh = merged;
      } else {
        mesh = group[0];
        // A clone shares geometry until explicitly detached. Preserve the source
        // container and other material variants when baking its local transform.
        mesh.makeGeometryUnique(); mesh.bakeCurrentTransformIntoVertices(true);
      }
      mesh.isVisible = false; mesh.setEnabled(false); mesh.isPickable = false;
      result.push(mesh);
    }
    this.variants.set(key, result);
    return result;
  }

  private materialBindingKey(asset: OriginalAsset, object: OriginalObject): string {
    let key = this.materialBindings.get(object);
    if (key === undefined) {
      key = JSON.stringify((asset.gltfMaterials ?? []).map(slot => this.materials.canonical(resolveMaterialPackage(asset, slot.materialIndex, object.materialOverrides).package)));
      this.materialBindings.set(object, key);
    }
    return key;
  }

  private async build(objects: OriginalObject[], target: TransformNode[], token: number, terrain = false, signal?: AbortSignal): Promise<number> {
    const groups = new Map<string, OriginalObject[]>();
    for (const object of objects) {
      if (explicitlyHidden(object)) { if (!terrain) this.stats.hidden++; continue; }
      // Spatial groups retain frustum culling rather than one city-wide bound.
      const cell = object.position.map(v => Math.floor(v / 128)).join(',');
      const mirrored = object.scale.reduce((a, b) => a * b, 1) < 0;
      const asset = this.assets.get(object.assetId);
      const key = `${object.assetId}|${asset ? this.materialBindingKey(asset, object) : object.id}|${cell}|${mirrored}`;
      const group = groups.get(key) ?? []; group.push(object); groups.set(key, group);
    }
    let done = 0, loaded = 0;
    const jobs = [...groups.values()];
    const worker = async () => {
      while (jobs.length && token === this.generation && !this.disposed && !signal?.aborted) {
        const rows = jobs.shift()!;
        const first = rows[0];
        const asset = this.assets.get(first.assetId);
        if (!asset) { this.failures.set(first.assetId, '清单中缺少模型'); continue; }
        try {
          const container = await this.container(asset);
          if (token !== this.generation || this.disposed || signal?.aborted) return;
          const meshes = container.meshes.filter((mesh): mesh is Mesh => mesh instanceof Mesh && mesh.getTotalVertices() > 0);
          {
            for (const source of this.variant(asset, first, meshes, terrain)) {
              const mesh = source.clone(`${first.id}/${source.name}`, null, true)!;
              mesh.parent = null; mesh.position.setAll(0); mesh.scaling.setAll(1); mesh.rotation.setAll(0); mesh.rotationQuaternion = Quaternion.Identity();
              mesh.material = source.material;
              mesh.isVisible = true; mesh.setEnabled(true); mesh.isPickable = false;
              const buffer = new Float32Array(rows.length * 16);
              rows.forEach((object, i) => {
                const transform = Matrix.Compose(Vector3.FromArray(object.scale), Quaternion.FromArray(object.rotation), Vector3.FromArray(object.position));
                transform.copyToArray(buffer, i * 16);
              });
              const det = Matrix.FromArray(buffer).determinant();
              mesh.sideOrientation = det < 0 ? Material.ClockWiseSideOrientation : Material.CounterClockWiseSideOrientation;
              mesh.thinInstanceSetBuffer('matrix', buffer, 16, true);
              mesh.thinInstanceRefreshBoundingInfo(true);
              mesh.freezeWorldMatrix(); target.push(mesh);
            }
          }
          loaded += rows.reduce((total, row) => total + sourceObjectCount(row), 0);
        } catch (error) { this.failures.set(asset.id, String(error)); }
        done++;
        this.onProgress(`${terrain ? '恢复原始地形' : '装配原关卡'} · ${done}/${groups.size}`, done, groups.size);
        // Asset fetches already yield. Do not await requestAnimationFrame here:
        // hidden preview tabs suspend it and would stall the import indefinitely.
      }
    };
    await Promise.all([worker(), worker(), worker()]);
    return loaded;
  }

  async select(levelId: string): Promise<void> {
    if (this.loading) return;
    this.streaming?.dispose(); this.streaming = undefined; this.streamNodes.clear();
    this.loading = true;
    const token = ++this.generation;
    this.stats.objects = 0; this.stats.hidden = 0; this.stats.ambiguousMaterials = 0;
    const previous = this.regionNodes; this.regionNodes = [];
    for (let i = 0; i < previous.length; i++) {
      previous[i].dispose(false, false);
      if (i % 64 === 0) {
        this.onProgress(`卸载上一区域 · ${i + 1}/${previous.length}`, i + 1, previous.length);
        await new Promise<void>(resolve => setTimeout(resolve, 0));
      }
    }
    // Variant templates can retain these materials across region switches.
    this.failures.clear();
    try {
      const baseline = new Set(this.streamingManifest.baseline.packages);
      const chosen = ['__baseline__', '__startup__'].includes(levelId) ? this.manifest.levels.filter(level => baseline.has(level.package)) : levelId === '__all__' ? this.manifest.levels.filter(level => level.scope === 'main-world') : this.manifest.levels.filter(level => level.id === levelId);
      const selected = chosen.length === 1 && chosen[0].scope === 'main-world' && chosen[0].id !== 'MainLevel'
        ? [...this.manifest.levels.filter(level => level.id === 'MainLevel'), ...chosen] : chosen;
      const objects = selected.flatMap(level => level.objects);
      this.stats.ambiguousMaterials = objects.filter(object => !explicitlyHidden(object)).reduce((count, object) => {
        const asset = this.assets.get(object.assetId);
        return count + (asset?.gltfMaterials ?? []).filter(slot => resolveMaterialPackage(asset!, slot.materialIndex, object.materialOverrides).ambiguous).length;
      }, 0);
      // MainLevel contains 9.5-km backdrop mountains. Use the original landscape
      // extent for city framing rather than pulling the camera outside the city.
      const terrainBounds = (this.terrainManifest?.objects ?? []).map(object => (object as OriginalObject & { bounds?: Bounds }).bounds);
      const candidates = ['__baseline__', '__startup__', '__all__', 'MainLevel'].includes(levelId) && terrainBounds.length ? terrainBounds : chosen.map(level => level.bounds);
      const bounded = candidates.filter((bounds): bounds is Bounds => !!bounds && bounds.min.every(Number.isFinite) && bounds.max.every(Number.isFinite));
      if (bounded.length) this.lastBounds = { min: [0, 1, 2].map(i => Math.min(...bounded.map(b => b.min[i]))) as V3, max: [0, 1, 2].map(i => Math.max(...bounded.map(b => b.max[i]))) as V3 };
      this.frameRegion();
      if (!this.terrainLoaded && this.terrainManifest) {
        this.terrainNodes.forEach(node => node.dispose(false, false)); this.terrainNodes = [];
        this.stats.terrain = await this.build(this.terrainManifest.objects, this.terrainNodes, token, true);
        this.terrainLoaded = this.stats.terrain === this.terrainManifest.objects.length;
      }
      const mainWorld = chosen.some(level => level.scope === 'main-world');
      this.terrainNodes.forEach(node => node.setEnabled(mainWorld));
      if (levelId === '__startup__') await this.runOriginalStartup(token);
      else {
        this.stats.objects = await this.build(objects, this.regionNodes, token);
        this.stats.assets = new Set(objects.map(object => object.assetId)).size;
      }
      await this.scene.whenReadyAsync();
      this.scene.render();
    } finally { this.loading = false; }
    if (this.highQuality !== this.terrainHighQuality) await this.setQuality(this.highQuality);
  }

  /** Execute recovered latent loading requests against actual scene ownership.
   * The scene is still a reference-pose inspection: BeginPlay actors, gameplay,
   * and unknown save branches are not fabricated by successful mesh loading.
   */
  private async runOriginalStartup(token: number): Promise<void> {
    const updateCounts = () => {
      this.stats.objects = [...this.streamNodes.values()].reduce((sum, entry) => sum + entry.count, 0);
      const objects = this.manifest.levels.filter(level => this.streamNodes.has(level.package)).flatMap(level => level.objects);
      this.stats.assets = new Set(objects.map(object => object.assetId)).size;
      this.stats.hidden = objects.filter(explicitlyHidden).length;
    };
    const streaming = OriginalStreaming.fromManifest(this.streamingManifest, {
      load: async request => {
        request.signal.throwIfAborted();
        if (this.streamNodes.has(request.package)) return;
        const level = this.manifest.levels.find(level => level.package === request.package);
        if (!level) throw new Error(`原加载链缺少关卡：${request.package}`);
        const nodes: TransformNode[] = [];
        try {
          const count = await this.build(level.objects, nodes, token, false, request.signal);
          request.signal.throwIfAborted();
          if (this.disposed || token !== this.generation) throw new Error('关卡装配已取消');
          const expected = level.objects.filter(object => !explicitlyHidden(object)).reduce((sum, object) => sum + sourceObjectCount(object), 0);
          if (count !== expected) throw new Error(`${request.levelName} 未完整装配 (${count}/${expected})`);
          // Resource completion includes shader/texture readiness, not merely
          // dispatching a fetch or creating an unresolved container promise.
          // Await this package only. A scene-wide readiness barrier would make
          // the independent LoadLevel timer wait for unrelated city packages.
          const deadline = performance.now() + 120000;
          while (!nodes.every(node => !(node instanceof Mesh) || node.isReady(true))) {
            request.signal.throwIfAborted();
            if (this.disposed || token !== this.generation) throw new Error('关卡装配已取消');
            if (this.materials.textureFailures.size) throw new Error(`${request.levelName} 纹理加载失败`);
            if (performance.now() > deadline) throw new Error(`${request.levelName} 材质未能在 120 秒内就绪`);
            await new Promise<void>((resolve, reject) => {
              const abort = () => { clearTimeout(timer); reject(request.signal.reason); };
              const timer = setTimeout(() => { request.signal.removeEventListener('abort', abort); resolve(); }, 16);
              request.signal.addEventListener('abort', abort, {once:true});
            });
          }
          request.signal.throwIfAborted();
          if (this.disposed || token !== this.generation) throw new Error('关卡装配已取消');
          this.streamNodes.set(request.package, {nodes, count}); this.regionNodes.push(...nodes);
          updateCounts();
        } catch (error) { nodes.forEach(node => node.dispose(false, false)); throw error; }
      },
      unload: async request => {
        request.signal.throwIfAborted();
        const entry = this.streamNodes.get(request.package);
        if (!entry) return;
        const owned = new Set(entry.nodes);
        entry.nodes.forEach(node => node.dispose(false, false));
        this.regionNodes = this.regionNodes.filter(node => !owned.has(node));
        this.streamNodes.delete(request.package); updateCounts();
      },
    }, {onEvent: event => this.onStreaming(event)});
    this.streaming = streaming;
    const resident = await streaming.prepareResidentWorld();
    if (resident.resident !== 'ready') throw new Error(resident.failure ?? '原常驻关卡未就绪');
    // This inspection explicitly uses original new-save defaults. It never
    // imports, changes or assumes the state of the user's Steam save.
    await streaming.beginPlay(createOriginalNewSaveFlags());
    await streaming.waitForOverlay();
    const result = streaming.getSnapshot();
    if (result.failure) throw new Error(result.failure);
  }

  frameRegion(close = false): void {
    const b = this.lastBounds;
    if (!b) return;
    const center = Vector3.FromArray(b.min).add(Vector3.FromArray(b.max)).scale(.5);
    const span = Math.max(b.max[0] - b.min[0], b.max[2] - b.min[2], 60);
    const radius = close ? Math.min(80, span * .15) : Math.max(100, span * .7);
    const target = new Vector3(center.x, close ? b.min[1] + 10 : center.y, center.z);
    this.camera.position.copyFrom(target.add(new Vector3(radius * .6, radius * .6, radius * .75)));
    this.camera.setTarget(target);
    this.camera.cameraDirection.setAll(0); this.camera.cameraRotation.setAll(0);
  }
  setSpeed(value: number): void { this.movementSpeed = value; }
  async setQuality(high: boolean): Promise<void> {
    this.highQuality = high;
    this.engine.setHardwareScalingLevel(high ? Math.max(1, window.devicePixelRatio / 2) : Math.max(1.5, window.devicePixelRatio / 1.25));
    if (this.loading || !this.terrainLoaded || !this.terrainManifest || high === this.terrainHighQuality) return;
    this.loading = true;
    const nodes: TransformNode[] = [];
    try {
      const objects = this.terrainManifest.objects.map(object => {
        const asset = this.assets.get(object.assetId)!;
        if (!high || !asset.highQualityUrl) return object;
        const id = `${asset.id}:lod2`;
        this.assets.set(id, { ...asset, id, url: asset.highQualityUrl });
        return { ...object, assetId: id };
      });
      const count = await this.build(objects, nodes, this.generation, true);
      if (count !== objects.length) throw new Error('高清地形未完整载入，保留之前的地形');
      const enabled = this.terrainNodes.some(node => node.isEnabled());
      this.terrainNodes.forEach(node => node.dispose(false, false));
      this.terrainNodes = nodes; nodes.forEach(node => node.setEnabled(enabled));
      this.terrainHighQuality = high;
    } catch (error) { nodes.forEach(node => node.dispose(false, false)); throw error; }
    finally { this.loading = false; }
  }
  setWireframe(enabled: boolean): void { this.scene.forceWireframe = enabled; }
  get failuresList(): [string, string][] { return [...this.failures]; }
  dispose(): void {
    this.streaming?.dispose();
    this.disposed = true; this.generation++;
    window.removeEventListener('resize', this.resize);
    window.removeEventListener('keydown', this.key); window.removeEventListener('keyup', this.key); window.removeEventListener('blur', this.blur);
    this.camera.detachControl(); this.scene.dispose(); this.engine.dispose();
  }
}
