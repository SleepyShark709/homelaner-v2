import './play-original.css';
import { Vector3 } from '@babylonjs/core/Maths/math.vector';
import { DirectionalLight } from '@babylonjs/core/Lights/directionalLight';
import { ShadowGenerator } from '@babylonjs/core/Lights/Shadows/shadowGenerator';
import '@babylonjs/core/Lights/Shadows/shadowGeneratorSceneComponent';
import { OriginalWorld } from './world/OriginalWorld';
import { Character } from './game/Character';
import { Input } from './game/Input';
import { Combat } from './game/Combat';
import { Population } from './game/Population';
import type { PlayerMotor } from './game/PlayerMotor';
import { firstHit } from './game/collision';
import type { Bounds, Vec3 } from './game/collision';
import { buildCollision } from './play/CollisionWorld';
import { OriginalPlayer } from './play/OriginalPlayer';
import { TerrainHeightfield } from './play/TerrainHeightfield';
import { sourceObjectCount } from './world/types';

document.title = 'UNDEFEATED · 原版可玩基线 B1';
document.querySelector<HTMLDivElement>('#app')!.innerHTML = `
  <canvas id="world" tabindex="0" aria-label="原版城市可玩切片，WASD 移动，拖动鼠标转向"></canvas>
  <header class="play-header"><div class="play-brand">UNDEFEATED<small>ORIGINAL PLAYABLE BASELINE · B1</small></div><div class="play-badge">原生资产 · 预览物理</div></header>
  <aside class="play-panel">
    <h1>原版街区 · 可玩切片</h1>
    <p>原角色、原骨架与原始街区资产；地形高度来自原 Landscape 高度场。建筑碰撞为静态 AABB 代理，跳跃/重力/相机手感仍是预览。</p>
    <p class="warn">本切片不是完整原版玩法：AI、车辆、任务、攻击、热视线与自由破坏尚未接入。</p>
    <div class="play-keys">
      <kbd>W A S D</kbd><span>移动</span>
      <kbd>拖动鼠标</kbd><span>转向</span>
      <kbd>SPACE</kbd><span>地面跳跃 / 空中开飞 / 飞行退飞</span>
      <kbd>E / Q</kbd><span>上升 / 下降；地面按住 E 蓄升</span>
      <kbd>SHIFT</kbd><span>冲刺</span>
      <kbd>ALT</kbd><span>慢行</span>
      <kbd>F</kbd><span>互动（预留）</span>
      <kbd>R</kbd><span>回到出生点</span>
    </div>
  </aside>
  <div class="play-hud"><div>位置 <b id="hud-position">—</b></div><div>状态 <b id="hud-mode">—</b></div><div>速度 <b id="hud-speed">—</b></div><div>FPS <b id="hud-fps">—</b></div></div>
  <div class="play-loading" id="loading"><div><strong id="load-title">装配原版可玩街区</strong><p id="load-message">读取原关卡、材质与地形…</p><progress id="progress" max="1" value="0"></progress></div></div>
  <div class="play-paused" id="paused" hidden>已暂停 · 点击继续</div>`;

