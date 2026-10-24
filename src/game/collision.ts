export type Vec3 = [number, number, number];
export interface Bounds { min: Vec3; max: Vec3 }
export interface Obstacle extends Bounds { id: string }
export interface Hit { time: number; normal: Vec3; id: string }

// Swept box against the Minkowski expansion of static geometry. Positions are feet.
export function sweep(origin: Vec3, delta: Vec3, box: Bounds, half: Vec3 = [0, 0, 0]): Omit<Hit, 'id'> | null {
  let near = -Infinity, far = Infinity;
  const normal: Vec3 = [0, 0, 0];
  for (let axis = 0; axis < 3; axis++) {
    const low = box.min[axis] - half[axis], high = box.max[axis] + half[axis];
    if (Math.abs(delta[axis]) < 1e-10) {
      if (origin[axis] <= low + 1e-7 || origin[axis] >= high - 1e-7) return null;
      continue;
    }
    let a = (low - origin[axis]) / delta[axis], b = (high - origin[axis]) / delta[axis];
    const sign = delta[axis] > 0 ? -1 : 1;
    if (a > b) [a, b] = [b, a];
    if (a > near) { near = a; normal.fill(0); normal[axis] = sign; }
    far = Math.min(far, b);
    if (near > far) return null;
  }
  if (near < -1e-7 || near > 1 || far <= 0) return null;
  return { time: Math.max(0, near), normal };
}

export function firstHit(origin: Vec3, delta: Vec3, obstacles: Obstacle[], half: Vec3 = [0, 0, 0]): Hit | null {
  let nearest: Hit | null = null;
  for (const box of obstacles) {
    const hit = sweep(origin, delta, box, half);
    if (hit && (!nearest || hit.time < nearest.time)) nearest = { ...hit, id: box.id };
  }
  return nearest;
}

export function moveAndSlide(feet: Vec3, delta: Vec3, obstacles: Obstacle[], half: Vec3 = [0.36, 0.96, 0.36]): { position: Vec3; normals: Vec3[] } {
  const center: Vec3 = [feet[0], feet[1] + half[1], feet[2]];
  let remaining: Vec3 = [...delta];
  const normals: Vec3[] = [];
  for (let iteration = 0; iteration < 4; iteration++) {
    const hit = firstHit(center, remaining, obstacles, half);
    if (!hit) { for (let i = 0; i < 3; i++) center[i] += remaining[i]; break; }
    const safeTime = Math.max(0, hit.time - 0.001 / Math.max(Math.hypot(...remaining), 0.001));
    for (let i = 0; i < 3; i++) center[i] += remaining[i] * safeTime;
    remaining = remaining.map(value => value * (1 - hit.time)) as Vec3;
    const into = remaining.reduce((sum, value, i) => sum + value * hit.normal[i], 0);
    for (let i = 0; i < 3; i++) remaining[i] -= Math.min(0, into) * hit.normal[i];
    normals.push(hit.normal);
    if (Math.hypot(...remaining) < 1e-6) break;
  }
  return { position: [center[0], center[1] - half[1], center[2]], normals };
}
