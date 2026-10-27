import sys, struct
sys.path[:0]=['/work/iostore','/work/cs']
from zen import Zen
def scan(path, nbones):
    d=open(path,'rb').read()
    z=Zen(d)
    ed=None
    for ei,e in enumerate(z.exports):
        x=z.export_data(ei)
        if ed is None or len(x)>len(ed): ed=x; en=e['name']
    out=[]
    for off in range(0, len(ed)-40):
        mat, base, ntri, rt, cs, bvi, ncloth, nmap = struct.unpack_from('<HIIIIIII', ed, off)
        if not (mat < 64 and rt in (0,1) and cs in (0,1) and ncloth==0 and 1<=nmap<=nbones and ntri>0 and ntri<5_000_000): continue
        if off+30+2*nmap+8 > len(ed): continue
        bm=struct.unpack_from('<%dH'%nmap, ed, off+30)
        if max(bm)>=nbones: continue
        nv, mbi = struct.unpack_from('<Ii', ed, off+30+2*nmap)
        if not (0<nv<10_000_000 and 1<=mbi<=12): continue
        out.append((off, mat, base, ntri, bvi, nmap, nv, mbi, max(bm)))
    return en, len(ed), out
for p, nb in [(a, int(b)) for a,b in zip(sys.argv[1::2], sys.argv[2::2])]:
    en, n, out = scan(p, nb)
    print('==', p.split('/')[-1], en, n, 'sections found', len(out))
    for o in out: print('   off %d mat %d baseIdx %d tris %d baseVert %d bones %d verts %d maxInfl %d maxBone %d'%o)
