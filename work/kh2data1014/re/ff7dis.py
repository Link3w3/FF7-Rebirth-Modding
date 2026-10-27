import sys, struct
sys.path.insert(0, '/work/grab1014/refl')
from pe import PE
import capstone
EXE = '/data/uploads/FINAL FANTASY VII REBIRTH/End/Binaries/Win64/ff7rebirth_.exe'
p = PE(EXE)
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
md.detail = False
def dis(va, n=80, stop_ret=True):
    off = p.off(va)
    code = p.data[off:off + n * 15]
    out = []
    for ins in md.disasm(code, va):
        out.append(ins)
        if len(out) >= n: break
        if stop_ret and ins.mnemonic in ('ret', 'int3') and len(out) > 3: break
    return out
if __name__ == '__main__':
    va = int(sys.argv[1], 16)
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 80
    for ins in dis(va, n, stop_ret=len(sys.argv) < 4):
        print('%x  %-8s %s' % (ins.address, ins.mnemonic, ins.op_str))
