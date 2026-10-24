"""Additional material arithmetic from original frozen uniforms/DXBC; preserve prior contracts."""
from pathlib import Path
import importlib.util,json,struct,math,copy,collections,hashlib
spec=importlib.util.spec_from_file_location('base',Path(__file__).with_name('restore-evidenced-shaders.py'));s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
m=s.m;ROOT=s.ROOT;WORK=s.WORK;D=s.SHADERS
TARGETS=['/Game/ModularStreetPack/Materials/Concrete_Mat','/Game/UrbanCity/Materials/Tileable/cobbleStone_01_Mat','/Game/GTFreeMaterials/Materials/Ground_GrassThickGreen']
def literals(shader,values):
 data=Path(shader['assemblyFile']).with_suffix('.dxbc').read_bytes();parts=struct.unpack_from('<I',data,28)[0];words=[]
 for off in struct.unpack_from('<'+'I'*parts,data,32):
  if data[off:off+4] not in (b'SHDR',b'SHEX'):continue
  size=struct.unpack_from('<I',data,off+4)[0]
  words.extend((q,struct.unpack_from('<f',data,q)[0]) for q in range(off+8,off+8+size,4))
 result={}
 for text in values:
  found=[(q,v) for q,v in words if math.isfinite(v) and f'{v:.6f}'==text];unique={v for q,v in found}
  if text=='0.400000' and len(unique)==2:
   table=dict(words);vectors={v for q,v in found if table.get(q+4)==v and table.get(q+8)==v};assert len(vectors)==1
   vector=next(iter(vectors));scalar=next(iter(unique-vectors))
   result[text]={'value':vector,'variantValues':{'scalarMacroMultiply':scalar,'vectorColorPower':vector},'candidates':[{'value':v,'dxbcByteOffsets':[q for q,x in found if x==v]} for v in sorted(unique)],'note':'Disassembly rounds both to six decimals; scalar multiply adjacent to 0.6 differs from repeated xyz power literal.'};continue
  assert len(unique)==1,(text,unique)
  result[text]={'value':next(iter(unique)),'dxbcByteOffsets':[q for q,v in found]}
 return result
