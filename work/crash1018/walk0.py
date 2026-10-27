import sys, struct
sys.path.insert(0, '/work/crash1018')
import unwind
from mdmp import Dump
def walk(dump_path, exe_path, depth=40):
    dm = Dump(dump_path)
    pe = unwind.PE(exe_path)
    ex = dm.exception()
    regs = dm.context(ex['ctx'])
    out = []
    if regs['Rip'] == 0:
        ret = struct.unpack('<Q', dm.read(regs['Rsp'], 8))[0]
        out.append(('null call', 0, 0))
        regs = dict(regs); regs['Rip'] = ret; regs['Rsp'] += 8
    for _ in range(depth):
        m, off = dm.module_of(regs['Rip'])
        out.append((m, off, regs['Rip']))
        if m != 'ff7rebirth_.exe':
            break
        unwind.chained = False
        try:
            regs = pe.unwind(off, regs, lambda a, n: dm.read(a, n) or b'\0' * n)
        except Exception as e:
            out.append(('unwind error', str(e), 0)); break
        if regs is None or regs['Rip'] == 0:
            break
    return out, pe, regs
if __name__ == '__main__':
    frames, pe, regs = walk(sys.argv[1], sys.argv[2])
    for m, off, rip in frames:
        f = pe.func(off) if m == 'ff7rebirth_.exe' else None
        print('%-16s +0x%-10x %s' % (m, off if isinstance(off, int) else 0, ('func 0x%x+0x%x' % (f[0], off - f[0])) if f else ''))
