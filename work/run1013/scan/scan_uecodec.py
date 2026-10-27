"""Find retail (memory-mapped) AnimSequences whose bone data uses one of UE's own codecs instead of ACL.
RebirthEngineV5 reads every memory-mapped animation as ACL, so these fail to load ("Invalid boolean ...").
Usage: python3 scan_uecodec.py <Content root> <subfolder> -> prints JSON lines."""
import os, struct, sys, json

def fstr(d, p):
    n = struct.unpack_from('<i', d, p)[0]; p += 4
    if n == 0: return '', p
    if n < 0: return d[p:p - 2 * n].decode('utf-16-le', 'replace').rstrip('\0'), p - 2 * n
    return d[p:p + n].decode('latin-1').rstrip('\0'), p + n

def summary(ua):
    p = 0
    tag, legacy = struct.unpack_from('<Ii', ua, p); p += 8
    if tag != 0x9E2A83C1: return None
    if legacy != -4: p += 4
    p += 8
    n = struct.unpack_from('<i', ua, p)[0]; p += 4 + 20 * n
    p += 4  # total header size
    _, p = fstr(ua, p)
    flags = struct.unpack_from('<I', ua, p)[0]; p += 4
    name_count, name_off = struct.unpack_from('<ii', ua, p); p += 8
    if not (flags & 0x80000000): _, p = fstr(ua, p)
    p += 8
    exp_count, exp_off, imp_count, imp_off = struct.unpack_from('<iiii', ua, p)
    names = []
    q = name_off
    for _ in range(name_count):
        s, q = fstr(ua, q); q += 4; names.append(s)
    imports = []
    q = imp_off
    for _ in range(imp_count):
        cp, cpn, cn, cnn, outer, on, onn = struct.unpack_from('<iiiiiii', ua, q); q += 28
        imports.append((names[cn], names[on]))
    exports = []
    q = exp_off
    for _ in range(exp_count):
        cls = struct.unpack_from('<i', ua, q)[0]
        name = names[struct.unpack_from('<i', ua, q + 16)[0]]
        size, off = struct.unpack_from('<qq', ua, q + 28)
        exports.append((cls, name, size, off)); q += 104
    return flags, imports, exports

ACL_TAGS = (0xac10ac10, 0xac11ac11)
root, sub = sys.argv[1], sys.argv[2]
for dirpath, _, files in os.walk(os.path.join(root, sub)):
    for f in sorted(files):
        if not f.endswith('.uasset'): continue
        path = os.path.join(dirpath, f)
        try:
            ua = open(path, 'rb').read()
            s = summary(ua)
            if not s: continue
            flags, imports, exports = s
            anims = [e for e in exports if e[0] < 0 and imports[-e[0] - 1][1] == 'AnimSequence']
            if not anims: continue
            ue = open(path[:-7] + '.uexp', 'rb').read()
            data = ua + ue
            for cls, name, size, off in anims:
                d = data[off:off + size]
                i = d.find(b'\x00\x00\x01\x00\x10\x00')
                if i < 4 or i > 4096: continue
                hdr = i - 4
                fcs, sz, idk, pad = struct.unpack_from('<IIHH', d, hdr)
                pm1 = hdr + 12 + pad
                packed1, num1 = struct.unpack_from('<Qi', d, pm1)
                if num1 <= 0: continue
                stream = pm1 + 48
                tag = struct.unpack_from('<I', d, stream + 8)[0]
                if tag in ACL_TAGS: continue
                rel = os.path.relpath(path, root).replace(os.sep, '/')
                print(json.dumps(dict(file=rel, export=name, stream_bytes=num1, first=list(struct.unpack_from('<4i', d, stream)))))
        except Exception as ex:
            print(json.dumps(dict(file=os.path.relpath(path, root), error=str(ex))))
