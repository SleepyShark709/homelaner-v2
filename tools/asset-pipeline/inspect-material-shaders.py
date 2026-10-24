"""Bounded read-only cooked material shader extraction, not REA Evidence."""
from pathlib import Path
import json,base64,struct,hashlib,ctypes,re,importlib.util,argparse
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'research/world-recovery/material-shader-recovery';OUT.mkdir(exist_ok=True)
TARGETS=['/Game/ForgottenHotel/Materials/Tiling_Mats/WorldTilingMaster','/Game/UrbanCity/Materials/Foliage/Foliage_Mat','/Game/UrbanCity/Materials/Props/prp_bench_Mat']
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(b):return hashlib.sha256(b).hexdigest()
def resource_table(b):
 q=4;out={'resourceTableBits':struct.unpack_from('<I',b)[0]}
 for name in ['srvMap','samplerMap','uavMap','layoutHashes','textureMap']:
  n=struct.unpack_from('<I',b,q)[0];q+=4;assert n<2048;out[name]=list(struct.unpack_from('<'+'I'*n,b,q));q+=4*n
 assert q==len(b)
 def entries(a):
  res=[]
  for cb in range(len(out['layoutHashes'])):
   start=a[cb] if cb<len(a) else 0
   if not start:continue
   for token in a[start:]:
    if token==0xffffffff or token>>24!=cb:break
    res.append({'constantBuffer':cb,'resourceIndex':(token>>8)&65535,'bindIndex':token&255})
  return res
 out['textureBindings']=entries(out['textureMap']);out['samplerBindings']=entries(out['samplerMap']);return out
def lz4_shader(b,start,literal):
 q=start;out=bytearray();magic=-1;target=None
 for _ in range(100000):
  token=b[q];q+=1;n=token>>4
  if n==15:
   while True:
    add=b[q];q+=1;n+=add
    if add!=255:break
  if n>500000 or q+n>len(b):raise ValueError()
  out.extend(b[q:q+n]);q+=n
  if magic<0:
   magic=out.find(b'DXBC')
   if magic<0 and (q>literal+4 or len(out)>1024):raise ValueError()
  if magic>=0 and target is None and len(out)>=magic+32:
   size=struct.unpack_from('<I',out,magic+24)[0];assert 32<size<500000;target=magic+size
  if target and len(out)>=target:return bytes(out[:magic]),bytes(out[magic:target]),q
  offset=struct.unpack_from('<H',b,q)[0];q+=2
  if not 0<offset<=len(out):raise ValueError()
  n=(token&15)+4
  if (token&15)==15:
   while True:
    add=b[q];q+=1;n+=add
    if add!=255:break
  if len(out)+n>500000:raise ValueError()
  for _ in range(n):out.append(out[-offset])
  if target and len(out)>=target:return bytes(out[:magic]),bytes(out[magic:target]),q
 raise ValueError()
