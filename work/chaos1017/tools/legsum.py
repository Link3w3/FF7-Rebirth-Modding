"""Legacy (.uasset) package summary: counts and the name map."""
import struct, sys

def fstring(d, p):
    n = struct.unpack_from('<i', d, p)[0]; p += 4
    if n == 0: return '', p
    if n < 0:
        s = d[p:p - n * 2].decode('utf-16-le', 'replace').rstrip('\x00'); return s, p - n * 2
    s = d[p:p + n].decode('latin-1').rstrip('\x00'); return s, p + n

def summary(d):
    p = 0
    tag, legacy = struct.unpack_from('<Ii', d, p); p += 8
    assert tag == 0x9E2A83C1, hex(tag)
    if legacy != -4: p += 4
    ue4, lic = struct.unpack_from('<ii', d, p); p += 8
    n = struct.unpack_from('<i', d, p)[0]; p += 4
    customs = []
    for k in range(n):
        g = d[p:p + 16]; v = struct.unpack_from('<i', d, p + 16)[0]; customs.append((g.hex(), v)); p += 20
    total = struct.unpack_from('<i', d, p)[0]; p += 4
    folder, p = fstring(d, p)
    flags = struct.unpack_from('<I', d, p)[0]; p += 4
    name_count, name_off = struct.unpack_from('<ii', d, p); p += 8
    filter_editor = bool(flags & 0x80000000)
    loc = ''
    if ue4 >= 516 and not filter_editor:
        loc, p = fstring(d, p)
    if ue4 >= 459:
        p += 8
    exp_count, exp_off, imp_count, imp_off, dep_off = struct.unpack_from('<iiiii', d, p); p += 20
    names = []
    q = name_off
    for k in range(name_count):
        s, q = fstring(d, q)
        q += 4  # hashes (ue4 >= 504)
        names.append(s)
    return dict(ue4=ue4, licensee=lic, customs=len(customs), total=total, folder=folder, flags=hex(flags), names=name_count,
                exports=exp_count, imports=imp_count, cooked=filter_editor), names

if __name__ == '__main__':
    for f in sys.argv[1:]:
        d = open(f, 'rb').read()
        s, names = summary(d)
        print(f.rsplit('/', 1)[1], s)

def imports_of(d):
    """(class package, class name, outer index, object name) of each import (UE4.26 editor package)."""
    s, names = summary(d)
    p = 0
    tag, legacy = struct.unpack_from('<Ii', d, p); p += 8
    if legacy != -4: p += 4
    ue4, lic = struct.unpack_from('<ii', d, p); p += 8
    n = struct.unpack_from('<i', d, p)[0]; p += 4 + n * 20
    p += 4
    folder, p = fstring(d, p)
    flags = struct.unpack_from('<I', d, p)[0]; p += 4
    p += 8
    if not (flags & 0x80000000):
        loc, p = fstring(d, p)
    p += 8
    exp_count, exp_off, imp_count, imp_off = struct.unpack_from('<iiii', d, p)
    out = []
    q = imp_off
    def nm(i, num):
        return names[i] + ('_%d' % (num - 1) if num else '')
    for k in range(imp_count):
        cp, cpn, cn, cnn, outer, on, onn = struct.unpack_from('<iiiiiii', d, q)
        q += 28
        q += 4  # bImportOptional? (4.26: no) -> check below
        out.append((nm(cp, cpn), nm(cn, cnn), outer, nm(on, onn)))
    return out, imp_off, exp_off
