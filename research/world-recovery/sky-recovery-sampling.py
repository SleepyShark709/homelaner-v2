"""Sky mesh UV correspondence and original HDR layout evidence, no source changes."""
import pathlib,importlib.util,math,struct,re,json
ROOT=pathlib.Path(__file__).resolve().parents[2];OUT=ROOT/'research/world-recovery/sky-recovery'
spec=importlib.util.spec_from_file_location('g',ROOT/'tools/asset-pipeline/export-world.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
w=g.READ(g.OUT/'geometry-manifest.json');asset=next(x for x in w['assets'] if x['sourcePackage']=='/Game/Skies/Meshes/SM_SkyDome');path=ROOT/'public'/asset['url'].lstrip('/');d=g.READ(path);bs=[(path.parent/b['uri']).read_bytes() for b in d['buffers']];pr=d['meshes'][0]['primitives'][0];pos=g.m.accessor(d,bs,pr['attributes']['POSITION']);uv=g.m.accessor(d,bs,pr['attributes']['TEXCOORD_0']);norm=g.m.accessor(d,bs,pr['attributes']['NORMAL'])
samples=[]
for label,axis in [('UE+X',[1,0,0]),('UE-X',[-1,0,0]),('UE+Y',[0,0,1]),('UE-Y',[0,0,-1]),('UE+Z',[0,1,0])]:
    distances=[sum((x-y)**2 for x,y in zip(g.m.mul(p,1/g.m.norm(p)),axis)) if g.m.norm(p)>0 else math.inf for p in pos];best=min(distances)
    candidates=[i for i,x in enumerate(distances) if abs(x-best)<1e-8]
    for i in candidates[:4]:samples.append({'axis':label,'vertex':i,'positionRHmeters':pos[i],'uv0':uv[i],'shaderUV':[uv[i][0],uv[i][1]*2],'normalDotPosition':g.m.dot(norm[i],pos[i]),'directionError':best})
hdr=ROOT/'public/assets/world/textures/Game/Skies/Textures/T_SkyCloudy11.hdr';data=hdr.read_bytes();match=re.search(rb'-Y (\d+) \+X (\d+)\n',data[:100]);assert match;h,width=map(int,match.groups());offset=match.end();assert len(data)-offset==h*width*4
pixels=[]
for x,y in [(0,0),(width//2,0),(0,h//2),(width//2,h//2),(width//2,h-1),(width-1,h-1)]:
    vals=list(data[offset+(y*width+x)*4:offset+(y*width+x+1)*4]);rgb=[v*2.**(vals[3]-128-8) for v in vals[:3]] if vals[3] else [0.,0.,0.];pixels.append({'x':x,'y':y,'rgbe':vals,'linearRGB':rgb})
source=ROOT/'research/rea-audit/extracted-world-assets/UNDEFEATED/Content/Skies/Textures/T_SkyCloudy11.uexp'
with source.open('rb') as f:
    header=f.read(312);assert struct.unpack_from('<iii',header,251)==(width,h,1)
    assert struct.unpack_from('<i',header,263)[0]==13 and header[267:280]==b'PF_FloatRGBA\0'
    firstmip,mips,cooked,flags,count,size,combined=struct.unpack_from('<6iQ',header,280)
    assert (firstmip,mips,cooked,flags,count,size,combined)==(0,14,1,72,width*h*8,width*h*8,312+source.with_suffix('.uasset').stat().st_size)
    f.seek(312+size);assert struct.unpack('<iii',f.read(12))==(width,h,1)
    checks=[]
    for x,y in [(s['x'],s['y']) for s in pixels]+[((i*211)%width,(i*73)%h) for i in range(31)]:
        f.seek(312+(y*width+x)*8);rgba=struct.unpack('<4e',f.read(8));v=max(rgba[:3]);expected=[0]*4
        if v>=1e-32:
            mantissa,exponent=math.frexp(v);scale=mantissa*256/v;expected=[int(c*scale) for c in rgba[:3]]+[exponent+128]
        actual=list(data[offset+(y*width+x)*4:offset+(y*width+x+1)*4]);assert actual==expected,(x,y,actual,expected)
        checks.append({'x':x,'y':y,'originalHalfFloatRGBA':list(rgba),'exportedRGBE':actual,'exactExporterMatch':True})
result={'mesh':{'assetId':asset['id'],'sourcePackage':asset['sourcePackage'],'url':asset['url'],'sha256':g.HASH(path),'vertexCount':len(pos),'bounds':asset['bounds'],'uv0Min':[min(x[i] for x in uv) for i in range(2)],'uv0Max':[max(x[i] for x in uv) for i in range(2)],'axisUVSamples':samples,'normalDotPositionRange':[min(g.m.dot(n,p) for n,p in zip(norm,pos)),max(g.m.dot(n,p) for n,p in zip(norm,pos))]},'image':{'url':'/assets/world/textures/Game/Skies/Textures/T_SkyCloudy11.hdr','sha256':g.HASH(hdr),'width':width,'height':h,'header':data[:offset].decode(),'payloadOffset':offset,'payloadBytes':len(data)-offset,'storage':'uncompressed row-major RGBE, despite rle_rgbe format header; verified byte length and UEViewer WriteHDR source','orientation':'-Y +X: rows in source order, y=0 top and x=0 left; no vertical flip in WriteHDR','decode':'linearRGB = RGBbytes * 2^(Ebyte-128-8), zero if Ebyte=0','pixelSamples':pixels,'alpha':'RGBE stores exponent, not original texture alpha; material Opacity is scalar'},'originalPixelValidation':{'source':str(source),'sha256':g.HASH(source),'format':'PF_FloatRGBA','mipCount':mips,'topMipDataOffsetInUexp':312,'topMipPayloadBytes':size,'samples':checks,'exactlyMatchedSamples':len(checks),'precisionBoundary':'RGBE quantizes source half-float RGB. This verifies the exporter transform and row orientation, not bit-exact half-float output.'}}
g.WRITE(OUT/'sampling-evidence.json',result);print(json.dumps(result,ensure_ascii=False))
try:
 import numpy as np
 from PIL import Image
 a=np.frombuffer(data[offset:],dtype=np.uint8).reshape(h,width,4)[::8,::8,:];rgb=a[:,:,:3].astype(float)*np.exp2(a[:,:,3:4].astype(float)-136);rgb=np.where(a[:,:,3:4]==0,0,rgb);preview=np.clip((rgb/(1+rgb))**(1/2.2)*255,0,255).astype('uint8');Image.fromarray(preview).save(OUT/'hdr-preview-reinhard.png')
except ImportError:pass
