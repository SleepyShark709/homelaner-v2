"""Differentially validate the new material contracts against retained DXBC operations."""
from pathlib import Path
import importlib.util,math,json,random,hashlib,collections
spec=importlib.util.spec_from_file_location('vm',Path(__file__).with_name('validate-evidenced-shaders.py'));v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
ROOT=v.ROOT;D=v.D;clamp=v.clamp;dot=v.dot;norm=v.norm;cross=v.cross;mix=v.mix
def main():
 manifest=v.read(ROOT/'public/assets/world/material-manifest.json');bindings=v.read(D/'round2-bindings.json')['materials'];rng=random.Random(20261025);errors=[];counts=collections.Counter();rough_bins=collections.Counter();maxerr=0.
 for pkg,b in bindings.items():
  rec=manifest['materials'][pkg]['shaderRecovery'];assembly=Path(b['shader']['assemblyFile']).read_text().splitlines();assert hashlib.sha256(Path(b['shader']['assemblyFile']).with_suffix('.dxbc').read_bytes()).hexdigest()==b['shader']['sha256']
  literals={k:x['value'] for k,x in b.get('literalEvidence',{}).items()};cb=b['materialConstantBuffer']
  for trial in range(160):
   N=norm([rng.uniform(-1,1) for _ in range(3)]);T=norm(cross(N,[0,1,0]));hand=-1. if trial%3 else 1.
   if trial%2:
    N2=norm([rng.uniform(-1,1) for _ in range(3)]);T2=norm(cross(N2,[0,1,0]));N=mix(N,N2,.25);T=mix(T,T2,.25)
   B=[x*hand for x in cross(N,T)];V=norm([rng.uniform(-1,1) for _ in range(3)]);uv=[rng.uniform(-3,10),rng.uniform(-3,10)]
   def sample(reg,uv):
    a=math.sin(uv[0]*.7+uv[1]*1.3+reg*.37);b=math.cos(uv[0]*1.1-uv[1]*.9+reg*.17)
    if reg==15:return [.5+.2*a,.5+.2*b,.1,.7]
    result=[.5+.45*a,.5+.45*b,.4+.3*a,.7]
    if reg==18 and rec['kind']=='grass-parallax-macro' and trial%3:result[0]*=.15
    return result
   regs={'v0':T+[0.],'v1':N+[hand],'v2':uv+[0.,0.],'v3':uv+[0.,0.],'r0':B+[0.],'r2':[-x*473. for x in V]+[0.],
    'cb0[138]':[0.,0.,0.,1.],'cb0[143]':[0.,0.,0.,0.]}
   for i,p in enumerate(b['vectorRegisters']):regs[f'cb{cb}[{i}]']=p['value'][:]
   for p in b['scalarRegisters']:regs.setdefault(f"cb{cb}[{p['register']}]",[0.]*4)['xyzw'.index(p['component'])]=p['value'][0]
   vm=v.VM(regs,sample,dict(literals));kind=rec['kind']
   if kind=='concrete-mildew':
    first='sample_b_indexable(texture2d)(float,float,float,float) r4.xyz, v2.xyxx, t16.xyzw, s3, cb0[143].y';last='mov_sat r0.w, r0.w'
    a=sample(16,uv)[:3];w=sample(17,uv)[0]*rec['gradientAmount']+sample(18,uv)[0]*rec['mildewAmount'];expected=[clamp(x+w*(c-x)) for x,c in zip(a,rec['mildewColorLinear'])]
    for line in assembly[assembly.index(first):assembly.index(last)+1]:vm.run(line)
    pairs=list(zip(vm.r['r4'][:3],expected))+[(vm.r['r0'][3],clamp(sample(19,uv)[0]))]
   elif kind=='standard-pbr-evidenced':
    first='sample_b_indexable(texture2d)(float,float,float,float) r4.xyz, v2.xyxx, t14.xyzw, s3, cb0[143].y';last='mov_sat r0.w, r0.w'
    for line in assembly[assembly.index(first):assembly.index(last)+1]:vm.run(line)
    pairs=list(zip(vm.r['r4'][:3],[clamp(x) for x in sample(14,uv)[:3]]))+[(vm.r['r0'][3],clamp(sample(15,uv)[0]))]
   else:
    first='dp3 r0.w, -r2.xyzx, -r2.xyzx';last='mad_sat r0.w, r0.w, l(-3.500000), l(1.000000)'
    for line in assembly[assembly.index(first):assembly.index(last)+1]:
     # Original scalar macro blend coefficient and xyz power coefficient round to the same disassembly decimal.
     vm.literalMap['0.400000']=rec['macroColorScale'] if line.startswith('mad r1.w, r0.w,') else rec['grazingColorPower']
     vm.run(line)
    h=sample(14,[u*rec['heightUVScale'] for u in uv])[0]*rec['heightScale']+rec['heightBias'];uvp=[uv[0]+h*dot(T,V),uv[1]+h*dot(B,V)]
    macro=math.prod(sample(16,[u*scale for u in uv])[0]+bias for scale,bias in zip(rec['macroUVScales'],rec['macroOffsets']))
    C=[x*t*(macro*rec['macroColorScale']+rec['macroColorBias']) for x,t in zip(sample(17,uvp)[:3],rec['tintLinear'])]
    f=max(abs(1-max(dot(N,V),0)),rec['fresnelMinimum'])**rec['fresnelPower'];col=[clamp(x*rec['facingColorScale']+(max(x,0)**rec['grazingColorPower']-x*rec['facingColorScale'])*f) for x in C]
    rough=clamp(rec['roughnessBias']+rec['roughnessScale']*(sample(18,uvp)[0]*rec['glossScale'])*(macro*(1-rec['macroRoughnessContrast'])+rec['macroRoughnessContrast']))
    rough_bins['zero' if rough==0 else 'one' if rough==1 else 'interior']+=1
    xy=[2*x-1 for x in sample(15,uvp)[:2]];nt=norm(xy+[math.sqrt(max(1-dot(xy,xy),0))*rec['normalZScale']]);normal=norm([T[i]*nt[0]+B[i]*nt[1]+N[i]*nt[2] for i in range(3)])
    pairs=list(zip(vm.r['r2'][:3],col))+[(vm.r['r0'][3],rough)]+list(zip(vm.r['r0'][:3],normal))
   delta=max(abs(a-b) for a,b in pairs);maxerr=max(maxerr,delta);counts[kind]+=1
   if delta>1e-9:errors.append({'package':pkg,'trial':trial,'maxError':delta,'pairs':pairs})
 assert rough_bins['zero']>0 and rough_bins['interior']>50,rough_bins
 report={'trialsByKind':dict(counts),'grassRoughnessTestOutcomes':dict(rough_bins),'totalTrials':sum(counts.values()),'maxFloat64Difference':maxerr,'errors':errors,'method':'Independent original DXBC subset execution and contract expressions; native shader float32 literal values retained, varied UV/analytical distinct-channel texture samples, camera direction, nonunit interpolated TBN and original instance parameters. Not browser GPU/screenshot equivalence.'}
 (D/'round2-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print({k:len(x) if k=='errors' else x for k,x in report.items()});print(errors[:1]);assert not errors
if __name__=='__main__':main()