def disassemble(b):
 dll=ctypes.WinDLL('d3dcompiler_47.dll');fn=dll.D3DDisassemble;fn.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_uint,ctypes.c_char_p,ctypes.POINTER(ctypes.c_void_p)];fn.restype=ctypes.c_long
 blob=ctypes.c_void_p();buf=ctypes.create_string_buffer(b);hr=fn(buf,len(b),0,None,ctypes.byref(blob))
 if hr<0 or not blob:raise ValueError('D3DDisassemble rejected')
 vt=ctypes.cast(blob,ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
 ptr=ctypes.WINFUNCTYPE(ctypes.c_void_p,ctypes.c_void_p)(vt[3])(blob);size=ctypes.WINFUNCTYPE(ctypes.c_size_t,ctypes.c_void_p)(vt[4])(blob)
 result=ctypes.string_at(ptr,size).decode('utf-8').rstrip('\0');ctypes.WINFUNCTYPE(ctypes.c_ulong,ctypes.c_void_p)(vt[2])(blob);return result
def shaders(b,folder):
 results=[];failed=[]
 for hit in re.finditer(b'DXBC',b):
  literal=hit.start();found=None
  for start in range(max(0,literal-512),literal):
   try:
    prefix,bytecode,end=lz4_shader(b,start,literal);table=resource_table(prefix);assembly=disassemble(bytecode)
    stage=re.search(r'\b[phvdgc]s_5_0\b',assembly).group();found=(start,end,prefix,bytecode,table,assembly,stage);break
   except (ValueError,AssertionError,struct.error,IndexError,AttributeError):continue
  if not found:failed.append(literal);continue
  start,end,prefix,bytecode,table,assembly,stage=found;i=len(results);stem=folder/f'shader-{i}-{stage}';stem.with_suffix('.dxbc').write_bytes(bytecode);stem.with_suffix('.asm').write_text(assembly,encoding='utf-8')
  results.append({'dxbcLiteralOffsetInExtras':literal,'lz4CandidateStart':start,'lz4ConsumedEnd':end,'decodedPrefixHex':prefix.hex(),'bytes':len(bytecode),'sha256':sha(bytecode),'stage':stage,'assemblyFile':str(stem.with_suffix('.asm')),'resourceTable':table})
 print('extracted shaders',len(results),'unresolved literals',len(failed),flush=True);return {'shaders':results,'unresolvedDxbcLiterals':failed}
spec=importlib.util.spec_from_file_location('restore',Path(__file__).with_name('restore-world-materials.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def frozen(b,doc,e):
 pos=8;n=struct.unpack_from('<I',b,pos)[0];pos+=4;names=[]
 for _ in range(n):
  ln=struct.unpack_from('<i',b,pos)[0];pos+=4;assert 0<ln<10000;names.append(b[pos:pos+ln-1].decode());pos+=ln+4
 n=struct.unpack_from('<I',b,pos)[0];pos+=4+6*n+4
 assert struct.unpack_from('<II',b,pos)==(1,1);pos+=8+8+20
 layout=struct.unpack_from('<II',b,pos);pos+=8
 fs=struct.unpack_from('<I',b,pos)[0];pos+=4;f=b[pos:pos+fs];fstart=pos;pos+=fs
 nv,ns,nm=struct.unpack_from('<III',b,pos);pos+=12;assert nv==0 and nm==0
 patches={}
 for _ in range(ns):
  ni,no,count=struct.unpack_from('<III',b,pos);pos+=12;assert count<10000
  for offset in struct.unpack_from('<'+'I'*count,b,pos):patches[offset]=names[ni]
  pos+=count*4
 def arr(off):
  ptr,num,maxnum=struct.unpack_from('<qii',f,off);assert num==maxnum and 0<=num<10000;start=off+(ptr>>1);assert not num or 0<=start<len(f);return start,num
 def header(off):
  st,n=arr(off);return [{'offset':struct.unpack_from('<I',f,st+i*8)[0],'size':struct.unpack_from('<I',f,st+i*8+4)[0]} for i in range(n)]
 cache=m.value(m.prop(e['Data'],'CachedExpressionData'),doc);refs=cache['ReferencedTextures']
 scalar=[];vector=[];textures=[]
 for typ,off,stride,dest in [('scalar',144,24,scalar),('vector',160,36,vector),('texture',176,28,textures)]:
  st,n=arr(off)
  for i in range(n):
   q=st+i*stride;d={'index':i,'frozenOffset':q,'parameter':patches.get(q),'parameterIndex':struct.unpack_from('<i',f,q+12)[0],'associationByte':f[q+16]}
   if typ=='scalar':d['defaultValue']=struct.unpack_from('<f',f,q+20)[0]
   if typ=='vector':d['defaultValue']=list(struct.unpack_from('<4f',f,q+20))
   if typ=='texture':
    d['textureIndex']=struct.unpack_from('<i',f,q+20)[0];d['samplerSource']=f[q+24];d['virtualTextureLayerIndex']=f[q+25];d['defaultTextureObject']=refs[d['textureIndex']]
   dest.append(d)
 ps,n=arr(288);data=f[ps:ps+n];vh,sh=header(112),header(128)
 for h in vh+sh:h['bytesHex']=data[h['offset']:h['offset']+h['size']].hex()
 return {'frozenStartInExtras':fstart,'frozenBytes':len(f),'frozenSHA256':sha(f),'layoutParametersRaw':layout,'scalarParameters':scalar,'vectorParameters':vector,'textureParameters2D':textures,'uniformVectorPreshaders':vh,'uniformScalarPreshaders':sh,'namePatches':patches,'preshaderDataHex':data.hex(),'preshaderDataFrozenOffset':ps},f
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--target',action='append');args=parser.parse_args()
 materials=read(ROOT/'public/assets/world/material-manifest.json')['materials']
 for pkg in args.target or TARGETS:
  doc=read(materials[pkg]['source']['decodedFile']);e=doc['Exports'][0];b=base64.b64decode(e['Extras']['$value'])
  folder=OUT/pkg.rsplit('/',1)[-1];folder.mkdir(exist_ok=True);(folder/'extras.bin').write_bytes(b)
  print(pkg,len(b),b[:90].hex(),'DXBC',b.count(b'DXBC'),flush=True)
  info,f=frozen(b,doc,e);(folder/'frozen.bin').write_bytes(f);m.write(folder/'uniforms.json',info)
  print('texture',info['textureParameters2D'],'scalar',info['scalarParameters'],'preshaders',info['uniformVectorPreshaders'],info['uniformScalarPreshaders'],flush=True)
  result=shaders(b,folder);result.update(package=pkg,extrasSha256=sha(b),source=materials[pkg]['source'],method='Bounded LZ4 candidate extraction; complete D3D11 resource-table prefix and Microsoft D3DDisassemble validation; not REA retained Evidence');m.write(folder/'index.json',result)
if __name__=='__main__':main()
