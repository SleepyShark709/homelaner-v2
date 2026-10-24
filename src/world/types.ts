export type V3 = [number, number, number];
export type Q4 = [number, number, number, number];
export interface Bounds { min: V3; max: V3 }
export interface SourceMaterial { package: string; object?: string; reference?: string }
export interface MaterialSlot { slotIndex: number; slotName?: string; material: SourceMaterial | null }
export interface OriginalObject {
  id: string; assetId: string; position: V3; rotation: Q4; scale: V3;
  source?: { package?: string; actor?: string; component?: string; exportIndex?: number };
  materialOverrides?: MaterialSlot[];
  geometryMode?: string;
  sourceComponents?: { id: string }[];
  visibilityProperties?: Record<string, unknown>;
}
export interface OriginalAsset {
  id: string; url: string; sourcePackage?: string; bounds?: Bounds;
  highQualityUrl?: string;
  sourceMaterialSlots?: MaterialSlot[];
  gltfMaterials?: { materialIndex: number; name: string; sourceSlotCandidates: number[] }[];
  geometryStats?: { triangles?: number };
}
export interface OriginalLevel {
  id: string; package: string; scope: 'main-world' | 'supplemental';
  bounds?: Bounds; objects: OriginalObject[];
}
export interface GeometryManifest {
  schemaVersion: number; coordinateSystem: string; originUE: V3;
  assets: OriginalAsset[]; levels: OriginalLevel[];
  spawnCandidates?: { levelId: string; position: V3; rotation: Q4; sourceActor: string }[];
  gaps: unknown[]; totals: Record<string, number>;
}
export interface TextureChannel {
  texturePackage?: string; url: string; colorSpace?: string; channel?: string;
  texCoord?: number; normalConvention?: string; sourceParameter?: string;
}
export interface OriginalMaterial {
  sourcePackage: string; parent?: string | null; baseMaterial?: string;
  blendMode?: string; doubleSided?: boolean; alphaCutoff?: number;
  channels: Partial<Record<'baseColor' | 'normal' | 'roughness' | 'metallic' | 'occlusion' | 'emissive' | 'opacity', TextureChannel | null>>;
  factors?: { baseColor?: number[] | null; roughness?: number | null; metallic?: number | null; emissive?: number[] | null; opacity?: number | null };
  packedPBR?: { url: string; channels?: Record<string, string> } | null;
  packedOpacity?: TextureChannel | null;
  unsupported?: unknown[]; status?: string;
  parameters?: Record<string, Record<string, {value: unknown}>>;
  embeddedInstance?: {className?: string; sourceParameters?: unknown[]; remainingProperties?: {name: string}[]};
  shaderRecovery?: Record<string, unknown>;
}
export interface MaterialManifest {
  schemaVersion: number; materials: Record<string, OriginalMaterial>; textures?: Record<string, unknown>;
}
export interface TerrainManifest {
  coordinateSystem: string; originUE: V3; assets: OriginalAsset[]; objects: OriginalObject[];
  totals?: Record<string, number>; limitations?: string[];
}
export interface StreamingManifest {
  schemaVersion: number;
  baseline: {packages: string[]; levelNames: string[]; stage: string};
  startupSequence: unknown[];
}

// A repeated source material may occupy several UE slots. A merged glTF primitive
// is safe to override only when every candidate slot resolves to the same material.
export function resolveMaterialPackage(asset: OriginalAsset, materialIndex: number, overrides: MaterialSlot[] = []): { package: string | null; ambiguous: boolean } {
  const candidates = asset.gltfMaterials?.find(item => item.materialIndex === materialIndex)?.sourceSlotCandidates ?? [];
  const resolved = candidates.map(slotIndex => {
    const replacement = overrides.find(item => item.slotIndex === slotIndex)?.material;
    return (replacement ?? asset.sourceMaterialSlots?.find(item => item.slotIndex === slotIndex)?.material)?.package ?? null;
  });
  const unique = new Set(resolved);
  return { package: unique.size === 1 ? resolved[0] : null, ambiguous: unique.size > 1 };
}

export function explicitlyHidden(object: OriginalObject): boolean {
  const p = object.visibilityProperties ?? {};
  return p.bHiddenInGame === true || p.bVisible === false || p.actorHidden === true;
}

export function sourceObjectCount(object: OriginalObject): number {
  return object.sourceComponents?.length || 1;
}
