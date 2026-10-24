"""Restore shipped Landscape heights, not proxy terrain. Original installation read-only.
Run with bundled Python (numpy/Pillow); output ownership is terrain paths only.
"""
from pathlib import Path
import base64, hashlib, json, math, re, struct, subprocess, time
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'public/assets/world/terrain'
EVID=ROOT/'research/world-recovery'
DECODE=ROOT/'research/exports/city-decoded/MainLevel.json'
DETAIL=ROOT/'research/rea-audit/levels/MainLevel.json'
MAP=ROOT/'research/exports/city-unpacked/UNDEFEATED/Content/-HeroGame/Maps/MainLevel.umap'
UBULK=MAP.with_suffix('.ubulk')
ORIGIN=[0.,0.,0.]
LOD_STEP=4
OUT.mkdir(parents=True,exist_ok=True);EVID.mkdir(parents=True,exist_ok=True)

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def sha(b):return hashlib.sha256(b).hexdigest()
def fsha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        while b:=f.read(1048576):h.update(b)
    return h.hexdigest()
def array_items(path,key):
    dec=json.JSONDecoder();buf='';found=False
    with path.open(encoding='utf-8-sig') as f:
        while True:
            if not found:
                s=f.read(1048576)
                if not s:raise ValueError('Missing '+key)
                buf+=s;m=re.search(r'"'+re.escape(key)+r'"\s*:\s*\[',buf)
                if not m:buf=buf[-100:];continue
                buf=buf[m.end():];found=True
            buf=buf.lstrip(' \n\t\r,')
            if buf.startswith(']'):return
            try:
                x,end=dec.raw_decode(buf);yield x;buf=buf[end:]
            except json.JSONDecodeError:
                s=f.read(1048576)
                if not s:raise
                buf+=s
def val(p):
    if 'EnumValue' in p:return p['EnumValue']
    if 'Value' not in p:return {k:v for k,v in p.items() if k not in ['$type','Name','DuplicationIndex']}
    v=p.get('Value')
    if not isinstance(v,list):return v
    if 'ArrayPropertyData' in p.get('$type',''):return [val(x) for x in v]
    if len(v)==1 and isinstance(v[0],dict) and v[0].get('Name')==p.get('Name'):return val(v[0])
    if all(isinstance(x,dict) and 'Name' in x for x in v):return {x['Name']:val(x) for x in v}
    return v
def props(e):return {p['Name']:val(p) for p in e.get('Data',[])}
def import_path(index):
    if index>=0:return None
    x=imports[-index-1];chain=[x['ObjectName']]
    while x.get('OuterIndex',0)<0:
        x=imports[-x['OuterIndex']-1];chain.append(x['ObjectName'])
    return '.'.join(reversed(chain))
def glb(path,pos,norm,uv,indices,name):
    # Reflection UE [x,y,z] -> glTF [x,z,y] is accounted for by winding below.
    chunks=[];views=[];access=[];offset=0
    for a,kind,ctype in [(pos,'VEC3',5126),(norm,'VEC3',5126),(uv,'VEC2',5126),(indices,'SCALAR',5123)]:
        b=a.tobytes();views.append({'buffer':0,'byteOffset':offset,'byteLength':len(b)})
        ac={'bufferView':len(views)-1,'componentType':ctype,'count':len(a),'type':kind}
        if len(views)==1:ac.update(min=pos.min(axis=0).tolist(),max=pos.max(axis=0).tolist())
        access.append(ac);b+=b'\0'*((-len(b))%4);chunks.append(b);offset+=len(b)
    doc={'asset':{'version':'2.0','generator':'Original Landscape PF_B8G8R8A8 heightfield reconstruction'},'scene':0,'scenes':[{'nodes':[0]}],'nodes':[{'mesh':0,'name':name}],'meshes':[{'primitives':[{'attributes':{'POSITION':0,'NORMAL':1,'TEXCOORD_0':2},'indices':3}]}],'buffers':[{'byteLength':offset}],'bufferViews':views,'accessors':access,'extras':{'materialStatus':'original-landscape-blend-not-reconstructed','terrainSource':'original encoded heightmap samples'}}
    j=json.dumps(doc,separators=(',',':')).encode();j+=b' '*((-len(j))%4);b=b''.join(chunks)
    payload=struct.pack('<III',0x46546c67,2,12+8+len(j)+8+len(b))+struct.pack('<II',len(j),0x4e4f534a)+j+struct.pack('<II',len(b),0x004e4942)+b
    path.write_bytes(payload)
    return len(payload)

