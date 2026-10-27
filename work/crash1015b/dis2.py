import struct, sys, re
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
PATH = '/data/uploads/FINAL FANTASY VII REBIRTH/End/Binaries/Win64/ff7rebirth_.exe'
d = open(PATH, 'rb').read()
pe = struct.unpack_from('<I', d, 0x3c)[0]
nsec = struct.unpack_from('<H', d, pe + 6)[0]
optsz = struct.unpack_from('<H', d, pe + 20)[0]
imgsize = struct.unpack_from('<I', d, pe + 24 + 56)[0]
secs = []
o = pe + 24 + optsz
for i in range(nsec):
    name = d[o:o+8].rstrip(b'\0').decode(errors='replace')
    vsz, va, rsz, rptr = struct.unpack_from('<IIII', d, o + 8)
    secs.append((name, va, vsz, rptr, rsz)); o += 40
def off(rva):
    for n, va, vsz, rp, rs in secs:
        if va <= rva < va + max(vsz, rs): return rva - va + rp
pdata = [s for s in secs if s[0] == '.pdata'][0]
funcs = []
for k in range(pdata[2] // 12):
    b, e, u = struct.unpack_from('<III', d, pdata[3] + 12 * k)
    if b: funcs.append((b, e))
funcs.sort()
import bisect
starts = [b for b, e in funcs]
def func_of(rva):
    i = bisect.bisect_right(starts, rva) - 1
    if i >= 0 and funcs[i][0] <= rva < funcs[i][1]: return funcs[i]
def string_at(rva):
    p = off(rva)
    if p is None: return None
    s = d[p:p+200]
    if len(s) > 4 and s[1] == 0 and s[3] == 0:
        try:
            t = s.decode('utf-16-le').split('\0')[0]
            if len(t) >= 3 and t.isprintable(): return 'L"' + t + '"'
        except Exception: pass
    t = s.split(b'\0')[0]
    if len(t) >= 3 and all(32 <= c < 127 for c in t): return '"' + t.decode() + '"'
    return None
md = Cs(CS_ARCH_X86, CS_MODE_64)
def dis(rva, mark=None, lo=None, hi=None):
    f = func_of(rva)
    if not f:
        print('no function for %x' % rva); return
    b, e = f
    print('function %x-%x (%d bytes)' % (b, e, e - b))
    code = d[off(b):off(b) + (e - b)]
    for ins in md.disasm(code, b):
        if lo is not None and not (lo <= ins.address <= hi): continue
        extra = ''
        m = re.search(r'rip ([+-]) 0x([0-9a-f]+)', ins.op_str)
        if m:
            t = ins.address + ins.size + (int(m.group(2), 16) if m.group(1) == '+' else -int(m.group(2), 16))
            s = string_at(t)
            extra = '   ; %x %s' % (t, s or '')
        flag = ' <<<' if mark is not None and ins.address == mark else ''
        print('%8x: %-8s %s%s%s' % (ins.address, ins.mnemonic, ins.op_str, extra, flag))
if __name__ == '__main__':
    rva = int(sys.argv[1], 16)
    lo = int(sys.argv[2], 16) if len(sys.argv) > 2 else None
    hi = int(sys.argv[3], 16) if len(sys.argv) > 3 else None
    dis(rva, rva, lo, hi)
