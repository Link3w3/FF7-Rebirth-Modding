import sys, struct
sys.path.insert(0,'/work/crash1018')
import unwind
from mdmp import Dump
EXE="/data/uploads/FINAL FANTASY VII REBIRTH/End/Binaries/Win64/ff7rebirth_.exe"
pe=unwind.PE(EXE)
raw=pe.d
IMG=0x140000000
def q(rva):
    return struct.unpack_from('<Q', pe.data_at(rva,8))[0]
def d32(rva):
    return struct.unpack_from('<I', pe.data_at(rva,4))[0]
def cname(vt_rva):
    try:
        col=q(vt_rva-8)-IMG
        td=d32(col+12)
        n=pe.data_at(td+16,200).split(b'\0')[0]
        return n.decode()
    except Exception:
        return None
def run(path):
    dm=Dump(path)
    ex=dm.exception()
    regs=dm.context(ex['ctx'])
    base=[b for b,s,n in dm.modules if n.lower().endswith('ff7rebirth_.exe')][0]
    # ranges in dump
    total=sum(s for a,s in getattr(dm,'mem',[])) if hasattr(dm,'mem') else None
    print('==', path, 'base', hex(base))
    seen=set()
    for i in range(40):
        m,off=dm.module_of(regs['Rip'])
        fn=pe.func(off) if m=='ff7rebirth_.exe' else None
        objs=[]
        for r in ('Rcx','Rdx','Rbx','Rsi','Rdi','R12','R13','R14','R15','Rbp'):
            v=regs.get(r,0)
            if v in seen or v < 0x10000: continue
            b=dm.read(v,16)
            if not b: continue
            vt=struct.unpack_from('<Q',b,0)[0]
            if base <= vt < base+0x10000000:
                nm=cname(vt-base)
                if nm:
                    seen.add(v); objs.append('%s=%x:%s'%(r,v,nm))
        print('  %2d %-16s +0x%-8x %-22s %s'%(i,m,off,('fn %x+%x'%(fn[0],off-fn[0])) if fn else '', ' '.join(objs)))
        if m!='ff7rebirth_.exe': break
        try:
            regs=pe.unwind(off, regs, lambda a,n: dm.read(a,n) or b'\0'*n)
        except Exception as e:
            print('unwind err',e); break
        if not regs or regs['Rip']==0: break
for p in sys.argv[1:]: run(p)
