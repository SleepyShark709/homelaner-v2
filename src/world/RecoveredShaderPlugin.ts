import { MaterialPluginBase } from '@babylonjs/core/Materials/materialPluginBase';
import type { PBRMaterial } from '@babylonjs/core/Materials/PBR/pbrMaterial';
import type { Texture } from '@babylonjs/core/Materials/Textures/texture';
import type { BaseTexture } from '@babylonjs/core/Materials/Textures/baseTexture';
import type { UniformBuffer } from '@babylonjs/core/Materials/uniformBuffer';
import type { TextureChannel } from './types';

export interface WorldShaderContract {
  kind: 'world-triplanar'; worldScaleUEcmNegative: number[]; originUEcm: number[]; tintLinear: number[];
  normalIntensity: number; roughnessMultiplier: number; metallic: number;
  textures: {baseColor: TextureChannel; normal: TextureChannel; roughness: TextureChannel};
}
export interface FoliageShaderContract {
  kind: 'foliage-vertex-mask'; baseMultiplier: number; occlusionMultiplier: number;
  vertexColorSource?: {status?: string};
}

/** Original WorldTilingMaster operations, recovered from the cooked VS/PS.
 * Babylon still supplies preview lighting; this is not the UE renderer. */
export class WorldTriplanarPlugin extends MaterialPluginBase {
  private readonly maps: Texture[];
  constructor(material: PBRMaterial, private contract: WorldShaderContract, texture: (channel: TextureChannel) => Texture) {
    super(material, 'OriginalWorldTiling', 200, {}, true, false);
    this.maps = [texture(contract.textures.baseColor), texture(contract.textures.normal), texture(contract.textures.roughness)];
    this._enable(true);
  }
  getClassName(): string { return 'WorldTriplanarPlugin'; }
  isReadyForSubMesh(): boolean { return this.maps.every(texture => texture.isReady()); }
  getActiveTextures(textures: BaseTexture[]): void { textures.push(...this.maps); }
  hasTexture(texture: BaseTexture): boolean { return this.maps.includes(texture as Texture); }
  getAttributes(attributes: string[]): void { if (!attributes.includes('tangent')) attributes.push('tangent'); }
  getSamplers(samplers: string[]): void { samplers.push('ueAlbedoMap', 'ueNormalMap', 'ueRoughnessMap'); }
  getUniforms() {
    return {
      ubo: [
        {name: 'ueWorldScale', size: 3, type: 'vec3'}, {name: 'ueOrigin', size: 3, type: 'vec3'},
        {name: 'ueTint', size: 3, type: 'vec3'}, {name: 'ueControls', size: 4, type: 'vec4'},
        {name: 'ueGamma', size: 2, type: 'vec2'},
      ],
      fragment: '#ifndef UNIFORMBUFFERS\nuniform vec3 ueWorldScale;\nuniform vec3 ueOrigin;\nuniform vec3 ueTint;\nuniform vec4 ueControls;\nuniform vec2 ueGamma;\n#endif',
    };
  }
  bindForSubMesh(buffer: UniformBuffer): void {
    const c = this.contract;
    buffer.updateFloat3('ueWorldScale', c.worldScaleUEcmNegative[0], c.worldScaleUEcmNegative[1], c.worldScaleUEcmNegative[2]);
    buffer.updateFloat3('ueOrigin', ...c.originUEcm as [number, number, number]);
    buffer.updateFloat3('ueTint', ...c.tintLinear as [number, number, number]);
    buffer.updateFloat4('ueControls', c.normalIntensity, c.roughnessMultiplier, c.metallic, 'rgba'.indexOf(c.textures.roughness.channel ?? 'r'));
    buffer.updateFloat2('ueGamma', c.textures.baseColor.colorSpace === 'srgb' ? 1 : 0, c.textures.roughness.colorSpace === 'srgb' ? 1 : 0);
    ['ueAlbedoMap', 'ueNormalMap', 'ueRoughnessMap'].forEach((name, i) => buffer.setTexture(name, this.maps[i]));
  }
  getCustomCode(type: string): Record<string, string> | null {
    if (type === 'vertex') return {
      CUSTOM_VERTEX_DEFINITIONS: `
#ifndef TANGENT
attribute vec4 tangent;
#endif
varying vec3 ueTangent;
varying vec3 ueNormal;
varying float ueHandedness;`,
      CUSTOM_VERTEX_UPDATE_WORLDPOS: `
// UE static vertex factory removes axis lengths, retaining negative-axis signs.
mat3 ueNoScale = mat3(finalWorld);
ueNoScale[0] /= max(length(ueNoScale[0]), 1e-10);
ueNoScale[1] /= max(length(ueNoScale[1]), 1e-10);
ueNoScale[2] /= max(length(ueNoScale[2]), 1e-10);
vec3 ueLocalN = normalUpdated.xzy;
vec3 ueLocalT = tangent.xyz.xzy;
vec3 ueLocalB = cross(ueLocalN, ueLocalT) * tangent.w;
ueLocalT = cross(ueLocalB, ueLocalN) * tangent.w;
ueTangent = (ueNoScale * ueLocalT.xzy).xzy;
ueNormal = (ueNoScale * ueLocalN.xzy).xzy;
ueHandedness = tangent.w * sign(dot(cross(ueNoScale[0], ueNoScale[1]), ueNoScale[2]));`,
    };
    if (type !== 'fragment') return null;
    return {
      CUSTOM_FRAGMENT_DEFINITIONS: `
varying vec3 ueTangent;
varying vec3 ueNormal;
varying float ueHandedness;
uniform sampler2D ueAlbedoMap;
uniform sampler2D ueNormalMap;
uniform sampler2D ueRoughnessMap;
vec3 ueSRGB(vec3 c) { return mix(c / 12.92, pow((c + 0.055) / 1.055, vec3(2.4)), step(vec3(0.04045), c)); }
vec3 ueAlbedo(vec2 uv) { vec4 c = texture2D(ueAlbedoMap, uv); return ueGamma.x > 0.5 ? ueSRGB(c.rgb) : c.rgb; }
float ueRoughness(vec2 uv) {
  vec4 c = texture2D(ueRoughnessMap, uv); if (ueGamma.y > 0.5) c.rgb = ueSRGB(c.rgb);
  if (ueControls.w < 0.5) return c.r; if (ueControls.w < 1.5) return c.g;
  if (ueControls.w < 2.5) return c.b; return c.a;
}
vec3 ueDecodeNormal(vec2 uv) {
  vec2 xy = texture2D(ueNormalMap, uv).rg * 2.0 - 1.0;
  return vec3(xy, sqrt(max(1.0 - dot(xy, xy), 0.0)));
}
vec3 uePosition() { return (vPositionW.xzy * 100.0 + ueOrigin) / ueWorldScale; }
vec2 ueColorWeights() { return clamp(3.0 * abs(ueNormal.xz) - 1.0, 0.0, 1.0); }
`,
      CUSTOM_FRAGMENT_BEFORE_LIGHTS: `
vec3 ueQ = uePosition(); vec2 ueBlend = ueColorWeights();
surfaceAlbedo = clamp(mix(mix(ueAlbedo(ueQ.xz), ueAlbedo(ueQ.yz), ueBlend.x), ueAlbedo(ueQ.xy), ueBlend.y) * ueTint, 0.0, 1.0);
vec3 ueA = ueDecodeNormal(ueQ.xz), ueB = ueDecodeNormal(ueQ.yz), ueC = ueDecodeNormal(ueQ.xy);
vec3 ueNXZ = vec3(-ueA.x, ueA.z * ueNormal.y, -ueA.y);
vec3 ueNYZ = vec3(ueB.z * ueNormal.x, -ueB.x, -ueB.y);
vec3 ueNXY = vec3(-ueC.x, -ueC.y, ueC.z * ueNormal.z);
vec3 ueW = normalize(mix(mix(ueNXZ, ueNYZ, clamp(abs(ueNormal.x), 0.0, 1.0)), ueNXY, clamp(abs(ueNormal.z), 0.0, 1.0)));
// Keep interpolated T/N magnitudes. UModel normalizes its quantized vertex
// vectors on export; that documented precision difference remains in the input.
vec3 ueBasisB = cross(ueNormal, ueTangent) * ueHandedness;
vec3 ueNT = normalize(vec3(dot(ueTangent, ueW) * ueControls.x, dot(ueBasisB, ueW) * ueControls.x, dot(ueNormal, ueW)));
normalW = normalize(ueTangent * ueNT.x + ueBasisB * ueNT.y + ueNormal * ueNT.z).xzy;
`,
      CUSTOM_FRAGMENT_UPDATE_METALLICROUGHNESS: `
vec3 ueRQ = uePosition(); vec2 ueRB = ueColorWeights();
metallicRoughness = clamp(vec2(ueControls.z, mix(mix(ueRoughness(ueRQ.xz), ueRoughness(ueRQ.yz), ueRB.x), ueRoughness(ueRQ.xy), ueRB.y) * ueControls.y), 0.0, 1.0);`,
    };
  }
}