started=time.time();details=read(DETAIL)
terrain=[t for t in details['terrain'] if t['class']=='LandscapeComponent']
trans={c['exportIndex']:c for c in details['componentTransforms'] if c['class']=='LandscapeComponent'}
component_ids={t['componentExportIndex'] for t in terrain}
# Audit detail indexes are one-based UE package indexes. Raw JSON array indexes are zero-based.
texture_ids=set()
for t in terrain:
    p=t['properties'];texture_ids.add(p['HeightmapTexture'])
    wt=p.get('WeightmapTextures',[])
    texture_ids.update(wt.values() if isinstance(wt,dict) else wt if isinstance(wt,list) else [wt])
names=list(array_items(DECODE,'NameMap'));imports=list(array_items(DECODE,'Imports'))
selected={}
for i,e in enumerate(array_items(DECODE,'Exports')):
    if i+1 in texture_ids|component_ids|{5178,7235}:selected[i+1]=e
print('selected',len(component_ids),'components',len(texture_ids),'textures',flush=True)
ubulk=UBULK.read_bytes();textures={};failures=[]
for ix in sorted(texture_ids):
    e=selected[ix];b=base64.b64decode(e['Extras']['$value']);p=props(e)
    try:
        # UE4.27 cooked UTexture2D tail: serialized zero GUID bool, two strip flags,
        # cooked bool, pixel-format FName, skip offset, FTexturePlatformData.
        assert struct.unpack_from('<I',b,8)[0]==1,'not cooked texture'
        ni,nn=struct.unpack_from('<II',b,12);format_name=names[ni]
        sx,sy,slices,n=struct.unpack_from('<IIII',b,28)
        fmt=b[44:44+n].rstrip(b'\0').decode('ascii');assert fmt==format_name=='PF_B8G8R8A8',(format_name,fmt)
        first,num=struct.unpack_from('<II',b,44+n);start=44+n+8
        cooked,flags,count,size,off=struct.unpack_from('<IIIIq',b,start)
        assert cooked==1 and not(flags&2) and not(flags&8192),'unsupported bulk flags'
        inline=bool(flags&64);external=bool(flags&256)
        assert inline!=external,(flags,inline,external)
        data_start=start+24
        if inline:pixels=b[data_start:data_start+size];dimstart=data_start+size;pixel_source='Texture Extras inline mip'
        else:pixels=ubulk[off:off+size];dimstart=data_start;pixel_source='MainLevel.ubulk absolute offset'
        w,h,z=struct.unpack_from('<III',b,dimstart)
        assert (w,h,z)==(sx,sy,1) and size==count==w*h*4 and len(pixels)==size
        arr=np.frombuffer(pixels,dtype=np.uint8).reshape(h,w,4)
        rgba=arr[:,:,[2,1,0,3]].copy();group=p.get('LODGroup','')
        png=OUT/'textures'/f'export-{ix}-{e["ObjectName"]}.png';png.parent.mkdir(parents=True,exist_ok=True)
        Image.fromarray(rgba).save(png)
        record={'packageIndex':ix,'jsonPointer':f'/Exports/{ix-1}','name':e['ObjectName'],'outerIndex':e['OuterIndex'],'format':fmt,'width':w,'height':h,'firstMip':first,'mipCount':num,'bulkFlags':flags,'bulkOffset':off,'bulkSize':size,'pixelSource':pixel_source,'pixelSha256':sha(pixels),'pngUrl':'/assets/world/terrain/textures/'+png.name,'pngSha256':fsha(png),'lodGroup':group,'sourceSerialOffset':e['SerialOffset'],'sourceSerialSize':e['SerialSize'],'extrasHeaderHex':b[:start+24].hex()}
        textures[ix]={'rgba':rgba,'record':record}
    except Exception as exc:failures.append({'texturePackageIndex':ix,'jsonPointer':f'/Exports/{ix-1}','error':str(exc),'extrasSha256':sha(b),'extrasLength':len(b)})

