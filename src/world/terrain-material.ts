import { ShaderMaterial } from '@babylonjs/core/Materials/shaderMaterial';
import { Texture } from '@babylonjs/core/Materials/Textures/texture';
import { Vector2, Vector3 } from '@babylonjs/core/Maths/math.vector';
import type { Scene } from '@babylonjs/core/scene';
import '@babylonjs/core/Shaders/ShadersInclude/instancesDeclaration';
import '@babylonjs/core/Shaders/ShadersInclude/instancesVertex';

type LayerName = 'Grass' | 'Ground' | 'Sand';
interface Layer { albedo: {url: string; colorSpace: string}; normal: {url: string}; tintLinear: number[] }
interface TerrainRecipe {
  id: string; sectionBaseUE: number[]; textureUVScale: number[]; textureUVOffset: number[];
  weightmap: {url: string; channels: Partial<Record<LayerName, number>>; width: number; height: number};
  heightNormal: {url: string; atlasWidth: number; atlasHeight: number; atlasOriginPixels: number[]};
}
export interface TerrainMaterialManifest {
  schemaVersion: number; layers: Record<LayerName, Layer>; objects: TerrainRecipe[];
}

const vertexSource = `precision highp float;
attribute vec3 position;
attribute vec3 normal;
uniform mat4 viewProjection;
#include<instancesDeclaration>
varying vec2 vGrid;
varying vec3 vNormal;
void main(void) {
  #include<instancesVertex>
  vGrid = position.xz;
  vNormal = normalize(mat3(finalWorld) * normal);
  gl_Position = viewProjection * finalWorld * vec4(position, 1.0);
}`;
const fragmentSource = `precision highp float;
varying vec2 vGrid;
varying vec3 vNormal;
uniform sampler2D grassTexture;
uniform sampler2D groundTexture;
uniform sampler2D sandTexture;
uniform sampler2D weightTexture;
uniform sampler2D grassNormal;
uniform sampler2D groundNormal;
uniform sampler2D sandNormal;
uniform sampler2D heightNormal;
uniform vec2 heightAtlasSize;
uniform vec2 heightAtlasOrigin;
uniform vec2 textureScale;
uniform vec2 textureOffset;
uniform vec2 weightSize;
uniform vec3 layerChannels;
uniform vec3 grassTint;
uniform vec3 groundTint;
uniform vec3 sandTint;
vec3 toLinear(vec3 c) {
  return mix(c / 12.92, pow((c + 0.055) / 1.055, vec3(2.4)), step(vec3(0.04045), c));
}
float weightChannel(vec4 weights, float index) {
  if (index < -0.5) return 0.0;
  if (index < 0.5) return weights.r;
  if (index < 1.5) return weights.g;
  if (index < 2.5) return weights.b;
  return weights.a;
}
vec3 unpackNormal(vec2 rg) {
  vec2 xy = rg * 2.0 - 1.0;
  return vec3(xy, sqrt(max(1.0 - dot(xy, xy), 0.0)));
}
void main(void) {
  vec2 localGrid = vGrid;
  vec2 uv = localGrid * textureScale + textureOffset;
  vec2 weightUV = (localGrid + min(floor(localGrid / 63.0), vec2(1.0)) + 0.5) / weightSize;
  vec4 weights = texture2D(weightTexture, weightUV);
  vec3 w = vec3(weightChannel(weights, layerChannels.x), weightChannel(weights, layerChannels.y), weightChannel(weights, layerChannels.z));
  vec3 albedo = clamp(
    toLinear(texture2D(grassTexture, uv).rgb) * grassTint * w.x +
    toLinear(texture2D(groundTexture, uv).rgb) * groundTint * w.y +
    toLinear(texture2D(sandTexture, uv).rgb) * sandTint * w.z, 0.0, 1.0);
  vec3 n = normalize(unpackNormal(texture2D(grassNormal, uv).rg) * w.x +
    unpackNormal(texture2D(groundNormal, uv).rg) * w.y + unpackNormal(texture2D(sandNormal, uv).rg) * w.z);
  vec2 heightUV = (heightAtlasOrigin + localGrid + min(floor(localGrid / 63.0), vec2(1.0)) + 0.5) / heightAtlasSize;
  vec3 N = unpackNormal(texture2D(heightNormal, heightUV).ba);
  vec3 T = normalize(vec3(N.z, 0.0, -N.x));
  vec3 B = cross(N, T);
  vec3 worldNormal = normalize(n.x * T + n.y * B + n.z * N).xzy;
  // Original layer arithmetic above; illumination below is explicitly a Web preview.
  float sun = max(dot(worldNormal, normalize(vec3(-0.374, 0.75, 0.544))), 0.0);
  vec3 lit = albedo * (0.75 + 5.0 * sun);
  vec3 mapped = clamp((lit * (2.51 * lit + 0.03)) / (lit * (2.43 * lit + 0.59) + 0.14), 0.0, 1.0);
  gl_FragColor = vec4(pow(mapped, vec3(1.0 / 2.2)), 1.0);
}`;

