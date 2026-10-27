import sys, glob, os, collections, json
sys.path[:0]=['/work/cs','/work/weap1012/tools','/work/fx1018/editor/Python','/work/iostore']
from zen import Zen
import gameids
PK, OB = gameids.load()
from rebirth_fx.fxcore import Package
NULL=0xFFFFFFFFFFFFFFFF
rows=[]
kinds=collections.Counter(); comp=collections.Counter(); skel=collections.Counter(); errs=[]
for f in sorted(glob.glob('pkgs/*.uasset')):
    rel=os.path.basename(f)[:-7].replace('__','/')
    d=open(f,'rb').read(); z=Zen(d)
    imps=[OB.get(i & ~(3<<62), hex(i)) for i in z.imports if i!=NULL and (i>>62)==2]
    mi=[i for i,e in enumerate(z.exports) if e['global_import']!=NULL]
    props={}
    try:
        p=Package(d,rel)
        cls={i:c for i,(c,v,b) in p.exports.items()}
        mcls=[cls.get(i,'?') for i in mi]
        for i in mi:
            if i in p.exports:
                c,v,b=p.exports[i]
                props={k:str(x.value)[:100] for k,x in v.value.items()}
    except Exception as e:
        mcls=['ERR']; errs.append((rel,str(e)[:100]))
    k='/'.join(mcls)
    kinds[k]+=1
    c=[x for x in imps if 'Compression' in x]
    comp[(k, c[0].split('/')[-1] if c else None)]+=1
    sk=[x for x in imps if x.endswith('Skeleton')]
    skel[tuple(sk)]+=1
    other=[x for x in imps if 'Compression' not in x and not x.endswith('Skeleton')]
    rows.append(dict(path='/Game/'+rel, kind=k, comp=(c[0].split('/')[-1] if c else None), skel=sk, other=other, props=props, size=len(d)))
json.dump(rows, open('survey.json','w'), indent=1)
print(kinds); print(comp); print(skel); print(errs[:5])
oc=collections.Counter()
for r in rows:
    for o in r['other']: oc['/'.join(o.split('/')[:4]) if o.startswith('/Game') else o[:20]]+=1
print(oc.most_common(25))
