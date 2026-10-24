import { MaterialPluginBase } from '@babylonjs/core/Materials/materialPluginBase';
import type { PBRMaterial } from '@babylonjs/core/Materials/PBR/pbrMaterial';
import type { Texture } from '@babylonjs/core/Materials/Textures/texture';
import type { BaseTexture } from '@babylonjs/core/Materials/Textures/baseTexture';
import type { UniformBuffer } from '@babylonjs/core/Materials/uniformBuffer';
import type { TextureChannel } from './types';

type TextureFactory = (channel: TextureChannel) => Texture;
const linearRGB = `vec3 rsLinear(vec3 c, float gamma) {
  return gamma > 0.5 ? mix(c / 12.92, pow((c + 0.055) / 1.055, vec3(2.4)), step(vec3(0.04045), c)) : c;
}`;
const uvDeclaration = `
#ifndef UV1
attribute vec2 uv;
#endif
varying vec2 rsUV;`;
const basisDeclaration = `
#ifndef TANGENT
attribute vec4 tangent;
#endif
varying vec3 rsT;
varying vec3 rsN;
varying float rsHand;`;
// The original LocalVertexFactory equations, including nonunit interpolated
// frames and retained handedness; see material-shader-recovery/vertex-frame.json.
const basisAssignment = `
mat3 rsNoScale = mat3(finalWorld);
rsNoScale[0] /= max(length(rsNoScale[0]), 1e-10);
rsNoScale[1] /= max(length(rsNoScale[1]), 1e-10);
rsNoScale[2] /= max(length(rsNoScale[2]), 1e-10);
vec3 rsLocalN = normalUpdated.xzy;
vec3 rsLocalT = tangent.xyz.xzy;
vec3 rsLocalB = cross(rsLocalN, rsLocalT) * tangent.w;
rsLocalT = cross(rsLocalB, rsLocalN) * tangent.w;
rsT = (rsNoScale * rsLocalT.xzy).xzy;
rsN = (rsNoScale * rsLocalN.xzy).xzy;
rsHand = tangent.w * sign(dot(cross(rsNoScale[0], rsNoScale[1]), rsNoScale[2]));`;

abstract class SourceTexturePlugin extends MaterialPluginBase {
  protected maps: Texture[] = [];
  protected constructor(material: PBRMaterial, name: string, priority: number) {
    super(material, name, priority, {}, true, false);
  }
  protected initialize(channels: TextureChannel[], texture: TextureFactory): void {
    this.maps = channels.map(texture); this._enable(true);
  }
  isReadyForSubMesh(): boolean { return this.maps.every(texture => texture.isReady()); }
  getActiveTextures(textures: BaseTexture[]): void { textures.push(...this.maps); }
  hasTexture(texture: BaseTexture): boolean { return this.maps.includes(texture as Texture); }
  getAttributes(attributes: string[]): void { if (!attributes.includes('uv')) attributes.push('uv'); }
}

