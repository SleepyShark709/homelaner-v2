import type { MaterialManifest, OriginalMaterial } from './types';

function renderingDefinition(record: OriginalMaterial): string {
  const channels = Object.fromEntries(Object.entries(record.channels ?? {}).map(([role, texture]) => [role, texture && {
    url: texture.url, colorSpace: texture.colorSpace, channel: texture.channel, texCoord: texture.texCoord, normalConvention: texture.normalConvention,
  }]));
  const parameters = Object.fromEntries(Object.entries(record.parameters ?? {}).map(([kind, entries]) => [kind,
    Object.fromEntries(Object.entries(entries).sort(([a], [b]) => a.localeCompare(b)).map(([name, entry]) => [name, entry.value])),
  ]));
  return JSON.stringify({baseMaterial: record.baseMaterial, channels, parameters, factors: record.factors,
    packedPBR: record.packedPBR, packedOpacity: record.packedOpacity, blendMode: record.blendMode,
    doubleSided: record.doubleSided, alphaCutoff: record.alphaCutoff, shaderRecovery: record.shaderRecovery});
}

/** An empty saved MID inherits its parent. This only shares immutable preview
 * rendering; source identities and future per-instance runtime state stay separate. */
export function canonicalMaterialSource(source: string, manifest: MaterialManifest, seen = new Set<string>()): string {
  if (seen.has(source)) return source;
  seen.add(source);
  const record = manifest.materials[source];
  const embedded = record?.embeddedInstance;
  if (!record?.parent || embedded?.className !== 'MaterialInstanceDynamic' || embedded.sourceParameters?.length !== 0 ||
      !embedded.remainingProperties?.every(property => property.name === 'CachedReferencedTextures')) return source;
  const parent = manifest.materials[record.parent];
  if (!parent || renderingDefinition(record) !== renderingDefinition(parent)) return source;
  return canonicalMaterialSource(record.parent, manifest, seen);
}
