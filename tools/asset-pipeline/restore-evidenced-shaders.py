"""Restore three bounded original material computations from retained cooked DXBC."""
from pathlib import Path
import json,struct,math,copy,importlib.util,collections
ROOT=Path(__file__).resolve().parents[2];WORK=ROOT/'research/world-recovery';SHADERS=WORK/'material-shader-recovery'
spec=importlib.util.spec_from_file_location('restore',Path(__file__).with_name('restore-world-materials.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
TARGETS=['/Game/ForgottenHotel/Materials/Tiling_Mats/WorldTilingMaster','/Game/UrbanCity/Materials/Foliage/Foliage_Mat','/Game/UrbanCity/Materials/Props/prp_bench_Mat']
def effective_parameter(mat,p,kind):
 v=mat['parameters'][kind].get(p['parameter'],{}).get('value',p['defaultValue'])
 return m.rgba(v) if isinstance(v,dict) else [float(v)]*4 if isinstance(v,(int,float)) else v
def evaluate(u,h,mat):
 b=bytes.fromhex(h['bytesHex']);q=0;stack=[]
 while q<len(b):
  op=b[q];q+=1
  if op in (3,4):
   i=struct.unpack_from('<H',b,q)[0];q+=2;p=u['scalarParameters' if op==3 else 'vectorParameters'][i];stack.append((effective_parameter(mat,p,'scalar' if op==3 else 'vector'),p['parameter']))
  elif op==2:
   v=list(struct.unpack_from('<4f',b,q));q+=16;stack.append((v,str(v)))
  elif op==25:
   v,e=stack.pop();stack.append(([abs(x) for x in v],'abs('+e+')'))
  elif op==7:
   y,ye=stack.pop();x,xe=stack.pop();stack.append(([a*b for a,b in zip(x,y)],'('+xe+'*'+ye+')'))
  elif op==35:
   n=b[q];ix=b[q+1:q+5];q+=5;v,e=stack.pop();result=[v[ix[0]]]*4 if n==1 else [v[i] for i in ix[:n]]+[0.]*(4-n);stack.append((result,e+'.'+''.join('rgba'[i] for i in ix[:n])))
  else:raise ValueError('Unimplemented preshader opcode '+str(op))
 assert len(stack)==1 and all(math.isfinite(x) for x in stack[0][0]);return {'value':stack[0][0],'expression':stack[0][1],'bytesHex':h['bytesHex'],'offset':h['offset']}
def bind(pkg,mat):
 folder=SHADERS/pkg.rsplit('/',1)[-1];idx=m.read(folder/'index.json');u=m.read(folder/'uniforms.json');s=idx['shaders'][0];assert s['stage']=='ps_5_0'
 groups=collections.defaultdict(list)
 for x in s['resourceTable']['textureBindings']:groups[x['constantBuffer']].append(x)
 candidates=[(cb,rs) for cb,rs in groups.items() if sorted(x['resourceIndex'] for x in rs)==list(range(0,2*len(u['textureParameters2D']),2))];assert len(candidates)==1
 cb,rs=candidates[0];bindings={}
 for r in rs:
  p=u['textureParameters2D'][r['resourceIndex']//2];tex=mat['parameters']['texture'].get(p['parameter'],{}).get('value',p['defaultTextureObject']);bindings[r['bindIndex']]={'package':tex,'parameter':p['parameter'],'textureParameterIndex':p['index'],'resourceIndex':r['resourceIndex']}
 vr=[evaluate(u,h,mat) for h in u['uniformVectorPreshaders']];sr=[evaluate(u,h,mat) for h in u['uniformScalarPreshaders']]
 return {'package':pkg,'materialConstantBuffer':cb,'textures':bindings,'vectorRegisters':vr,'scalarRegisters':[dict(v,register=len(vr)+i//4,component='xyzw'[i%4]) for i,v in enumerate(sr)],'shader':s,'source':idx['source'],'indexFile':str(folder/'index.json')}
def channel(manifest,binding,register,component,role,lines):
 record=binding['textures'][register];t=manifest['textures'][record['package']];assert t['status']=='exported-original-pixels'
 c={k:t[k] for k in ['url','colorSpace']};c.update(texturePackage=record['package'],channel=component,texCoord=0,sourceParameter=record['parameter'] or f'DXBC:t{register}',
  evidence={'file':str(Path(binding['indexFile']).relative_to(ROOT)),'pointer':'/shaders/0','package':binding['package']},
  shaderEvidence={'assemblyFile':binding['shader']['assemblyFile'],'assemblyLines':lines,'shaderSha256':binding['shader']['sha256'],'textureRegister':register,'constantBuffer':binding['materialConstantBuffer'],'resourceIndex':record['resourceIndex'],'componentSwizzle':component},
  mappingBasis='Original DXBC sampler swizzle and dataflow plus frozen texture table and complete D3D11 resource binding, not texture-name inference',uvMappingStatus='original TEXCOORD0')
 if role=='normal':c.update(normalConvention=t.get('normalConvention','unknown'),normalValidation={k:t[k] for k in ['greenChannelTransformation','validation','sourceBulkSha256','reason'] if k in t})
 return c
WORLD_FORMULA={
 'vertexTangentFrame':'For static meshes: Blocal=cross(Nlocal,Tlocal)*localHand; Tcorrected=cross(Blocal,Nlocal)*localHand. Build noScaleWorld by dividing each finalWorld basis axis by its positive length (retain negative-axis sign). VS T=noScaleWorld*Tcorrected, N=noScaleWorld*Nlocal, hand=original tangent sign*primitive determinant sign. No inverse-transpose and no output-vector normalization. For original UE instanced path its matrix axes are individually normalized before the same transform; exact original instance sign policy is separately recorded.',
 'position':'absoluteUEcm = 100 * worldPositionRHmeters.xzy + originUEcm; q = absoluteUEcm / worldScaleUEcmNegative',
 'sourcePreViewTranslation':'Original PS: TEXCOORD9 translated world position minus View.PreViewTranslation (cb0[70].xyz). Web absolute world position already excludes camera translation; do not subtract camera position. Use final world position after every actor/instance transform.',
 'normalCoordinates':'T=v0.xyz and N=v1.xyz are unnormalized linear-centroid pixel interpolants of original world tangent/normal. B=cross(N,T)*v1.w is rebuilt per pixel; do NOT normalize T,N,B before weight/projection math. Convert the correct original Web RH basis by .xzy; preserve reflection and instance determinant handedness.',
 'weightsColor':'blendX=clamp(3*abs(N.x)-1,0,1); blendZ=clamp(3*abs(N.z)-1,0,1)',
 'baseColor':'clamp(mix(mix(sampleAlbedo(q.xz).rgb,sampleAlbedo(q.yz).rgb,blendX),sampleAlbedo(q.xy).rgb,blendZ)*tintLinear,0,1)',
 'roughness':'clamp(mix(mix(sampleRoughness(q.xz).r,sampleRoughness(q.yz).r,blendX),sampleRoughness(q.xy).r,blendZ)*roughnessMultiplier,0,1)',
 'normalDecode':'decode(uv)=vec3(2*sampleNormal(uv).rg-1,sqrt(max(1-dot(2*sampleNormal(uv).rg-1,2*sampleNormal(uv).rg-1),0)))',
 'normalProjection':'a=decode(q.xz); b=decode(q.yz); c=decode(q.xy); nxz=vec3(-a.x,a.z*N.y,-a.y); nyz=vec3(b.z*N.x,-b.x,-b.y); nxy=vec3(-c.x,-c.y,c.z*N.z)',
 'normalBlend':'W=normalize(mix(mix(nxz,nyz,clamp(abs(N.x),0,1)),nxy,clamp(abs(N.z),0,1)))',
 'normalIntensity':'nT=normalize(vec3(dot(T,W)*normalIntensity,dot(B,W)*normalIntensity,dot(N,W))); outUE=normalize(T*nT.x+B*nT.y+N*nT.z); worldNormalRH=outUE.xzy',
 'normalIntensityOrthonormalEquivalent':'Not valid generally for the original interpolated frame. Only mathematically valid for a proven orthonormal TBN: outUE=normalize(normalIntensity*W + (1-normalIntensity)*dot(N,W)*N)',
 'sampling':'Texture RGB decoded using original SRGB state; alpha remains linear. Repeat wrap; original PNG rows unchanged. No green-channel flip for the explicit UE world normal projection.',
 'metallic':'clamp(metallic,0,1)','specular':'0.5 UE default-lit scalar (F0=0.04 for dielectric)','selectionEmissive':'SelectionColor.rgb*SelectionColor.a; default zero; preserve if set'}
def world_record(manifest,mat,b):
 assert b['materialConstantBuffer']==3
 vr,sr=b['vectorRegisters'],b['scalarRegisters'];scale=vr[4]['value'][:3];assert all(x<0 for x in scale)
 assert sr[0]['expression']=='World Align Normal Intensity' and sr[2]['expression']=='Metalness' and sr[3]['expression']=='RoughnessBrightness'
 c={role:channel(manifest,b,reg,comp,role,lines) for role,reg,comp,lines in [('normal',6,'rgb',[82,134]),('baseColor',7,'rgb',[136,145]),('roughness',8,'r',[146,154])]}
 return {'version':1,'kind':'world-triplanar','status':'original-cooked-computation-statically-recovered','authoritativeRoles':['baseColor','normal','roughness','metallic'],
  'worldScaleUEcmNegative':scale,'originUEcm':[0,0,0],'tintLinear':vr[7]['value'][:3],'normalIntensity':sr[0]['value'][0],'roughnessMultiplier':sr[3]['value'][0],'metallic':sr[2]['value'][0],
  'textures':c,'formula':WORLD_FORMULA,'factorPolicy':'Plugin writes final baseColor,roughness,metallic and worldNormal; do not reapply generic channels/factors to these roles.',
  'evidence':{'bindingFile':str(SHADERS/'bindings.json'),'materialConstantBuffer':3,'shaderSha256':b['shader']['sha256'],'assemblyFile':b['shader']['assemblyFile'],'normalLines':[80,134],'colorAndRoughnessLines':[135,156]},
  'limitations':['Static original material operations, not lighting/postprocess equivalence.','World-aligned normal requires geometric original world normal and orthonormal tangent frame or full stated TBN formula.','Origin remains zero in current export; update originUEcm if future origin rebasing is introduced.']}
def main():
 manifest=m.read(m.OUT/'material-manifest.json');records={};original={};worlds=[]
 for pkg,mat in manifest['materials'].items():
  if mat['baseMaterial'] not in TARGETS:continue
  original[pkg]={'status':mat['status'],'channels':copy.deepcopy(mat['channels']),'factors':copy.deepcopy(mat['factors'])}
  b=bind(mat['baseMaterial'],mat);records[pkg]=b
  if mat['baseMaterial']==TARGETS[0]:
   r=world_record(manifest,mat,b);mat['shaderRecovery']=r;worlds.append({'sourcePackage':pkg,'shaderRecovery':r})
  elif mat['baseMaterial']==TARGETS[2]:
   for role,reg,comp,lines in [('normal',9,'rgb',[88,106]),('baseColor',10,'rgb',[108,114]),('metallic',11,'r',[109,115]),('roughness',12,'r',[110,111]),('occlusion',13,'r',[112,116])]:mat['channels'][role]=channel(manifest,b,reg,comp,role,lines)
   mat['factors'].update(baseColor=[1,1,1,1],roughness=b['scalarRegisters'][1]['value'][0],metallic=1)
   m.pack_orm(mat,manifest['textures'])
   mat['shaderRecovery']={'version':1,'kind':'standard-pbr-evidenced','status':'original-material-inputs-recovered','formula':{'baseColor':'clamp(sample(t10,UV0).rgb,0,1)','metallic':'clamp(sample(t11,UV0).r,0,1)','roughness':'clamp(sample(t12,UV0).r*Param,0,1)','occlusion':'clamp(sample(t13,UV0).r,0,1)','normal':'RG tangent normal with positive reconstructed Z','specular':'0.5'},'evidence':{'bindingFile':str(SHADERS/'bindings.json'),'shaderSha256':b['shader']['sha256']},'limitations':['UE lighting/decal/lightmap/view overrides are not part of recovered material inputs.']}
  else:
   for role,reg,comp,lines in [('normal',5,'rgb',[81,100]),('baseColor',6,'rgb',[102,105]),('roughness',7,'r',[106,107]),('opacity',6,'a',[102,128])]:mat['channels'][role]=channel(manifest,b,reg,comp,role,lines)
   sr=b['scalarRegisters'];mat['factors'].update(baseColor=None,roughness=sr[3]['value'][0],metallic=0,opacity=1);m.pack_orm(mat,manifest['textures']);m.pack_opacity(mat)
   mat['shaderRecovery']={'version':1,'kind':'foliage-vertex-mask','status':'original-cooked-computation-with-vertex-data-dependency','baseMultiplier':3,'occlusionMultiplier':sr[1]['value'][0],'roughnessMultiplier':sr[3]['value'][0],'specular':sr[2]['value'][0],'subsurfaceStrength':sr[7]['value'][0],
    'formula':{'baseColor':'clamp(3*sampleAlbedo(UV0).rgb*clamp(vertexColor.r*occlusionMultiplier,0,1),0,1)','opacity':'sampleAlbedo(UV0).a','alphaCutoff':0.3333,'roughness':'clamp(sampleRoughness(UV0).r*roughnessMultiplier,0,1)','metallic':0,'subsurfaceColor':'clamp(sampleAlbedo(UV0).rgb*subsurfaceStrength,0,1)','normal':'RG tangent normal; original world normal multiplied by TwoSidedSign'},
    'factorPolicy':'Plugin must replace final albedo; generic PBR channels/ORM/packedOpacity provide other recovered inputs. Do not multiply original vertex color RGB conventionally.',
    'evidence':{'bindingFile':str(SHADERS/'bindings.json'),'shaderSha256':b['shader']['sha256'],'assemblyFile':b['shader']['assemblyFile'],'assemblyLines':[81,134]},
    'vertexColorSource':{'status':'source-backed-default-white','value':[1,1,1,1],'scope':'26 source meshes,688 map components and31 exact templates audited','evidence':'research/world-recovery/geometry-vertex-color-audit.json','basis':'Native LOD0 color vertex counts zero; no component/template OverrideVertexColors; UModel supports original colors when present'},
    'limitations':['Default white applies to the audited geometry scope; future meshes with actual color buffers must supply original COLOR0.r.','Two-sided foliage subsurface lighting, wind deformation, per-instance LOD dither and original engine lighting are not restored by ordinary PBR.','ORM packing is 8-bit quantized and can move scalar clamp before filtering; source formula remains authoritative.']}
  mat['status']='partial-dxbc-recovery';mat['unsupported']=[x for x in mat['unsupported'] if not x.startswith('Base color shader connection unknown')]
  if mat['baseMaterial']!=TARGETS[0]:mat['unsupported'].append('Recovered material inputs have explicit shaderRecovery; complete original lighting not reconstructed.')
 m.write(SHADERS/'bindings.json',{'provenance':'Original cooked Extras DXBC/frozen uniform/source parameter analysis with Microsoft disassembly; not REA output','materials':records})
 vertex_sources=[]
 for filename,url,lines in [
  ('UE-LocalVertexFactory-4.26.ush','https://raw.githubusercontent.com/CFHH/UnrealEngine-4.26/main/Engine/Shaders/Private/LocalVertexFactory.ush',[479,486,691,746,794,796,933]),
  ('UE-SceneData-4.26.ush','https://raw.githubusercontent.com/CFHH/UnrealEngine-4.26/main/Engine/Shaders/Private/SceneData.ush',[11,40,79,83]),
  ('UE-PrimitiveUniformShaderParameters-4.26.h','https://raw.githubusercontent.com/CFHH/UnrealEngine-4.26/main/Engine/Source/Runtime/Engine/Public/PrimitiveUniformShaderParameters.h',[88,102])]:
  file=SHADERS/filename;vertex_sources.append({'file':str(file.relative_to(ROOT)),'sha256':m.sha(file),'url':url,'relevantLines':lines,'role':'Epic UE4.26 source mirror for layout/semantic corroboration; not asserted to be the exact original game source'})
 dxbc=SHADERS/'WorldTilingMaster/shader-22-vs_5_0.dxbc'
 m.write(SHADERS/'vertex-frame.json',{'originalStaticMeshShader':{'file':str(dxbc.relative_to(ROOT)),'sha256':m.sha(dxbc),'assemblyFile':str(dxbc.with_suffix('.asm').relative_to(ROOT)),'sourceLines':[48,59,60,83]},
  'corroboratingSources':vertex_sources,'formula':WORLD_FORMULA['vertexTangentFrame'],
  'interpolation':'Original PS T,N are linear centroid interpolants; no PS normalization before original triplanar weights. Rebuild B per pixel from cross(N,T)*hand.',
  'axisHandedness':'UModel transforms XYZ by swapping Y/Z, normalizes XYZ separately, and retains tangent.w=sign(originalNormal.w). Convert T/N back with .xzy before original UE cross products; do not add a second coordinate-reflection sign.',
  'glTFPrecisionLimitation':'UModel separately normalizes original quantized T/N XYZ; the original pre-normalization magnitudes are not recoverable from current glTF. Original source arithmetic recovered, browser inputs retain this exporter difference.',
  'instancePolicyLimitation':'Original UE instancing normalizes combined instance-to-world axes but TangentToWorldSign uses primitive determinant sign; arbitrary negative per-instance determinant equivalence is not claimed. Current non-instanced original components grouped as Web instances use their original primitive transforms.'})
 m.write(WORK/'material-shader-contract.sample.json',next(x for x in worlds if x['sourcePackage'].endswith('/MI_FloorAsphalt')))
 if not (SHADERS/'before-recovery.json').exists():m.write(SHADERS/'before-recovery.json',original)
 m.write(m.OUT/'material-manifest.json',manifest)
 print('Restored shader descriptors',len(records),'world',len(worlds))
if __name__=='__main__':main()
