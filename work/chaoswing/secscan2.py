import sys, struct
sys.path[:0]=['/work/iostore','/work/cs']
from zen import Zen
def bones_of(path):
    return [l.split()[0] for l in open(path) if l.strip()]
def scan(path, nbones):
    d=open(path,'rb').read()
    z=Zen(d)
    best=None
    for ei,e in enumerate(z.exports):
        x=z.export_data(ei)
        if best is None or len(x)>len(best[1]): best=(e['name'],x)
    en, ed = best
    out=[]
    for off in range(0, len(ed)-60):
        mat, base, ntri, rt = struct.unpack_from('<HIII', ed, off+2)
        if mat>=64 or rt not in (0,1) or ntri==0 or ntri>5_000_000: continue
        mask = ed[off+16]
        cs, bvi, ncloth, nmap = struct.unpack_from('<IIII', ed, off+17)
        if cs not in (0,1) or ncloth!=0 or not (1<=nmap<=nbones): continue
        p=off+33
        if p+2*nmap+10>len(ed): continue
        bm=struct.unpack_from('<%dH'%nmap, ed, p); p+=2*nmap
        if max(bm)>=nbones: continue
        nv, mbi, cidx = struct.unpack_from('<Iih', ed, p)
        if not (0<nv<10_000_000 and 1<=mbi<=12 and cidx==-1): continue
        out.append(dict(off=off, mat=mat, base=base, ntri=ntri, bvi=bvi, nmap=nmap, nv=nv, mbi=mbi, bm=bm))
    return en, len(ed), out
if __name__=='__main__':
    p, nb, bonesfile = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    names=bones_of(bonesfile)
    en,n,out=scan(p,nb)
    print('==', p.split('/')[-1], en, n, 'sections', len(out))
    for s in out:
        hi=[names[b] for b in s['bm'] if b>=564]
        print('  off %(off)d mat %(mat)d tris %(ntri)d baseVert %(bvi)d verts %(nv)d maxInfl %(mbi)d bones %(nmap)d'%s, 'max', max(s['bm']))
