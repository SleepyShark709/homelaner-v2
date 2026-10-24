import { Engine } from '@babylonjs/core/Engines/engine';
import { Scene } from '@babylonjs/core/scene';
import { FreeCamera } from '@babylonjs/core/Cameras/freeCamera';
import { Vector3 } from '@babylonjs/core/Maths/math.vector';
import { Color3, Color4 } from '@babylonjs/core/Maths/math.color';
import { HemisphericLight } from '@babylonjs/core/Lights/hemisphericLight';
import { DirectionalLight } from '@babylonjs/core/Lights/directionalLight';
import { ShadowGenerator } from '@babylonjs/core/Lights/Shadows/shadowGenerator';
import '@babylonjs/core/Lights/Shadows/shadowGeneratorSceneComponent';
import { registerBuiltInLoaders } from '@babylonjs/loaders/dynamic';
import { Input } from './Input';
import { World } from './World';
import { Character } from './Character';
import { Population } from './Population';
import { Combat } from './Combat';
import { PlayerMotor } from './PlayerMotor';
import { firstHit } from './collision';
import type { Vec3 } from './collision';

registerBuiltInLoaders();
export interface FrameInfo { speed: number; altitude: number; mode: string; fps: number; position: Vec3; meshes: number; paused: boolean; renderMs: number }
export class Game {
  readonly engine: Engine;
  readonly scene: Scene;
  readonly input: Input;
  readonly world: World;
  readonly character: Character;
  readonly population: Population;
  combat!: Combat;
  motor!: PlayerMotor;
  private readonly camera: FreeCamera;
  private readonly shadows: ShadowGenerator;
  private accumulator = 0;
  private ready = false;
  private cameraInitialized = false;
  private hudTime = 0;
  private renderMs = 0;
  private readonly resize = () => this.engine.resize();
  onFrame: (frame: FrameInfo) => void = () => {};
  onPause: () => void = () => {};
  constructor(readonly canvas: HTMLCanvasElement) {
    this.engine = new Engine(canvas, true, { stencil: true, preserveDrawingBuffer: true });
    this.engine.setHardwareScalingLevel(Math.max(1.5, window.devicePixelRatio / 1.25));
    this.scene = new Scene(this.engine);
    this.scene.skipPointerMovePicking = true;
    this.scene.useRightHandedSystem = true;
    this.scene.clearColor = Color4.FromHexString('#b8d4deff');
    this.scene.fogMode = Scene.FOGMODE_EXP2;
    this.scene.fogDensity = 0.0018;
    this.scene.fogColor = Color3.FromHexString('#b8d4de');
    this.scene.ambientColor = new Color3(0.15, 0.17, 0.2);
    const sky = new HemisphericLight('sky', new Vector3(0, 1, 0), this.scene);
    sky.intensity = 1.1; sky.groundColor = new Color3(0.32, 0.31, 0.28);
    const sun = new DirectionalLight('sun', new Vector3(-0.45, -1, -0.25), this.scene);
    sun.intensity = 2.3; sun.diffuse = new Color3(1, 0.94, 0.83);
    this.shadows = new ShadowGenerator(1024, sun);
    this.shadows.useBlurExponentialShadowMap = true;
    this.shadows.blurKernel = 24;
    this.shadows.setDarkness(0.32);
    this.camera = new FreeCamera('third-person', new Vector3(0, 4, 7), this.scene);
    this.camera.minZ = 0.12; this.camera.maxZ = 3000; this.camera.fov = 0.95;
    this.input = new Input(canvas);
    this.input.onPause = () => { this.accumulator = 0; this.character.pause(true); this.population.pause(true); this.combat?.pause(); this.onPause(); };
    this.world = new World(this.scene);
    this.character = new Character(this.scene);
    this.population = new Population(this.scene, this.world.obstacles);
    window.addEventListener('resize', this.resize);
  }
  async load(progress: (message: string) => void): Promise<void> {
    await this.world.load(progress);
    progress('装配原版角色、头发、墨镜与动画');
    await this.character.load(this.shadows);
    progress('载入原版路人、车辆和可破坏道具');
    await this.population.load();
    const spawn: Vec3 = [...this.world.manifest.spawn]; spawn[1] += 0.04;
    this.motor = new PlayerMotor(spawn, [...this.world.obstacles, ...this.population.solidBoxes], this.world.manifest.bounds);
    this.combat = new Combat(this.scene, this.input, this.motor, this.character, this.population, this.camera, this.world.obstacles);
    await this.combat.load();
    this.character.update(this.motor, 1);
    this.character.pause(true);
    this.ready = true;
    this.updateCamera(1);
    this.engine.runRenderLoop(() => this.frame());
  }
  start(): void { this.input.clear(); this.input.active = true; this.character.pause(false); this.population.pause(false); this.accumulator = 0; }
  pause(): void { this.input.pause(); }
  setQuality(high: boolean): void { this.engine.setHardwareScalingLevel(high ? Math.max(1, window.devicePixelRatio / 1.5) : Math.max(1.5, window.devicePixelRatio / 1.25)); }
  reset(): void { this.combat.reset(); this.motor.reset(); this.input.clear(); this.input.yaw = Math.PI; this.input.pitch = 0.14; this.character.update(this.motor, 1); this.character.pause(!this.input.active); this.cameraInitialized = false; this.updateCamera(1); }
  resetCity(): void { this.population.reset(); this.reset(); }
  private frame(): void {
    if (!this.ready || document.hidden) return;
    const dt = Math.min(this.engine.getDeltaTime() / 1000, 0.067);
    if (this.input.active) {
      this.population.update(dt);
      this.motor.obstacles.splice(0, this.motor.obstacles.length, ...this.world.obstacles, ...this.population.solidBoxes);
      this.accumulator += dt;
      while (this.accumulator >= 1 / 120) { this.motor.update(1 / 120, this.input); this.accumulator -= 1 / 120; }
      this.character.update(this.motor, dt);
      this.updateCamera(dt);
      this.combat.update(dt);
    }
    const renderStart = performance.now();
    this.scene.render();
    this.renderMs = this.renderMs * 0.9 + (performance.now() - renderStart) * 0.1;
    this.hudTime += dt;
    if (this.hudTime >= 0.1) {
      this.hudTime = 0;
      this.onFrame({ speed: Math.hypot(...this.motor.velocity), altitude: Math.max(0, this.motor.position[1] - (this.world.manifest.groundY ?? this.world.manifest.bounds.min[1])), mode: this.motor.flying ? '飞行' : this.motor.grounded ? '地面' : '腾空', fps: this.engine.getFps(), position: [...this.motor.position], meshes: this.world.visibleMeshes.length, paused: !this.input.active, renderMs: this.renderMs });
    }
  }
  private updateCamera(dt: number): void {
    const target = new Vector3(this.motor.position[0], this.motor.position[1] + 1.35, this.motor.position[2]);
    const distance = this.motor.flying ? 8 : 5.5;
    const forward = new Vector3(Math.sin(this.input.yaw), 0, Math.cos(this.input.yaw));
    const offset = forward.scale(-Math.cos(this.input.pitch) * distance);
    offset.y = 0.8 + Math.sin(this.input.pitch) * distance;
    const hit = firstHit(target.asArray() as Vec3, offset.asArray() as Vec3, this.world.obstacles, [0.15, 0.15, 0.15]);
    if (hit) offset.scaleInPlace(Math.max(0.03, hit.time - 0.02));
    const destination = target.add(offset);
    if (!this.cameraInitialized || hit) this.camera.position.copyFrom(destination);
    else this.camera.position.copyFrom(Vector3.Lerp(this.camera.position, destination, 1 - Math.exp(-10 * dt)));
    this.cameraInitialized = true;
    // Put the reticle above the character so the body doesn't hide nearby targets.
    this.camera.setTarget(target.add(new Vector3(0, 1, 0)));
    this.camera.fov += ((this.motor.flying && Math.hypot(...this.motor.velocity) > 45 ? 1.12 : 0.95) - this.camera.fov) * Math.min(1, dt * 4);
  }
  dispose(): void { window.removeEventListener('resize', this.resize); this.input.dispose(); this.combat?.dispose(); this.population.dispose(); this.character.dispose(); this.world.dispose(); this.scene.dispose(); this.engine.dispose(); }
}