export interface ConcreteShaderContract {
  kind: 'concrete-mildew'; textures: {baseColor: TextureChannel; gradientMask: TextureChannel; mildewMask: TextureChannel};
  gradientAmount: number; mildewAmount: number; mildewColorLinear: number[];
}
export class ConcreteMildewPlugin extends SourceTexturePlugin {
  constructor(material: PBRMaterial, private contract: ConcreteShaderContract, texture: TextureFactory) {
    super(material, 'OriginalConcreteMildew', 202);
    this.initialize([contract.textures.baseColor, contract.textures.gradientMask, contract.textures.mildewMask], texture);
  }
  getClassName(): string { return 'ConcreteMildewPlugin'; }
  getSamplers(samplers: string[]): void { samplers.push('rsConcrete', 'rsGradient', 'rsMildew'); }
  getUniforms() {
    return {ubo: [{name:'rsMaskAmounts',size:2,type:'vec2'}, {name:'rsMildewColor',size:3,type:'vec3'}, {name:'rsConcreteGamma',size:3,type:'vec3'}],
      fragment:'#ifndef UNIFORMBUFFERS\nuniform vec2 rsMaskAmounts;\nuniform vec3 rsMildewColor;\nuniform vec3 rsConcreteGamma;\n#endif'};
  }
  bindForSubMesh(buffer: UniformBuffer): void {
    const c = this.contract;
    buffer.updateFloat2('rsMaskAmounts', c.gradientAmount, c.mildewAmount);
    buffer.updateFloat3('rsMildewColor', ...c.mildewColorLinear as [number,number,number]);
    buffer.updateFloat3('rsConcreteGamma', ...[c.textures.baseColor,c.textures.gradientMask,c.textures.mildewMask].map(t => t.colorSpace === 'srgb' ? 1 : 0) as [number,number,number]);
    ['rsConcrete','rsGradient','rsMildew'].forEach((name,i) => buffer.setTexture(name,this.maps[i]));
  }
  getCustomCode(type: string): Record<string,string> | null {
    if (type === 'vertex') return {CUSTOM_VERTEX_DEFINITIONS:uvDeclaration, CUSTOM_VERTEX_UPDATE_WORLDPOS:'rsUV = uv;'};
    if (type !== 'fragment') return null;
    return {CUSTOM_FRAGMENT_DEFINITIONS:`varying vec2 rsUV;
uniform sampler2D rsConcrete;
uniform sampler2D rsGradient;
uniform sampler2D rsMildew;
${linearRGB}`,
      CUSTOM_FRAGMENT_BEFORE_LIGHTS:`
vec3 rsBase = rsLinear(texture2D(rsConcrete,rsUV).rgb,rsConcreteGamma.x);
float rsWeight = rsLinear(texture2D(rsGradient,rsUV).rgb,rsConcreteGamma.y).r * rsMaskAmounts.x
  + rsLinear(texture2D(rsMildew,rsUV).rgb,rsConcreteGamma.z).r * rsMaskAmounts.y;
surfaceAlbedo = clamp(mix(rsBase,rsMildewColor,rsWeight),0.0,1.0);`};
  }
}

