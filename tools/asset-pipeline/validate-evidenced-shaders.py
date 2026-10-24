"""Independent bounded DXBC arithmetic interpreter versus recovered world formulas."""
from pathlib import Path
import json,math,re,random,hashlib
ROOT=Path(__file__).resolve().parents[2];D=ROOT/'research/world-recovery/material-shader-recovery'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def clamp(x):return max(0.,min(1.,x))
def dot(x,y):return sum(a*b for a,b in zip(x,y))
def norm(v):return [x/math.sqrt(dot(v,v)) for x in v]
def mix(a,b,t):return [x+(y-x)*t for x,y in zip(a,b)]
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def sampled(reg,uv):
 a=math.sin(uv[0]*.7+uv[1]*1.3);b=math.cos(uv[0]*1.1-uv[1]*.9)
 return [.5+.2*a,.5+.2*b,.4+.3*a,.6+.3*b] if reg==6 else [.5+.45*a,.5+.45*b,.35+.3*a,.6]
class VM:
 def __init__(self,r,sampler=sampled,literalMap=None):self.r=r;self.sampler=sampler;self.literalMap=literalMap or {}
 def arg(self,s):
  sign=-1 if s.startswith('-') else 1;s=s.lstrip('-');absolute=s.startswith('|');s=s.strip('|')
  if s.startswith('l('):v=[self.literalMap.get(x.strip(),float(x)) for x in s[2:-1].split(',')];v=v*4 if len(v)==1 else v
  else:
   name,sw=(s.rsplit('.',1) if '.' in s else (s,'xyzw'));v=[self.r[name]['xyzw'.index(c)] for c in sw]
  if len(v)==1:v=v*4
  return [sign*(abs(x) if absolute else x) for x in v]
 def put(self,d,v):
  name,sw=d.split('.');self.r.setdefault(name,[0.]*4)
  for c in sw:self.r[name]['xyzw'.index(c)]=v['xyzw'.index(c)]
 def run(self,line):
  op,rest=line.split(' ',1);args=re.split(r', (?![^()]*\))',rest)
  if op.startswith('sample'):
   uv=self.arg(args[1]);tex,sw=args[2].split('.');v=self.sampler(int(tex[1:]),uv);self.put(args[0],[v['xyzw'.index(c)] for c in sw]);return
  sat=op.endswith('_sat');op=op.removesuffix('_sat');a=[self.arg(x) for x in args[1:]]
  if op=='mov':v=a[0]
  elif op=='add':v=[x+y for x,y in zip(*a)]
  elif op=='mul':v=[x*y for x,y in zip(*a)]
  elif op=='mad':v=[x*y+z for x,y,z in zip(*a)]
  elif op=='div':v=[x/y for x,y in zip(*a)]
  elif op=='min':v=[min(x,y) for x,y in zip(*a)]
  elif op=='max':v=[max(x,y) for x,y in zip(*a)]
  elif op in ['dp2','dp3']:v=[dot(a[0][:int(op[-1])],a[1][:int(op[-1])])]*4
  elif op=='sqrt':v=[math.sqrt(x) for x in a[0]]
  elif op=='rsq':v=[1/math.sqrt(x) for x in a[0]]
  elif op=='ge':v=[1. if x>=y else 0. for x,y in zip(*a)]
  elif op=='log':v=[math.log2(x) if x>0 else float('-inf') for x in a[0]]
  elif op=='exp':v=[2**x for x in a[0]]
  elif op=='movc':v=[y if x else z for x,y,z in zip(*a)]
  else:raise ValueError(line)
  self.put(args[0],[clamp(x) for x in v] if sat else v)
