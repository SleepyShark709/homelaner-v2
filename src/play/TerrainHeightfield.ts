import type { TerrainManifest } from '../world/types';

/** The terrain manifest carries the serialized Landscape heightfields beyond
 * the base TerrainManifest type used by the static viewer. */
export interface HeightfieldMeta {
  id: string;
  url: string;
  encoding: string;
  width: number;
  height: number;
  sha256: string;
  position: [number, number, number];
  horizontalStepMeters: [number, number];
  heightOffset: number;
  heightMultiplierMeters: number;
  heightBaseMeters: number;
  heightFormula?: string;
  collisionCaveat?: string;
}

interface Field {
  meta: HeightfieldMeta;
  data: DataView;
}

/** Exact original Landscape full-resolution height sampler.
 *
 * This samples the recovered uint16 heightfields, not the rendered LOD mesh and
 * not the original cooked PhysX collision. The manifest documents the local
 * height formula; bilinear interpolation is a viewer-side interpolation between
 * original vertices, so it is not a claim of the original triangle collision.
 */
export class TerrainHeightfield {
  private constructor(private readonly fields: Field[]) {}

  get count(): number { return this.fields.length; }

  static async load(manifest: TerrainManifest & { heightfields?: HeightfieldMeta[] }): Promise<TerrainHeightfield> {
    const metas = manifest.heightfields ?? [];
    if (!metas.length) throw new Error('地形清单缺少 heightfields，无法建立可玩地面');
    const fields = await Promise.all(metas.map(async meta => {
      const response = await fetch(meta.url, { cache: 'force-cache' });
      if (!response.ok) throw new Error(`${meta.url} 读取失败 (${response.status})`);
      const buffer = await response.arrayBuffer();
      const expected = meta.width * meta.height * 2;
      if (buffer.byteLength !== expected) throw new Error(`${meta.id} 高度数据长度不符: ${buffer.byteLength}/${expected}`);
      return { meta, data: new DataView(buffer) } satisfies Field;
    }));
    return new TerrainHeightfield(fields);
  }

  heightAt(x: number, z: number): number | null {
    for (const { meta, data } of this.fields) {
      const [ox, , oz] = meta.position;
      const [stepX, stepZ] = meta.horizontalStepMeters;
      const spanX = (meta.width - 1) * stepX;
      const spanZ = (meta.height - 1) * stepZ;
      if (x < ox || x > ox + spanX || z < oz || z > oz + spanZ) continue;
      const gx = (x - ox) / stepX;
      const gz = (z - oz) / stepZ;
      const x0 = Math.min(meta.width - 2, Math.max(0, Math.floor(gx)));
      const z0 = Math.min(meta.height - 2, Math.max(0, Math.floor(gz)));
      const fx = Math.min(1, Math.max(0, gx - x0));
      const fz = Math.min(1, Math.max(0, gz - z0));
      const sample = (column: number, row: number) => {
        const value = data.getUint16((row * meta.width + column) * 2, true);
        return meta.heightBaseMeters + (value - meta.heightOffset) * meta.heightMultiplierMeters;
      };
      const h00 = sample(x0, z0);
      const h10 = sample(x0 + 1, z0);
      const h01 = sample(x0, z0 + 1);
      const h11 = sample(x0 + 1, z0 + 1);
      return (h00 * (1 - fx) + h10 * fx) * (1 - fz) + (h01 * (1 - fx) + h11 * fx) * fz;
    }
    return null;
  }

  bounds(): { min: [number, number, number]; max: [number, number, number] } {
    const min: [number, number, number] = [Infinity, Infinity, Infinity];
    const max: [number, number, number] = [-Infinity, -Infinity, -Infinity];
    for (const { meta } of this.fields) {
      const [ox, oy, oz] = meta.position;
      const [stepX, stepZ] = meta.horizontalStepMeters;
      min[0] = Math.min(min[0], ox);
      min[1] = Math.min(min[1], oy + meta.heightBaseMeters + (0 - meta.heightOffset) * meta.heightMultiplierMeters);
      min[2] = Math.min(min[2], oz);
      max[0] = Math.max(max[0], ox + (meta.width - 1) * stepX);
      max[1] = Math.max(max[1], oy + meta.heightBaseMeters + (65535 - meta.heightOffset) * meta.heightMultiplierMeters);
      max[2] = Math.max(max[2], oz + (meta.height - 1) * stepZ);
    }
    return { min, max };
  }
}
