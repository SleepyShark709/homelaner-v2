"""Package only statically evidenced Landscape material; no guessed layers or Web edits.
Requires terrain-uniform-binding-check.py output and existing original texture exports.
"""
from pathlib import Path
import ast,json,re,struct,hashlib
ROOT=Path(__file__).resolve().parents[2]
E=ROOT/'research/world-recovery'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
tree=ast.parse((ROOT/'tools/asset-pipeline/restore-world-terrain.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name in ['array_items','val','props']],type_ignores=[]),'helpers','exec'))
t=read(ROOT/'public/assets/world/terrain-manifest.json');m=read(ROOT/'public/assets/world/material-manifest.json')
u=read(E/'terrain-uniform-binding-check.json')['records'];si=read(E/'terrain-material-shaders/index.json')

# FD3D11ShaderResourceTable: base bits, SRV/sampler/UAV/layout arrays, then texture array.
def resource_table(hexdata):
    b=bytes.fromhex(hexdata);q=4;out={'resourceTableBits':struct.unpack_from('<I',b)[0]}
    for name in ['srvMap','samplerMap','uavMap','layoutHashes','textureMap']:
        n=struct.unpack_from('<I',b,q)[0];q+=4;assert n<2048
        out[name]=list(struct.unpack_from('<'+'I'*n,b,q));q+=4*n
    assert q==len(b),(q,len(b))
    def entries(a):
        # Initial offset table is indexed by uniform buffer. Tokens follow; EOS is ffffffff.
        count=len(out['layoutHashes']);res=[]
        for cb in range(count):
            start=a[cb] if cb<len(a) else 0
            if not start:continue
            for token in a[start:]:
                if token==0xffffffff or token>>24!=cb:break
                res.append({'constantBuffer':cb,'resourceIndex':(token>>8)&65535,'bindIndex':token&255,'token':hex(token)})
        return res
    out['textureBindings']=entries(out['textureMap']);out['samplerBindings']=entries(out['samplerMap']);return out

overrides={'Texture Scale':0.20000000298023224,'Metalic':0.,'Spec':0.12807300686836243,'Roughness':1.,'SandColor':[0.5364480018615723,0.5699999928474426,0.4801490008831024,1.]}
def eval_preshader(row,h):
    b=bytes.fromhex(h['bytesHex']);op=b[0];index=struct.unpack_from('<H',b,1)[0]
    assert op in (3,4)
    param=row['scalarParameters' if op==3 else 'vectorParameters'][index]
    v=overrides.get(param['parameter'],param['defaultValue']);v=[v]*4 if op==3 else v
    expr=param['parameter']
    if len(b)>3:
        assert len(b)==9 and b[3]==35
        count=b[4];indices=list(b[5:9]);assert 1<=count<=4
        v=[v[i] for i in indices[:count]]+[0.]*(4-count);expr+='.'+''.join('rgba'[i] for i in indices[:count])
    return {'expression':expr,'defaultOrInstanceValue':v,'preshaderHex':h['bytesHex'],'preshaderDataOffset':h['offset']}

binding_records=[];resource_validated=0;resource_prefix_unparsed=[]
for row,shaders in zip(u,si):
    assert row['exportIndex']==shaders['exportIndex']
    candidates=[]
    for n,s in enumerate(shaders['shaders']):
        try:tab=resource_table(s['decodedPrefixHex'])
        except (AssertionError,struct.error,IndexError) as err:
            resource_prefix_unparsed.append({'exportIndex':row['exportIndex'],'shaderIndex':n,'reason':str(err)});continue
        resource_validated+=1
        if s['stage']!='ps_5_0':continue
        for cb in range(len(tab['layoutHashes'])):
            binds=[x for x in tab['textureBindings'] if x['constantBuffer']==cb]
            if sorted(x['resourceIndex'] for x in binds)==list(range(0,2*len(row['textureParameters2D']),2)):
                candidates.append((n,s,cb,tab,binds))
    assert candidates
    target=6 if row['exportIndex']==5623 else 18 if row['exportIndex']==5675 else 0
    n,s,cb,tab,binds=next((x for x in candidates if x[0]==target),candidates[0])
    for x in binds:
        p=row['textureParameters2D'][x['resourceIndex']//2];x.update(parameter=p['parameter'],defaultTexture=p['defaultTextureObject'],textureParameterIndex=p['index'])
        if p['parameter'] in ['Ground','GroundNormal']:
            suffix='alb' if p['parameter']=='Ground' else 'n';x['effectiveTexture']='/Game/GTFreeMaterials/Textures/Ground_MuddyGrass/Ground_MuddyGrass_2k_'+suffix
        else:x['effectiveTexture']=p['defaultTextureObject'].split('.')[0]
    vectors=[eval_preshader(row,h) for h in row['uniformVectorPreshaders']]
    scalars=[eval_preshader(row,h) for h in row['uniformScalarPreshaders']]
    binding_records.append({'exportIndex':row['exportIndex'],'shaderIndex':n,'shaderSHA256':s['sha256'],'assemblyFile':s['assemblyFile'],'materialConstantBuffer':cb,'textureBindings':binds,'samplerBindings':[x for x in tab['samplerBindings'] if x['constantBuffer']==cb],'vectorRegisters':vectors,'scalarRegisters':[dict(x,register=len(vectors)+i//4,component='xyzw'[i%4]) for i,x in enumerate(scalars)],'prefixFullyConsumed':True})
three=next(x for x in binding_records if x['exportIndex']==5623)
assert three['materialConstantBuffer']==3
assert three['vectorRegisters'][1]['expression']=='LayerMask_Grass'
assert three['vectorRegisters'][2]['expression']=='LayerMask_Ground'
assert three['vectorRegisters'][3]['expression']=='LayerMask_Sand'
assert three['vectorRegisters'][6]['expression']=='GrassColor.rgb'
assert three['vectorRegisters'][8]['expression']=='SandColor.rgb'
assert three['scalarRegisters'][0]['register']==9 and three['scalarRegisters'][0]['expression']=='Texture Scale'

layers={}
for name,alb,norm,tint in [
    ('Grass','/Game/Downtown/Textures/Grass_A','/Game/Downtown/Textures/Grass_N',three['vectorRegisters'][6]['defaultOrInstanceValue'][:3]),
    ('Ground','/Game/GTFreeMaterials/Textures/Ground_MuddyGrass/Ground_MuddyGrass_2k_alb','/Game/GTFreeMaterials/Textures/Ground_MuddyGrass/Ground_MuddyGrass_2k_n',[1.,1.,1.]),
    ('Sand','/Game/Assets/Texture/T_SandDunes_D','/Game/Assets/Texture/T_SandDunes_N',three['vectorRegisters'][8]['defaultOrInstanceValue'][:3])]:
    def texture(pkg):
        x=m['textures'][pkg];f=ROOT/'public'/x['url'].lstrip('/');assert sha(f)==x['sha256']
        return {k:x[k] for k in ['url','sourcePackage','colorSpace','width','height','sha256']}|{'wrap':'repeat','rowOrientation':'original PNG rows; do not invert Y'}
    a,b=texture(alb),texture(norm);b.update(encoding='RG tangent normal, Z reconstructed positive',flipGreen=False)
    layers[name]={'albedo':a,'normal':b,'tintLinear':tint}

ids={i-1 for h in t['heightfields'] for i in h['sourceMaterialInstances']}|{5611,5623,5672,5675}|{int(h['id'].split('-')[-1])-1 for h in t['heightfields']}
ex={i:e for i,e in enumerate(array_items(ROOT/'research/exports/city-decoded/MainLevel.json','Exports')) if i in ids}
tex={x['packageIndex']:x for x in t['textures']};objects=[];checks=[]
for h in t['heightfields']:
    componentExport=int(h['id'].split('-')[-1])-1
    componentProperties=props(ex[componentExport])
    assert componentProperties['WeightmapSubsectionOffset']==0.5
    assert len(h['sourceMaterialInstances'])==1
    eix=h['sourceMaterialInstances'][0]-1;pr=props(ex[eix]);staticIndex=pr['Parent']-1;assert staticIndex in [5611,5623,5672,5675]
    assert props(ex[staticIndex])['Parent']==-270
    masks={v['ParameterInfo']['Name']:v['ParameterValue'] for v in pr['VectorParameterValues']}
    textures={v['ParameterInfo']['Name']:v['ParameterValue'] for v in pr['TextureParameterValues']}
    wt={x['weightmapTexturePackageIndex'] for x in h['weightmapLayers']};assert len(wt)==1
    wix=next(iter(wt));assert textures['Weightmap0']==wix
    channels={}
    for la in h['weightmapLayers']:
        name=la['layerInfoName'].removesuffix('_LayerInfo');c=la['rgbaChannel'];v=masks['LayerMask_'+name]
        assert [float(v[x]) for x in ['R','G','B','A']]==[int(i==c) for i in range(4)],(h['id'],name,c,v)
        channels[name]=c
    height=tex[h['sourceHeightmapTexturePackageIndex']];w=tex[wix];assert textures['Heightmap']==height['packageIndex']
    scale=overrides['Texture Scale'];o={'id':h['id'],'sectionBaseUE':h['sectionBaseUE'],'componentSizeQuads':126,'subsectionSizeQuads':63,'numSubsections':2,'meshPositionXZContainsSectionBase':False,'localGridScaleMeters':h['horizontalStepMeters'],'textureUVScale':[scale,scale],'textureUVOffset':[v*scale for v in h['sectionBaseUE']],
       'weightmap':{'url':w['pngUrl'],'sha256':w['pngSha256'],'channels':channels,'width':w['width'],'height':w['height'],'colorSpace':'linear','uvScale':[1/w['width'],1/w['height']],'uvBias':[.5/w['width'],.5/w['height']],'uvFormula':'(localGrid + min(floor(localGrid / 63), 1) + 0.5) / vec2(width,height)','wrap':'clamp','sourceWeightmapScaleBias':h['weightmapScaleBias']},
       'heightNormal':{'url':height['pngUrl'],'sha256':height['pngSha256'],'atlasWidth':height['width'],'atlasHeight':height['height'],'atlasOriginPixels':h['sourceAtlasPixelOrigin'],'channels':['B','A'],'colorSpace':'linear','uvFormula':'(atlasOriginPixels + localGrid + min(floor(localGrid / 63), 1) + 0.5) / atlasSize','wrap':'clamp'},
       'source':{'componentExport':componentExport,'weightmapSubsectionOffset':0.5,'materialInstanceExport':eix,'staticPermutationExport':staticIndex,'jsonFile':'research/exports/city-decoded/MainLevel.json','pointer':'/Exports/'+str(eix)+'/Data'}}
    objects.append(o);checks.append({'id':h['id'],'allocationAndLayerMaskMatch':True,'weightmapAndHeightmapReferenceMatch':True,'parentChainMatch':True})
manifest={'schemaVersion':1,'status':'original-material-computation-statically-recovered','provenance':'UAssetAPI + original cooked DXBC + frozen uniform and D3D11 resource tables; UE source layout corroboration. Not REA output.','runtimeVerified':False,'layers':layers,'objects':objects,
 'materialFactors':{'metallic':0,'roughness':1,'specular':overrides['Spec'],'specularModel':'UE default-lit specular scalar; not Babylon specularPower'},
 'formula':{'textureUV':'(localGrid + sectionBaseUE) * TextureScale; localGrid=GLB_POSITION.xz / localGridScaleMeters; POSITION excludes SectionBase','baseColorLinear':'clamp(sum(sRGBToLinear(albedo_layer(uv))*tintLinear_layer*weight_layer),0,1)','weightNormalization':'none added; use original channel values; do not divide by weight sum','tangentNormal':'n_l=vec3(2*RG_l-1,sqrt(max(1-dot(2*RG_l-1,2*RG_l-1),0))); n=normalize(sum(w_l*n_l))','heightNormalUE':'N=vec3(2*heightBA-1,sqrt(max(1-dot(2*heightBA-1,2*heightBA-1),0)))','tangentBasisUE':'T=normalize(vec3(N.z,0,-N.x)); B=cross(N,T); outUE=normalize(n.x*T+n.y*B+n.z*N)','normalWorld':'For the recovered unrotated MainLevel actor, worldNormal=outUE.xzy. Do not flip the normal PNG green channel when using this explicit UE basis.','selectionEmissive':'SelectionColor.rgb * SelectionColor.a; ordinary default SelectionColor is zero; runtime editor/override values not captured'},
 'previewBoundary':['Original deferred lighting, exposure, shadow/lightmap, view overrides, texture mip bias and original frame have not been recreated or runtime compared.','If only albedo or mesh-derived geometric normals are used, label that omission; the original height BA terrain-normal basis is provided separately.','Original shader applies global normal override cb0[138] and material roughness override cb0[139]; their live values are unknown. The material formula here uses identity normal override for preview.','Reuse original PNG bytes. GPU API orientation must preserve increasing row with increasing UE local Y.'],
 'evidence':{'contract':'research/world-recovery/landscape-material-contract.json','bindingCheck':'research/world-recovery/terrain-material-bindings.json'},'validation':{'objects':len(objects),'componentMaskReferencesVerified':len(checks),'shaderResourcePrefixesFullyParsed':resource_validated,'materialTexturePNGHashChecks':6}}
write(ROOT/'public/assets/world/terrain-material-manifest.json',manifest)
write(E/'terrain-material-bindings.json',{'sourceLayout':'terrain-UE-ShaderCore-4.26.h + terrain-UE-D3D11ShaderResources-4.26.h + terrain-UE-RHIDefinitions-4.26.h','resourcePrefixesFullyParsed':resource_validated,'unparsedCandidatePrefixes':resource_prefix_unparsed,'permutations':binding_records,'componentChecks':checks})
print(json.dumps(manifest['validation']))
