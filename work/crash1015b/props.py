# The reflected properties of a native class, from its static property params in the exe (name -> offset).
import dis2, struct, sys
d = dis2.d
base = 0x140000000
def rva_of_file(o):
    for n, va, vsz, rp, rs in dis2.secs:
        if rp <= o < rp + rs: return o - rp + va
def find_all(b):
    out = []; i = d.find(b)
    while i >= 0:
        out.append(i); i = d.find(b, i + 1)
    return out
def params_for(name):
    res = []
    for o in find_all(name.encode() + b'\0'):
        if o > 0 and d[o-1] != 0: continue
        rva = rva_of_file(o)
        if rva is None: continue
        ptr = struct.pack('<Q', base + rva)
        for p in find_all(ptr):
            prva = rva_of_file(p)
            # FGenericPropertyParams: name, repnotify, flags(8), genflags(1)+pad, objflags(4), arraydim(4), offset(4)
            gen = d[p + 0x18]
            arr, off = struct.unpack_from('<ii', d, p + 0x20)
            res.append((prva, gen, arr, off))
    return res
if __name__ == '__main__':
    for n in sys.argv[1:]:
        for prva, gen, arr, off in params_for(n):
            print('%-40s params@%x gen %2d dim %d offset 0x%x' % (n, prva, gen, arr, off))
