"""Restore source-backed material parameters and texture pixels, independently of meshes.
Run with bundled Python (Pillow). No original-install writes; no guessed Compact packing.
"""
from pathlib import Path
import argparse,collections,copy,hashlib,json,math,shutil,struct,subprocess,time
from urllib.parse import quote,unquote
from PIL import Image,ImageChops
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'public/assets/world';WORK=ROOT/'research/world-recovery'
SOURCE=WORK/'material-source';RAW=WORK/'material-texture-exports';TOOLS=ROOT/'tools/asset-pipeline'
PAK=Path('E:/SteamLibrary/steamapps/common/UNDEFEATED/UNDEFEATED/Content/Paks/UNDEFEATED-WindowsNoEditor.pak')
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,d):
 p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
 for i in range(20):
  try:tmp.replace(p);return
  except PermissionError:
   if i==19:raise
   time.sleep(.1)
def run(args,timeout=240):return subprocess.run([str(x) for x in args],capture_output=True,timeout=timeout,creationflags=subprocess.CREATE_NO_WINDOW)
def relative(pkg):return ('UNDEFEATED/Content/'+pkg[6:]) if pkg.startswith('/Game/') else ('Engine/Content/'+pkg[8:])
def public_relative(pkg):return pkg.lstrip('/')
def url(p):return '/'+quote(p.relative_to(ROOT/'public').as_posix(),safe='/')
def fields(v):return v.get('Value',[]) if isinstance(v,dict) else v
def prop(v,name):return next((x for x in fields(v) if isinstance(x,dict) and x.get('Name')==name),None)
def ref(doc,index):
 if not index:return None
 x=doc['Imports'][-index-1] if index<0 else doc['Exports'][index-1]
 if x['ObjectName'].startswith(('/Game/','/Engine/')):return x['ObjectName']
 return ref(doc,x.get('OuterIndex',0))
def value(p,doc):
 if p is None:return None
 v=p.get('Value',p.get('EnumValue'))
 if 'ObjectPropertyData' in p.get('$type',''):return ref(doc,v)
 if isinstance(v,list):
  if 'ArrayPropertyData' in p.get('$type',''):return [value(x,doc) for x in v]
  if len(v)==1 and v[0].get('Name')==p.get('Name'):return value(v[0],doc)
  return {x['Name']:value(x,doc) for x in v}
 if isinstance(v,str) and v in ['+0','-0']:return 0.0
 return v
def rgba(v):
 if isinstance(v,dict) and all(k in v for k in 'RGB'):return [float(v[k]) for k in 'RGB']+[float(v.get('A',1))]
 return None
def evidence(file,pointer,pkg):return {'file':str(Path(file).relative_to(ROOT)),'pointer':pointer,'package':pkg}

def inputs():
 closure=read(ROOT/'research/rea-audit/world-asset-dependency-closure.json');old=read(ROOT/'research/rea-audit/material-coverage.json')
 nodes={n['package']:n for n in closure['nodes']};files={p:Path(n['decodedFile']) for p,n in nodes.items() if n.get('decodedFile')}
 for n in old['sourceMaterialDependencyClosure']+old.get('sampledTextureMetadata',[]):
  if n.get('decodedFile'):files.setdefault(n['package'],ROOT/n['decodedFile'])
 supplement=WORK/'material-supplement.json'
 if supplement.exists():
  for pkg,n in read(supplement)['packages'].items():
   if n.get('decodedFile'):files.setdefault(pkg,Path(n['decodedFile']))
 return nodes,files

