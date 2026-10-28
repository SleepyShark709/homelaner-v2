import './play-original.css';
// Babylon's Ray side-effect is required for scene.createPickingRay/pickWithRay
// used by the ground/plaza diagnostics.
import '@babylonjs/core/Culling/ray';
import { Matrix, Quaternion, Vector3 } from '@babylonjs/core/Maths/math.vector';
import { Color3 } from '@babylonjs/core/Maths/math.color';
import { DirectionalLight } from '@babylonjs/core/Lights/directionalLight';
import { ShadowGenerator } from '@babylonjs/core/Lights/Shadows/shadowGenerator';
import { SSAO2RenderingPipeline } from '@babylonjs/core/PostProcesses/RenderPipeline/Pipelines/ssao2RenderingPipeline';
import '@babylonjs/core/Lights/Shadows/shadowGeneratorSceneComponent';
import { StandardMaterial } from '@babylonjs/core/Materials/standardMaterial';
import { Texture } from '@babylonjs/core/Materials/Textures/texture';
import { CreateGround } from '@babylonjs/core/Meshes/Builders/groundBuilder';
import { CreateTorus } from '@babylonjs/core/Meshes/Builders/torusBuilder';
import { Mesh } from '@babylonjs/core/Meshes/mesh';
import { OriginalWorld } from './world/OriginalWorld';
import { Character } from './game/Character';
import { Footsteps } from './game/Footsteps';
import { Input } from './game/Input';
import { Combat } from './game/Combat';
import { Population } from './game/Population';
import type { PlayerMotor } from './game/PlayerMotor';
import { firstHit } from './game/collision';
import type { Bounds, Vec3 } from './game/collision';
import { buildCollision } from './play/CollisionWorld';
import { OriginalPlayer } from './play/OriginalPlayer';
import { TerrainHeightfield } from './play/TerrainHeightfield';
import { WalkableSurfaces } from './play/WalkableSurfaces';
import { sourceObjectCount } from './world/types';

document.title = 'UNDEFEATED · 原版可玩基线 B1';
document.querySelector<HTMLDivElement>('#app')!.innerHTML = `
  <canvas id="world" tabindex="0" aria-label="原版城市可玩切片，WASD 移动，拖动鼠标转向"></canvas>
  <header class="play-header"><div class="play-brand">UNDEFEATED<small>ORIGINAL PLAYABLE BASELINE · B1</small></div><div class="play-badge">原生资产 · 预览物理</div></header>
  <aside class="play-panel">
    <h1>原版街区 · 可玩切片</h1>
    <p>原角色、原骨架与原始街区资产；地形高度来自原 Landscape 高度场。建筑碰撞为静态 AABB 代理，跳跃/重力/相机手感仍是预览。</p>
    <p class="warn">本切片不是完整原版玩法：AI、车辆、任务与完整攻击状态仍未接入；镭射眼为作者预览，默认关闭，需 ?heat=1 启用；mode=free 为自由破坏预览。</p>
    <div class="play-keys">
      <kbd>W A S D</kbd><span>移动</span>
      <kbd>拖动鼠标</kbd><span>转向</span>
      <kbd>SPACE</kbd><span>地面跳跃 / 空中开飞 / 飞行退飞</span>
      <kbd>E / Q</kbd><span>上升 / 下降；地面按住 E 蓄升</span>
      <kbd>SHIFT</kbd><span>冲刺</span>
      <kbd>ALT</kbd><span>慢行</span>
      <kbd>F</kbd><span>退出飞行并落地</span>
      <kbd>R</kbd><span>回到出生点</span>
    </div>
  </aside>
  <div class="play-minimap" id="minimap-wrap" hidden><canvas id="minimap" width="420" height="420" aria-label="原版 minimap 底图与玩家位置"></canvas><img class="play-minimap-frame" src="/assets/world/minimap/frame.png" alt=""><img class="play-minimap-tint" src="/assets/world/minimap/frame-tint-red.png" alt=""></div>
  <div class="play-hud"><div>位置 <b id="hud-position">—</b></div><div>状态 <b id="hud-mode">—</b></div><div>速度 <b id="hud-speed">—</b></div><div id="hud-free-row" hidden>破坏 <b id="hud-destroyed">0</b> · 命中 <b id="hud-hits">0</b></div><div id="hud-quest-row" hidden>任务区域 <b id="hud-quests">—</b></div><div id="hud-crosswalk-row" hidden>人行横道 <b id="hud-crosswalk">—</b></div><div>FPS <b id="hud-fps">—</b></div></div>
  <div class="play-loading" id="loading"><div><strong id="load-title">装配原版可玩街区</strong><p id="load-message">读取原关卡、材质与地形…</p><progress id="progress" max="1" value="0"></progress></div></div>
  <div class="play-paused" id="paused" hidden>已暂停 · 点击继续</div>
  <div class="play-quest" id="quest-hint" hidden></div>
  <div class="play-lock" id="lock-reticle" hidden><i></i><b id="lock-distance"></b></div>`;

