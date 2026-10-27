import sys, os, glob, re, json, contextlib, io, collections
sys.path[:0]=['/work/sephatb/tools','/work/iostore','/work/cs','/work/tools','/work/evil1013/tools','/work/swap1012/tools','/work/vincentfix','/work/weap1012/tools']
import build_atb as B
pat=re.compile(r'(?:CharaSpec_)?(PC0000_\d\d_Cloud_[A-Za-z0-9]+|PC0010_\d\d_Sephiroth_[A-Za-z0-9]+|WE0000_\d\d_Cloud_[A-Za-z0-9]+|WE1021_\d\d_[A-Za-z0-9]+|SU2030_\d\d_Alexander_[A-Za-z0-9]+|PC0011_\d\d_Vincent_[A-Za-z]+)')
rawpat=re.compile(rb'(PC0000_\d\d_Cloud_[A-Za-z0-9_]+|PC0010_\d\d_Sephiroth_[A-Za-z0-9_]+|WE0000_\d\d_Cloud_[A-Za-z0-9_]+|WE1021_\d\d_[A-Za-z0-9_]+|SU2030_\d\d_Alexander_[A-Za-z0-9_]+|PC0011_\d\d_Vincent_[A-Za-z_]+)')
out=collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(set)))
bad=[]
for f in sorted(glob.glob('c*/pkgs/*.uasset')):
    path='/Game/'+os.path.basename(f)[:-7].replace('__','/')
    d=open(f,'rb').read()
    if not rawpat.search(d): continue
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            t=B.Table(d)
    except Exception as e:
        bad.append((path,str(e)[:80], sorted(set(m.decode() for m in rawpat.findall(d)))[:10])); continue
    fl=[x[0][0] for x in t.fields]
    for k in t.at:
        r=t.row(k)
        for fn in fl:
            v=t.get(r,fn)
            stack=[v]
            while stack:
                x=stack.pop()
                if isinstance(x,(list,tuple)): stack.extend(x); continue
                if isinstance(x,dict): stack.extend(x.values()); continue
                if isinstance(x,str):
                    m=pat.fullmatch(x)
                    if m: out[path][fn][x].add(k)
    if path not in out:
        bad.append((path,'in bytes only', sorted(set(m.decode() for m in rawpat.findall(d)))[:10]))
res={p:{fn:{v:sorted(rows) for v,rows in vs.items()} for fn,vs in fs.items()} for p,fs in out.items()}
json.dump(dict(hits=res,bad=bad), open('scan.json','w'), indent=1)
for p,fs in sorted(res.items()):
    for fn,vs in fs.items():
        print('%-60s %-26s %s'%(p.replace('/Game/DataObject/Field/',''),fn,' '.join('%s(%d)'%(v,len(r)) for v,r in sorted(vs.items()))[:700]))
print('--- not decoded / bytes only:')
for b in bad: print(b)