def main():
 manifest=m.read(m.OUT/'material-manifest.json');old={k:copy.deepcopy(v['shaderRecovery']) for k,v in manifest['materials'].items() if v.get('shaderRecovery') and v['baseMaterial'] not in TARGETS};records={};samples=[]
 for pkg,mat in manifest['materials'].items():
  if mat['baseMaterial'] not in TARGETS:continue
  source=m.read(mat['source']['decodedFile']);source_export=source['Exports'][int(mat['source']['exportPointer'].split('/')[-1])]
  assert m.value(m.prop(source_export.get('Data',[]),'bHasStaticPermutationResource'),source) is not True,'Instance permutation requires its own shader: '+pkg
  b=s.bind(mat['baseMaterial'],mat);b['instanceStaticPermutationCheck']='No serialized bHasStaticPermutationResource=true; named instance parameters evaluated against inherited original shader';records[pkg]=b;kind=mat['baseMaterial'];vr,sr=b['vectorRegisters'],b['scalarRegisters']
  ev={'bindingFile':'research/world-recovery/material-shader-recovery/round2-bindings.json','assemblyFile':b['shader']['assemblyFile'],'shaderSha256':b['shader']['sha256'],'materialConstantBuffer':b['materialConstantBuffer']}
  def c(reg,channel,role,lines):return s.channel(manifest,b,reg,channel,role,lines)
  if kind==TARGETS[0]:
   assert b['materialConstantBuffer']==1 and sr[1]['expression']=='Mildew Gradient Amount' and sr[2]['expression']=='Mildew Amount' and vr[3]['expression']=='Mildew Color.rgb'
   textures={'baseColor':c(16,'rgb','baseColor',[103,110]),'gradientMask':c(17,'r','mask',[104,107]),'mildewMask':c(18,'r','mask',[105,107])}
   mat['channels'].update(baseColor=textures['baseColor'],normal=c(15,'rgb','normal',[86,101]),roughness=c(19,'r','roughness',[111,112]));mat['factors'].update(baseColor=None,roughness=1,metallic=0);m.pack_orm(mat,manifest['textures'])
   rec={'version':1,'kind':'concrete-mildew','status':'original-cooked-computation-statically-recovered','authoritativeRoles':['baseColor'],'textures':textures,'uvSource':'TEXCOORD0','gradientAmount':sr[1]['value'][0],'mildewAmount':sr[2]['value'][0],'mildewColorLinear':vr[3]['value'][:3],'specular':.5,
    'formula':{'weight':'sampleGradient(UV0).r*gradientAmount + sampleMildew(UV0).r*mildewAmount; do not clamp this weight','baseColor':'clamp(albedo(UV0).rgb + weight*(mildewColorLinear-albedo(UV0).rgb),0,1)','normal':'ordinary original RG tangent normal at UV0','roughness':'clamp(sampleRoughness(UV0).r,0,1)','metallic':0},
    'factorPolicy':'Plugin replaces final albedo only; ordinary channels/packedPBR provide original normal and roughness. Do not apply generic vertex color to final albedo.',
    'evidence':ev,'limitations':['Original engine lighting, decals and view overrides are outside recovered material computation.']}
  elif kind==TARGETS[1]:
   assert b['materialConstantBuffer']==1
   for role,reg,comp,lines in [('normal',13,'rgb',[79,94]),('baseColor',14,'rgb',[96,98]),('roughness',15,'r',[97,99])]:mat['channels'][role]=c(reg,comp,role,lines)
   mat['factors'].update(baseColor=[1,1,1,1],roughness=1,metallic=0);m.pack_orm(mat,manifest['textures'])
   const=literals(b['shader'],['0.389381']);b['literalEvidence']=const
   rec={'version':1,'kind':'standard-pbr-evidenced','status':'original-material-inputs-recovered','specular':const['0.389381']['value'],'formula':{'baseColor':'clamp(sampleAlbedo(UV0).rgb,0,1)','roughness':'clamp(sampleRoughness(UV0).r,0,1)','normal':'original RG tangent normal at UV0','metallic':0,'specular':'original DXBC constant, see numeric specular'},'evidence':ev,'limitations':['UE specular scalar must use the correct dielectric F0 conversion, not an unrelated shininess parameter.','Ordinary PBR does not reproduce original baked lighting or view overrides.']}
  else:
   assert b['materialConstantBuffer']==2 and sr[1]['expression']=='Macro_roughnessContrast'
   const=literals(b['shader'],['0.100000','-0.036000','0.800000','0.213400','0.053410','0.002000','0.200000','0.500000','0.400000','0.600000','0.824033','0.185000','0.000100','-3.500000','0.150000']);b['literalEvidence']=const
   val=lambda t:const[t]['value']
   textures={role:c(reg,comp,role,lines) for role,reg,comp,lines in [('height',14,'r',[87,92]),('normal',15,'rgb',[93,114]),('macro',16,'r',[116,126]),('baseColor',17,'rgb',[129,148]),('gloss',18,'r',[151,154])]}
   mat['factors'].update(baseColor=None,roughness=1,metallic=0);mat['packedPBR']=None
   rec={'version':1,'kind':'grass-parallax-macro','status':'original-cooked-computation-statically-recovered','authoritativeRoles':['baseColor','normal','roughness','metallic'],'textures':textures,'uvSource':'TEXCOORD0',
    'heightUVScale':2.,'heightScale':val('0.100000'),'heightBias':val('-0.036000'),'normalZScale':val('0.800000'),
    'macroUVScales':[val('0.213400'),val('0.053410'),val('0.002000')],'macroOffsets':[val('0.200000'),val('0.200000'),val('0.500000')],
    'macroColorScale':const['0.400000']['variantValues']['scalarMacroMultiply'],'macroColorBias':val('0.600000'),'tintLinear':[1.,val('0.824033'),val('0.185000')],
    'facingColorScale':val('0.500000'),'grazingColorPower':val('0.400000'),'fresnelMinimum':val('0.000100'),'fresnelPower':6.,
    'macroRoughnessContrast':sr[1]['value'][0],'glossScale':2.,'roughnessScale':val('-3.500000'),'roughnessBias':1.,'metallic':0.,'specular':val('0.150000'),
    'formula':{
     'viewVector':'V=normalize(cameraAbsoluteUEcm - surfaceAbsoluteUEcm). Original shader uses normalize(-translatedWorldPosition) with camera-relative origin. For Web convert absolute world/camera positions .xzy before subtraction.',
     'tangentFrame':'Use original interpolated T,N without normalization and B=cross(N,T)*hand, as vertex-frame.json; keep original UE handedness.',
     'parallaxUV':'h=height(uv0*heightUVScale).r*heightScale+heightBias; uvP=uv0+h*vec2(dot(T,V),dot(B,V)); no division by view.z',
     'macro':'k=(macro(uv0*macroUVScales.x).r+macroOffsets.x)*(macro(uv0*macroUVScales.y).r+macroOffsets.y)*(macro(uv0*macroUVScales.z).r+macroOffsets.z); use uv0, not uvP',
     'tintedColor':'C=albedo(uvP).rgb*tintLinear*(k*macroColorScale+macroColorBias)',
     'fresnel':'f=pow(max(abs(1-max(dot(N,V),0)),fresnelMinimum),fresnelPower); do not normalize interpolated N or clamp f before color mix',
     'baseColor':'clamp(mix(C*facingColorScale,pow(max(C,0),vec3(grazingColorPower)),f),0,1)',
     'roughness':'clamp(roughnessBias + roughnessScale*(gloss(uvP).r*glossScale)*(k*(1-macroRoughnessContrast)+macroRoughnessContrast),0,1)',
     'normal':'xy=2*normal(uvP).rg-1; z=sqrt(max(1-dot(xy,xy),0)); nT=normalize(vec3(xy,z*normalZScale)); worldNormalUE=normalize(T*nT.x+B*nT.y+N*nT.z); worldNormalRH=worldNormalUE.xzy',
     'colorSpace':'Decode each texture RGB using original per-texture colorSpace before taking any R value; alpha stays linear. Repeat wrap, original PNG rows.'},
    'factorPolicy':'Plugin writes all authoritative roles and uses raw recovered textures; no generic UV0 normal or packed ORM substitution and no duplicate factors.',
    'evidence':ev,'limitations':['Original view mip-bias, instanced LOD dithering, lighting and postprocessing are not reconstructed by this material contract.','Uses existing glTF T/N normalization; original packed-vector magnitude precision is retained as a known geometry difference.']}
  mat['shaderRecovery']=rec;mat['status']='partial-dxbc-recovery';mat['unsupported']=[x for x in mat['unsupported'] if not x.startswith('Base color shader connection unknown')];samples.append({'sourcePackage':pkg,'shaderRecovery':rec})
 for pkg,value in old.items():assert manifest['materials'][pkg]['shaderRecovery']==value,'Prior contract changed: '+pkg
 m.write(D/'round2-bindings.json',{'materials':records,'provenance':'Original cooked shader bytes, frozen uniforms, complete D3D11 tables and DXBC; not REA retained Evidence'})
 m.write(WORK/'material-shader-round2-contract.sample.json',samples);m.write(m.OUT/'material-manifest.json',manifest)
 m.write(D/'round2-preservation.json',{'priorContractCount':len(old),'priorContractsUnchanged':True,'priorContractsSha256':hashlib.sha256(json.dumps(old,sort_keys=True).encode()).hexdigest(),'newContractCount':len(records),'newPackages':list(records),'originalTexturesReexported':False})
 f0_sources=[]
 for relative,lines in [('node_modules/@babylonjs/core/Materials/PBR/pbrBaseMaterial.pure.js',[1653,1662]),('node_modules/@babylonjs/core/Shaders/ShadersInclude/pbrBlockReflectivity.js',[82,109])]:
  file=ROOT/relative;f0_sources.append({'file':relative,'sha256':m.sha(file),'lines':lines})
 m.write(D/'specular-f0-mapping.json',{'originalSources':[{'package':p,'assemblyFile':b['shader']['assemblyFile'],'shaderSha256':b['shader']['sha256'],'instruction':'mul ..., specular, l(0.080000)','line':154 if p.endswith('Concrete_Mat') else 143 if p.endswith('cobbleStone_01_Mat') else 206} for p,b in records.items() if p in TARGETS],
  'originalFormula':'dielectricF0=0.08*UESpecular; mix with baseColor by metallic','babylonSources':f0_sources,
  'babylonFormula':'defaultF0=((IOR-1)/(IOR+1))^2; dielectricF0=defaultF0*metallicF0Factor*metallicReflectanceColor',
  'mappingAtIOR1_5AndWhiteReflectance':'metallicF0Factor=2*UESpecular','scope':'Matches dielectric F0 only. Current Babylon also uses specularWeight/factor in F90 and energy terms; full UE Fresnel/lighting equivalence not claimed.'})
 print('New descriptors',len(records),'preserved contracts',len(old))
if __name__=='__main__':main()