const el = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id) as T;
const canvas = el<HTMLCanvasElement>('world');
const viewer = new OriginalWorld(canvas);
const input = new Input(canvas);
// Original PlayerBP CameraBoom_GEN_VARIABLE: TargetArmLength=400 cm,
// SocketOffset=(0,50,90) cm, boom RelativeLocation Z=70 cm.
const CAMERA = { armLength: 4.0, attackArmLength: 6.5, farArmLength: 8.0, farSpeed: 60, armSpeed: 2, farArmSpeed: 1, boomHeight: 0.7, socketRight: 0.5, socketUp: 0.9, lagSpeed: 15, fov: 90 };
input.pitch = 0.02;
const paused = el('paused');
const lockReticle = el('lock-reticle');
const lockDistance = el('lock-distance');
const params = new URLSearchParams(location.search);
const originalHudMode = params.get('hud') !== 'help';
if (originalHudMode) {
  document.body.classList.add('hud-original');
  el('minimap-wrap').hidden = false;
}
const minimapImage = new Image();
const minimapPlayerImage = new Image();
const minimapFireIcon = new Image();
const minimapAccidentIcon = new Image();
let minimapReady = false;
let minimapPlayerReady = false;
let minimapFireReady = false;
let minimapAccidentReady = false;
let minimapFireTinted: HTMLCanvasElement | undefined;
let minimapAccidentTinted: HTMLCanvasElement | undefined;
// The recovered icon PNGs are authored red/white masks; the original HUD tints
// the same shapes by state. Until the visualizer state machine is recovered,
// use the two recovered quest families' preview colours.
const tintMinimapIcon = (image: HTMLImageElement, color: string) => {
  const canvas = document.createElement('canvas');
  canvas.width = image.naturalWidth;
  canvas.height = image.naturalHeight;
  const context = canvas.getContext('2d');
  if (!context) return undefined;
  context.drawImage(image, 0, 0);
  context.globalCompositeOperation = 'source-in';
  context.fillStyle = color;
  context.fillRect(0, 0, canvas.width, canvas.height);
  return canvas;
};
minimapImage.onload = () => { minimapReady = true; };
minimapImage.onerror = () => { minimapReady = false; };
minimapImage.src = '/assets/world/minimap/static.png';
minimapPlayerImage.onload = () => { minimapPlayerReady = true; };
minimapPlayerImage.src = '/assets/world/minimap/player.png';
minimapFireIcon.onload = () => {
  minimapFireReady = true;
  minimapFireTinted = tintMinimapIcon(minimapFireIcon, '#ff7a1a');
};
minimapFireIcon.src = '/assets/world/minimap/icon-fire.png';
minimapAccidentIcon.onload = () => {
  minimapAccidentReady = true;
  minimapAccidentTinted = tintMinimapIcon(minimapAccidentIcon, '#54c8ff');
};
minimapAccidentIcon.src = '/assets/world/minimap/icon-accident.png';
// Recovered T_StaticMinimap_Tex covers exactly [-1300, 1300] m on both axes.
// The HUD crops to the city island (source pixels 210..760) so the ocean margin
// is not shown; icon layout is still unresolved.
const MINIMAP_SOURCE_ORIGIN = 240, MINIMAP_SOURCE_SIZE = 490;
const MINIMAP_WORLD_MIN = (MINIMAP_SOURCE_ORIGIN / 1024) * 2600 - 1300;
const MINIMAP_WORLD_SPAN = (MINIMAP_SOURCE_SIZE / 1024) * 2600;
const MINIMAP_PIXELS = 420;
const drawMinimap = (position: number[], yaw: number) => {
  if (!minimapReady) return;
  const canvas = el<HTMLCanvasElement>('minimap');
  const context = canvas.getContext('2d');
  if (!context) return;
  context.clearRect(0, 0, MINIMAP_PIXELS, MINIMAP_PIXELS);
  context.drawImage(minimapImage, MINIMAP_SOURCE_ORIGIN, MINIMAP_SOURCE_ORIGIN, MINIMAP_SOURCE_SIZE, MINIMAP_SOURCE_SIZE, 0, 0, MINIMAP_PIXELS, MINIMAP_PIXELS);
  // Default keeps the nearest-8 preview used for the same-camera HUD. ?minimap=all
  // shows all 21 recovered quest triggers for inspection; neither reproduces the
  // original active-quest icon state machine/colour filtering yet.
  const nearbyQuests = !questPreview ? [] : params.get('minimap') === 'all'
    ? questAreas
    : [...questAreas]
      .sort((a, b) => Math.hypot(a.position[0] - position[0], a.position[2] - position[2]) - Math.hypot(b.position[0] - position[0], b.position[2] - position[2]))
      .slice(0, 8);
  for (const area of nearbyQuests) {
    const qx = ((area.position[0] - MINIMAP_WORLD_MIN) / MINIMAP_WORLD_SPAN) * MINIMAP_PIXELS;
    const qy = ((MINIMAP_WORLD_MIN + MINIMAP_WORLD_SPAN - area.position[2]) / MINIMAP_WORLD_SPAN) * MINIMAP_PIXELS;
    if (qx < -16 || qy < -16 || qx > MINIMAP_PIXELS + 16 || qy > MINIMAP_PIXELS + 16) continue;
    const icon = area.kind === 'fire'
      ? (minimapFireTinted ?? minimapFireIcon)
      : (minimapAccidentTinted ?? minimapAccidentIcon);
    const ready = area.kind === 'fire' ? minimapFireReady : minimapAccidentReady;
    if (ready) context.drawImage(icon, qx - 12, qy - 12, 24, 24);
  }
  const markerX = ((position[0] - MINIMAP_WORLD_MIN) / MINIMAP_WORLD_SPAN) * MINIMAP_PIXELS;
  const markerY = ((MINIMAP_WORLD_MIN + MINIMAP_WORLD_SPAN - position[2]) / MINIMAP_WORLD_SPAN) * MINIMAP_PIXELS;
  context.save();
  context.translate(markerX, markerY);
  context.rotate(yaw);
  if (minimapPlayerReady) {
    context.drawImage(minimapPlayerImage, -30, -30, 60, 60);
  } else {
    context.beginPath();
    context.moveTo(0, -15);
    context.lineTo(10, 12);
    context.lineTo(0, 7);
    context.lineTo(-10, 12);
    context.closePath();
    context.fillStyle = '#f4f1dc';
    context.strokeStyle = '#17130d';
    context.lineWidth = 2;
    context.fill();
    context.stroke();
  }
  context.restore();
};
const cameraArmOverride = Number(params.get('arm'));
if (Number.isFinite(cameraArmOverride) && cameraArmOverride > 0) CAMERA.armLength = cameraArmOverride;
const cameraFovOverride = Number(params.get('fov'));
if (Number.isFinite(cameraFovOverride) && cameraFovOverride > 0) CAMERA.fov = cameraFovOverride;
const exposureOverride = params.has('exposure') ? Number(params.get('exposure')) : 0.55;
if (Number.isFinite(exposureOverride) && exposureOverride > 0) {
  // Preview exposure calibration against the same-camera original: the original
  // start frame is in shade and has mean luma ~56, while the uncalibrated Web
  // frame is ~86. This is not a recovered UE auto-exposure/tone curve.
  viewer.scene.imageProcessingConfiguration.exposure = exposureOverride;
}
if (params.get('ssao') !== '0') {
  // Preview contact shading for the same-camera comparison. This is a
  // screen-space approximation, not a reconstruction of the original AO/lightmaps.
  const ssao = new SSAO2RenderingPipeline('preview-ssao', viewer.scene, { ssaoRatio: 0.75, blurRatio: 1 }, [viewer.camera]);
  ssao.totalStrength = 0.9;
  ssao.radius = 0.5;
  ssao.samples = 16;
  ssao.expensiveBlur = false;
}
const absoluteCamera = (params.get('cam') ?? '').split(',').map(Number);
const absoluteYaw = Number(params.get('camyaw'));
const absolutePitch = Number(params.get('campitch'));
const hasAbsoluteCamera = absoluteCamera.length === 3 && absoluteCamera.every(Number.isFinite);
const requestedDistrict = params.get('district') ?? 'ResidentialArea1';
const plazaMode = params.get('plaza') === '1';
const freeMode = params.get('mode') === 'free';
const exactSpawn = params.get('exact') === '1';
const startupMode = params.get('startup') === '1' || plazaMode;
if (freeMode) {
  document.title = 'UNDEFEATED · 自由破坏预览';
  const badge = document.querySelector<HTMLElement>('.play-badge');
  if (badge) badge.textContent = '自由破坏预览 · 非原版';
  const warn = document.querySelector<HTMLElement>('.warn');
  if (warn) warn.textContent = '自由破坏为可选预览：可摧毁市民/车辆/道具，市民会复活；镭射眼需 ?heat=1；任务和完整原版 AI 尚未接入。';
  el('hud-free-row').hidden = false;
}
const playDistrict = plazaMode ? 'MainLevel' : startupMode ? 'ResidentialArea1' : requestedDistrict;
let player: OriginalPlayer | undefined;
let character: Character | undefined;
let combat: Combat | undefined;
let population: Population | undefined;
let shadows: ShadowGenerator | undefined;
type QuestArea = { id: string; kind: string; position: Vec3; radius?: number };
let questAreas: QuestArea[] = [];
const questPreview = params.get('quests') === '1';
let questMessageUntil = 0;
const visitedQuests = new Set<string>();
const crosswalkMarkers: Vec3[] = [];
const questHint = el('quest-hint');