const el = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id) as T;
const canvas = el<HTMLCanvasElement>('world');
const viewer = new OriginalWorld(canvas);
const input = new Input(canvas);
// Original PlayerBP CameraBoom_GEN_VARIABLE: TargetArmLength=400 cm,
// SocketOffset=(0,50,90) cm, boom RelativeLocation Z=70 cm.
const CAMERA = { armLength: 4.0, boomHeight: 0.7, socketRight: 0.5, socketUp: 0.9, lagSpeed: 15, fov: 90 };
input.pitch = 0.02;
const paused = el('paused');
const requestedDistrict = new URLSearchParams(location.search).get('district') ?? 'ResidentialArea1';
const startupMode = new URLSearchParams(location.search).get('startup') === '1';
const playDistrict = startupMode ? 'ResidentialArea1' : requestedDistrict;
let player: OriginalPlayer | undefined;
let character: Character | undefined;
let combat: Combat | undefined;
let population: Population | undefined;
let shadows: ShadowGenerator | undefined;

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
  // The static world includes reference-pose skeletal citizens baked into the
  // MainLevel batches. B1 has no population/AI yet, so hide those mannequins
  // rather than presenting them as live characters next to the player.
  for (const mesh of viewer.scene.meshes) {
    if (/^MainLevel:/.test(mesh.name) && /SK_Male|SK_Hair|SK_Sunglasses/.test(mesh.name)) {
      mesh.setEnabled(false);
      mesh.isVisible = false;
    }
  }
  el('load-title').textContent = '载入原角色与地形';
  el('load-message').textContent = '读取 144 块原高度场与街区碰撞代理…';
  // The original program shows a dynamic character shadow. Use the viewer's
  // existing source-sun direction; only the player casts, while static scenery
  // receives. This is preview lighting, not the original shadow cascade.
  const sourceSun = viewer.scene.lights.find(light => light.name === 'source-sun-direction') as DirectionalLight | undefined;
  if (sourceSun) {
    shadows = new ShadowGenerator(1024, sourceSun);
    shadows.useBlurExponentialShadowMap = true;
    shadows.blurKernel = 16;
    shadows.setDarkness(0.35);
    for (const mesh of viewer.scene.meshes) {
      if (mesh.isEnabled() && mesh.isVisible && mesh.getTotalVertices() > 0) mesh.receiveShadows = true;
    }
  }
  const terrain = await TerrainHeightfield.load(viewer.terrainManifest);
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
  const baseX = (legacy?.spawn?.[0] ?? fallbackX) + (legacy ? offsetX : 0);
  const baseZ = (legacy?.spawn?.[2] ?? fallbackZ) + (legacy ? offsetZ : 0);
  const rotation = candidate?.rotation ?? [0, 0, 0, 1];
  input.yaw = legacy ? Math.PI : 2 * Math.atan2(rotation[1], rotation[3]);
  const candidateGround = terrain.heightAt(baseX, baseZ) ?? 0;
  let spawn: Vec3 = [baseX, candidateGround + 0.02, baseZ];
  for (const [dx, dz] of [[0, 0], [3, 0], [-3, 0], [0, 3], [0, -3], [5, 5], [-5, 5], [5, -5], [-5, -5]]) {
    const x = baseX + dx, z = baseZ + dz;
    const y = (terrain.heightAt(x, z) ?? 0) + 0.02;
    if (!insideBox([x, y, z], collision.boxes)) { spawn = [x, y, z]; break; }
  }
  const terrainBounds = terrain.bounds();
  const bounds: Bounds = { min: [terrainBounds.min[0], -180, terrainBounds.min[2]], max: [terrainBounds.max[0], terrainBounds.max[1] + 600, terrainBounds.max[2]] };
  player = new OriginalPlayer(spawn, terrain, collision.spatial, bounds);
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
  if (nearestBuilding) {
    input.yaw = nearestBuilding.yaw;
    player.heading = input.yaw;
  }
  character = new Character(viewer.scene);
  await character.load(shadows);
  character.update(player, 1);
  // Preview population: original citizen/vehicle/prop meshes and animations,
  // but placements/routes come from the previous prototype manifest, not a
  // recovered original AI/quest system. Damage stays in baseline mode here.
  population = new Population(viewer.scene, collision.boxes);
  if (playDistrict === 'ResidentialArea1') {
    let manifestUrl = '/assets/population-manifest.json';
    let populationOffset: [number, number] = [offsetX, offsetZ];
    if (new URLSearchParams(location.search).get('population') === 'original') {
      const original = await fetch('/assets/world/population-original-citizens.json', { method: 'HEAD' }).catch(() => null);
      if (original?.ok) {
        // Optional inspection mode generated by
        // tools/asset-pipeline/export-citizen-spawns.mjs from the decoded
        // CitizenWayPoint spawn points; already in restored-world metres.
        manifestUrl = '/assets/world/population-original-citizens.json';
        populationOffset = [0, 0];
      }
    }
    await population.load({ manifestUrl, worldOffset: populationOffset });
  }
  population.pause(true);
  combat = new Combat(viewer.scene, input, player as unknown as PlayerMotor, character, population, viewer.camera, collision.boxes, { heatVision: false });
  combat.mode = 'baseline';
  await combat.load();
  viewer.camera.detachControl();
  viewer.camera.minZ = 0.12;
  // HeroComponent interpolates Camera.FieldOfView to 90; UE's value is
  // horizontal, so convert to Babylon's vertical FOV at the current aspect.
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
  const updateCamera = (dt = 1 / 60) => {
    if (!player) return;
    const yaw = input.yaw, pitch = input.pitch;
    right.set(Math.cos(yaw), 0, -Math.sin(yaw));
    base.set(player.position[0], player.position[1] + CAMERA.boomHeight, player.position[2]);
    base.addInPlace(right.scale(CAMERA.socketRight));
    base.y += CAMERA.socketUp;
    forward.set(Math.sin(yaw) * Math.cos(pitch), -Math.sin(pitch), Math.cos(yaw) * Math.cos(pitch));
    const offset = forward.scale(-CAMERA.armLength);
    const nearby = collision.spatial.nearby(base.x, base.z, CAMERA.armLength + 2);
    const hit = firstHit(base.asArray() as Vec3, offset.asArray() as Vec3, nearby, [0.2, 0.2, 0.2]);
    const safe = hit ? Math.max(0.08, hit.time - 0.02) : 1;
    look.copyFrom(base).addInPlace(forward.scale(20));
    look.y += 0.25;
    const desired = base.add(offset.scale(safe));
    if (!cameraInitialized || hit) {
      viewer.camera.position.copyFrom(desired);
      cameraTarget.copyFrom(look);
      cameraInitialized = true;
    } else {
      // PlayerBP CameraLagSpeed/CameraRotationLagSpeed = 15.
      const alpha = 1 - Math.exp(-CAMERA.lagSpeed * dt);
      viewer.camera.position.copyFrom(Vector3.Lerp(viewer.camera.position, desired, alpha));
      cameraTarget.copyFrom(Vector3.Lerp(cameraTarget, look, alpha));
    }
    viewer.camera.setTarget(cameraTarget);
  };
  updateCamera();

  let accumulator = 0;
  let hudTime = 0;
  viewer.scene.registerBeforeRender(() => {
    if (!player || !character || !input.active) return;
    const dt = Math.min(viewer.engine.getDeltaTime() / 1000, 0.05);
    population?.update(dt);
    player.setDynamicBoxes(population?.solidBoxes ?? []);
    accumulator += dt;
    while (accumulator >= 1 / 120) { player.update(1 / 120, input); accumulator -= 1 / 120; }
    character.update(player, dt);
    combat?.update(dt);
    updateCamera(dt);
    hudTime += dt;
    if (hudTime > 0.1) {
      hudTime = 0;
      const stats = player.stats();
      canvas.dataset.player = JSON.stringify(stats);
      canvas.dataset.fps = String(viewer.engine.getFps());
      el('hud-position').textContent = stats.position.map(value => value.toFixed(1)).join(' / ');
      el('hud-mode').textContent = stats.flying ? (stats.state === 'fly' ? '飞行冲刺' : '飞行悬停') : stats.grounded ? (stats.state === 'run' ? '地面移动' : '地面待机') : '腾空';
      el('hud-speed').textContent = `${stats.speed.toFixed(1)} m/s${stats.charge > 0 ? ` · 蓄升 ${stats.charge.toFixed(1)}s` : ''}`;
      el('hud-fps').textContent = String(Math.round(viewer.engine.getFps()));
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
    (window as typeof window & { __undefeatedPlay?: unknown }).__undefeatedPlay = { viewer, player, character, input, collision, combat, population, shadows };
  }
  console.info('B1 playable slice ready', { spawn, objects, collision: collision.stats });
} catch (error) {
  el('load-title').textContent = '可玩切片未就绪';
  el('load-message').textContent = error instanceof Error ? error.message : String(error);
  document.body.dataset.ready = 'error';
  console.error(error);
}

window.addEventListener('pagehide', () => viewer.dispose(), { once: true });
