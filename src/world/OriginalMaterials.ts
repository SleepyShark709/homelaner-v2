import { Scene } from '@babylonjs/core/scene';
import { PBRMaterial } from '@babylonjs/core/Materials/PBR/pbrMaterial';
import { Texture } from '@babylonjs/core/Materials/Textures/texture';
import { Color3 } from '@babylonjs/core/Maths/math.color';
import type { MaterialManifest, TextureChannel } from './types';
import { canonicalMaterialSource } from './material-identity';
import { WorldTriplanarPlugin, FoliageVertexMaskPlugin, type WorldShaderContract, type FoliageShaderContract } from './RecoveredShaderPlugin';
import { ConcreteMildewPlugin, GrassParallaxPlugin, SkyEmissionPlugin, type ConcreteShaderContract, type GrassShaderContract, type SkyMaterialManifest } from './RecoveredSurfacePlugins';

export class OriginalMaterials {
  private cache = new Map<string, PBRMaterial>();
  private textures = new Map<string, Texture>();
  private sourceAliases = new Map<string, string>();
  readonly textureFailures = new Set<string>();
  readonly unknownMaterials = new Set<string>();
  readonly deferredNormals = new Set<string>();
  constructor(private scene: Scene, readonly manifest: MaterialManifest, private sky?: SkyMaterialManifest) {}

  canonical(source: string | null): string | null {
    if (source === null) return null;
    if (!this.sourceAliases.has(source)) this.sourceAliases.set(source, canonicalMaterialSource(source, this.manifest));
    return this.sourceAliases.get(source)!;
  }

  private texture(channel: TextureChannel): Texture {
    const key = `${channel.url}|${channel.colorSpace ?? 'linear'}|${channel.texCoord ?? 0}`;
    let texture = this.textures.get(key);
    if (!texture) {
      // Same UV orientation as the glTF loader; these are exported pixel assets.
      texture = new Texture(channel.url, this.scene, false, false, Texture.TRILINEAR_SAMPLINGMODE, undefined,
        () => this.textureFailures.add(channel.url));
      texture.gammaSpace = channel.colorSpace === 'srgb';
      texture.coordinatesIndex = channel.texCoord ?? 0;
      texture.anisotropicFilteringLevel = 8;
      this.textures.set(key, texture);
    }
    return texture;
  }

