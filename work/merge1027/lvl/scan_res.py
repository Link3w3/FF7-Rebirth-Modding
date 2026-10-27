import sys, os, glob, re, json, contextlib, io, collections
sys.path[:0]=['/work/sephatb/tools','/work/iostore','/work/cs','/work/tools','/work/evil1013/tools','/work/swap1012/tools','/work/vincentfix','/work/weap1012/tools']
import build_atb as B
pat=re.compile(r'(?:CharaSpec_)?(PC0000_\d\d_Cloud_[A-Za-z0-9]+|PC0010_\d\d_Sephiroth_[A-Za-z0-9]+|WE0000_\d\d_Cloud_[A-Za-z0-9]+|WE1021_\d\d_[A-Za-z0-9]+|SU2030_\d\d_Alexander_[A-Za-z0-9]+|PC0011_\d\d_Vincent_[A-Za-z]+)(_NoBattle|_Reserve)?(OA\d\d|SFV\d\d)?')
rawpat=re.compile(rb'(PC0000_\d\d_Cloud_|PC0010_\d\d_Sephiroth_|WE0000_\d\d_Cloud_|WE1021_\d\d_|SU2030_\d\d_Alexander_|PC0011_\d\d_Vincent_)')
files=sorted(glob.glob('/work/owncloud/gx/tab3/pkgs/*.uasset'))+['/work/owncloud/gx/van3/pkgs/DataObject__Resident__CharaSpec.uasset']
skip={'CharaSpec','CharaPopPack','CharaPopAsset','Effect2SoundTable','BattleDamageSource','BattleAbility'}
for f in files:
    name=os.path.basename(f)[:-7].split('__')[-1]
    if name in skip: continue
    d=open(f,'rb').read()
    if not rawpat.search(d): continue
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            t=B.Table(d)
    except Exception as e:
        print('BAD',name,str(e)[:60]); continue
    fl=[x[0][0] for x in t.fields]
    hits=collections.defaultdict(collections.Counter)
    for k in t.at:
        r=t.row(k)
        for fn in fl:
            stack=[t.get(r,fn)]
            while stack:
                x=stack.pop()
                if isinstance(x,(list,tuple)): stack.extend(x); continue
                if isinstance(x,str) and pat.fullmatch(x): hits[fn][x]+=1
    for fn,c in hits.items():
        print('%-30s %-30s %s'%(name,fn,' '.join('%s:%d'%kv for kv in sorted(c.items()))[:600]))
