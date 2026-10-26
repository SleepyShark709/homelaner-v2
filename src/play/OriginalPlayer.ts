import { moveAndSlide } from '../game/collision.ts';
import type { Bounds, Obstacle, Vec3 } from '../game/collision.ts';
import type { Input } from '../game/Input.ts';
import { TUNING, type MotionState } from '../game/PlayerMotor.ts';
import type { SpatialBoxes } from './CollisionWorld.ts';
import type { TerrainHeightfield } from './TerrainHeightfield.ts';
import type { WalkableSurfaces } from './WalkableSurfaces.ts';

/** UE GravityScale 5 * 980 cm/s^2 = 49 m/s^2, recovered from HeroComponent. */
const ORIGINAL_GRAVITY = 49;
/** MaxAcceleration: 2048 cm/s^2 walking, 4096 flying, 15000 sprinting. */
const ACCELERATION_WALK = 20.48;
const ACCELERATION_FLY = 40.96;
const ACCELERATION_SPRINT = 150;

export interface PlaySpawn {
  position: Vec3;
  /** Original actor/coordinate evidence, kept separate from the preview clamp. */
  source: string;
}

export interface PlayStats {
  position: Vec3; velocity: Vec3; flying: boolean; grounded: boolean;
  state: MotionState; speed: number; charge: number;
}

/**
 * B1 original-input movement slice.
 *
 * Input/state semantics follow the recovered PlayerBP -> HeroComponent contract:
 * Space jumps on the ground, opens flight in the air and exits flight while
 * flying; E/Q are vertical inputs; holding E on the ground charges flight; Shift
 * sprints; Alt walks; F is reserved for interaction. Walk/sprint/fly speed
 * ceilings and acceleration reuse the recovered defaults (1000/3000/4000/7000
 * cm/s and 2048/15000 acceleration equivalents). Jump impulse, gravity and the
 * collision proxy are preview values and are labelled as such in the scene UI.
 */
export class OriginalPlayer {
  position: Vec3;
  velocity: Vec3 = [0, 0, 0];
  flying = false;
  grounded = false;
  heading = Math.PI;
  state: MotionState = 'idle';
  sprint = false;
  walk = false;
  charge = 0;
  private sprintFast = false;
  private sprintBlocked = false;
  readonly spawn: Vec3;
  private readonly ground: TerrainHeightfield;
  private readonly surfaces?: WalkableSurfaces;
  private readonly boxes: SpatialBoxes;
  private readonly bounds: Bounds;
  private dynamicBoxes: Obstacle[] = [];

  constructor(
    spawn: Vec3,
    ground: TerrainHeightfield,
    boxes: SpatialBoxes,
    terrainBounds: Bounds,
    surfaces?: WalkableSurfaces,
  ) {
    this.spawn = [...spawn];
    this.position = [...spawn];
    this.ground = ground;
    this.boxes = boxes;
    this.bounds = terrainBounds;
    this.surfaces = surfaces;
  }

  /** Landscape plus recovered flat floor tops (plaza brick floors). */
  private supportAt(x: number, z: number, feetY: number): number {
    const terrain = this.ground.heightAt(x, z) ?? 0;
    const floor = this.surfaces?.topAt(x, z, feetY, 0.75);
    return floor !== undefined ? Math.max(terrain, floor) : terrain;
  }

  /** Vehicles/props from the preview population. These move, so they are not
   * baked into the static spatial grid; the scene supplies them each frame. */
  setDynamicBoxes(boxes: Obstacle[]): void { this.dynamicBoxes = boxes; }

  reset(): void {
    this.position = [...this.spawn];
    this.velocity = [0, 0, 0];
    this.flying = false;
    this.grounded = false;
    this.charge = 0;
    this.state = 'idle';
  }

