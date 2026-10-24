import { firstHit, moveAndSlide } from './collision.ts';
import type { Bounds, Obstacle, Vec3 } from './collision';
import type { Input } from './Input';

export const TUNING = { walk: 10, sprint: 30, fly: 40, boost: 70, acceleration: 150, jump: 20, gravity: 9.81, height: 1.92, radius: 0.36 };
export type MotionState = 'idle' | 'run' | 'jump' | 'hover' | 'fly';
export class PlayerMotor {
  position: Vec3;
  velocity: Vec3 = [0, 0, 0];
  flying = false;
  grounded = false;
  heading = Math.PI;
  state: MotionState = 'idle';
  contacts = 0;
  readonly spawn: Vec3;
  readonly obstacles: Obstacle[];
  readonly bounds: Bounds;
  constructor(spawn: Vec3, obstacles: Obstacle[], bounds: Bounds) { this.spawn = spawn; this.obstacles = obstacles; this.bounds = bounds; this.position = [...spawn]; }
  reset(): void { this.position = [...this.spawn]; this.velocity = [0, 0, 0]; this.flying = false; this.state = 'idle'; }
  update(dt: number, input: Input): void {
    if (input.pressed('KeyR')) this.reset();
    if (input.pressed('KeyF')) { this.flying = !this.flying; this.velocity[1] = this.flying ? 3 : 0; }
    const jump = input.pressed('Space');
    const support = firstHit([this.position[0], this.position[1] + 0.96, this.position[2]], [0, -0.06, 0], this.obstacles, [0.36, 0.96, 0.36]);
    this.grounded = !!support && support.normal[1] > 0;
    if (jump && !this.flying) {
      if (this.grounded) this.velocity[1] = TUNING.jump;
      else { this.flying = true; this.velocity[1] = 0; }
    }
    const forward = input.axis(['KeyW', 'ArrowUp'], ['KeyS', 'ArrowDown']);
    const right = input.axis(['KeyD', 'ArrowRight'], ['KeyA', 'ArrowLeft']);
    const vertical = this.flying ? input.axis(['Space'], ['ControlLeft', 'ControlRight', 'KeyQ']) : 0;
    const sin = Math.sin(input.yaw), cos = Math.cos(input.yaw);
    let desired: Vec3 = [sin * forward - cos * right, vertical, cos * forward + sin * right];
    const length = Math.hypot(...desired);
    const sprint = input.held('ShiftLeft', 'ShiftRight');
    const speed = this.flying ? (sprint ? TUNING.boost : TUNING.fly) : (sprint ? TUNING.sprint : TUNING.walk);
    if (length > 0) desired = desired.map(v => v / length * speed) as Vec3;
    const acceleration = TUNING.acceleration * dt;
    for (let i = 0; i < 3; i++) {
      if (i === 1 && !this.flying) { this.velocity[1] -= TUNING.gravity * dt; continue; }
      this.velocity[i] += Math.max(-acceleration, Math.min(acceleration, desired[i] - this.velocity[i]));
    }
    if (this.grounded && !this.flying && !jump && this.velocity[1] < 0) this.velocity[1] = -0.4;
    const delta = this.velocity.map(v => v * dt) as Vec3;
    let result = moveAndSlide(this.position, delta, this.obstacles);
    if (!this.flying && this.grounded && !jump && result.normals.some(normal => normal[0] || normal[2])) {
      const raised = moveAndSlide(this.position, [0, 0.45, 0], this.obstacles);
      if (raised.position[1] - this.position[1] > 0.44) {
        const across = moveAndSlide(raised.position, [delta[0], 0, delta[2]], this.obstacles);
        const down = moveAndSlide(across.position, [0, -0.51, 0], this.obstacles);
        const distance = (p: Vec3) => Math.hypot(p[0] - this.position[0], p[2] - this.position[2]);
        if (down.normals.some(normal => normal[1] > 0) && distance(down.position) > distance(result.position) + 1e-5) result = down;
      }
    }
    this.position = result.position;
    this.contacts += result.normals.length;
    for (const normal of result.normals) {
      for (let i = 0; i < 3; i++) if (normal[i] && this.velocity[i] * normal[i] < 0) this.velocity[i] = 0;
      if (normal[1] > 0) this.grounded = true;
    }
    // Limit this recovered district. These boundaries are a preview constraint, not original game rules.
    for (const i of [0, 2]) {
      const clamped = Math.max(this.bounds.min[i] + 1, Math.min(this.bounds.max[i] - 1, this.position[i]));
      if (clamped !== this.position[i]) this.velocity[i] = 0;
      this.position[i] = clamped;
    }
    if (this.position[1] > this.bounds.max[1]) { this.position[1] = this.bounds.max[1]; this.velocity[1] = 0; }
    if (this.position[1] < this.bounds.min[1] - 30) this.reset();
    const planar = Math.hypot(this.velocity[0], this.velocity[2]);
    if (this.flying) this.heading = input.yaw;
    else if (planar > 0.2) this.heading = Math.atan2(this.velocity[0], this.velocity[2]);
    this.state = this.flying ? (planar > 6 ? 'fly' : 'hover') : this.grounded ? (planar > 0.5 ? 'run' : 'idle') : 'jump';
  }
}
