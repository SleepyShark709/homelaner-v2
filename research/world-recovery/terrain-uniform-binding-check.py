"""Bounded static UE4 frozen material inspection. Does not generate runtime materials."""
import ast,pathlib,json,re,base64,struct,hashlib
p=pathlib.Path
ROOT=p(__file__).resolve().parents[2]
tree=ast.parse((ROOT/'tools/asset-pipeline/restore-world-terrain.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name in ['array_items','val','props']],type_ignores=[]),'h','exec'))
level=ROOT/'research/exports/city-decoded/MainLevel.json'; im=list(array_items(level,'Imports'))
def obj(ix):
    if ix>=0:return str(ix)
    x=im[-ix-1];name=x['ObjectName'];o=x['OuterIndex'];return obj(o)+'.'+name if o<0 else name
out=[]
for ei,e in enumerate(array_items(level,'Exports')):
    if ei not in [5611,5623,5672,5675]:continue
    b=base64.b64decode(e['Extras']['$value']); pos=8;n=struct.unpack_from('<I',b,pos)[0];pos+=4;names=[]
    for _ in range(n):
        ln=struct.unpack_from('<i',b,pos)[0];pos+=4;names.append(b[pos:pos+ln-1].decode());pos+=ln+4
    n=struct.unpack_from('<I',b,pos)[0];pos+=4+6*n+4
    assert struct.unpack_from('<II',b,pos)==(1,1);pos+=8+8+20
    layout=struct.unpack_from('<II',b,pos);pos+=8
    fs=struct.unpack_from('<I',b,pos)[0];pos+=4;f=b[pos:pos+fs];fstart=pos;pos+=fs
    nv,ns,nm=struct.unpack_from('<III',b,pos);pos+=12;assert nv==0 and nm==0
    patches={}
    for _ in range(ns):
        ni,no,count=struct.unpack_from('<III',b,pos);pos+=12;assert count<100
        for offset in struct.unpack_from('<'+'I'*count,b,pos):patches[offset]=names[ni]
        pos+=count*4
    def arr(off):
        ptr,num,maxnum=struct.unpack_from('<qii',f,off);assert num==maxnum;start=off+(ptr>>1);assert not num or 0<=start<len(f);return start,num
    def header(off):
        st,n=arr(off);return [dict(offset=struct.unpack_from('<I',f,st+i*8)[0],size=struct.unpack_from('<I',f,st+i*8+4)[0]) for i in range(n)]
    scalar=[];vector=[];textures=[]
    for typ,off,stride,dest in [('scalar',144,24,scalar),('vector',160,36,vector),('texture',176,28,textures)]:
        st,n=arr(off)
        for i in range(n):
            q=st+i*stride;d={'index':i,'frozenOffset':q,'parameter':patches.get(q),'parameterIndex':struct.unpack_from('<i',f,q+12)[0],'associationByte':f[q+16]}
            if typ=='scalar':d['defaultValue']=struct.unpack_from('<f',f,q+20)[0]
            if typ=='vector':d['defaultValue']=list(struct.unpack_from('<4f',f,q+20))
            if typ=='texture':
                d['textureIndex']=struct.unpack_from('<i',f,q+20)[0];d['samplerSource']=f[q+24];d['virtualTextureLayerIndex']=f[q+25]
                d['defaultTextureObject']=obj(props(e)['CachedReferencedTextures'][d['textureIndex']])
            dest.append(d)
    ps,n=arr(288);data=f[ps:ps+n];vh,sh=header(112),header(128)
    for h in vh+sh:h['bytesHex']=data[h['offset']:h['offset']+h['size']].hex()
    record={'exportIndex':ei,'extrasSHA256':hashlib.sha256(b).hexdigest(),'extrasBytes':len(b),'frozenStartInExtras':fstart,'frozenBytes':len(f),'frozenSHA256':hashlib.sha256(f).hexdigest(),'layoutParametersRaw':layout,'scalarParameters':scalar,'vectorParameters':vector,'textureParameters2D':textures,'uniformVectorPreshaders':vh,'uniformScalarPreshaders':sh,'namePatches':patches,'preshaderDataHex':data.hex(),'preshaderDataFrozenOffset':ps}
    out.append(record)
    (ROOT/('research/world-recovery/terrain-material-shaders/export-'+str(ei)+'-extras.bin')).write_bytes(b)
    (ROOT/('research/world-recovery/terrain-material-shaders/export-'+str(ei)+'-frozen.bin')).write_bytes(f)
    print(ei,'SCALARS',[(x['parameter'],x['defaultValue']) for x in scalar],'TEXTURES',[(x['parameter'],x['textureIndex'],x['defaultTextureObject']) for x in textures],'VECTORHEADERS',vh,'SCALARHEADERS',sh)
(ROOT/'research/world-recovery/terrain-uniform-binding-check.json').write_text(json.dumps({'method':'Bounded CUE4Parse UE4.26+ layout interpretation with array-count/bounds assertions; register binding still incomplete','records':out},ensure_ascii=False,indent=2),encoding='utf-8')
