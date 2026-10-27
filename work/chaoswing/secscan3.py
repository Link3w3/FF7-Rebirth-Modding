import sys, struct
sys.path[:0]=['/work/iostore','/work/cs']
from zen import Zen
def find_sections(ed, nb):
    out=[]
    for off in range(40,len(ed)-8):
        n=struct.unpack_from('<I',ed,off)[0]
        if not (1<=n<=nb): continue
        if off+4+2*n+8>len(ed): continue
        # previous u32 = cloth count 0, before that baseVertexIndex
        if struct.unpack_from('<I',ed,off-4)[0]!=0: continue
        bm=struct.unpack_from('<%dH'%n, ed, off+4)
        if max(bm)>=nb or len(set(bm))!=n: continue
        nv, mbi = struct.unpack_from('<II', ed, off+4+2*n)
        cidx = struct.unpack_from('<h', ed, off+12+2*n)[0]
        if not (0<nv<5_000_000 and 1<=mbi<=12 and cidx==-1): continue
        # walk back: bvi at off-8, then 4+4+1+4 back to ntri
        bvi=struct.unpack_from('<I',ed,off-8)[0]
        out.append(dict(off=off,n=n,bm=bm,nv=nv,mbi=mbi,bvi=bvi, pre=ed[off-36:off].hex(' ')))
    return out
if __name__=='__main__':
    p, nb, bonesfile = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    names=[l.split()[0] for l in open(bonesfile) if l.strip()]
    d=open(p,'rb').read(); z=Zen(d)
    for ei,e in enumerate(z.exports):
        ed=z.export_data(ei)
        secs=find_sections(ed, nb)
        if not secs: continue
        print('==', p.split('/')[-1], e['name'], len(ed), 'sections', len(secs))
        for s in secs:
            print('  off %(off)d bones %(n)d verts %(nv)d maxInfl %(mbi)d baseVert %(bvi)d'%s, '| pre', s['pre'][-60:])
            if len(sys.argv)>4: print('     ', ' '.join(names[b] for b in s['bm']))