export interface GrassShaderContract {
  kind: 'grass-parallax-macro';
  textures: {height:TextureChannel;normal:TextureChannel;macro:TextureChannel;baseColor:TextureChannel;gloss:TextureChannel};
  heightUVScale:number; heightScale:number; heightBias:number; normalZScale:number;
  macroUVScales:number[]; macroOffsets:number[]; macroColorScale:number; macroColorBias:number;
  tintLinear:number[]; facingColorScale:number; grazingColorPower:number; fresnelMinimum:number; fresnelPower:number;
  macroRoughnessContrast:number; glossScale:number; roughnessScale:number; roughnessBias:number; metallic:number;
}
export class GrassParallaxPlugin extends SourceTexturePlugin {
  constructor(material:PBRMaterial, private contract:GrassShaderContract, texture:TextureFactory) {
    super(material,'OriginalGrassParallax',203);
    const t = contract.textures; this.initialize([t.height,t.normal,t.macro,t.baseColor,t.gloss],texture);
  }
  getClassName():string { return 'GrassParallaxPlugin'; }
  getAttributes(attributes:string[]):void { super.getAttributes(attributes); if (!attributes.includes('tangent')) attributes.push('tangent'); }
  getSamplers(samplers:string[]):void { samplers.push('rsHeight','rsNormal','rsMacro','rsAlbedo','rsGloss'); }
  getUniforms() {
    return {ubo:[
      {name:'rsHeightFactors',size:4,type:'vec4'}, {name:'rsMacroScales',size:3,type:'vec3'},
      {name:'rsMacroOffsets',size:3,type:'vec3'}, {name:'rsColorFactors',size:4,type:'vec4'},
      {name:'rsFresnel',size:2,type:'vec2'}, {name:'rsRoughFactors',size:4,type:'vec4'},
      {name:'rsGrassTint',size:3,type:'vec3'}, {name:'rsGrassGamma',size:4,type:'vec4'},
      {name:'rsGrassMetal',size:1,type:'float'}, {name:'rsGlossGamma',size:1,type:'float'},
    ],fragment:`#ifndef UNIFORMBUFFERS
uniform vec4 rsHeightFactors;
uniform vec3 rsMacroScales;
uniform vec3 rsMacroOffsets;
uniform vec4 rsColorFactors;
uniform vec2 rsFresnel;
uniform vec4 rsRoughFactors;
uniform vec3 rsGrassTint;
uniform vec4 rsGrassGamma;
uniform float rsGrassMetal;
uniform float rsGlossGamma;
#endif`};
  }
  bindForSubMesh(buffer:UniformBuffer):void {
    const c=this.contract,t=c.textures;
    buffer.updateFloat4('rsHeightFactors',c.heightUVScale,c.heightScale,c.heightBias,c.normalZScale);
    buffer.updateFloat3('rsMacroScales',...c.macroUVScales as [number,number,number]);
    buffer.updateFloat3('rsMacroOffsets',...c.macroOffsets as [number,number,number]);
    buffer.updateFloat4('rsColorFactors',c.macroColorScale,c.macroColorBias,c.facingColorScale,c.grazingColorPower);
    buffer.updateFloat2('rsFresnel',c.fresnelMinimum,c.fresnelPower);
    buffer.updateFloat4('rsRoughFactors',c.macroRoughnessContrast,c.glossScale,c.roughnessScale,c.roughnessBias);
    buffer.updateFloat3('rsGrassTint',...c.tintLinear as [number,number,number]);
    buffer.updateFloat4('rsGrassGamma',...[t.height,t.normal,t.macro,t.baseColor].map(v=>v.colorSpace==='srgb'?1:0) as [number,number,number,number]);
    buffer.updateFloat('rsGlossGamma',t.gloss.colorSpace==='srgb'?1:0); buffer.updateFloat('rsGrassMetal',c.metallic);
    ['rsHeight','rsNormal','rsMacro','rsAlbedo','rsGloss'].forEach((name,i)=>buffer.setTexture(name,this.maps[i]));
  }
  getCustomCode(type:string):Record<string,string>|null {
    if(type==='vertex') return {CUSTOM_VERTEX_DEFINITIONS:uvDeclaration+basisDeclaration,CUSTOM_VERTEX_UPDATE_WORLDPOS:`rsUV = uv;\n${basisAssignment}`};
    if(type!=='fragment') return null;
    return {CUSTOM_FRAGMENT_DEFINITIONS:`
varying vec2 rsUV;
varying vec3 rsT;
varying vec3 rsN;
varying float rsHand;
uniform sampler2D rsHeight;
uniform sampler2D rsNormal;
uniform sampler2D rsMacro;
uniform sampler2D rsAlbedo;
uniform sampler2D rsGloss;
${linearRGB}
vec3 rsView() { return normalize((vEyePosition.xyz-vPositionW).xzy); }
vec3 rsB() { return cross(rsN,rsT)*rsHand; }
vec2 rsParallax() {
  float h = rsLinear(texture2D(rsHeight,rsUV*rsHeightFactors.x).rgb,rsGrassGamma.x).r * rsHeightFactors.y + rsHeightFactors.z;
  vec3 v = rsView(); return rsUV + h * vec2(dot(rsT,v),dot(rsB(),v));
}

float rsMacroValue() {
  return (rsLinear(texture2D(rsMacro,rsUV*rsMacroScales.x).rgb,rsGrassGamma.z).r+rsMacroOffsets.x)
    * (rsLinear(texture2D(rsMacro,rsUV*rsMacroScales.y).rgb,rsGrassGamma.z).r+rsMacroOffsets.y)
    * (rsLinear(texture2D(rsMacro,rsUV*rsMacroScales.z).rgb,rsGrassGamma.z).r+rsMacroOffsets.z);
}`,
      CUSTOM_FRAGMENT_BEFORE_LIGHTS:`
vec2 rsP = rsParallax();
vec3 rsC = rsLinear(texture2D(rsAlbedo,rsP).rgb,rsGrassGamma.w) * rsGrassTint * (rsMacroValue()*rsColorFactors.x+rsColorFactors.y);
float rsF = pow(max(abs(1.0-max(dot(rsN,rsView()),0.0)),rsFresnel.x),rsFresnel.y);
surfaceAlbedo = clamp(mix(rsC*rsColorFactors.z,pow(max(rsC,vec3(0.0)),vec3(rsColorFactors.w)),rsF),0.0,1.0);
vec2 rsXY = rsLinear(texture2D(rsNormal,rsP).rgb,rsGrassGamma.y).rg*2.0-1.0;
vec3 rsNT = normalize(vec3(rsXY,sqrt(max(1.0-dot(rsXY,rsXY),0.0))*rsHeightFactors.w));
normalW = normalize(rsT*rsNT.x+rsB()*rsNT.y+rsN*rsNT.z).xzy;`,
      CUSTOM_FRAGMENT_UPDATE_METALLICROUGHNESS:`
float rsG = rsLinear(texture2D(rsGloss,rsParallax()).rgb,rsGlossGamma).r;
float rsR = rsRoughFactors.w+rsRoughFactors.z*rsG*rsRoughFactors.y*(rsMacroValue()*(1.0-rsRoughFactors.x)+rsRoughFactors.x);
metallicRoughness = clamp(vec2(rsGrassMetal,rsR),0.0,1.0);`};
  }
}