export class FoliageVertexMaskPlugin extends MaterialPluginBase {
  constructor(material: PBRMaterial, private contract: FoliageShaderContract) {
    super(material, 'OriginalFoliageMask', 201, {}, true, false);
    this._enable(true);
  }
  getClassName(): string { return 'FoliageVertexMaskPlugin'; }
  getUniforms() {
    return {ubo: [{name: 'ueFoliageFactors', size: 2, type: 'vec2'}], fragment: '#ifndef UNIFORMBUFFERS\nuniform vec2 ueFoliageFactors;\n#endif'};
  }
  bindForSubMesh(buffer: UniformBuffer): void { buffer.updateFloat2('ueFoliageFactors', this.contract.baseMultiplier, this.contract.occlusionMultiplier); }
  getCustomCode(type: string): Record<string, string> | null {
    if (type !== 'fragment') return null;
    return {CUSTOM_FRAGMENT_UPDATE_ALBEDO: `
#ifdef ALBEDO
vec3 ueLeafColor = albedoTexture.rgb;
#ifdef GAMMAALBEDO
ueLeafColor = mix(ueLeafColor / 12.92, pow((ueLeafColor + 0.055) / 1.055, vec3(2.4)), step(vec3(0.04045), ueLeafColor));
#endif
float ueVertexRed = 1.0;
#ifdef VERTEXCOLOR
ueVertexRed = vColor.r;
#endif
surfaceAlbedo = clamp(ueLeafColor * ueFoliageFactors.x * clamp(ueVertexRed * ueFoliageFactors.y, 0.0, 1.0), 0.0, 1.0);
#endif`};
  }
}