  update(dt: number, input: Input): void {
    if (input.pressed('KeyR')) this.reset();
    // F exits flight and lets gravity land the player. Space also toggles flight
    // while airborne, but F is the explicit "land" input shown in the HUD help.
    if (input.pressed('KeyF') && this.flying) {
      this.flying = false;
      this.velocity[1] = Math.min(0, this.velocity[1]);
    }
    const ground = this.supportAt(this.position[0], this.position[2], this.position[1]);
    this.grounded = !this.flying && this.position[1] <= ground + 0.08;
    this.walk = input.held('AltLeft', 'AltRight');
    const forward = input.axis(['KeyW', 'ArrowUp'], ['KeyS', 'ArrowDown']);
    const right = input.axis(['KeyD', 'ArrowRight'], ['KeyA', 'ArrowLeft']);
    const moving = forward !== 0 || right !== 0;
    const shiftHeld = input.held('ShiftLeft', 'ShiftRight');
    // H is the heat-vision key; E remains takeoff/ascend and must keep charging.
    const heatHeld = input.held('KeyH');
    // P07: Shift only arms sprint; StartSprint requires movement input. Walk
    // mode cancels sprint. P08 resets a sprint once speed falls below 850 cm/s
    // walking or 2000 cm/s flying; keep it disarmed until Shift/movement is
    // released so holding Shift does not instantly re-arm it.
    if (!shiftHeld || !moving || this.walk) {
      this.sprint = false;
      this.sprintFast = false;
      this.sprintBlocked = false;
    } else {
      if (!this.sprint) this.sprint = !this.sprintBlocked;
      if (this.sprint) {
        const speed3 = Math.hypot(this.velocity[0], this.velocity[1], this.velocity[2]);
        const threshold = this.flying ? 20 : 8.5;
        if (speed3 >= threshold) this.sprintFast = true;
        else if (this.sprintFast) {
          this.sprint = false;
          this.sprintFast = false;
          this.sprintBlocked = true;
        }
      }
    }
    const jump = input.pressed('Space');

    // P06: ground E charge starts a super/automatic flight after one second.
    if (this.grounded && !this.flying) {
      this.charge = input.held('KeyE') && !heatHeld ? this.charge + dt : 0;
      if (this.charge > 1) {
        this.flying = true;
        this.grounded = false;
        this.charge = 0;
        this.velocity[1] = Math.max(this.velocity[1], TUNING.jump);
      }
    } else {
      this.charge = 0;
    }

    // P04: ground Space jumps; airborne Space opens flight; flight Space exits.
    if (this.flying) {
      if (jump && this.charge === 0) this.flying = false;
    } else if (this.grounded) {
      if (jump) { this.velocity[1] = TUNING.jump; this.grounded = false; }
    } else if (jump) {
      this.flying = true;
      this.velocity[1] = 0;
    }

    const verticalInput = (input.held('KeyE') && !heatHeld ? 1 : 0) - (input.held('KeyQ') ? 1 : 0);
    const sin = Math.sin(input.yaw), cos = Math.cos(input.yaw);
    const speed = this.walk ? 2.5 : this.flying ? (this.sprint ? TUNING.boost : TUNING.fly) : (this.sprint ? TUNING.sprint : TUNING.walk);
    let desiredX = sin * forward - cos * right;
    let desiredZ = cos * forward + sin * right;
    const length = Math.hypot(desiredX, desiredZ);
    if (length > 0) { desiredX = desiredX / length * speed; desiredZ = desiredZ / length * speed; }
    const desiredY = this.flying ? verticalInput * speed : this.grounded ? -0.4 : this.velocity[1];
    const acceleration = (this.flying ? ACCELERATION_FLY : this.sprint ? ACCELERATION_SPRINT : ACCELERATION_WALK) * dt;
    this.velocity[0] += Math.max(-acceleration, Math.min(acceleration, desiredX - this.velocity[0]));
    this.velocity[2] += Math.max(-acceleration, Math.min(acceleration, desiredZ - this.velocity[2]));
    if (this.flying) this.velocity[1] += Math.max(-acceleration, Math.min(acceleration, desiredY - this.velocity[1]));
    else if (!this.grounded) this.velocity[1] -= ORIGINAL_GRAVITY * dt;
    else if (this.velocity[1] < 0) this.velocity[1] = -0.4;

    const nearby: Obstacle[] = this.boxes.nearby(this.position[0], this.position[2], 8);
    for (const box of this.dynamicBoxes) {
      if (box.max[0] < this.position[0] - 8 || box.min[0] > this.position[0] + 8 ||
          box.max[2] < this.position[2] - 8 || box.min[2] > this.position[2] + 8) continue;
      nearby.push(box);
    }
    const moved = moveAndSlide(this.position, [this.velocity[0] * dt, this.velocity[1] * dt, this.velocity[2] * dt], nearby, [TUNING.radius, TUNING.height / 2, TUNING.radius]);
    this.position = moved.position;
    for (const normal of moved.normals) {
      for (let axis = 0; axis < 3; axis++) if (normal[axis] && this.velocity[axis] * normal[axis] < 0) this.velocity[axis] = 0;
      if (normal[1] > 0) this.grounded = true;
    }

    // Terrain and recovered floor tops are the ground; nearby boxes only block walls.
    const groundNow = this.supportAt(this.position[0], this.position[2], this.position[1]);
    if (this.position[1] <= groundNow + 0.03) {
      if (this.position[1] < groundNow + 0.02) this.position[1] = groundNow + 0.02;
      if (this.velocity[1] < 0) this.velocity[1] = 0;
      this.grounded = true;
    } else if (!this.flying) {
      this.grounded = false;
    }
    for (const axis of [0, 2] as const) {
      const min = this.bounds.min[axis] + 1, max = this.bounds.max[axis] - 1;
      const clamped = Math.max(min, Math.min(max, this.position[axis]));
      if (clamped !== this.position[axis]) this.velocity[axis] = 0;
      this.position[axis] = clamped;
    }
    if (this.position[1] < this.bounds.min[1] - 80) this.reset();

    const planar = Math.hypot(this.velocity[0], this.velocity[2]);
    if (this.flying) {
      this.heading = input.yaw;
      this.state = planar > 6 ? 'fly' : 'hover';
    } else if (this.grounded) {
      if (planar > 0.2) this.heading = Math.atan2(this.velocity[0], this.velocity[2]);
      this.state = planar > 0.5 ? 'run' : 'idle';
    } else {
      this.state = 'jump';
    }
  }

  stats(): PlayStats {
    return {
      position: [...this.position], velocity: [...this.velocity], flying: this.flying,
      grounded: this.grounded, state: this.state, speed: Math.hypot(...this.velocity), charge: this.charge,
    };
  }
}
