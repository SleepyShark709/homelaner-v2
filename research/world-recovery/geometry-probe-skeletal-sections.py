import base64,struct,runpy
U=runpy.run_path(__file__.replace('geometry-probe-skeletal-sections.py','geometry-audit-vertex-colors.py'));g=U['g'];Reader=U['Reader']
for x in g.READ(g.EVID/'geometry-base-assets.json'):
    if not any(len(m['sourceSlotCandidates'])>1 for m in x['gltfMaterials']):continue
    d=g.READ(x['materialSlotEvidence']['decoded']);e=next(e for e in d['Exports'] if e['ObjectName']==x['sourcePackage'].rsplit('/',1)[1]);b=base64.b64decode(e['Extras']['$value']);r=Reader(b,x['materialSlotEvidence']['nativeSkeletalMaterialArray']['endOffsetInExtras'])
    n=r.read('i');bones=[r.read('iii') for _ in range(n)];assert all(0<=v[0]<len(d['NameMap']) and -1<=v[2]<n for v in bones)
    pn=r.read('i');assert pn==n;r.p+=pn*40
    mn=r.read('i');mp=[r.read('iii') for _ in range(mn)];assert mn==n
    cooked,lods=r.read('ii');assert cooked==1 and 0<lods<16
    flags=r.read('BB');out,inline=r.read('ii');required=r.read('i');r.p+=required*2
    sc=r.read('i');print(x['sourcePackage'],'bones',n,'sections',sc,'offset',r.p)
    for j in range(sc):
        start=r.p;flags=r.read('BB');material=r.read('h');base,tris,recompute=r.read('iii');mask=r.read('B');shadow,vertexbase=r.read('iI');cloth=r.read('i');assert cloth==0,(j,'cloth',cloth,r.p)
        bn=r.read('i');assert 0<=bn<=n,(j,'bonemap',bn,r.p);bonemap=[r.read('H') for _ in range(bn)];nv,influences=r.read('ii');clothidx=r.read('h');r.p+=20
        if not flags[1]&1:
            dup=r.read('i');r.p+=dup*4;dupi=r.read('i');r.p+=dupi*8
        disabled=r.read('i');assert recompute in (0,1) and shadow in (0,1) and disabled in (0,1),(j,start,flags,material,base,tris,recompute,mask,shadow,vertexbase,nv,influences,clothidx,disabled)
        print(j,material,base,tris,nv,flags,'end',r.p)