export class OriginalTerrainMaterials {
  private textures = new Map<string, Texture>();
  private cache = new Map<string, ShaderMaterial>();
  constructor(private scene: Scene, readonly manifest: TerrainMaterialManifest, private failures: Set<string>) {}
  private texture(url: string, clamp = false): Texture {
    const key = `${url}|${clamp}`;
    let texture = this.textures.get(key);
    if (!texture) {
      texture = new Texture(url, this.scene, false, false, Texture.TRILINEAR_SAMPLINGMODE, undefined, () => this.failures.add(url));
      texture.gammaSpace = false; // The original sRGB albedo is decoded in the shader.
      texture.wrapU = texture.wrapV = clamp ? Texture.CLAMP_ADDRESSMODE : Texture.WRAP_ADDRESSMODE;
      texture.anisotropicFilteringLevel = 8;
      this.textures.set(key, texture);
    }
    return texture;
  }
  get(id: string): ShaderMaterial | undefined {
    if (this.cache.has(id)) return this.cache.get(id);
    const recipe = this.manifest.objects.find(object => object.id === id);
    if (!recipe) return;
    const material = new ShaderMaterial(`original-landscape/${id}`, this.scene, {vertexSource, fragmentSource}, {
      attributes: ['position', 'normal'], uniforms: ['world', 'viewProjection', 'textureScale', 'textureOffset', 'weightSize', 'layerChannels', 'grassTint', 'groundTint', 'sandTint', 'heightAtlasSize', 'heightAtlasOrigin'],
      samplers: ['grassTexture', 'groundTexture', 'sandTexture', 'weightTexture', 'grassNormal', 'groundNormal', 'sandNormal', 'heightNormal'],
    });
    material.metadata = {source: '/Game/-HeroGame/Materials/M_LandScape', recovery: 'original-layer-albedo-and-normal-blend', illumination: 'web-preview', normals: 'original-height-BA-basis'};
    material.setVector2('textureScale', Vector2.FromArray(recipe.textureUVScale));
    material.setVector2('textureOffset', Vector2.FromArray(recipe.textureUVOffset));
    material.setVector2('weightSize', new Vector2(recipe.weightmap.width, recipe.weightmap.height));
    material.setVector3('layerChannels', new Vector3(...(['Grass', 'Ground', 'Sand'] as LayerName[]).map(layer => recipe.weightmap.channels[layer] ?? -1) as [number, number, number]));
    for (const name of ['Grass', 'Ground', 'Sand'] as LayerName[]) {
      const layer = this.manifest.layers[name];
      material.setTexture(`${name.toLowerCase()}Texture`, this.texture(layer.albedo.url));
      material.setTexture(`${name.toLowerCase()}Normal`, this.texture(layer.normal.url));
      material.setVector3(`${name.toLowerCase()}Tint`, Vector3.FromArray(layer.tintLinear));
    }
    material.setTexture('weightTexture', this.texture(recipe.weightmap.url, true));
    material.setTexture('heightNormal', this.texture(recipe.heightNormal.url, true));
    material.setVector2('heightAtlasSize', new Vector2(recipe.heightNormal.atlasWidth, recipe.heightNormal.atlasHeight));
    material.setVector2('heightAtlasOrigin', Vector2.FromArray(recipe.heightNormal.atlasOriginPixels));
    this.cache.set(id, material); return material;
  }
}
