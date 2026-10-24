"""Read UE4.27 native LOD0 color buffers and exact component LOD color overrides."""
import base64,collections,importlib.util,pathlib,struct
ROOT=pathlib.Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('geometry',ROOT/'tools/asset-pipeline/export-world.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
oldread=g.READ;oldhash=g.HASH;g.READ=lambda p:oldread(pathlib.Path(p));g.HASH=lambda p:oldhash(pathlib.Path(p))
class Reader:
    def __init__(self,b,offset=0):self.b=b;self.p=offset
    def read(self,f):
        v=struct.unpack_from('<'+f,self.b,self.p);self.p+=struct.calcsize('<'+f);return v[0] if len(v)==1 else list(v)
    def bulk(self):
        size,n=self.read('ii');assert 0<=n<10000000 and 0<size<=64,(self.p,size,n)
        start=self.p;self.p+=size*n;assert self.p<=len(self.b);return {'offset':start,'elementSize':size,'count':n,'byteLength':size*n}
def colors(r):
    start=r.p;flags=r.read('BB');stride,n=r.read('ii');assert stride in (0,4) and 0<=n<10000000,(start,flags,stride,n)
    data=r.bulk() if n and not flags[0]&2 else None
    if data:assert data['count']==n and data['elementSize']==4
    values=[tuple(r.b[i:i+4]) for i in range(data['offset'],data['offset']+data['byteLength'],4)] if data else []
    return {'offset':start,'endOffset':r.p,'stripFlags':flags,'stride':stride,'numVertices':n,'bulk':data,'nonWhiteVertexCount':sum(x!=(255,255,255,255) for x in values),'channelMinBGRA':[min(x[i] for x in values) for i in range(4)] if values else None,'channelMaxBGRA':[max(x[i] for x in values) for i in range(4)] if values else None}
def mesh_color(asset):
    ev=asset['materialSlotEvidence'];d=g.READ(ev['decoded']);ex=next(e for e in d['Exports'] if e['ObjectName']==asset['sourcePackage'].rsplit('/',1)[1]);b=base64.b64decode(ex['Extras']['$value']);r=Reader(b,ev['nativeLod0SectionArrayEndOffset']);deviation=r.read('f');cooked,inline=r.read('ii');assert cooked==0 and inline==1
    flags=r.read('BB');stride,n=r.read('ii');pos=r.bulk();assert stride==12 and pos['count']==n and pos['elementSize']==12
    vflags=r.read('BB');uvs,vn,full,high=r.read('iiii');assert vn==n and full in (0,1) and high in (0,1)
    tangent=r.bulk();uv=r.bulk();assert tangent['count']==n and tangent['elementSize']==(16 if high else 8);assert uv['count']==n*uvs and uv['elementSize']==(8 if full else 4)
    col=colors(r);assert col['numVertices'] in (0,n)
    gltf=g.READ(ROOT/'public'/asset['url'].lstrip('/'));attrs=[p['attributes'].get('COLOR_0') for m in gltf['meshes'] for p in m['primitives']]
    return {'id':asset['id'],'package':asset['sourcePackage'],'decoded':ev['decoded'],'sha256':g.HASH(ev['decoded']),'nativeExtrasBytes':len(b),'nativeExtrasSha256':__import__('hashlib').sha256(b).hexdigest(),'positionVertexCount':n,'positionBulk':pos,'tangentBulk':tangent,'uvBulk':uv,'color':col,'gltfColorAccessors':attrs}
def component_colors(ex):
    b=base64.b64decode(ex.get('Extras',{}).get('$value',''));r=Reader(b)
    if not b:return {'nativeExtrasBytes':0,'lods':[],'status':'no-native-serialized-LODData'}
    assert r.read('i')==0
    if len(b)==4:return {'nativeExtrasBytes':4,'lods':[],'status':'no-native-serialized-LODData'}
    n=r.read('i');assert 0<=n<=16,(len(b),n)
    lods=[]
    for i in range(n):
        flags=r.read('BB');assert flags[0]&1,'editor data unexpected'
        if not flags[0]&2:r.p+=16
        has=0 if flags[1]&1 else r.read('B');assert has in (0,1)
        lods.append({'lod':i,'stripFlags':flags,'loadVertexColorData':has,'colors':colors(r) if has else None})
    return {'nativeExtrasBytes':len(b),'nativeExtrasSha256':__import__('hashlib').sha256(b).hexdigest(),'lodDataEndOffset':r.p,'remainingSubclassBytes':len(b)-r.p,'lods':lods,'status':'parsed'}
def run():
    assets=g.READ(g.EVID/'geometry-base-assets.json');mats=g.READ(g.OUT/'material-manifest.json')['materials'];target='/Game/UrbanCity/Materials/Foliage/Foliage_Mat'
    is_foliage=lambda pkg:pkg==target or mats.get(pkg,{}).get('baseMaterial')==target
    selected={x['id']:x for x in assets if any(s['material'] and is_foliage(s['material']['package']) for s in x['sourceMaterialSlots'])}
    world=g.READ(g.OUT/'geometry-manifest.json');components={}
    for level in world['levels']:
        for o in level['objects']:
            override=any(x.get('material') and is_foliage(x['material']['package']) for x in o['materialOverrides'])
            if o['assetId'] in selected or override:components[(o['source']['package'],o['source']['exportIndex'])]=o;selected.setdefault(o['assetId'],next(x for x in assets if x['id']==o['assetId']))
    records=[];fail=[]
    for x in selected.values():
        try:records.append(mesh_color(x))
        except Exception as e:fail.append({'assetId':x['id'],'error':repr(e)})
    paths=g.READ(g.EVID/'geometry-template-resolution.json')['decodedPackagePaths'];cache={};comps=[]
    for (pkg,idx),o in components.items():
        try:
            if pkg not in cache:cache[pkg]=g.READ(paths[pkg])
            comps.append({'source':o['source'],'assetId':o['assetId'],'componentClass':o['componentClass'],**component_colors(cache[pkg]['Exports'][idx-1])})
        except Exception as e:fail.append({'source':o['source'],'error':repr(e)})
    templates={}
    for o in components.values():
        for item in o.get('templateRecovery',{}).get('chain',[])[1:]:
            key=(item['package'],item['exportIndex'])
            if key in templates:continue
            try:
                pkg,idx=key
                if pkg not in cache:cache[pkg]=g.READ(paths[pkg])
                templates[key]={'source':item,**component_colors(cache[pkg]['Exports'][idx-1])}
            except Exception as e:fail.append({'template':item,'error':repr(e)})
    result={'scope':'LOD0 of exact mesh/material references whose effective base is Foliage_Mat; all 41 map packages, original native per-component LOD color override payloads. Not an audit of every shader or runtime paint.','targetBaseMaterial':target,'meshes':records,'components':comps,'componentTemplates':list(templates.values()),'failures':fail,'summary':{'meshes':len(records),'components':len(comps),'componentTemplates':len(templates),'nativeMeshColorVertices':sum(x['color']['numVertices'] for x in records),'nativeMeshNonWhiteVertices':sum(x['color']['nonWhiteVertexCount'] for x in records),'componentOverrideColorBuffers':sum(bool(l['colors']) for x in comps for l in x['lods']),'templateOverrideColorBuffers':sum(bool(l['colors']) for x in templates.values() for l in x['lods']),'failures':len(fail)}}
    g.WRITE(g.EVID/'geometry-vertex-color-audit.json',result);print(result['summary']);print(fail[:4])
if __name__=='__main__':run()
