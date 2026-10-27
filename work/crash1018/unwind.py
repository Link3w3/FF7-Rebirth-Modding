"""x64 stack walk of a minidump's crashing thread through ff7rebirth_.exe's unwind data (.pdata/.xdata)."""
import struct, sys, bisect
sys.path.insert(0, '/work/crash1018')
from mdmp import Dump

class PE:
    def __init__(self, path):
        self.d = d = open(path, 'rb').read()
        pe = struct.unpack_from('<I', d, 0x3c)[0]
        nsec = struct.unpack_from('<H', d, pe + 6)[0]
        opt = pe + 24
        self.image_base = struct.unpack_from('<Q', d, opt + 24)[0]
        ndirs = struct.unpack_from('<I', d, opt + 108)[0]
        dirs = [struct.unpack_from('<II', d, opt + 112 + 8 * i) for i in range(ndirs)]
        secoff = opt + struct.unpack_from('<H', d, pe + 20)[0]
        self.sections = []
        for i in range(nsec):
            o = secoff + 40 * i
            name = d[o:o + 8].rstrip(b'\0').decode()
            vsize, va, rsize, rptr = struct.unpack_from('<IIII', d, o + 8)
            self.sections.append((name, va, vsize, rptr, rsize))
        pva, psize = dirs[3]
        self.funcs = []
        for k in range(psize // 12):
            b, e, u = struct.unpack_from('<III', self.data_at(pva + 12 * k, 12), 0)
            self.funcs.append((b, e, u))
        self.funcs.sort()
        self.starts = [f[0] for f in self.funcs]

    def off(self, rva):
        for name, va, vsize, rptr, rsize in self.sections:
            if va <= rva < va + max(vsize, rsize):
                return rptr + rva - va
        raise KeyError(hex(rva))

    def data_at(self, rva, n):
        o = self.off(rva)
        return self.d[o:o + n]

    def func(self, rva):
        i = bisect.bisect_right(self.starts, rva) - 1
        if i >= 0 and self.funcs[i][0] <= rva < self.funcs[i][1]:
            return self.funcs[i]
        return None

    def unwind(self, rva, regs, read):
        """regs: dict with Rsp, Rip, and others; returns new regs (caller) or None."""
        f = self.func(rva)
        if f is None:   # a leaf: the return address is at rsp
            ret = struct.unpack('<Q', read(regs['Rsp'], 8))[0]
            r = dict(regs); r['Rip'] = ret; r['Rsp'] = regs['Rsp'] + 8
            return r
        begin, end, uinfo = f
        r = dict(regs)
        offset_in = rva - begin
        while True:
            hdr = self.data_at(uinfo, 4)
            ver_flags, prolog, ncodes, frame = hdr[0], hdr[1], hdr[2], hdr[3]
            flags = ver_flags >> 3
            freg, foff = frame & 15, frame >> 4
            codes = self.data_at(uinfo + 4, 2 * ncodes)
            REG = ['Rax', 'Rcx', 'Rdx', 'Rbx', 'Rsp', 'Rbp', 'Rsi', 'Rdi', 'R8', 'R9', 'R10', 'R11', 'R12', 'R13', 'R14', 'R15']
            if freg:
                # the frame register holds rsp + 16*foff after the prolog
                r['Rsp'] = r[REG[freg]] - 16 * foff
            i = 0
            while i < ncodes:
                code_off, op = codes[2 * i], codes[2 * i + 1]
                uop, info = op & 15, op >> 4
                applies = offset_in >= code_off or chained
                if uop == 0:      # UWOP_PUSH_NONVOL
                    if applies:
                        r[REG[info]] = struct.unpack('<Q', read(r['Rsp'], 8))[0]; r['Rsp'] += 8
                    i += 1
                elif uop == 1:    # UWOP_ALLOC_LARGE
                    if info == 0:
                        size = struct.unpack_from('<H', codes, 2 * (i + 1))[0] * 8; n = 2
                    else:
                        size = struct.unpack_from('<I', codes, 2 * (i + 1))[0]; n = 3
                    if applies: r['Rsp'] += size
                    i += n
                elif uop == 2:    # UWOP_ALLOC_SMALL
                    if applies: r['Rsp'] += info * 8 + 8
                    i += 1
                elif uop == 3:    # UWOP_SET_FPREG
                    i += 1
                elif uop == 4:    # UWOP_SAVE_NONVOL
                    o = struct.unpack_from('<H', codes, 2 * (i + 1))[0] * 8
                    if applies: r[REG[info]] = struct.unpack('<Q', read(r['Rsp'] + o, 8))[0]
                    i += 2
                elif uop == 5:    # UWOP_SAVE_NONVOL_FAR
                    o = struct.unpack_from('<I', codes, 2 * (i + 1))[0]
                    if applies: r[REG[info]] = struct.unpack('<Q', read(r['Rsp'] + o, 8))[0]
                    i += 3
                elif uop == 8:    # UWOP_SAVE_XMM128
                    i += 2
                elif uop == 9:    # UWOP_SAVE_XMM128_FAR
                    i += 3
                elif uop == 10:   # UWOP_PUSH_MACHFRAME
                    i += 1
                else:
                    i += 1
            if flags & 4:      # UNW_FLAG_CHAININFO
                o = 4 + 2 * ((ncodes + 1) & ~1)
                b2, e2, u2 = struct.unpack_from('<III', self.data_at(uinfo + o, 12), 0)
                uinfo = u2
                chained = True
                continue
            break
        ret = struct.unpack('<Q', read(r['Rsp'], 8))[0]
        r['Rip'] = ret; r['Rsp'] += 8
        return r

chained = False

def walk(dump_path, exe_path, depth=40):
    global chained
    dm = Dump(dump_path)
    pe = PE(exe_path)
    ex = dm.exception()
    regs = dm.context(ex['ctx'])
    base = [b for b, s, n in dm.modules if n.lower().endswith('ff7rebirth_.exe')][0]
    out = []
    for _ in range(depth):
        m, off = dm.module_of(regs['Rip'])
        out.append((m, off, regs['Rip']))
        if m != 'ff7rebirth_.exe':
            break
        chained = False
        try:
            regs = pe.unwind(off, regs, lambda a, n: dm.read(a, n) or b'\0' * n)
        except Exception as e:
            out.append(('unwind error', str(e), 0)); break
        if regs is None or regs['Rip'] == 0:
            break
    return out, pe

if __name__ == '__main__':
    frames, pe = walk(sys.argv[1], sys.argv[2])
    for m, off, rip in frames:
        f = pe.func(off) if m == 'ff7rebirth_.exe' else None
        print('%-16s +0x%-8x %s' % (m, off if isinstance(off, int) else 0, ('func 0x%x+0x%x' % (f[0], off - f[0])) if f else ''))