export interface SkyShaderContract {
  texture: TextureChannel; uvScale: number[]; contrast: number; brightness: number;
  tint: number[]; selectionColor: number[]; opacity: number;
}
export interface SkyMaterialManifest {schemaVersion: number; materials: Record<string,SkyShaderContract>}

/** Original two-dimensional HDR emission on the original hemisphere UVs.
 * It is not an environment cubemap and does not replace UE's missing fog,
 * reflections, pre-exposure, weather state or complete lighting equation.
 */
export class SkyEmissionPlugin extends SourceTexturePlugin {
  constructor(material:PBRMaterial, private contract:SkyShaderContract, texture:TextureFactory) {
    super(material,'OriginalSkyEmission',204);
    this.initialize([contract.texture],texture);
  }
  getClassName():string {return 'SkyEmissionPlugin';}
  getSamplers(samplers:string[]):void {samplers.push('rsSky');}
  getUniforms() {
    return {ubo:[{name:'rsSkyUV',size:2,type:'vec2'},{name:'rsSkyFactors',size:3,type:'vec3'},
      {name:'rsSkyTint',size:3,type:'vec3'},{name:'rsSkySelection',size:4,type:'vec4'}],
      fragment:`#ifndef UNIFORMBUFFERS
uniform vec2 rsSkyUV;
uniform vec3 rsSkyFactors;
uniform vec3 rsSkyTint;
uniform vec4 rsSkySelection;
#endif`};
  }
  bindForSubMesh(buffer:UniformBuffer):void {
    const c=this.contract;
    buffer.updateFloat2('rsSkyUV',...c.uvScale as [number,number]);
    buffer.updateFloat3('rsSkyFactors',c.contrast,c.brightness,c.opacity);
    buffer.updateFloat3('rsSkyTint',...c.tint as [number,number,number]);
    buffer.updateFloat4('rsSkySelection',...c.selectionColor as [number,number,number,number]);
    buffer.setTexture('rsSky',this.maps[0]);
  }
  getCustomCode(type:string):Record<string,string>|null {
    if(type==='vertex') return {CUSTOM_VERTEX_DEFINITIONS:uvDeclaration,CUSTOM_VERTEX_UPDATE_WORLDPOS:'rsUV = uv;'};
    if(type!=='fragment') return null;
    return {CUSTOM_FRAGMENT_DEFINITIONS:`varying vec2 rsUV;
uniform sampler2D rsSky;
float rsSkyPower(float h) {return h > 0.0 ? exp2(log2(h)*rsSkyFactors.x) : 0.0;}`,
      CUSTOM_FRAGMENT_UPDATE_ALPHA:'alpha = clamp(rsSkyFactors.z,0.0,1.0);',
      CUSTOM_FRAGMENT_BEFORE_FINALCOLORCOMPOSITION:`
vec3 rsHDR = texture2D(rsSky,rsUV*rsSkyUV).rgb;
vec3 rsEmission = vec3(rsSkyPower(rsHDR.r),rsSkyPower(rsHDR.g),rsSkyPower(rsHDR.b))*rsSkyFactors.y*rsSkyTint;
finalEmissive = max(mix(rsEmission,rsSkySelection.rgb,rsSkySelection.a),vec3(0.0));`};
  }
}
