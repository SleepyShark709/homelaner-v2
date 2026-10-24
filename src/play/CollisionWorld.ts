import type { Obstacle } from '../game/collision';
import type { OriginalAsset, OriginalLevel } from '../world/types';

function rotate(q: [number, number, number, number], v: [number, number, number]): [number, number, number] {
  const [x, y, z, w] = q;
  const ix = w * v[0] + y * v[2] - z * v[1];
  const iy = w * v[1] + z * v[0] - x * v[2];
  const iz = w * v[2] + x * v[1] - y * v[0];
  const iw = -x * v[0] - y * v[1] - z * v[2];
  return [
    ix * w + iw * -x + iy * -z - iz * -y,
    iy * w + iw * -y + iz * -x - ix * -z,
    iz * w + iw * -z + ix * -y - iy * -x,
  ];
}

export interface CollisionBuild {
  boxes: Obstacle[];
  spatial: SpatialBoxes;
  stats: { sourceObjects: number; boxes: number; skippedTerrain: number; skippedUnbounded: number; skippedSmall: number; skippedHuge: number };
}

/** Axis-aligned approximations of the original static mesh objects.
 *
 * Asset-local bounds are transformed by the recovered object TRS. Rotation is
 * reduced to its world AABB. This is a viewer collision proxy, not the original
 * cooked PhysX geometry; roofs/overhangs and concave shapes are approximated.
 */
export function buildCollision(levels: OriginalLevel[], assets: OriginalAsset[]): CollisionBuild {
  const assetById = new Map(assets.map(asset => [asset.id, asset]));
  const boxes: Obstacle[] = [];
  const spatial = new SpatialBoxes(20);
  const stats = { sourceObjects: 0, boxes: 0, skippedTerrain: 0, skippedUnbounded: 0, skippedSmall: 0, skippedHuge: 0 };
  for (const level of levels) {
    for (const object of level.objects) {
      stats.sourceObjects++;
      const asset = assetById.get(object.assetId);
      if (!asset?.bounds) { stats.skippedUnbounded++; continue; }
      if (/landscape|heightfield/i.test(asset.id) || /landscape/i.test(asset.sourcePackage ?? '')) { stats.skippedTerrain++; continue; }
      const min: [number, number, number] = [Infinity, Infinity, Infinity];
      const max: [number, number, number] = [-Infinity, -Infinity, -Infinity];
      for (const ix of [asset.bounds.min[0], asset.bounds.max[0]]) {
        for (const iy of [asset.bounds.min[1], asset.bounds.max[1]]) {
          for (const iz of [asset.bounds.min[2], asset.bounds.max[2]]) {
            const local: [number, number, number] = [ix * object.scale[0], iy * object.scale[1], iz * object.scale[2]];
            const rotated = rotate(object.rotation, local);
            for (let axis = 0; axis < 3; axis++) {
              const value = rotated[axis] + object.position[axis];
              min[axis] = Math.min(min[axis], value);
              max[axis] = Math.max(max[axis], value);
            }
          }
        }
      }
      const sizeX = max[0] - min[0], sizeY = max[1] - min[1], sizeZ = max[2] - min[2];
      if (sizeY < 1.2 || sizeX < 0.35 || sizeZ < 0.35) { stats.skippedSmall++; continue; }
      if (sizeX > 500 || sizeZ > 500 || sizeY > 400) { stats.skippedHuge++; continue; }
      const box: Obstacle = { id: object.id, min, max };
      boxes.push(box);
      spatial.add(box);
      stats.boxes++;
    }
  }
  return { boxes, spatial, stats };
}

export class SpatialBoxes {
  private readonly cells = new Map<string, Obstacle[]>();
  private readonly cellSize: number;
  constructor(cellSize: number) { this.cellSize = cellSize; }
  add(box: Obstacle): void {
    const cells = this.coveredCells(box.min[0], box.min[2], box.max[0], box.max[2]);
    for (const key of cells) {
      const list = this.cells.get(key);
      if (list) list.push(box); else this.cells.set(key, [box]);
    }
  }
  nearby(x: number, z: number, radius = 4): Obstacle[] {
    const result: Obstacle[] = [];
    const seen = new Set<string>();
    for (const key of this.coveredCells(x - radius, z - radius, x + radius, z + radius)) {
      for (const box of this.cells.get(key) ?? []) {
        if (seen.has(box.id)) continue;
        seen.add(box.id);
        result.push(box);
      }
    }
    return result;
  }
  private coveredCells(minX: number, minZ: number, maxX: number, maxZ: number): string[] {
    const cells: string[] = [];
    const x0 = Math.floor(minX / this.cellSize), x1 = Math.floor(maxX / this.cellSize);
    const z0 = Math.floor(minZ / this.cellSize), z1 = Math.floor(maxZ / this.cellSize);
    for (let x = x0; x <= x1; x++) for (let z = z0; z <= z1; z++) cells.push(`${x},${z}`);
    return cells;
  }
}
