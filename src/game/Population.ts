import { Scene } from '@babylonjs/core/scene';
import { TransformNode } from '@babylonjs/core/Meshes/transformNode';
import { LoadAssetContainerAsync } from '@babylonjs/core/Loading/sceneLoader';
import type { AssetContainer, InstantiatedEntries } from '@babylonjs/core/assetContainer';
import type { Bounds, Obstacle, Vec3 } from './collision';
import { firstHit } from './collision';
import { vehicleShouldHold } from './traffic';
import { applyDamage, FREE_RULES } from './combat-rules';
import type { AttackSpec, Damageable, PlayMode, TargetKind } from './combat-rules';

interface Model { id: string; kind: TargetKind; url: string; bounds: Bounds; forwardAxis: string; groundOffset: number }
interface Route { id: string; kind: string; points: Vec3[]; closed: boolean }
interface Spawn { id: string; modelId: string; position: Vec3; yaw: number; routeId?: string }
interface Manifest { models: Model[]; spawns: Spawn[]; routes: Route[]; originUE?: Vec3 }
export interface Actor extends Damageable { position: Vec3; root: TransformNode; model: Model; spawn: Spawn; route?: Route; routeIndex: number; routeDirection: number; entries: InstantiatedEntries; clip: string; defeatedTime: number; velocity: Vec3; fleeTime: number; fleeDirection: Vec3 }
export class Population {
  readonly actors: Actor[] = [];
  private readonly containers: AssetContainer[] = [];
  private manifest!: Manifest;
  private paused = true;
  constructor(readonly scene: Scene, readonly walls: Obstacle[]) {}
  async load(options: { worldOffset?: [number, number]; manifestUrl?: string } = {}): Promise<void> {
    const response = await fetch(options.manifestUrl ?? '/assets/population-manifest.json');
    if (!response.ok) throw new Error('人车资源清单未生成');
    this.manifest = await response.json();
    // The previous prototype used a district-local origin. The restored world
    // uses absolute coordinates, so callers can shift placements/routes without
    // changing the old ?view=prototype behavior.
    const [offsetX, offsetZ] = options.worldOffset ?? [0, 0];
    if (offsetX || offsetZ) {
      for (const spawn of this.manifest.spawns) {
        spawn.position = [spawn.position[0] + offsetX, spawn.position[1], spawn.position[2] + offsetZ];
      }
      for (const route of this.manifest.routes) {
        route.points = route.points.map(point => [point[0] + offsetX, point[1], point[2] + offsetZ] as Vec3);
      }
    }
    for (const model of this.manifest.models) {
      const container = await LoadAssetContainerAsync(model.url, this.scene);
      container.meshes.forEach(mesh => { mesh.receiveShadows = true; });
      this.containers.push(container);
      for (const spawn of this.manifest.spawns.filter(item => item.modelId === model.id)) {
        const entries = container.instantiateModelsToScene(name => `${spawn.id}/${name}`, false, { doNotInstantiate: model.kind === 'citizen' });
        const root = new TransformNode(spawn.id, this.scene);
        entries.rootNodes.forEach(node => { node.parent = root; });
        root.getChildMeshes().forEach(mesh => { mesh.isPickable = false; });
        const actor: Actor = { id: spawn.id, kind: model.kind, alive: true, health: this.health(model.kind), min: [0, 0, 0], max: [0, 0, 0], position: [...spawn.position], root, model, spawn, entries, route: this.manifest.routes.find(route => route.id === spawn.routeId), routeIndex: 1, routeDirection: 1, clip: '', defeatedTime: 0, velocity: [0, 0, 0], fleeTime: 0, fleeDirection: [0, 0, 0] };
        this.actors.push(actor);
        this.place(actor, spawn.yaw);
        this.animate(actor, 'Citizen_N_Walk_F');
      }
    }
    this.pause(true);
  }
  private health(kind: TargetKind): number { return kind === 'citizen' ? FREE_RULES.citizenHealth : kind === 'vehicle' ? FREE_RULES.vehicleHealth : FREE_RULES.propHealth; }
  private place(actor: Actor, yaw: number): void {
    actor.root.position.copyFromFloats(...actor.position);
    actor.root.position.y += actor.model.groundOffset;
    const correction = actor.model.forwardAxis === '+X' ? -Math.PI / 2 : actor.model.forwardAxis === '-Z' ? Math.PI : 0;
    actor.root.rotation.y = yaw + correction;
    const { min, max } = actor.model.bounds;
    const c = Math.cos(actor.root.rotation.y), s = Math.sin(actor.root.rotation.y);
    const corners = [[min[0], min[2]], [min[0], max[2]], [max[0], min[2]], [max[0], max[2]]];
    const xs = corners.map(([x, z]) => x * c + z * s + actor.position[0]);
    const zs = corners.map(([x, z]) => -x * s + z * c + actor.position[2]);
    actor.min = [Math.min(...xs), actor.position[1], Math.min(...zs)];
    actor.max = [Math.max(...xs), actor.position[1] + max[1] - min[1], Math.max(...zs)];
  }
  private animate(actor: Actor, clip: string): void {
    if (actor.clip === clip) return;
    actor.entries.animationGroups.forEach(group => group.stop());
    const group = actor.entries.animationGroups.find(item => item.name.endsWith(clip));
    group?.start(true); if (this.paused) group?.pause();
    actor.clip = clip;
  }
  pause(paused: boolean): void {
    this.paused = paused;
    for (const actor of this.actors) {
      const group = actor.entries.animationGroups.find(item => item.name.endsWith(actor.clip));
      if (paused || !actor.alive) group?.pause(); else group?.play(true);
    }
  }
  update(dt: number): void {
    for (const actor of this.actors) {
      if (!actor.alive) {
        actor.defeatedTime += dt;
        if (actor.kind === 'citizen' && actor.defeatedTime < 1.2) {
          actor.velocity[1] -= 16 * dt;
          const delta = actor.velocity.map(value => value * dt) as Vec3;
          const hit = firstHit([actor.position[0], actor.position[1] + 0.45, actor.position[2]], delta, this.walls, [0.25, 0.25, 0.25]);
          for (let i = 0; i < 3; i++) actor.position[i] += delta[i] * (hit ? Math.max(0, hit.time - 0.02) : 1);
          if (hit) actor.velocity = [0, 0, 0];
          actor.root.position.copyFromFloats(...actor.position); actor.root.position.y += 0.4;
          actor.root.rotation.x = -Math.min(Math.PI / 2, actor.defeatedTime * 5);
        }
        if (actor.defeatedTime > 2.5) actor.root.setEnabled(false);
        // Preview city lifecycle: citizens return after a short delay. The
        // original spawner cadence/count is not recovered; vehicles/props stay
        // destroyed for the rest of the session.
        if (actor.kind === 'citizen' && actor.defeatedTime >= 8) this.revive(actor);
        continue;
      }
      if (actor.kind === 'prop') continue;
      if (actor.fleeTime > 0) {
        actor.fleeTime -= dt;
        const delta = actor.fleeDirection.map(value => value * 4.5 * dt) as Vec3;
        const hit = firstHit([actor.position[0], actor.position[1] + 1, actor.position[2]], delta, this.walls, [0.4, 0.8, 0.4]);
        if (!hit) { actor.position[0] += delta[0]; actor.position[2] += delta[2]; }
        else actor.fleeTime = 0;
        this.place(actor, Math.atan2(actor.fleeDirection[0], actor.fleeDirection[2]));
        this.animate(actor, 'Citizen_N_Run_F');
        continue;
      }
      const route = actor.route;
      if (!route || route.points.length < 2) { this.animate(actor, 'Citizen_N_Idle_Pose'); continue; }
      const target = route.points[actor.routeIndex];
      const dx = target[0] - actor.position[0], dz = target[2] - actor.position[2];
      const distance = Math.hypot(dx, dz), speed = actor.kind === 'vehicle' ? 5 : 1.35;
      if (actor.kind === 'vehicle' && distance > 0.01) {
        const forward: Vec3 = [dx / distance, 0, dz / distance];
        const blocked = this.actors.some(other => other !== actor && other.alive && other.kind === 'vehicle' && vehicleShouldHold(actor.position, other.position, forward));
        if (blocked) continue;
      }
      if (distance < speed * dt + 0.08) {
        actor.position = [...target];
        let next = actor.routeIndex + actor.routeDirection;
        if (next >= route.points.length || next < 0) {
          if (route.closed) next = (next + route.points.length) % route.points.length;
          else { actor.routeDirection *= -1; next = actor.routeIndex + actor.routeDirection; }
        }
        actor.routeIndex = next;
      } else {
        actor.position[0] += dx / distance * speed * dt; actor.position[2] += dz / distance * speed * dt;
        actor.position[1] += (target[1] - actor.position[1]) * Math.min(1, speed * dt / distance);
      }
      this.place(actor, Math.atan2(dx, dz));
      this.animate(actor, 'Citizen_N_Walk_F');
    }
  }
  alert(origin: Vec3): void {
    for (const actor of this.actors) {
      if (actor.kind !== 'citizen' || !actor.alive) continue;
      const dx = actor.position[0] - origin[0], dz = actor.position[2] - origin[2], distance = Math.hypot(dx, dz);
      if (distance < 25 && distance > 0.1) { actor.fleeTime = 3; actor.fleeDirection = [dx / distance, 0, dz / distance]; }
    }
  }
  hit(id: string, attack: AttackSpec, mode: PlayMode): 'ignored' | 'hit' | 'destroyed' {
    const actor = this.actors.find(item => item.id === id);
    if (!actor) return 'ignored';
    const result = applyDamage(mode, actor, attack);
    if (result === 'destroyed') {
      actor.entries.animationGroups.forEach(group => group.pause());
      actor.velocity = [attack.direction[0] * 9, 5, attack.direction[2] * 9];
      if (actor.kind !== 'citizen') actor.root.setEnabled(false);
    }
    return result;
  }
  reset(): void {
    for (const actor of this.actors) this.revive(actor);
  }
  private revive(actor: Actor): void {
    actor.alive = true; actor.health = this.health(actor.kind); actor.position = [...actor.spawn.position]; actor.defeatedTime = 0; actor.velocity = [0, 0, 0]; actor.fleeTime = 0; actor.routeIndex = 1; actor.routeDirection = 1;
    actor.root.setEnabled(true); actor.root.rotation.x = 0; this.place(actor, actor.spawn.yaw);
    actor.clip = ''; this.animate(actor, 'Citizen_N_Walk_F');
  }
  /** All live actor AABBs, including citizens. The original game has actor
   * collision; this proxy is still an AABB, not the cooked capsule. */
  get solidBoxes(): Obstacle[] { return this.actors.filter(actor => actor.alive); }
  get remaining(): number { return this.actors.filter(actor => actor.alive).length; }
  dispose(): void { this.actors.forEach(actor => { actor.entries.dispose(); actor.root.dispose(); }); this.containers.forEach(container => container.dispose()); }
}