  get(source: string | null): PBRMaterial {
    source = this.canonical(source);
    const key = source ?? '__unresolved__';
    const cached = this.cache.get(key);
    if (cached) return cached;
    const material = new PBRMaterial(key, this.scene);
    // Neutral fallback is explicitly unverified, never inferred from asset names.
    material.albedoColor = new Color3(.45, .45, .45);
    material.metallic = 0;
    material.roughness = .8;
    this.cache.set(key, material);
    const record = source ? this.manifest.materials[source] : undefined;
    if (!record) { this.unknownMaterials.add(key); return material; }
    material.metadata = { sourcePackage: source, recoveryStatus: record.status, unsupported: record.unsupported };
    const worldShader = record.shaderRecovery?.kind === 'world-triplanar';
    const grassShader = record.shaderRecovery?.kind === 'grass-parallax-macro';
    const concreteShader = record.shaderRecovery?.kind === 'concrete-mildew';
    const allSurfaceShader = worldShader || grassShader;
    const factors = record.factors ?? {};
    if (typeof record.shaderRecovery?.specular === 'number') {
      // Original DXBC F0 = .08 * specular. Babylon's default IOR 1.5 gives
      // .04 before this factor. This matches F0 only: Babylon's F90/energy
      // model remains preview lighting (see specular-f0-mapping.json).
      material.metallicF0Factor = 2 * record.shaderRecovery.specular;
    }
    if (factors.baseColor?.length) material.albedoColor = Color3.FromArray(factors.baseColor);
    if (factors.roughness != null) material.roughness = factors.roughness;
    if (factors.metallic != null) material.metallic = factors.metallic;
    if (factors.emissive?.length) material.emissiveColor = Color3.FromArray(factors.emissive);
    if (factors.opacity != null) material.alpha = factors.opacity;
    if (source === '/Game/UrbanCity/Materials/Tileable/Tilable_metal_TintC_Inst') {
      // Recovered Tint Colour / Tint Opacity from the material instance. The diffuse
      // texture is retained; this tint replaces the unverified white fallback on the
      // storefront mullions. Full -Tilable_mat layering is still not reconstructed.
      material.albedoColor = new Color3(0.14, 0.145, 0.17);
      material.metallic = 0.5;
      material.roughness = 0.45;
    }
    if (source === '/Game/UrbanCity/Materials/-Window_mat') {
      // Recovered master-cached parameters: the shader's Param colour is almost black-blue,
      // roughness is very low, and the emissive colour is scaled by EmissiveAmount.
      // This replaces the unverified neutral fallback; full shader math is still not reconstructed.
      material.albedoColor = new Color3(0.014750001, 0.017312495, 0.025);
      material.metallic = 0.1;
      material.roughness = 0.062217001;
      material.emissiveColor = new Color3(0.26752028 * 0.15, 0.315 * 0.15, 0.26144999 * 0.15);
    }
    const channels = record.channels ?? {};
    if (channels.baseColor && !allSurfaceShader && !concreteShader) {
      material.albedoTexture = this.texture(channels.baseColor);
      if (!factors.baseColor?.length) material.albedoColor = Color3.White();
    }
    if (channels.normal && !allSurfaceShader) {
      const convention = channels.normal.normalConvention?.toLowerCase();
      if (convention === 'directx' || convention === 'opengl') {
        material.bumpTexture = this.texture(channels.normal);
        material.invertNormalMapX = false;
        // Babylon's RH glTF loader inverts Y for OpenGL normal maps. UE's
        // unflipped DirectX green channel requires the opposite setting.
        material.invertNormalMapY = convention === 'opengl';
      } else this.deferredNormals.add(key);
    }
    if (record.packedPBR && !allSurfaceShader) {
      material.metallicTexture = this.texture({ url: record.packedPBR.url, colorSpace: 'linear' });
      material.useRoughnessFromMetallicTextureAlpha = false;
      material.useRoughnessFromMetallicTextureGreen = true;
      material.useMetallnessFromMetallicTextureBlue = true;
      material.useAmbientOcclusionFromMetallicTextureRed = record.packedPBR.channels?.occlusion === 'r';
      // Packed channels already include recovered scalar factors.
      material.roughness = 1; material.metallic = 1;
    }
    if (!allSurfaceShader && channels.occlusion && ['r', 'rgb'].includes(channels.occlusion.channel ?? '')) {
      material.ambientTexture = this.texture(channels.occlusion);
      material.useAmbientInGrayScale = true;
    }
    if (channels.emissive) {
      material.emissiveTexture = this.texture(channels.emissive);
      if (!factors.emissive?.length) material.emissiveColor = Color3.White();
    }
    material.backFaceCulling = record.doubleSided !== true;
    material.twoSidedLighting = record.doubleSided === true;
    const blend = record.blendMode?.toLowerCase() ?? '';
    const opacity = record.packedOpacity ?? channels.opacity;
    if (opacity?.channel === 'a') {
      material.opacityTexture = this.texture(opacity);
      material.opacityTexture.hasAlpha = true;
    }
    if (blend.includes('masked')) {
      material.transparencyMode = PBRMaterial.PBRMATERIAL_ALPHATEST;
      material.alphaCutOff = record.alphaCutoff ?? .333333;
    } else if (blend.includes('translucent')) {
      material.transparencyMode = PBRMaterial.PBRMATERIAL_ALPHABLEND;
    }
    if (worldShader) {
      material.albedoColor = Color3.White(); material.metallic = 0; material.roughness = 1;
      new WorldTriplanarPlugin(material, record.shaderRecovery as unknown as WorldShaderContract, channel => this.texture(channel));
    } else if (record.shaderRecovery?.kind === 'foliage-vertex-mask') {
      new FoliageVertexMaskPlugin(material, record.shaderRecovery as unknown as FoliageShaderContract);
    } else if (concreteShader) {
      new ConcreteMildewPlugin(material, record.shaderRecovery as unknown as ConcreteShaderContract, channel => this.texture(channel));
    } else if (grassShader) {
      material.albedoColor = Color3.White(); material.metallic = 0; material.roughness = 1;
      new GrassParallaxPlugin(material, record.shaderRecovery as unknown as GrassShaderContract, channel => this.texture(channel));
    }
    const sky = source ? this.sky?.materials[source] : undefined;
    if (sky) {
      material.metadata.skyRecovery = 'original-HDR-emission; remaining lighting and compositing are preview';
      new SkyEmissionPlugin(material, sky, channel => this.texture(channel));
    }
    return material;
  }
}
