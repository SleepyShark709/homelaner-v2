export interface WalkableSurface {
  id: string;
  level: string;
  source: string;
  asset: string;
  material: string | null;
  minX: number;
  maxX: number;
  minZ: number;
  maxZ: number;
  top: number;
  bottom: number;
  area: number;
}

/**
 * AABB top surfaces from recovered flat /Mesh/Floor/ meshes (plaza brick
 * floors and similar). These are sampled in addition to the Landscape
 * heightfield; they are not cooked PhysX and have no side collision.
 */
export class WalkableSurfaces {
  private constructor(readonly surfaces: WalkableSurface[]) {}
  static async load(url: string): Promise<WalkableSurfaces> {
    try {
      const response = await fetch(url);
      if (!response.ok) return new WalkableSurfaces([]);
      const data = await response.json() as { surfaces?: WalkableSurface[] };
      return new WalkableSurfaces(Array.isArray(data.surfaces) ? data.surfaces : []);
    } catch {
      return new WalkableSurfaces([]);
    }
  }
  /** Highest floor top that is at most maxStep above the current feet height. */
  topAt(x: number, z: number, feetY: number, maxStep = 1): number | undefined {
    let best: number | undefined;
    for (const s of this.surfaces) {
      if (x < s.minX || x > s.maxX || z < s.minZ || z > s.maxZ) continue;
      if (s.top > feetY + maxStep) continue;
      if (best === undefined || s.top > best) best = s.top;
    }
    return best;
  }
}