def main():
 manifest=read(ROOT/'public/assets/world/material-manifest.json');bindings=read(D/'bindings.json')['materials'];rng=random.Random(709);errors=[];trials=0;other_trials=0;maxerr=0.
 for pkg,b in bindings.items():
  s=b['shader'];assembly=Path(s['assemblyFile']).read_text().splitlines();bc=Path(s['assemblyFile']).with_suffix('.dxbc').read_bytes();assert hashlib.sha256(bc).hexdigest()==s['sha256']
  mat=manifest['materials'][pkg];rec=mat['shaderRecovery']
  if rec['kind']!='world-triplanar':
   foliage=rec['kind']=='foliage-vertex-mask'
   first='sample_b_indexable(texture2d)(float,float,float,float) r4.xyzw, v4.xyxx, t6.xyzw, s3, cb0[143].y' if foliage else 'sample_b_indexable(texture2d)(float,float,float,float) r4.xyz, v2.xyxx, t10.xyzw, s4, cb0[143].y'
   last='mul_sat r4.xyz, r4.xyzx, cb2[3].wwww' if foliage else 'mov_sat r1.w, r1.w'
   snippet=assembly[assembly.index(first):assembly.index(last)+1]
   for trial in range(100):
    samples={i:[rng.random() for _ in range(4)] for i in range(5,14)};vertex=rng.random();regs={'v2':[vertex,0,0,0],'v4':[0,0,0,0],'cb0[143]':[0,0,0,0]}
    for i,v in enumerate(b['vectorRegisters']):regs[f'cb2[{i}]']=v['value'][:]
    for v in b['scalarRegisters']:regs.setdefault(f"cb2[{v['register']}]",[0.]*4)['xyzw'.index(v['component'])]=v['value'][0]
    vm=VM(regs,lambda reg,uv:samples[reg])
    for line in snippet:vm.run(line)
    if foliage:
     expected=[clamp(3*x*clamp(vertex*rec['occlusionMultiplier'])) for x in samples[6][:3]]
     cmp=list(zip(vm.r['r5'][:3],expected))+[(vm.r['r0'][3],clamp(samples[7][0]*rec['roughnessMultiplier']))]+list(zip(vm.r['r4'][:3],[clamp(x*rec['subsurfaceStrength']) for x in samples[6][:3]]))+[(vm.r['r4'][3],samples[6][3])]
     assert 'add r1.w, r4.w, l(-0.333300)' in assembly
    else:
     cmp=list(zip(vm.r['r4'][:3],samples[10][:3]))+[(vm.r['r5'][0],samples[11][0]),(vm.r['r0'][3],clamp(samples[12][0]*mat['factors']['roughness'])),(vm.r['r1'][3],samples[13][0])]
    delta=max(abs(x-y) for x,y in cmp);maxerr=max(maxerr,delta);other_trials+=1
    if delta>1e-9:errors.append({'package':pkg,'trial':trial,'maxError':delta})
   continue
  start=assembly.index('add r3.xyz, v2.xyzx, -cb0[70].xyzx');end=assembly.index('mov_sat r3.x, cb3[8].z')
  for trial in range(25):
   N=norm([rng.uniform(-1,1) for _ in range(3)]);T=norm(cross(N,[0,1,0]))
   if trial%2:
    N2=norm([rng.uniform(-1,1) for _ in range(3)]);T2=norm(cross(N2,[0,1,0]));N=mix(N,N2,.3);T=mix(T,T2,.3)
   hand=-1. if trial%3==0 else 1.;B=[x*hand for x in cross(N,T)];pos=[rng.uniform(-80000,80000) for _ in range(3)];translation=[rng.uniform(-50000,50000) for _ in range(3)]
   regs={'v0':T+[0.],'v1':N+[hand],'v2':[a+b for a,b in zip(pos,translation)]+[0.],'r0':B+[0.],'cb0[70]':translation+[0.],'cb0[138]':[0.,0.,0.,1.],'cb0[139]':[0.,1.,0.,0.],'cb0[143]':[0.,0.,0.,0.]}
   for i,v in enumerate(b['vectorRegisters']):regs[f'cb3[{i}]']=v['value'][:]
   for v in b['scalarRegisters']:regs.setdefault(f"cb3[{v['register']}]",[0.]*4)['xyzw'.index(v['component'])]=v['value'][0]
   vm=VM(regs);actualNormal=None
   for line in assembly[start:end]:
    if line.startswith('mul r4.xyz, cb3[5]'):actualNormal=vm.r['r0'][:3]
    vm.run(line)
   q=[p/s for p,s in zip(pos,rec['worldScaleUEcmNegative'])];uxz=[q[0],q[2]];uyz=[q[1],q[2]];uxy=q[:2];wx,wz=clamp(3*abs(N[0])-1),clamp(3*abs(N[2])-1)
   col=mix(mix(sampled(7,uxz)[:3],sampled(7,uyz)[:3],wx),sampled(7,uxy)[:3],wz);col=[clamp(x*y) for x,y in zip(col,rec['tintLinear'])]
   rough=clamp(((sampled(8,uxz)[0]*(1-wx)+sampled(8,uyz)[0]*wx)*(1-wz)+sampled(8,uxy)[0]*wz)*rec['roughnessMultiplier'])
   def decode(uv):
    r,g=sampled(6,uv)[:2];x,y=2*r-1,2*g-1;return [x,y,math.sqrt(max(1-x*x-y*y,0))]
   a,bn,c=decode(uxz),decode(uyz),decode(uxy);nxz=[-a[0],a[2]*N[1],-a[1]];nyz=[bn[2]*N[0],-bn[0],-bn[1]];nxy=[-c[0],-c[1],c[2]*N[2]]
   W=norm(mix(mix(nxz,nyz,clamp(abs(N[0]))),nxy,clamp(abs(N[2]))));I=rec['normalIntensity'];nT=norm([dot(T,W)*I,dot(B,W)*I,dot(N,W)]);out=norm([T[i]*nT[0]+B[i]*nT[1]+N[i]*nT[2] for i in range(3)])
   comparisons=list(zip(vm.r['r5'][:3],col))+[(vm.r['r0'][3],rough)]+list(zip(actualNormal,out));delta=max(abs(a-b) for a,b in comparisons);maxerr=max(maxerr,delta);trials+=1
   if delta>1e-9:errors.append({'package':pkg,'trial':trial,'maxError':delta,'color':[vm.r['r5'][:3],col],'roughness':[vm.r['r0'][3],rough],'normal':[actualNormal,out]})
 report={'worldFormulaRandomTrials':trials,'foliageAndBenchRandomTrials':other_trials,'maximumFloat64Difference':maxerr,'errors':errors,'method':'Independent scalar/vector DXBC instruction subset execution from retained assembly versus contract formula, varied world positions/pre-view translations/geometric bases including nonunit interpolated frames and both handedness signs, and original instance parameters; analytical distinct-channel texture sampler. Does not establish browser GPU or complete original game visual equivalence.'}
 (D/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print({k:(len(v) if k=='errors' else v) for k,v in report.items()});print(errors[:1]);assert not errors
if __name__=='__main__':main()
