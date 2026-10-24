import type { Vec3 } from './collision';

/**
 * Preview traffic spacing: a vehicle holds if another live vehicle is close
 * and roughly ahead in its current travel direction. This is authored traffic
 * behavior, not a recovered BP_TrafficSystem state machine.
 */
export function vehicleShouldHold(self: Vec3, other: Vec3, forward: Vec3, gap = 7): boolean {
  const dx = other[0] - self[0], dz = other[2] - self[2];
  const distance = Math.hypot(dx, dz);
  if (distance < 0.01 || distance > gap) return false;
  const dot = (dx * forward[0] + dz * forward[2]) / distance;
  return dot > 0.75;
}