viewer.onProgress = (message, done, total) => {
  el('load-message').textContent = message;
  el<HTMLProgressElement>('progress').max = Math.max(total, 1);
  el<HTMLProgressElement>('progress').value = done;
};
input.onPause = () => {
  if (document.body.dataset.ready !== 'play') return;
  paused.hidden = false;
};
paused.onclick = () => {
  paused.hidden = true;
  input.clear();
  input.active = true;
  canvas.focus();
};

function insideBox(point: Vec3, boxes: { min: Vec3; max: Vec3 }[], margin = 0.55): boolean {
  return boxes.some(box => point[0] > box.min[0] - margin && point[0] < box.max[0] + margin &&
    point[2] > box.min[2] - margin && point[2] < box.max[2] + margin &&
    point[1] > box.min[1] - 0.2 && point[1] < box.max[1] + 1.6);
}

try {
  await viewer.load();
  if (!viewer.terrainManifest) throw new Error('地形清单未载入');
  await viewer.select(startupMode ? '__startup__' : requestedDistrict);
  // The world uses thin-instanced meshes for merged props. In this Babylon
  // path the thin-instance buffer does not draw, so materialize the instances
  // that matter for the playable slice as regular meshes with decomposed TRS.
  const materializeThin = (matches: (name: string) => boolean, center?: [number, number], radius = Infinity) => {
    for (const candidate of [...viewer.scene.meshes]) {
      if (!matches(candidate.name)) continue;
      const source = candidate as Mesh;
      const thin = source as unknown as { thinInstanceCount?: number; _thinInstanceDataStorage?: { matrixData?: Float32Array } };
      const count = thin.thinInstanceCount ?? 0;
      const data = thin._thinInstanceDataStorage?.matrixData;
      if (!data || count < 1) continue;
      for (let index = 0; index < count; index++) {
        const matrix = Array.from(data.slice(index * 16, index * 16 + 16));
        if (matrix.length < 16) continue;
        const clone = source.clone(`${source.name}-solid-${index}`, null, true);
        if (!clone) continue;
        const scale = new Vector3(), rotation = new Quaternion(), position = new Vector3();
        Matrix.FromArray(matrix).decompose(scale, rotation, position);
        if (center && Math.hypot(position.x - center[0], position.z - center[1]) > radius) continue;
        clone.thinInstanceCount = 0;
        clone.position.copyFrom(position);
        clone.scaling.copyFrom(scale);
        clone.rotationQuaternion = rotation;
        clone.setEnabled(true);
        clone.isVisible = true;
        clone.alwaysSelectAsActiveMesh = true;
      }
      source.setEnabled(false);
    }
  };
  materializeThin(name => /SM_Floor12000x15000/i.test(name));
  materializeThin(name => /Bench/i.test(name));

  // The static world includes reference-pose skeletal citizens baked into the
  // MainLevel batches. B1 has no population/AI yet, so hide those mannequins
  // rather than presenting them as live characters next to the player.
  for (const mesh of viewer.scene.meshes) {
    if (/^MainLevel:/.test(mesh.name) && /SK_Male|SK_Hair|SK_Sunglasses/.test(mesh.name)) {
      mesh.setEnabled(false);
      mesh.isVisible = false;
    }
  }
  if (new URLSearchParams(location.search).get('debug') === 'floors') {
    for (const mesh of viewer.scene.meshes) {
      if (!/SM_Floor12000x15000/i.test(mesh.name)) continue;
      const material = mesh.material as unknown as { emissiveColor?: { set(...values: number[]): void }; albedoColor?: { set(...values: number[]): void } } | null;
      material?.emissiveColor?.set(1, 0, 0);
      material?.albedoColor?.set(1, 0, 0);
    }
  }
  el('load-title').textContent = '载入原角色与地形';
  el('load-message').textContent = '读取 144 块原高度场与街区碰撞代理…';
  // The original program shows a dynamic character shadow. Use the viewer's
  // existing source-sun direction; only the player casts, while static scenery
  // receives. This is preview lighting, not the original shadow cascade.
  const sourceSun = viewer.scene.lights.find(light => light.name === 'source-sun-direction') as DirectionalLight | undefined;
  if (sourceSun && params.get('shadows') !== '0') {
    shadows = new ShadowGenerator(1024, sourceSun);
    shadows.useBlurExponentialShadowMap = true;
    shadows.blurKernel = 16;
    shadows.setDarkness(0.35);
    for (const mesh of viewer.scene.meshes) {
      if (mesh.isEnabled() && mesh.isVisible && mesh.getTotalVertices() > 0) mesh.receiveShadows = true;
    }
  }
  const terrain = await TerrainHeightfield.load(viewer.terrainManifest);
  const surfaces = await WalkableSurfaces.load('/assets/world/walkable-surfaces.json');
  if (params.get('traffic') === '1') {
    const traffic = await fetch('/assets/world/traffic-markers.json').then(response => response.ok ? response.json() : null).catch(() => null) as { markers?: Array<{ kind: string; position: Vec3 }> } | null;
    const crosswalkMaterial = new StandardMaterial('crosswalk-marker-mat', viewer.scene);
    crosswalkMaterial.emissiveColor = new Color3(0.95, 0.92, 0.55);
    crosswalkMaterial.diffuseColor = new Color3(0.95, 0.92, 0.55);
    crosswalkMaterial.disableLighting = true;
    for (const marker of traffic?.markers ?? []) {
      if (marker.kind !== 'crosswalk') continue;
      crosswalkMarkers.push(marker.position);
      const ring = CreateTorus('crosswalk-marker', { diameter: 4.4, thickness: 0.1, tessellation: 20 }, viewer.scene);
      ring.position.set(marker.position[0], marker.position[1] + 0.08, marker.position[2]);
      ring.material = crosswalkMaterial;
      ring.isPickable = false;
    }
    if (crosswalkMarkers.length) el('hud-crosswalk-row').hidden = false;
  }
  const quests = await fetch('/assets/world/quest-areas.json').then(response => response.ok ? response.json() : null).catch(() => null) as { areas?: QuestArea[] } | null;
  questAreas = quests?.areas ?? [];
  if (params.get('quests') === '1') {
    if (questAreas.length) el('hud-quest-row').hidden = false;
    for (const area of questAreas) {
      const diameter = Math.max(1.6, Math.min(100, (area.radius ?? 6) * 2));
      const marker = CreateTorus(`quest/${area.id}`, { diameter, thickness: 0.14, tessellation: 32 }, viewer.scene);
      marker.position.set(area.position[0], area.position[1] + 0.3, area.position[2]);
      const material = new StandardMaterial(`quest-mat/${area.id}`, viewer.scene);
      const color = area.kind === 'fire' ? new Color3(1, 0.24, 0.03) : new Color3(0.12, 0.62, 1);
      material.emissiveColor = color;
      material.diffuseColor = color;
      material.disableLighting = true;
      marker.material = material;
      marker.isPickable = false;
    }
  }
  if (new URLSearchParams(location.search).get('floors') === 'overlay') {
    // Preview-only fallback for recovered ground-brick floors that do not render
    // in the current material path. Uses the authored GroundBrick_B_A texture.
    for (const surface of surfaces.surfaces) {
      if (!surface.material?.includes('MI_GroundBrick') || surface.area > 200_000) continue;
      if (surface.level !== 'MainLevel' && surface.level !== playDistrict) continue;
      const width = surface.maxX - surface.minX, depth = surface.maxZ - surface.minZ;
      const ground = CreateGround(`floor-overlay/${surface.id}`, { width, height: depth }, viewer.scene);
      ground.position.set((surface.minX + surface.maxX) / 2, surface.top + 0.02, (surface.minZ + surface.maxZ) / 2);
      const material = new StandardMaterial(`floor-overlay-mat/${surface.id}`, viewer.scene);
      const texture = new Texture('/assets/world/textures/Game/Downtown/Textures/GroundBrick_B_A.png', viewer.scene);
      texture.uScale = width / 4; texture.vScale = depth / 4; texture.hasAlpha = false;
      material.diffuseTexture = texture;
      material.specularColor.set(0, 0, 0);
      material.backFaceCulling = false;
      ground.material = material;
      ground.receiveShadows = true;
      ground.isPickable = false;
    }
  }
  const selected = startupMode
    ? viewer.manifest.levels.filter(level => viewer.streamingManifest.baseline.packages.includes(level.package))
    : viewer.manifest.levels.filter(level => level.id === 'MainLevel' || level.id === playDistrict);
  const collision = buildCollision(selected, viewer.manifest.assets);
  const candidate = viewer.manifest.spawnCandidates?.find(item => item.levelId === 'MainLevel');
  const legacy = playDistrict === 'ResidentialArea1'
    ? await fetch('/assets/city/manifest.json', { cache: 'force-cache' }).then(response => response.json()).catch(() => null) as { spawn?: Vec3; originUE?: Vec3 } | null
    : null;
  // The old prototype city manifest is district-local: its originUE is
  // [-10000, -55000, 0] cm. The restored world uses absolute metres, so the
  // recorded spawn and preview population must be shifted by originUE/100.
  const offsetX = (legacy?.originUE?.[0] ?? 0) / 100;
  const offsetZ = (legacy?.originUE?.[1] ?? 0) / 100;
  const districtLevel = viewer.manifest.levels.find(level => level.id === playDistrict);
  const districtBounds = districtLevel?.bounds;
  const fallbackX = districtBounds ? (districtBounds.min[0] + districtBounds.max[0]) / 2 : (candidate?.position[0] ?? 50);
  const fallbackZ = districtBounds ? (districtBounds.min[2] + districtBounds.max[2]) / 2 : (candidate?.position[2] ?? 1.37);
  let baseX = (legacy?.spawn?.[0] ?? fallbackX) + (legacy ? offsetX : 0);
  let baseZ = (legacy?.spawn?.[2] ?? fallbackZ) + (legacy ? offsetZ : 0);
  const at = params.get('at');
  if (at) {
    const [x, z] = at.split(',').map(Number);
    if (Number.isFinite(x) && Number.isFinite(z)) { baseX = x; baseZ = z; }
  } else if (plazaMode) {
    baseX = 20; baseZ = 0;
  }
  materializeThin(name => /Tree|Palm/i.test(name), [baseX, baseZ], 120);
  materializeThin(name => /Billboard/i.test(name), [baseX, baseZ], 120);
  const rotation = candidate?.rotation ?? [0, 0, 0, 1];
  input.yaw = legacy ? Math.PI : 2 * Math.atan2(rotation[1], rotation[3]);
  const yawParam = params.get('yaw');
  if (yawParam !== null && Number.isFinite(Number(yawParam))) input.yaw = Number(yawParam);
  else if (plazaMode) input.yaw = 0;
  const terrainGround = terrain.heightAt(baseX, baseZ) ?? 0;
  const floorGround = surfaces.topAt(baseX, baseZ, terrainGround + 0.75) ?? -Infinity;
  const candidateGround = Math.max(terrainGround, floorGround);
  let spawn: Vec3 = [baseX, candidateGround + 0.02, baseZ];
  // The original spawn point is not always a viewer-safe point (district
  // centres can be inside collision proxies). Search outward in rings up to
  // 30 m; keep the first terrain point outside the static AABB set.
  const spawnOffsets: Array<[number, number]> = [[0, 0]];
  for (let radius = 3; radius <= 30; radius += 3) {
    for (let dx = -radius; dx <= radius; dx += 3) {
      for (let dz = -radius; dz <= radius; dz += 3) {
        if (Math.max(Math.abs(dx), Math.abs(dz)) === radius) spawnOffsets.push([dx, dz]);
      }
    }
  }
  for (const [dx, dz] of exactSpawn ? [[0, 0] as [number, number]] : spawnOffsets) {
    const x = baseX + dx, z = baseZ + dz;
    const terrainY = terrain.heightAt(x, z) ?? 0;
    const floorY = surfaces.topAt(x, z, terrainY + 0.75);
    const y = Math.max(terrainY, floorY ?? -Infinity) + 0.02;
    if (!exactSpawn && insideBox([x, y, z], collision.boxes)) continue;
    // Keep a 4 m third-person camera slot clear so a wall/balustrade does not
    // force the camera into the character at spawn. exact=1 is inspection-only
    // and deliberately bypasses both checks.
    if (!exactSpawn) {
      const cameraX = x - Math.sin(input.yaw) * 4, cameraZ = z - Math.cos(input.yaw) * 4;
      if (insideBox([cameraX, y + 1.6, cameraZ], collision.boxes)) continue;
    }
    spawn = [x, y, z];
    break;
  }
  const terrainBounds = terrain.bounds();
  const bounds: Bounds = { min: [terrainBounds.min[0], -180, terrainBounds.min[2]], max: [terrainBounds.max[0], terrainBounds.max[1] + 600, terrainBounds.max[2]] };
  player = new OriginalPlayer(spawn, terrain, collision.spatial, bounds, surfaces);
  player.heading = input.yaw;
  let nearestBuilding: { distance: number; yaw: number } | undefined;
  for (const mesh of viewer.scene.meshes) {
    if (!mesh.isEnabled() || !mesh.isVisible) continue;
    const materialName = mesh.material?.name ?? '';
    if (!/Building|Facade|Wall|House/i.test(materialName)) continue;
    const center = mesh.getBoundingInfo?.()?.boundingBox?.centerWorld;
    if (!center) continue;
    const dx = center.x - spawn[0], dz = center.z - spawn[2];
    const distance = Math.hypot(dx, dz);
    if (distance < 8 || distance > 160) continue;
    if (!nearestBuilding || distance < nearestBuilding.distance) nearestBuilding = { distance, yaw: Math.atan2(dx, dz) };
  }
  if (nearestBuilding && yawParam === null && !plazaMode) {
    input.yaw = nearestBuilding.yaw;
    player.heading = input.yaw;
  }
  character = new Character(viewer.scene);
  await character.load(shadows, params.get('skin') === 'homelander' ? 'homelander' : 'original');
  const footsteps = new Footsteps(params.get('audio') !== '0');
  character.onFootstep = () => footsteps.play();
  void footsteps.load().catch(error => console.warn('footstep audio unavailable', error));
  if (params.get('skin') === 'homelander' && !freeMode) {
    const badge = document.querySelector<HTMLElement>('.play-badge');
    if (badge) badge.textContent = 'Homelander · 动作映射';
  }
  character.update(player, 1);
  // Preview population: original citizen/vehicle/prop meshes and animations,
  // but placements/routes come from the previous prototype manifest, not a
  // recovered original AI/quest system. Damage stays in baseline mode here.
  population = new Population(viewer.scene, collision.boxes, (x, z, feetY) => {
    const ground = terrain.heightAt(x, z) ?? 0;
    const floor = surfaces.topAt(x, z, feetY, 0.75);
    return floor !== undefined ? Math.max(ground, floor) : ground;
  });
  if (playDistrict === 'ResidentialArea1') {
    let manifestUrl = '/assets/population-manifest.json';
    let populationOffset: [number, number] = [offsetX, offsetZ];
    const populationMode = new URLSearchParams(location.search).get('population');
    if (populationMode === 'original') {
      const original = await fetch('/assets/world/population-original-citizens.json', { method: 'HEAD' }).catch(() => null);
      if (original?.ok) {
        // Optional inspection mode generated by
        // tools/asset-pipeline/export-citizen-spawns.mjs from the decoded
        // CitizenWayPoint spawn points; already in restored-world metres.
        manifestUrl = '/assets/world/population-original-citizens.json';
        populationOffset = [0, 0];
      }
    } else {
      const waypointRoutes = await fetch('/assets/world/population-waypoint-routes.json', { method: 'HEAD' }).catch(() => null);
      if (waypointRoutes?.ok) {
        // Default preview placements retained; routes use recovered child
        // waypoints where available.
        manifestUrl = '/assets/world/population-waypoint-routes.json';
        populationOffset = [0, 0];
      }
    }
    await population.load({ manifestUrl, worldOffset: populationOffset, sandbox: true });
  }
  population.pause(true);
  combat = new Combat(viewer.scene, input, player as unknown as PlayerMotor, character, population, viewer.camera, collision.boxes, { heatVision: params.get('heat') === '1' });
  combat.mode = freeMode ? 'free' : 'baseline';
  await combat.load();
  combat.onSound = kind => {
    if (kind === 'swing') footsteps.playSwing();
    else if (kind === 'whoosh') footsteps.playWhoosh();
    else if (kind === 'heavy') footsteps.playHeavy();
    else if (kind === 'destruction') footsteps.playDestruction();
    else footsteps.playImpact();
  };
  viewer.camera.detachControl();
  viewer.camera.minZ = 0.12;
  // HeroComponent switches Camera.FieldOfView by HeroRank:
  // 0..6 -> 92,94,96,98,100,100,100. The preview starts at rank 0.
  const applyFov = () => {
    const aspect = viewer.engine.getRenderWidth() / Math.max(1, viewer.engine.getRenderHeight());
    viewer.camera.fov = 2 * Math.atan(Math.tan((CAMERA.fov * Math.PI) / 360) / aspect);
  };
  applyFov();
  window.addEventListener('resize', applyFov);

  const objects = selected.reduce((sum, level) => sum + level.objects.filter(object => !(object.visibilityProperties?.bHiddenInGame === true || object.visibilityProperties?.bVisible === false || object.visibilityProperties?.actorHidden === true)).reduce((n, object) => n + sourceObjectCount(object), 0), 0);
  canvas.dataset.objects = String(objects);
  canvas.dataset.terrain = String(terrain.count);
  canvas.dataset.failures = String(viewer.failuresList.length);
  canvas.dataset.textureFailures = String(viewer.materials.textureFailures.size);

  const base = new Vector3();
  const forward = new Vector3();
  const right = new Vector3();
  const look = new Vector3();
  const cameraTarget = new Vector3();
  let cameraInitialized = false;
  let cameraArm = CAMERA.armLength;
  const updateCamera = (dt = 1 / 60) => {
    if (hasAbsoluteCamera) {
      const [x, y, z] = absoluteCamera;
      const yaw = Number.isFinite(absoluteYaw) ? absoluteYaw : 0;
      const pitch = Number.isFinite(absolutePitch) ? absolutePitch : 0;
      viewer.camera.position.set(x, y, z);
      viewer.camera.setTarget(new Vector3(x + Math.sin(yaw) * Math.cos(pitch), y + Math.sin(pitch), z + Math.cos(yaw) * Math.cos(pitch)));
      const aspect = viewer.engine.getRenderWidth() / Math.max(1, viewer.engine.getRenderHeight());
      viewer.camera.fov = 2 * Math.atan(Math.tan((CAMERA.fov * Math.PI) / 360) / aspect);
      return;
    }
    if (!player) return;
    const yaw = input.yaw, pitch = input.pitch;
    const speed3 = Math.hypot(player.velocity[0], player.velocity[1], player.velocity[2]);
    const far = speed3 > CAMERA.farSpeed;
    const targetArm = far ? CAMERA.farArmLength : combat?.attacking ? CAMERA.attackArmLength : CAMERA.armLength;
    cameraArm += (targetArm - cameraArm) * (1 - Math.exp(-(far ? CAMERA.farArmSpeed : CAMERA.armSpeed) * dt));
    right.set(Math.cos(yaw), 0, -Math.sin(yaw));
    base.set(player.position[0], player.position[1] + CAMERA.boomHeight, player.position[2]);
    base.addInPlace(right.scale(CAMERA.socketRight));
    base.y += CAMERA.socketUp;
    forward.set(Math.sin(yaw) * Math.cos(pitch), -Math.sin(pitch), Math.cos(yaw) * Math.cos(pitch));
    const offset = forward.scale(-cameraArm);
    const nearby = collision.spatial.nearby(base.x, base.z, cameraArm + 2);
    const hit = firstHit(base.asArray() as Vec3, offset.asArray() as Vec3, nearby, [0.2, 0.2, 0.2]);
    const safe = hit ? Math.max(0.08, hit.time - 0.02) : 1;
    look.copyFrom(base).addInPlace(forward.scale(20));
    look.y += 0.25;
    const desired = base.add(offset.scale(safe));
    if (!cameraInitialized) {
      viewer.camera.position.copyFrom(desired);
      cameraTarget.copyFrom(look);
      cameraInitialized = true;
    } else {
      // PlayerBP CameraLagSpeed/CameraRotationLagSpeed = 15. When the boom
      // collides with geometry, ease quickly toward the safe point instead of
      // snapping every frame (which reads as flight jitter near buildings).
      const alpha = 1 - Math.exp(-(hit ? 45 : CAMERA.lagSpeed) * dt);
      viewer.camera.position.copyFrom(Vector3.Lerp(viewer.camera.position, desired, alpha));
      cameraTarget.copyFrom(Vector3.Lerp(cameraTarget, look, alpha));
    }
    viewer.camera.setTarget(cameraTarget);
    const cameraGround = terrain.heightAt(viewer.camera.position.x, viewer.camera.position.z) ?? 0;
    if (viewer.camera.position.y < cameraGround + 0.3) viewer.camera.position.y = cameraGround + 0.3;
  };
  updateCamera();

  let accumulator = 0;
  let hudTime = 0;
  viewer.scene.registerBeforeRender(() => {
    if (!player || !character || !input.active) return;
    const dt = Math.min(viewer.engine.getDeltaTime() / 1000, 0.05);
    population?.update(dt, player.position);
    player.setDynamicBoxes(population?.solidBoxes ?? []);
    accumulator += dt;
    while (accumulator >= 1 / 120) { player.update(1 / 120, input); accumulator -= 1 / 120; }
    character.update(player, dt);
    footsteps.setFlightWind(player.flying, Math.max(
      Math.hypot(player.velocity[0], player.velocity[2]) / 40,
      Math.abs(player.velocity[1]) / 40,
    ));
    combat?.update(dt);
    if (combat?.consumeCameraSnap()) cameraInitialized = false;
    const lock = combat?.getLockTarget();
    if (lock) {
      const viewport = viewer.camera.viewport.toGlobal(viewer.engine.getRenderWidth(), viewer.engine.getRenderHeight());
      const projected = Vector3.Project(Vector3.FromArray(lock.center), Matrix.IdentityReadOnly, viewer.scene.getTransformMatrix(), viewport);
      if (projected.z > 0 && projected.z < 1) {
        lockReticle.style.left = `${(projected.x / viewer.engine.getRenderWidth()) * canvas.clientWidth}px`;
        lockReticle.style.top = `${(projected.y / viewer.engine.getRenderHeight()) * canvas.clientHeight}px`;
        lockDistance.textContent = `${lock.distance.toFixed(1)} m`;
        lockReticle.hidden = false;
      } else {
        lockReticle.hidden = true;
      }
    } else {
      lockReticle.hidden = true;
    }
    updateCamera(dt);
    hudTime += dt;
    if (hudTime > 0.1) {
      hudTime = 0;
      const stats = player.stats();
      if (originalHudMode) drawMinimap(stats.position, input.yaw);
      canvas.dataset.player = JSON.stringify(stats);
      canvas.dataset.fps = String(viewer.engine.getFps());
      el('hud-position').textContent = stats.position.map(value => value.toFixed(1)).join(' / ');
      el('hud-mode').textContent = stats.flying ? (stats.state === 'fly' ? '飞行冲刺' : '飞行悬停') : stats.grounded ? (stats.state === 'run' ? '地面移动' : '地面待机') : '腾空';
      el('hud-speed').textContent = `${stats.speed.toFixed(1)} m/s${stats.charge > 0 ? ` · 蓄升 ${stats.charge.toFixed(1)}s` : ''}`;
      el('hud-fps').textContent = String(Math.round(viewer.engine.getFps()));
      if (freeMode && combat) {
        el('hud-destroyed').textContent = String(combat.destroyed);
        el('hud-hits').textContent = String(combat.hits);
      }
      if (crosswalkMarkers.length) {
        let nearest = Infinity;
        for (const marker of crosswalkMarkers) nearest = Math.min(nearest, Math.hypot(marker[0] - stats.position[0], marker[2] - stats.position[2]));
        el('hud-crosswalk').textContent = `${nearest.toFixed(1)} m`;
      }
      if (questPreview && questAreas.length) {
        let nearest: { area: QuestArea; distance: number } | undefined;
        for (const area of questAreas) {
          const distance = Math.hypot(area.position[0] - stats.position[0], area.position[1] - stats.position[1], area.position[2] - stats.position[2]);
          const radius = area.radius ?? 6;
          if (distance < radius && (!nearest || distance < nearest.distance)) nearest = { area, distance };
        }
        if (nearest) {
          visitedQuests.add(nearest.area.id);
          if (input.pressed('KeyF')) questMessageUntil = performance.now() + 2200;
          const active = performance.now() < questMessageUntil;
          questHint.hidden = false;
          questHint.textContent = active
            ? `任务区域 ${nearest.area.id} · 原版任务状态未恢复`
            : `任务区域 ${nearest.area.id} · 已发现 · F 查看`;
        } else {
          questHint.hidden = true;
        }
        el('hud-quests').textContent = `${visitedQuests.size}/${questAreas.length}`;
      } else {
        questHint.hidden = true;
      }
    }
  });

  paused.hidden = true;
  input.clear();
  input.active = true;
  canvas.focus();
  population?.pause(false);
  document.body.dataset.ready = 'play';
  el('loading').hidden = true;
  if (new URLSearchParams(location.search).get('debug') === '1') {
    (window as typeof window & { __undefeatedPlay?: unknown }).__undefeatedPlay = {
      viewer, player, character, input, collision, combat, population, shadows, terrain, surfaces, footsteps,
      pick: (x: number, y: number) => {
        for (const mesh of viewer.scene.meshes) {
          mesh.isPickable = true;
          mesh.computeWorldMatrix(true);
          mesh.refreshBoundingInfo({});
          const thin = mesh as unknown as { thinInstanceCount?: number; thinInstanceEnablePicking?: boolean; thinInstanceRefreshBoundingInfo?: (force?: boolean) => void };
          if ((thin.thinInstanceCount ?? 0) > 0) {
            thin.thinInstanceEnablePicking = true;
            thin.thinInstanceRefreshBoundingInfo?.(true);
          }
        }
        const canvas = viewer.engine.getRenderingCanvas();
        const rect = canvas?.getBoundingClientRect();
        const renderX = rect ? (x - rect.left) * viewer.engine.getRenderWidth() / rect.width : x;
        const renderY = rect ? (y - rect.top) * viewer.engine.getRenderHeight() / rect.height : y;
        const ray = viewer.scene.createPickingRay(renderX, renderY, Matrix.Identity(), viewer.camera);
        const hit = viewer.scene.pickWithRay(ray, () => true, true);
        return hit?.hit ? { mesh: hit.pickedMesh?.name, material: hit.pickedMesh?.material?.name, point: hit.pickedPoint?.asArray() } : null;
      },
      bakeFloors: () => {
        let fixed = 0;
        for (const candidate of viewer.scene.meshes) {
          if (!/SM_Floor12000x15000/i.test(candidate.name)) continue;
          const thin = candidate as unknown as { thinInstanceCount?: number; _thinInstanceDataStorage?: { matrixData?: Float32Array } };
          if (thin.thinInstanceCount !== 1 || !thin._thinInstanceDataStorage?.matrixData) continue;
          const mesh = candidate as Mesh;
          const matrix = Matrix.FromArray(Array.from(thin._thinInstanceDataStorage.matrixData.slice(0, 16)));
          thin.thinInstanceCount = 0;
          mesh.bakeTransformIntoVertices(matrix);
          mesh.refreshBoundingInfo();
          mesh.alwaysSelectAsActiveMesh = true;
          fixed++;
        }
        return fixed;
      },
    };
  }
  console.info('B1 playable slice ready', { spawn, objects, collision: collision.stats });
} catch (error) {
  el('load-title').textContent = '可玩切片未就绪';
  el('load-message').textContent = error instanceof Error ? error.message : String(error);
  document.body.dataset.ready = 'error';
  console.error(error);
}

window.addEventListener('pagehide', () => viewer.dispose(), { once: true });
