import sys, struct
sys.path.insert(0, '/work/cs')
from legacy import Legacy, R
def load(base):
    ua = open(base + '.uasset', 'rb').read(); ue = open(base + '.uexp', 'rb').read()
    return Legacy(ua, ue)
def props(L, r, end, ind=''):
    out = []
    while True:
        name = L.n((r.i32(), r.i32()))
        if name == 'None': break
        typ = L.n((r.i32(), r.i32())); size = r.i32(); aidx = r.i32()
        extra = None
        if typ == 'StructProperty': extra = L.n((r.i32(), r.i32())); r.guid()
        elif typ == 'BoolProperty': extra = r.d[r.p]; r.p += 1
        elif typ in ('ByteProperty', 'EnumProperty', 'ArrayProperty', 'SetProperty'): extra = L.n((r.i32(), r.i32()))
        elif typ == 'MapProperty': extra = (L.n((r.i32(), r.i32())), L.n((r.i32(), r.i32())))
        hg = r.d[r.p]; r.p += 1
        if hg: r.guid()
        vstart = r.p
        print(ind, name, typ, extra, 'size', size, 'at', vstart)
        r.p = vstart + size
    return r.p
base = sys.argv[1]
L = load(base)
e = L.exports[0]
d = L.d; off = e['offset']; size = e['size']
r = R(d, off)
p = props(L, r, off + size)
print('after props', p - off, 'of', size)
rest = d[p:off+size]
print(rest[:256].hex(' '))