def parse_material(pkg,file,doc,idx,e):
 data=e.get('Data',[]);parameters={'scalar':{},'vector':{},'texture':{}};fixed={};cache=prop(data,'CachedExpressionData')
 if cache:
  rawparams=prop(cache,'Parameters')
  for entry in fields(rawparams) or []:
   if entry.get('Name')!='RuntimeEntries':continue
   typ={0:'scalar',1:'vector',2:'texture'}.get(entry.get('DuplicationIndex',0))
   if not typ:continue
   infos=fields(prop(entry,'ParameterInfos')) or [];vals=fields(prop(rawparams,{'scalar':'ScalarValues','vector':'VectorValues','texture':'TextureValues'}[typ])) or []
   if len(infos)!=len(vals):continue
   for i,(info,v) in enumerate(zip(infos,vals)):
    name=value(prop(info,'Name'),doc)
    parameters[typ][name]={'value':value(v,doc),'origin':'master-cached-default','evidence':evidence(file,f'/Exports/{idx}/Data/{data.index(cache)}',pkg)}
 for kind,key in [('scalar','ScalarParameterValues'),('vector','VectorParameterValues'),('texture','TextureParameterValues')]:
  p=prop(data,key)
  if p:
   for i,item in enumerate(fields(p)):
    info=prop(item,'ParameterInfo');name=value(prop(info,'Name'),doc)
    if name:parameters[kind][name]={'value':value(prop(item,'ParameterValue'),doc),'origin':'instance-override','evidence':evidence(file,f'/Exports/{idx}/Data/{data.index(p)}/Value/{i}',pkg)}
 for key in ['BlendMode','TwoSided','OpacityMaskClipValue','ShadingModel','bTangentSpaceNormal']:
  p=prop(data,key)
  if p:fixed[key]={'value':value(p,doc),'evidence':evidence(file,f'/Exports/{idx}/Data/{data.index(p)}',pkg)}
 overrides=prop(data,'BasePropertyOverrides')
 if overrides:
  for key in ['BlendMode','TwoSided','OpacityMaskClipValue','ShadingModel']:
   if value(prop(overrides,'bOverride_'+key),doc):
    default={'BlendMode':'BLEND_Opaque','TwoSided':False,'OpacityMaskClipValue':0.3333,'ShadingModel':'MSM_DefaultLit'}[key]
    v=value(prop(overrides,key),doc);fixed[key]={'value':default if v is None else v,'evidence':evidence(file,f'/Exports/{idx}/Data/{data.index(overrides)}',pkg)}
 referenced=set()
 for i,x in enumerate(doc['Imports']):
  if x.get('ClassName','').startswith('Texture'):
   if p:=ref(doc,-i-1):referenced.add(p)
 return {'sourcePackage':pkg,'parent':value(prop(data,'Parent'),doc),'parameters':parameters,'fixed':fixed,'referencedTextures':sorted(referenced),
  'source':{'decodedFile':str(file),'decodedSha256':sha(file),'exportPointer':f'/Exports/{idx}'}}

def texture_metadata(pkg,file,doc,e):
 p=e.get('Data',[]);srgb=value(prop(p,'SRGB'),doc)
 return {'sourcePackage':pkg,'colorSpace':'linear' if srgb is False else 'srgb','srgbExplicit':srgb,
  'compression':value(prop(p,'CompressionSettings'),doc) or 'TC_Default','flipGreenMetadata':value(prop(p,'bFlipGreenChannel'),doc),
  'source':{'decodedFile':str(file),'decodedSha256':sha(file)},'status':'not-exported','url':None}

def prepare_textures(packages,inventory):
 wanted=[]
 for pkg in packages:
  for ext in ['.uasset','.uexp','.ubulk']:
   p=inventory.get((relative(pkg)+ext).casefold())
   if p and not (SOURCE/p).exists():wanted.append(p)
 if wanted:
  cmd=[TOOLS/'bin/repak.exe','unpack',PAK,'-o',SOURCE,'-q']
  for p in wanted:cmd+=['-i',p]
  result=run(cmd)
  if result.returncode:raise RuntimeError((result.stdout+result.stderr).decode(errors='replace')[-3000:])