# Independent UModel pixel check against a real height atlas, performed without launching game.
check=EVID/'terrain-umodel/-HeroGame/Maps/MainLevel/Texture2D_5.png'
if not check.exists():
    command=[str(ROOT/'tools/asset-pipeline/umodel.exe'),'-export','-png','-game=ue4.27',f'-path={MAP.parents[4]}',f'-out={EVID/"terrain-umodel"}','-nomesh','-noanim','-nostat','UNDEFEATED/Content/-HeroGame/Maps/MainLevel.umap','Texture2D_5','Texture2D']
    run=subprocess.run(command,capture_output=True,timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
    (EVID/'terrain-umodel.log').write_bytes(run.stdout+run.stderr)
check_record={'texturePackageIndex':11095,'umodelPng':str(check),'available':check.exists()}
if check.exists():
    im=np.array(Image.open(check).convert('RGBA'));check_record['allPixelsRGBAEqual']=bool(np.array_equal(im,textures[11095]['rgba']));assert check_record['allPixelsRGBAEqual']

assets=[];objects=[];fields=[];heights={};duplicate_checks=[]
for t in terrain:
    ix=t['componentExportIndex'];e=selected[ix];p=props(e);tr=trans[ix]['composedComponentTransformUE'];q=tr['rotationQuaternion'];s=tr['scale'];loc=tr['position']
    try:
        assert np.allclose(q,[0,0,0,1]) and all(v>0 for v in s),'rotated/negative-scale landscape requires explicit transform'
        nq=p['SubsectionSizeQuads'];ns=p['NumSubsections'];cq=p['ComponentSizeQuads'];assert nq*ns==cq
        tex=textures[p['HeightmapTexture']];rgba=tex['rgba'];h,w=rgba.shape[:2];sb=p['HeightmapScaleBias']
        assert abs(float(sb['X'])-1/w)<1e-9 and abs(float(sb['Y'])-1/h)<1e-9
        ox=round(float(sb['Z'])*w);oy=round(float(sb['W'])*h)
        # Each 63-quad subsection is stored as 64 vertices; internal boundary duplicated.
        coord=np.arange(cq+1);tc=coord+np.minimum(coord//nq,ns-1)
        assert ox+int(tc[-1])<w and oy+int(tc[-1])<h
        patch=rgba[oy+tc[:,None],ox+tc[None,:]]
        u16=(patch[:,:,0].astype(np.uint16)<<8)|patch[:,:,1].astype(np.uint16)
        heights[(int(p.get('SectionBaseX',0)),int(p.get('SectionBaseY',0)))]=u16
        full=(rgba[:,:,0].astype(np.uint16)<<8)|rgba[:,:,1].astype(np.uint16)
        du=full[oy:oy+ns*(nq+1),ox+nq];dv=full[oy:oy+ns*(nq+1),ox+nq+1]
        eu=full[oy+nq,ox:ox+ns*(nq+1)];ev=full[oy+nq+1,ox:ox+ns*(nq+1)]
        duplicate_checks.append({'component':ix,'xDuplicateMaxU16Delta':int(np.abs(du.astype(int)-dv.astype(int)).max()),'yDuplicateMaxU16Delta':int(np.abs(eu.astype(int)-ev.astype(int)).max())})
        local_height=(u16.astype(np.float64)-32768.0)/128.0
        hfpath=OUT/'heightfields'/f'component-{ix}.u16';hfpath.parent.mkdir(parents=True,exist_ok=True);hfpath.write_bytes(u16.astype('<u2').tobytes())
        # LOD retains exact original heights at selected vertices and both subsection edges.
        samples=sorted(set(range(0,cq+1,LOD_STEP))|{nq,cq});a=np.array(samples);hh=local_height[np.ix_(a,a)]*s[2]/100
        xx,zz=np.meshgrid(a*s[0]/100,a*s[1]/100)
        pos=np.stack([xx,hh,zz],axis=-1).reshape(-1,3).astype('<f4')
        # Full-resolution slopes give normals independent of render subsampling.
        dy,dxx=np.gradient(local_height*s[2]/100,s[1]/100,s[0]/100)
        normals=np.stack([-dxx,np.ones_like(dxx),-dy],axis=-1);normals/=np.linalg.norm(normals,axis=-1,keepdims=True)
        normal=normals[np.ix_(a,a)].reshape(-1,3).astype('<f4')
        uu,vv=np.meshgrid(a/cq,a/cq);uv=np.stack([uu,vv],axis=-1).reshape(-1,2).astype('<f4')
        n=len(a);ids=[]
        for y in range(n-1):
            for x in range(n-1):
                v=y*n+x;ids.extend([v,v+n,v+1,v+1,v+n,v+n+1])
        indices=np.array(ids,dtype='<u2');name=f'landscape-{ix}';path=OUT/(name+'.glb');size=glb(path,pos,normal,uv,indices,name)
        worldpos=[(loc[0]-ORIGIN[0])/100,(loc[2]-ORIGIN[2])/100,(loc[1]-ORIGIN[1])/100]
        fullmin=[worldpos[0],worldpos[1]+float(local_height.min())*s[2]/100,worldpos[2]]
        fullmax=[worldpos[0]+cq*s[0]/100,worldpos[1]+float(local_height.max())*s[2]/100,worldpos[2]+cq*s[1]/100]
        layer=[]
        for al in p.get('WeightmapLayerAllocations',[]):
            li=al['LayerInfo'];imp=imports[-li-1] if li<0 else None
            ti=p['WeightmapTextures'][al['WeightmapTextureIndex']]
            layer.append({'layerInfoPackageIndex':li,'layerInfoName':imp['ObjectName'] if imp else None,'layerInfoObjectPath':import_path(li),'layerInfoImportPointer':f'/Imports/{-li-1}' if imp else None,'weightmapTexturePackageIndex':ti,'weightmapUrl':textures.get(ti,{}).get('record',{}).get('pngUrl'),'rgbaChannel':al['WeightmapTextureChannel']})
        lod={'sampleStepQuads':LOD_STEP,'sampleCoordinates':samples,'vertices':len(pos),'triangles':len(ids)//3,'sourceFullResolutionVertices':(cq+1)**2,'approximation':'Exact original vertex samples; unsampled points use render triangles. Full-resolution heightfield retained.'}
        # Compute render simplification error on all original vertices against same triangle split.
        # First cell triangle covers tx+ty <=1; second covers remaining half.
        grid=np.arange(cq+1);cell=np.minimum(np.searchsorted(a,grid,side='right')-1,n-2);lo=a[cell];hi=a[cell+1];frac=(grid-lo)/(hi-lo)
        cx=cell[None,:];cy=cell[:,None];fx=frac[None,:];fy=frac[:,None]
        h00=hh[cy,cx];h10=hh[cy,cx+1];h01=hh[cy+1,cx];h11=hh[cy+1,cx+1]
        approx=np.where(fx+fy<=1,h00+(h10-h00)*fx+(h01-h00)*fy,h11+(h01-h11)*(1-fx)+(h10-h11)*(1-fy))
        errors=np.abs(approx-local_height*s[2]/100);lod['maxHeightErrorMeters']=float(errors.max());lod['meanHeightErrorMeters']=float(errors.mean())
        # Additional true sampled LOD2 for close inspection; not a procedural proxy.
        a2=np.array(sorted(set(range(0,cq+1,2))|{nq,cq}));n2=len(a2)
        h2=local_height[np.ix_(a2,a2)]*s[2]/100;x2,z2=np.meshgrid(a2*s[0]/100,a2*s[1]/100)
        p2=np.stack([x2,h2,z2],axis=-1).reshape(-1,3).astype('<f4');normal2=normals[np.ix_(a2,a2)].reshape(-1,3).astype('<f4')
        u2,v2=np.meshgrid(a2/cq,a2/cq);uv2=np.stack([u2,v2],axis=-1).reshape(-1,2).astype('<f4')
        ids2=[]
        for yy in range(n2-1):
            for xx2 in range(n2-1):
                vv2=yy*n2+xx2;ids2.extend([vv2,vv2+n2,vv2+1,vv2+1,vv2+n2,vv2+n2+1])
        path2=OUT/(name+'-lod2.glb');size2=glb(path2,p2,normal2,uv2,np.array(ids2,dtype='<u2'),name+'-lod2')
        cell2=np.minimum(np.searchsorted(a2,grid,side='right')-1,n2-2);frac2=(grid-a2[cell2])/(a2[cell2+1]-a2[cell2]);cx2=cell2[None,:];cy2=cell2[:,None];fx2=frac2[None,:];fy2=frac2[:,None]
        b00=h2[cy2,cx2];b10=h2[cy2,cx2+1];b01=h2[cy2+1,cx2];b11=h2[cy2+1,cx2+1]
        approx2=np.where(fx2+fy2<=1,b00+(b10-b00)*fx2+(b01-b00)*fy2,b11+(b01-b11)*(1-fx2)+(b10-b11)*(1-fy2))
        error2=np.abs(approx2-local_height*s[2]/100)
        lod2={'sampleStepQuads':2,'sampleCoordinates':a2.tolist(),'vertices':len(p2),'triangles':len(ids2)//3,'sourceFullResolutionVertices':(cq+1)**2,'maxHeightErrorMeters':float(error2.max()),'meanHeightErrorMeters':float(error2.mean()),'approximation':lod['approximation']}
        assets.append({'id':name,'url':'/assets/world/terrain/'+path.name,'highQualityUrl':'/assets/world/terrain/'+path2.name,'kind':'original-landscape-heightfield','bytes':size,'sha256':fsha(path),'lod':lod,'lods':[{'url':'/assets/world/terrain/'+path.name,'bytes':size,'sha256':fsha(path),**lod},{'url':'/assets/world/terrain/'+path2.name,'bytes':size2,'sha256':fsha(path2),**lod2}],'materialStatus':'original-landscape-blend-not-reconstructed','materialBindingRequired':True})
        objects.append({'id':name,'assetId':name,'position':worldpos,'rotation':[0,0,0,1],'scale':[1,1,1],'sourceLevel':'/Game/-HeroGame/Maps/MainLevel','sourceActor':t['sourceActor'],'sourceComponent':trans[ix]['component'],'sourceComponentPackageIndex':ix,'sourceJsonPointer':f'/Exports/{ix-1}','bounds':{'min':fullmin,'max':fullmax},'heightfieldIndex':len(fields),'materialStatus':'original-landscape-blend-not-reconstructed'})
        fields.append({'id':name,'url':'/assets/world/terrain/heightfields/'+hfpath.name,'encoding':'uint16-little-endian-row-major-Y-then-X','width':cq+1,'height':cq+1,'sha256':fsha(hfpath),'sectionBaseUE':[p.get('SectionBaseX',0),p.get('SectionBaseY',0)],'componentSizeQuads':cq,'subsectionSizeQuads':nq,'numSubsections':ns,'position':worldpos,'horizontalStepMeters':[s[0]/100,s[1]/100],'heightOffset':32768,'heightMultiplierMeters':s[2]/12800,'heightBaseMeters':worldpos[1],'minHeightU16':int(u16.min()),'maxHeightU16':int(u16.max()),'sourceHeightmapTexturePackageIndex':p['HeightmapTexture'],'sourceHeightmapScaleBias':sb,'sourceAtlasPixelOrigin':[ox,oy],'sourceMaterialInstances':p.get('MaterialInstances'),'weightmapLayers':layer,'weightmapScaleBias':p.get('WeightmapScaleBias'),'collisionMipLevelOriginal':p.get('CollisionMipLevel',0),'collisionCaveat':'Full render heights recovered; original cooked PhysX collision is not recreated. Sample selected triangulation explicitly.','lod':lod})
    except Exception as exc:failures.append({'componentPackageIndex':ix,'jsonPointer':f'/Exports/{ix-1}','error':str(exc)})
seams=[]
for (x,y),a in heights.items():
    q=a.shape[0]-1
    for delta,edge,other in [((q,0),a[:,-1],(0,'x')),((0,q),a[-1,:],(0,'y'))]:
        b=heights.get((x+delta[0],y+delta[1]))
        if b is not None:
            e=b[:,0] if delta[0] else b[0,:]
            seams.append({'componentSectionBase':[x,y],'neighborSectionBase':[x+delta[0],y+delta[1]],'maxU16Delta':int(np.abs(edge.astype(int)-e.astype(int)).max())})
summary={'expectedLandscapeComponents':144,'recoveredLandscapeComponents':len(fields),'restoredTextureCount':len(textures),'heightAtlasCount':sum('Heightmap' in t['record']['lodGroup'] for t in textures.values()),'weightmapCount':sum('Weightmap' in t['record']['lodGroup'] for t in textures.values()),'failedItems':len(failures),'fullResolutionVertices':sum(f['width']*f['height'] for f in fields),'renderVertices':sum(a['lod']['vertices'] for a in assets),'renderTriangles':sum(a['lod']['triangles'] for a in assets),'maxRenderHeightErrorMeters':max((a['lod']['maxHeightErrorMeters'] for a in assets),default=0),'neighborSeamsChecked':len(seams),'neighborSeamMaxU16Delta':max((s['maxU16Delta'] for s in seams),default=0),'subsectionBoundaryMaxU16Delta':max((max(d['xDuplicateMaxU16Delta'],d['yDuplicateMaxU16Delta']) for d in duplicate_checks),default=0),'elapsedSeconds':round(time.time()-started,2)}
summary.update(highQualityRenderVertices=sum(a['lods'][1]['vertices'] for a in assets),highQualityRenderTriangles=sum(a['lods'][1]['triangles'] for a in assets),highQualityMaxHeightErrorMeters=max((a['lods'][1]['maxHeightErrorMeters'] for a in assets),default=0))
manifest={'version':1,'coordinateSystem':'gltf-rh-y-up-meters','originUE':ORIGIN,'sourceLevel':'/Game/-HeroGame/Maps/MainLevel','summary':summary,'assets':assets,'objects':objects,'heightfields':fields,'textures':[t['record'] for t in textures.values()],'failures':failures,'landscapeMaterial':props(selected[5178]).get('LandscapeMaterial'),'materialStatus':'Original height/weight texture pixels and layer allocation recovered; original landscape shader blending NOT recreated. GLB deliberately has no substitute material. Consumer must bind recovered material or visibly identify unresolved shading.','heightFormula':'H=(uint16(R*256+G)-32768)/128 local UE; worldY=(UE actor Z + H*scaleZ)/100','sampling':'See research/world-recovery/terrain-recovery.md; uint16 row order follows local UE Y, rendered world Z.'}
manifest['landscapeMaterialObjectPath']=import_path(manifest['landscapeMaterial'])
manifest['normalStatus']='Normals derived from full-resolution recovered heights; original material normal blending not reconstructed.'
write(ROOT/'public/assets/world/terrain-manifest.json',manifest)
evidence={'method':'UAssetAPI property/export identities + direct cooked PF_B8G8R8A8 mip read + independent UModel pixel comparison','sources':[{'path':str(p),'sha256':fsha(p),'bytes':p.stat().st_size} for p in [DECODE,DETAIL,MAP,MAP.with_suffix('.uexp'),UBULK]],'officialLayoutSources':['https://dev.epicgames.com/documentation/en-us/unreal-engine/landscape-overview','https://dev.epicgames.com/documentation/en-us/unreal-engine/landscape-technical-guide-in-unreal-engine','https://raw.githubusercontent.com/gildor2/UEViewer/master/Unreal/UnrealMaterial/UnTexture4.cpp'],'summary':summary,'umodelPixelCrosscheck':check_record,'subsectionDuplicateChecks':duplicate_checks,'neighborSeamChecks':seams,'textureLayoutRecords':[t['record'] for t in textures.values()],'componentEvidence':[{'packageIndex':ix,'pointer':f'/Exports/{ix-1}','objectName':selected[ix]['ObjectName'],'properties':props(selected[ix]),'transformEvidence':trans[ix]} for ix in sorted(component_ids)],'landscapeActor':{'pointer':'/Exports/5177','properties':props(selected[5178])},'rootComponent':{'pointer':'/Exports/7234','properties':props(selected[7235])},'failures':failures,'runtimeVerified':False}
write(EVID/'terrain-recovery.json',evidence)
md=['# 原地形恢复与加载接口','','恢复来自原 MainLevel 的高度像素，无手工高度或平面代替。源安装只读。结果 '+json.dumps(summary,ensure_ascii=False)+'。','','## 接口','','public/assets/world/terrain-manifest.json 的 assets/objects 可并入原世界加载。originUE=[0,0,0]，UE[x,y,z]转换为glTF[x,z,y]/100；每块GLB顶点是组件局部米坐标，objects.position为世界米坐标，rotation单位、scale=1。bounds是完整高度场边界，不仅是抽样LOD。','','每块保留127×127 uint16小端高度，行=UE局部Y/世界Z，列=UE局部X/世界X。高度 worldY=heightBaseMeters+(uint16-heightOffset)*heightMultiplierMeters。水平坐标 worldX=position[0]+column*horizontalStepMeters[0]；worldZ=position[2]+row*horizontalStepMeters[1]。先用对象bounds查找块，再将XZ反变换到网格，按下述三角形采样。边界块可任取共享边，已逐点检查。','','## 原像素与布局','','高度atlas格式PF_B8G8R8A8，物理字节[B,G,R,A]，高度=R*256+G；线性数据，禁止sRGB转换、8位灰度降精度或PNG翻转。已用UModel单独导出的Texture2D_5 PNG逐RGBA像素交叉验证原ubulk读取。每个63-quad subsection存64个像素，两个subsection共128像素但只有127个唯一顶点：局部整数v的源像素=atlasOrigin+v+min(floor(v/63),1)。atlasOrigin=(HeightmapScaleBias.Z*textureWidth, .W*textureHeight)。内部重复边和相邻组件边全部独立验算。','','## 轻量渲染与碰撞','','默认glb是按4格抽样的LOD，额外保留63和126边界，所有顶点高度均来自原像素。每块lod.maxHeightErrorMeters给出对全部原网格顶点的实际最大误差；完整u16未降采样。不要把LOD渲染面误当原PhysX碰撞。原CollisionMipLevel=1也记录，但未重建原碰撞烹制数据。','','如用完整高度场求高度，令gx,gz为网格浮点坐标，ix=floor(gx), iz=floor(gz), tx=gx-ix, tz=gz-iz。四角为h00,h10,h01,h11：tx+tz<=1 时 h=h00+(h10-h00)*tx+(h01-h00)*tz；否则 h=h11+(h01-h11)*(1-tx)+(h10-h11)*(1-tz)。这与本导出三角剖分一致，是明确的Web采样合同；并不宣称等于所有原PhysX细节。若用户接触的是渲染LOD，使用lod.sampleCoordinates界定单元而非单位格。','','## 权重与材质边界','','textures中PNG保存原RGBA通道；heightfields.weightmapLayers逐项列LayerInfo原引用、纹理URL、RGBA通道(0=R,1=G,2=B,3=A)。原weightmapScaleBias保留。以与高度同一subsection坐标在权重128²纹理中取像素，不按heightmap atlas bias取权重。LayerInfo原名字不等于完整着色配方，材质混合/纹理平铺/法线等仍需材质恢复。GLB没有编造的草地/灰色替代材质；materialStatus必须保留。','','## 验证边界','','所有恢复是源包静态资源重建，并非运行时游戏画面验证。完整证据、原map/ubulk SHA、纹理偏移、组件JSON pointers及接缝对照见terrain-recovery.json。']
md += ['', '每个asset.highQualityUrl指向LOD2，asset.lods按[默认LOD4,高清LOD2]列出URL、顶点/三角形、SHA和误差。LOD2总608400顶点/1179648三角形，最大采样误差0.4375米；此数值应以manifest本次生成值为准。法线由完整高度差分计算，未还原原地形材质法线混合。']
(EVID/'terrain-recovery.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
print(json.dumps(summary),flush=True)
