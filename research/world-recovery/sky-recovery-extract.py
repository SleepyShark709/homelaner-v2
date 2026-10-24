"""Read-only original sky DXBC and frozen uniform extraction; no manifest changes."""
import base64,importlib.util,pathlib,struct
ROOT=pathlib.Path(__file__).resolve().parents[2];OUT=ROOT/'research/world-recovery/sky-recovery';OUT.mkdir(exist_ok=True)
spec=importlib.util.spec_from_file_location('inspect',ROOT/'tools/asset-pipeline/inspect-material-shaders.py');s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
materials=s.read(ROOT/'public/assets/world/material-manifest.json');pkg='/Game/Skies/Materials/M_Skies_Master';mat=materials['materials'][pkg];doc=s.read(mat['source']['decodedFile']);e=doc['Exports'][0];b=base64.b64decode(e['Extras']['$value']);(OUT/'extras.bin').write_bytes(b)
u,f=s.frozen(b,doc,e);(OUT/'frozen.bin').write_bytes(f)
refs=s.m.value(s.m.prop(e['Data'],'CachedExpressionData'),doc)['ReferencedTextures']
def arr(off):
    ptr,n,maxn=struct.unpack_from('<qii',f,off);assert n==maxn and 0<=n<1000;return off+(ptr>>1),n
st,n=arr(192);cubes=[]
for i in range(n):
    q=st+i*28;texindex=struct.unpack_from('<i',f,q+20)[0];cubes.append({'index':i,'frozenOffset':q,'parameter':u['namePatches'].get(q),'parameterIndex':struct.unpack_from('<i',f,q+12)[0],'associationByte':f[q+16],'textureIndex':texindex,'samplerSource':f[q+24],'virtualTextureLayerIndex':f[q+25],'defaultTextureObject':refs[texindex]})
u['textureParametersCube']=cubes;s.m.write(OUT/'uniforms.json',u)
result=s.shaders(b,OUT);result.update(package=pkg,extrasSha256=s.sha(b),source=mat['source'],method='Original cooked LZ4 shader extraction with validated DXBC and complete resource prefix; Microsoft D3DDisassemble; not REA retained native Evidence')
s.m.write(OUT/'index.json',result);s.m.write(OUT/'material-descriptors.json',{key:materials['materials'][key] for key in [pkg,'/Game/-HeroGame/Maps/SubLevel/LightingTest#export:14']});s.m.write(OUT/'texture-descriptor.json',materials['textures']['/Game/Skies/Textures/T_SkyCloudy11'])
print('cube params',cubes);print('uniforms',u['scalarParameters'],u['vectorParameters']);print('shaders',len(result['shaders']))
