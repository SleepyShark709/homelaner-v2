import { Scene } from '@babylonjs/core/scene';
import { MeshBuilder } from '@babylonjs/core/Meshes/meshBuilder';
import type { Mesh } from '@babylonjs/core/Meshes/mesh';
import { StandardMaterial } from '@babylonjs/core/Materials/standardMaterial';
import { SpriteManager } from '@babylonjs/core/Sprites/spriteManager';
import { Sprite } from '@babylonjs/core/Sprites/sprite';
import '@babylonjs/core/Sprites/spriteSceneComponent';
import { Constants } from '@babylonjs/core/Engines/constants';
import { Color3, Color4 } from '@babylonjs/core/Maths/math.color';
import { Quaternion, Vector3 } from '@babylonjs/core/Maths/math.vector';
import type { Vec3 } from './collision';

export class Effects {
  private readonly red: StandardMaterial;
  private readonly gold: StandardMaterial;
  private readonly blue: StandardMaterial;
  private readonly beams: Mesh[];
  private readonly sparks: { mesh: Mesh; age: number; life: number; velocity: Vector3; size: number }[] = [];
  private readonly streaks: { mesh: Mesh; age: number; life: number; size: number }[] = [];
  private readonly slashes: { sprite: Sprite; age: number; life: number }[] = [];
  private readonly slashManager: SpriteManager;
  private readonly dust: { sprite: Sprite; age: number; life: number; size: number }[] = [];
  private readonly dustManager: SpriteManager;
  private readonly blastManager: SpriteManager;
  private readonly blasts: { sprite: Sprite; age: number; life: number; startSize: number; grow: number; alpha: number }[] = [];
  private dustClock = 0;
  private trailClock = 0;
  constructor(readonly scene: Scene) {
    const material = (name: string, color: string) => { const mat = new StandardMaterial(name, scene); mat.emissiveColor = Color3.FromHexString(color); mat.disableLighting = true; return mat; };
    this.red = material('heat-red', '#ff3122'); this.gold = material('impact-gold', '#ffd38a'); this.blue = material('fist-cyan', '#c5ffff');
    this.gold.alpha = 0.75; this.blue.alpha = 0.7;
    this.slashManager = new SpriteManager('normal-attack-slash-atlas', '/assets/vfx/-HeroGame/Res/Effect/T_ky_slash01_4x4.png', 16, { width: 512, height: 512 }, scene);
    this.slashManager.blendMode = Constants.ALPHA_ADD;
    this.slashManager.disableDepthWrite = true;
    this.slashManager.isPickable = false;
    this.dustManager = new SpriteManager('fly-smoke-atlas', '/assets/vfx/-HeroGame/Res/Effect/T_RaP_Smoke_puff_4x4_2k.png', 64, { width: 256, height: 256 }, scene);
    this.dustManager.blendMode = Constants.ALPHA_COMBINE;
    this.dustManager.disableDepthWrite = true;
    this.dustManager.isPickable = false;
    this.blastManager = new SpriteManager('start-sprint-blast', '/assets/vfx/InfinityBladeEffects/Effects/FX_Textures/Gradient/T_BlastWave.png', 8, { width: 512, height: 512 }, scene);
    this.blastManager.blendMode = Constants.ALPHA_ADD;
    this.blastManager.disableDepthWrite = true;
    this.blastManager.isPickable = false;
    this.beams = [0, 1].map(index => { const mesh = MeshBuilder.CreateCylinder(`eye-beam-${index}`, { height: 1, diameter: 0.035, tessellation: 6 }, scene); mesh.material = this.red; mesh.isPickable = false; mesh.setEnabled(false); return mesh; });
  }
  private streak(point: Vec3, direction: Vector3, color: 'gold' | 'blue', length: number, life: number): void {
    if (this.streaks.length >= 96) this.streaks.shift()!.mesh.dispose();
    const mesh = MeshBuilder.CreateSphere('speed-streak', { diameter: 1, segments: 4 }, this.scene);
    mesh.material = color === 'blue' ? this.blue : this.gold;
    mesh.isPickable = false;
    mesh.position.copyFromFloats(...point);
    mesh.rotation.y = Math.atan2(direction.x, direction.z);
    mesh.scaling.set(0.045, length, 0.045);
    this.streaks.push({ mesh, age: 0, life, size: length });
  }
  /** Procedural sprint/fly speed streaks. These are authored preview VFX, not
   * recovered UE particle systems. */
  speedTrail(position: Vec3, velocity: Vec3, flying: boolean, sprinting: boolean, dt: number): void {
    this.trailClock += dt;
    const speed = Math.hypot(velocity[0], velocity[1], velocity[2]);
    if ((!flying && !sprinting) || speed < 6) return;
    if (this.trailClock < 0.055) return;
    this.trailClock = 0;
    const direction = new Vector3(-velocity[0], -velocity[1] * 0.2, -velocity[2]);
    if (direction.lengthSquared() < 1e-5) return;
    direction.normalize();
    const y = flying ? position[1] + 1.0 + Math.random() * 0.6 : position[1] + 0.6 + Math.random() * 0.5;
    const sideVector = new Vector3(direction.z, 0, -direction.x);
    for (let i = 0; i < 2; i++) {
      const side = (i === 0 ? -1 : 1) * (flying ? 0.8 : 0.55) + (Math.random() - 0.5) * 0.25;
      const point: Vec3 = [
        position[0] + direction.x * 0.8 + sideVector.x * side,
        y,
        position[2] + direction.z * 0.8 + sideVector.z * side,
      ];
      this.streak(point, direction, flying ? 'blue' : 'gold', flying ? 1.8 + Math.random() * 0.7 : 1.0 + Math.random() * 0.45, flying ? 0.5 : 0.4);
    }
  }
  swing(point: Vec3, direction: Vec3): void {
    const view = Vector3.FromArray(direction);
    if (view.lengthSquared() < 1e-5) return;
    view.normalize();
    for (let i = 0; i < 3; i++) {
      const side = (i - 1) * 0.22;
      this.streak([point[0] + view.z * side, point[1] + 0.1, point[2] - view.x * side], view, 'blue', 0.45 + i * 0.08, 0.14);
    }
  }
  /** Original P_NormalAttackSlash: 4x4 T_ky_slash01 atlas, frames 3..10,
   * lifetime 0.2 s. SpriteManager handles the camera-facing quad and atlas UVs. */
  slash(point: Vec3): void {
    const sprite = new Sprite('normal-attack-slash', this.slashManager);
    sprite.position.copyFromFloats(point[0], point[1], point[2]);
    sprite.width = 1.1;
    sprite.height = 1.1;
    sprite.playAnimation(3, 10, false, 0.2 / 8);
    this.slashes.push({ sprite, age: 0, life: 0.2 });
  }
  /** Original P_FlyDust / P_FlyIdleDust smoke: T_RaP_Smoke_puff_4x4_2k,
   * 0.85..1.5 s lifetime, soft alpha smoke. Authored emission cadence around
   * the recovered four POP emitters; not a full GPU emitter reproduction yet. */
  flyDust(position: Vec3, velocity: Vec3, flying: boolean, dt: number): void {
    if (!flying) { this.dustClock = 0; return; }
    this.dustClock -= dt;
    if (this.dustClock > 0) return;
    this.dustClock = 0.08;
    const speed = Math.hypot(velocity[0], velocity[2]);
    const backX = speed > 1 ? -velocity[0] / speed : 0;
    const backZ = speed > 1 ? -velocity[2] / speed : 0;
    for (let i = 0; i < 3; i++) {
      const sprite = new Sprite('fly-dust', this.dustManager);
      const angle = Math.random() * Math.PI * 2;
      const radius = 0.3 + Math.random() * 0.7;
      sprite.position.copyFromFloats(
        position[0] + backX * (0.3 + Math.random() * 0.8) + Math.cos(angle) * radius,
        position[1] + 0.05 + Math.random() * 0.45,
        position[2] + backZ * (0.3 + Math.random() * 0.8) + Math.sin(angle) * radius,
      );
      const size = 0.8 + Math.random() * 0.55;
      sprite.cellIndex = Math.floor(Math.random() * 16);
      sprite.width = size; sprite.height = size;
      sprite.color = new Color4(1, 1, 1, 0.62);
      this.dust.push({ sprite, age: 0, life: 0.9 + Math.random() * 0.5, size });
    }
  }
  /** Original P_StartSprint wave texture; one expanding shockwave at takeoff.
   * The source uses SM_BlastWave; the sprite keeps the recovered texture and
   * timing, pending the mesh emitter conversion. */
  startSprint(position: Vec3): void {
    const sprite = new Sprite('start-sprint-blast', this.blastManager);
    sprite.position.copyFromFloats(position[0], position[1] + 0.08, position[2]);
    sprite.width = 0.45; sprite.height = 0.45;
    sprite.color = new Color4(1, 1, 1, 0.65);
    this.blasts.push({ sprite, age: 0, life: 0.4, startSize: 0.45, grow: 1.4, alpha: 0.65 });
  }
  /** Original P_AirAttack_Shock reuses T_BlastWave; larger, shorter shockwave
   * at the air-attack point. The three-emitter mesh system is still pending. */
  airShock(point: Vec3): void {
    const sprite = new Sprite('air-attack-shock', this.blastManager);
    sprite.position.copyFromFloats(point[0], point[1], point[2]);
    sprite.width = 1.0; sprite.height = 1.0;
    sprite.color = new Color4(1, 1, 1, 0.8);
    this.blasts.push({ sprite, age: 0, life: 0.3, startSize: 1.0, grow: 3.0, alpha: 0.8 });
  }
  heat(eyes: Vec3[] | null, end?: Vec3): void {
    this.beams.forEach((mesh, index) => {
      mesh.setEnabled(!!eyes && !!end);
      if (!eyes || !end) return;
      const start = Vector3.FromArray(eyes[index]), direction = Vector3.FromArray(end).subtract(start);
      const length = direction.length(); direction.normalize();
      mesh.position.copyFrom(start.add(direction.scale(length / 2)));
      mesh.scaling.y = length;
      const axis = Vector3.Cross(Vector3.Up(), direction);
      mesh.rotationQuaternion = axis.lengthSquared() < 1e-8 ? Quaternion.RotationAxis(Vector3.Right(), direction.y > 0 ? 0 : Math.PI) : Quaternion.RotationAxis(axis.normalize(), Math.acos(Math.max(-1, Math.min(1, direction.y))));
    });
  }
  projectile(): Mesh {
    const mesh = MeshBuilder.CreateSphere('fist-wave', { diameter: 0.8, segments: 6 }, this.scene);
    mesh.material = this.blue; mesh.isPickable = false; return mesh;
  }
  impact(point: Vec3, destroyed = false): void {
    const count = destroyed ? 8 : 2;
    for (let i = 0; i < count; i++) {
      if (this.sparks.length >= 64) this.sparks.shift()!.mesh.dispose();
      const size = destroyed ? 0.24 + i * 0.035 : 0.09;
      const mesh = MeshBuilder.CreateSphere('impact', { diameter: 1, segments: 4 }, this.scene);
      mesh.material = this.gold; mesh.isPickable = false; mesh.position.copyFromFloats(...point); mesh.scaling.setAll(size);
      const angle = i * 2.399;
      this.sparks.push({ mesh, age: 0, life: destroyed ? 0.85 : 0.18, size, velocity: new Vector3(Math.sin(angle) * (destroyed ? 7 : 2), 2 + i % 3, Math.cos(angle) * (destroyed ? 7 : 2)) });
    }
  }
  update(dt: number): void {
    for (let i = this.blasts.length - 1; i >= 0; i--) {
      const blast = this.blasts[i]; blast.age += dt;
      if (blast.age >= blast.life) { blast.sprite.dispose(); this.blasts.splice(i, 1); continue; }
      const progress = blast.age / blast.life;
      const scale = blast.startSize + progress * blast.grow;
      blast.sprite.width = scale; blast.sprite.height = scale;
      blast.sprite.color = new Color4(1, 1, 1, blast.alpha * (1 - progress));
    }
    for (let i = this.dust.length - 1; i >= 0; i--) {
      const puff = this.dust[i]; puff.age += dt;
      if (puff.age >= puff.life) { puff.sprite.dispose(); this.dust.splice(i, 1); continue; }
      const progress = puff.age / puff.life;
      const scale = puff.size * (1 + progress * 1.8);
      puff.sprite.width = scale; puff.sprite.height = scale;
      puff.sprite.color = new Color4(1, 1, 1, 0.62 * (1 - progress));
    }
    for (let i = this.slashes.length - 1; i >= 0; i--) {
      const slash = this.slashes[i]; slash.age += dt;
      if (slash.age >= slash.life) { slash.sprite.dispose(); this.slashes.splice(i, 1); }
    }
    for (let i = this.sparks.length - 1; i >= 0; i--) {
      const spark = this.sparks[i]; spark.age += dt;
      if (spark.age >= spark.life) { spark.mesh.dispose(); this.sparks.splice(i, 1); continue; }
      spark.velocity.y -= 5 * dt; spark.mesh.position.addInPlace(spark.velocity.scale(dt)); spark.mesh.scaling.setAll(spark.size * (1 - spark.age / spark.life));
    }
    for (let i = this.streaks.length - 1; i >= 0; i--) {
      const streak = this.streaks[i]; streak.age += dt;
      if (streak.age >= streak.life) { streak.mesh.dispose(); this.streaks.splice(i, 1); continue; }
      const fade = 1 - streak.age / streak.life;
      streak.mesh.scaling.x = streak.mesh.scaling.z = 0.045 * fade;
      streak.mesh.scaling.y = streak.size * (0.7 + fade * 0.3);
    }
  }
  reset(): void { this.heat(null); this.sparks.forEach(spark => spark.mesh.dispose()); this.sparks.length = 0; this.streaks.forEach(streak => streak.mesh.dispose()); this.streaks.length = 0; this.slashes.forEach(slash => slash.sprite.dispose()); this.slashes.length = 0; this.dust.forEach(puff => puff.sprite.dispose()); this.dust.length = 0; this.blasts.forEach(blast => blast.sprite.dispose()); this.blasts.length = 0; this.dustClock = 0; this.trailClock = 0; }
  dispose(): void { this.reset(); this.slashManager.dispose(); this.dustManager.dispose(); this.blastManager.dispose(); this.beams.forEach(mesh => mesh.dispose()); this.red.dispose(); this.gold.dispose(); this.blue.dispose(); }
}