def export_batch(packages,inventory):
 prepare_textures(packages,inventory)
 for mount in ['Game','Engine']:
  subset=[p for p in packages if p.startswith('/'+mount+'/')]
  if not subset:continue
  root=SOURCE/('UNDEFEATED/Content' if mount=='Game' else 'Engine/Content');output=RAW/mount
  sources=[SOURCE/inventory[(relative(p)+'.uasset').casefold()] for p in subset]
  cmd=[TOOLS/'umodel.exe','-export','-game=ue4.27','-png','-nooverwrite','-path='+root.as_posix(),'-out='+output.as_posix()]
  cmd+=['-pkg='+p.as_posix() for p in sources[1:]];cmd+=[sources[0]]
  result=run(cmd);log=(result.stdout+result.stderr).decode(errors='replace')
  key=hashlib.sha256('\n'.join(subset).encode()).hexdigest()[:16]
  (WORK/('material-texture-export-'+key+'.log')).write_text(log,encoding='utf-8')
  if result.returncode:print('Texture batch warning',result.returncode,log[-500:],flush=True)

def bc4(block):
 a,b=block[0],block[1];pal=[a,b]
 if a>b:pal += [((7-i)*a+i*b)//7 for i in range(1,7)]
 else:pal += [((5-i)*a+i*b)//5 for i in range(1,5)]+[0,255]
 bits=int.from_bytes(block[2:8],'little');return [pal[(bits>>(3*i))&7] for i in range(16)]
def verify_normal(pkg,img,meta):
 bulk=SOURCE/(relative(pkg)+'.ubulk');w,h=img.size
 if meta['compression']!='TC_Normalmap' or not bulk.exists() or w%4 or h%4:return {'normalConvention':'unknown','reason':'No verifiable BC5 top-mip source'}
 b=bulk.read_bytes();size=w*h
 if len(b)<size:return {'normalConvention':'unknown','reason':'Bulk too small for BC5 top mip'}
 pixels=img.convert('RGB');checks=[];flipped_checks=[];block_count=(w//4)*(h//4)
 blocks=sorted(set([0,1,w//4+1,block_count//2,block_count-1]+[(i*2654435761)%block_count for i in range(1,33)]))
 for block in blocks:
  data=b[block*16:block*16+16];red,green=bc4(data[:8]),bc4(data[8:]);bx=(block%(w//4))*4;by=(block//(w//4))*4
  for i in range(16):
   pixel=pixels.getpixel((bx+i%4,by+i//4));checks.append(abs(pixel[0]-red[i])<=1 and abs(pixel[1]-green[i])<=1);flipped_checks.append(abs(pixel[1]-(255-green[i]))<=1)
 if all(checks) and not all(flipped_checks):return {'normalConvention':'directx','greenChannelTransformation':'unchanged-from-cooked-BC5','validation':f'{len(checks)} pixels / {len(blocks)} distributed BC5 blocks: original R/G match within 1; inverted G hypothesis rejected','sourceBulkSha256':sha(bulk)}
 if all(checks):return {'normalConvention':'unknown','reason':'Sampled green values too close to 127.5 to distinguish original from inversion; no orientation claim'}
 return {'normalConvention':'unknown','reason':'BC5 source layout or decoder comparison did not match'}

def publish_texture(pkg,meta):
 src=RAW/(public_relative(pkg)+'.png');dest=OUT/'textures'/(public_relative(pkg)+'.png')
 if not src.exists():
  hdr=src.with_suffix('.hdr')
  if hdr.exists():
   target=dest.with_suffix('.hdr');target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(hdr,target)
   meta.update(status='exported-original-hdr-not-bound',url=url(target),sha256=sha(target),bytes=target.stat().st_size,unsupported='HDR image preserved; not bound to ordinary PNG/PBR slots')
   return
  meta['status']='export-failed-or-non-png';return
 try:
  with Image.open(src) as im:
   im.load();rgb=im.convert('RGB');r,g,b=rgb.split();rg=ImageChops.difference(r,g);rb=ImageChops.difference(r,b);error=max(rg.getextrema()[1],rb.getextrema()[1]);gray=error==0
   meta.update(width=im.width,height=im.height,mode=im.mode,exactGrayscale=gray,rgbChannelMaxDifference=error,alphaRange=im.convert('RGBA').getchannel('A').getextrema())
   if meta['compression']=='TC_Normalmap':meta.update(verify_normal(pkg,im,meta))
  dest.parent.mkdir(parents=True,exist_ok=True)
  if not dest.exists() or sha(dest)!=sha(src):shutil.copy2(src,dest)
  meta.update(url=url(dest),sha256=sha(dest),bytes=dest.stat().st_size,status='exported-original-pixels')
  meta['sourceFiles']=[{'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size} for ext in ['.uasset','.uexp','.ubulk'] if (p:=SOURCE/(relative(pkg)+ext)).exists()]
 except Exception as exc:meta['status']='validation-failed';meta['error']=str(exc)

ALIASES={'baseColor':['BaseColor','Base Color','Base color','BaseColorTexture','Diffuse','DiffuseTexture','Diffuse Texture','01. Diffuse Texture','Albedo','Color','Hair base'],
 'normal':['Normal','Normal Map','NormalMap','NormalTexture','Normal Tex','02. Normal Texture','Hair normal'],
 'roughness':['Roughness','RoughnessTexture','01. Roughness Texture','03. Roughness Texture'],
 'metallic':['Metallic','Metalness','MetallicTexture'],
 'occlusion':['AO','Ambient Occlusion','AmbientOcclusionTexture','Occlusion','AO Tex','Hair AO'],
 'emissive':['Emissive','Emissive Color','EmissiveColor','EmissiveTexture','EmmisiveTexture'],
 'opacity':['Opacity','Opacity Mask','OpacityMask','OpacityMaskTexture','OpacityTexture','Hair transp']}

def build_material(pkg,raw,tex,cache,trail=()):
 if pkg in cache:return cache[pkg]
 if pkg in trail:raise ValueError('Material parent cycle '+pkg)
 src=raw[pkg];parent=src['parent'];inherited=build_material(parent,raw,tex,cache,trail+(pkg,)) if parent in raw or parent in cache else None
 pars=copy.deepcopy(inherited['parameters']) if inherited else {'scalar':{},'vector':{},'texture':{}}
 fixed=copy.deepcopy(inherited['sourceProperties']) if inherited else {}
 for kind in pars:pars[kind].update(src['parameters'][kind])
 fixed.update(src['fixed']);m={'sourcePackage':pkg,'parent':parent,'baseMaterial':inherited['baseMaterial'] if inherited else pkg,
  'parameters':pars,'sourceProperties':fixed,'source':src['source'],'channels':{k:None for k in ALIASES},
  'factors':{k:None for k in ['baseColor','roughness','metallic','emissive','opacity']},'unsupported':[],
  'blendMode':fixed.get('BlendMode',{}).get('value','BLEND_Opaque'),'doubleSided':fixed.get('TwoSided',{}).get('value',False),
  'alphaCutoff':fixed.get('OpacityMaskClipValue',{}).get('value',.3333),'packedPBR':None}
 for role,names in ALIASES.items():
  candidate=next(((n,pars['texture'][n]) for n in names if n in pars['texture']),None)
  if not candidate:continue
  name,param=candidate;t=tex.get(param['value'])
  if not t or t['status']!='exported-original-pixels':m['unsupported'].append(role+': original texture pixels not available');continue
  # RGB565 BC1 quantization can make an originally gray scalar image differ by
  # several integer levels. Only allow this bounded discrepancy for an explicit
  # single-role scalar parameter; never apply this rule to Compact/mask atlases.
  scalar_gray=t.get('exactGrayscale') or t.get('rgbChannelMaxDifference',256)<=8
  channel='rgb' if role in ['baseColor','normal','emissive'] else ('r' if scalar_gray else None)
  if channel is None:m['unsupported'].append(role+': exact source scalar component not proven');continue
  entry={'texturePackage':param['value'],'url':t['url'],'colorSpace':t['colorSpace'],'channel':channel,'texCoord':0,'sourceParameter':name,'evidence':param['evidence'],
   'mappingBasis':'explicit source parameter semantic; complete shader formula not recovered','uvMappingStatus':'mesh UV0 projection; original shader UV math not reconstructed'}
  if channel=='r':entry['scalarProjection']={'sourceRole':name,'rgbChannelMaxDifference':t['rgbChannelMaxDifference'],'rule':'R component of explicit scalar-role image, RGB channels equal within at most 8/255 BC color quantization; not inferred packed-channel semantics'}
  if role=='normal':
   entry['normalConvention']=t.get('normalConvention','unknown');entry['normalValidation']={k:t[k] for k in ['greenChannelTransformation','validation','sourceBulkSha256','reason'] if k in t}
  m['channels'][role]=entry
 for role,names in [('baseColor',['Base color','BaseColor','Base Color','Color','Colour','ColorGlass','Glass_Color']),('emissive',['EmissiveColor','Emissive Color','Emissive01'])]:
  found=next((pars['vector'][n] for n in names if n in pars['vector']),None)
  if found:
   v=rgba(found['value'])
   if v and all(math.isfinite(x) and x>=0 for x in v):m['factors'][role]=v
 for role,names in [('roughness',['Roughness']),('metallic',['Metallic','Metalness']),('opacity',['Opacity'])]:
  found=next((pars['scalar'][n] for n in names if n in pars['scalar']),None)
  if found:
   v=found['value']
   if isinstance(v,(int,float)) and 0<=v<=1:m['factors'][role]=v
   else:m['unsupported'].append(role+': scalar outside direct PBR range; retained in parameters')
 emissive_controls=[pars['scalar'][n] for n in ['EmissiveScale','EmissiveOnOff','EmissiveAmount','EmissiveIntensity'] if n in pars['scalar']]
 if m['channels']['emissive'] and emissive_controls:
  factors=[x['value'] for x in emissive_controls]
  if all(isinstance(v,(int,float)) and math.isfinite(v) and v>=0 for v in factors):
   multiplier=math.prod(factors);color=m['factors']['emissive'] or [1,1,1,1]
   m['factors']['emissive']=[color[i]*multiplier for i in range(3)]+[color[3]]
   m['emissiveControlEvidence']=emissive_controls
 if any(n.casefold()=='compact' for n in pars['texture']):m['unsupported'].append('Compact channel packing not established; not bound as ORM')
 if not m['channels']['baseColor'] and not m['factors']['baseColor']:m['unsupported'].append('Base color shader connection unknown; no texture selected by filename')
 if fixed.get('ShadingModel',{}).get('value') not in [None,'MSM_DefaultLit','MSM_Unlit']:m['unsupported'].append('Original shading model '+str(fixed['ShadingModel']['value'])+' not reconstructed')
 if m['blendMode'] not in ['BLEND_Opaque','BLEND_Masked']:m['unsupported'].append('Translucency/refraction shader only partially represented by blend state')
 if any('Region' in n for n in pars['vector']):m['unsupported'].append('ID region coloring shader not reconstructed')
 if any('Wetness' in n for n in pars['scalar']):m['unsupported'].append('Weather/layered material shader not reconstructed')
 m['unsupported'].append('Compiled shader math and non-primary UV transforms not reconstructed')
 m['status']='partial-pbr-projection' if any(m['channels'].values()) or any(v is not None for v in m['factors'].values()) else 'shader-unmapped'
 cache[pkg]=m;return m

def pack_orm(m,tex):
 inputs={role:m['channels'][role] for role in ['occlusion','roughness','metallic']};factors=m['factors']
 if not any(inputs.values()):return
 size=(1,1)
 for c in inputs.values():
  if c:
   t=tex[c['texturePackage']];size=(max(size[0],t['width']),max(size[1],t['height']))
 layers=[];ev={};fallback=[]
 for role,default in [('occlusion',1),('roughness',1),('metallic',0)]:
  c=inputs[role];factor=factors.get(role)
  if c:
   im=Image.open(ROOT/'public'/unquote(c['url'].lstrip('/'))).convert('RGB').getchannel(c['channel'].upper())
   # Decode and multiply in one float expression before the single UNORM quantization.
   # This avoids a second rounding step for a source SRGB scalar multiplied by a factor.
   gain=factor if factor is not None else 1
   if c['colorSpace']=='srgb' or gain!=1:
    im=im.point([round(255*max(0,min(1,(((v/255/12.92) if v/255<=.04045 else ((v/255+.055)/1.055)**2.4) if c['colorSpace']=='srgb' else v/255)*gain))) for v in range(256)])
   if im.size!=size:im=im.resize(size,Image.Resampling.BILINEAR)
   # Explicit named scalar multiplier is a PBR projection, never called a recovered UE formula.
   ev[role]={'source':c,'scalarFactorApplied':factor if factor is not None else 1,'resizedTo':size,'quantization':'Single 8-bit UNORM round after source decode and scalar multiplication; packing may move clamping before texture filtering.'}
  else:
   v=factor if factor is not None else default;im=Image.new('L',size,round(v*255));ev[role]={'constant':v,'sourceScalar':factor is not None}
   if factor is None:fallback.append(role)
  layers.append(im)
 path=OUT/'materials'/(public_relative(m['sourcePackage'])+'.orm.png');path.parent.mkdir(parents=True,exist_ok=True);Image.merge('RGB',layers).save(path)
 m['packedPBR']={'url':url(path),'channels':{'occlusion':'r','roughness':'g','metallic':'b'},'colorSpace':'linear','scalarFactorsAlreadyApplied':True,
  'fallbackChannels':fallback,'evidence':ev,'sha256':sha(path),'width':size[0],'height':size[1]}

def pack_opacity(material):
 """Encode the explicitly selected scalar sample as alpha, preserving original pixels."""
 c=material['channels'].get('opacity')
 if not c:return
 if c['channel'] not in ['r','g','b','a']:raise ValueError('Opacity scalar channel required')
 source=ROOT/'public'/unquote(c['url'].lstrip('/'))
 signature=json.dumps({'sourceSha256':sha(source),'channel':c['channel'],'colorSpace':c['colorSpace']},sort_keys=True)
 path=OUT/'materials/opacity'/(hashlib.sha256(signature.encode()).hexdigest()+'.png')
 with Image.open(source) as original:
  alpha=original.convert('RGBA').getchannel(c['channel'].upper())
  # sRGB decoding affects RGB samples, never the alpha component.
  linearize=c['colorSpace']=='srgb' and c['channel']!='a'
  if linearize:alpha=alpha.point([round(255*((v/255/12.92) if v/255<=.04045 else ((v/255+.055)/1.055)**2.4)) for v in range(256)])
  if not path.exists():
   path.parent.mkdir(parents=True,exist_ok=True)
   rgba=Image.new('RGBA',alpha.size,(255,255,255,255));rgba.putalpha(alpha);rgba.save(path)
 material['packedOpacity']={'url':url(path),'colorSpace':'linear','channel':'a','scalarFactorsAlreadyApplied':False,
  'sha256':sha(path),'width':alpha.width,'height':alpha.height,
  'evidence':{'source':c,'sourceSha256':sha(source),'operation':'RGB=1; alpha=selected source component after source RGB color-space decoding; nearest 8-bit UNORM quantization',
    'sourceSrgbDecoded':linearize,'scalarFactorApplied':1,'quantizationMaxAbsoluteError':0.5/255}}

def overrides():
 world=read(ROOT/'research/rea-audit/world-coverage.json');out=[]
 for level in world['levels']:
  data=read(ROOT/'research/rea-audit'/level['details'])
  for row in data['materialOverrides']:
   out.append({'levelPackage':level['package'],'componentExportIndex':row['componentExportIndex'],'sourceActor':row['sourceActor'],
    'slots':[{'slotIndex':i,'materialPackage':p.rsplit('/',1)[0] if p and p.startswith(('/Game/','/Engine/')) else None,'rawReference':p} for i,p in enumerate(row['slots'])]})
 return out

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--skip-export',action='store_true');parser.add_argument('--reuse-texture-cache',action='store_true');parser.add_argument('--limit-textures',type=int,default=0);args=parser.parse_args()
 WORK.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
 nodes,files=inputs();raw={};tex={}
 for pkg,file in files.items():
  doc=read(file)
  for i,e in enumerate(doc.get('Exports',[])):
   ci=e.get('ClassIndex',0);cls=doc['Imports'][-ci-1]['ObjectName'] if ci<0 else None
   if cls in ['Material','MaterialInstanceConstant']:
    raw[pkg]=parse_material(pkg,file,doc,i,e)
    if pkg in nodes:raw[pkg]['source']['sourceFiles']=nodes[pkg].get('sourceFiles',[])
   elif cls=='Texture2D':tex[pkg]=texture_metadata(pkg,file,doc,e)
 inventory={p.casefold():p for p in (ROOT/'research/evidence/pak-files.txt').read_text().splitlines()}
 cached=read(WORK/'material-texture-progress.json')['textures'] if args.reuse_texture_cache and (WORK/'material-texture-progress.json').exists() else {}
 # Prioritize named parameter textures so an initial interrupted pass is useful.
 priority={v['value'] for m in raw.values() for v in m['parameters']['texture'].values()}
 packages=sorted(tex,key=lambda p:(p not in priority,p));packages=packages[:args.limit_textures] if args.limit_textures else packages
 for start in range(0,len(packages),24):
  batch=packages[start:start+24]
  if not args.skip_export:
   missing=[p for p in batch if not (RAW/(public_relative(p)+'.png')).exists()]
   if missing:export_batch(missing,inventory)
  for pkg in batch:
   old=cached.get(pkg)
   if old and old['source']['decodedSha256']==tex[pkg]['source']['decodedSha256'] and old.get('url') and (ROOT/'public'/unquote(old['url'].lstrip('/'))).exists():tex[pkg]=old
   else:publish_texture(pkg,tex[pkg])
  write(WORK/'material-texture-progress.json',{'attempted':min(start+24,len(packages)),'planned':len(packages),'exported':sum(t['status']=='exported-original-pixels' for t in tex.values()),'textures':tex})
  print('Textures',min(start+24,len(packages)),'/',len(packages),'exported',sum(t['status']=='exported-original-pixels' for t in tex.values()),flush=True)
 materials={}
 for pkg in raw:build_material(pkg,raw,tex,materials)
 for m in materials.values():
  pack_orm(m,tex);pack_opacity(m)
 manifest={'schemaVersion':1,'buildState':'complete-with-recorded-shader-gaps','materials':materials,'textures':tex,'instanceOverrides':overrides(),
  'policy':'No filename-based material colors or Compact channel assumptions. Parameter-semantic PBR projection; original shader formula incomplete.'}
 write(OUT/'material-manifest.json',manifest)
 summary={'materials':len(materials),'status':dict(collections.Counter(m['status'] for m in materials.values())),
  'texturePixelsExported':sum(t['status']=='exported-original-pixels' for t in tex.values()),'textureMetadataTotal':len(tex),
  'channelCounts':{k:sum(bool(m['channels'][k]) for m in materials.values()) for k in ALIASES},'ormPacked':sum(bool(m['packedPBR']) for m in materials.values()),
  'normalConventionCounts':dict(collections.Counter(t.get('normalConvention','not-normal') for t in tex.values())),
  'textureStatusCounts':dict(collections.Counter(t['status'] for t in tex.values())),
  'instanceOverrideComponents':len(manifest['instanceOverrides']),'sourceScriptSha256':sha(Path(__file__)),'originalInstallReadOnly':True}
 write(WORK/'material-restoration-report.json',summary);print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
