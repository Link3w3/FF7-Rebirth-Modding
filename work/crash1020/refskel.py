import sys, struct
sys.path[:0] = ['/work/iostore', '/work/cs']
from iostore import Toc
from zen import Zen
def find_refskel(z, data, nb):
    names = z.names
    for p in range(0, len(data) - 8):
        if struct.unpack_from('<i', data, p)[0] != nb: continue
        ok = True
        for k in range(min(nb, 40)):
            ni, nn, par = struct.unpack_from('<IIi', data, p + 4 + 12 * k)
            if ni >= len(names) or par < -1 or par >= k + (1 if k == 0 else 0) and k > 0 and par >= k:
                ok = False; break
        if not ok: continue
        q = p + 4 + 12 * nb
        if struct.unpack_from('<i', data, q)[0] != nb: continue
        bones = []
        for k in range(nb):
            ni, nn, par = struct.unpack_from('<IIi', data, p + 4 + 12 * k)
            t = struct.unpack_from('<10f', data, q + 4 + 40 * k)
            bones.append((names[ni], par, t))
        return p, bones
    return None, None
t = Toc(sys.argv[1]); want = sys.argv[2]; nb = int(sys.argv[3])
for i in range(t.entries):
    if t.chunk_type(i) != 2 or not t.files.get(i, '').endswith('/' + want + '.uasset'): continue
    z = Zen(t.read(i))
    k = [n for n, e in enumerate(z.exports) if e['name'] == want][0]
    data = z.export_bytes(k)
    p, bones = find_refskel(z, data, nb)
    print('refskel at', p)
    # bounds: the 7 floats right before the Materials array? print the 64 bytes before
    for b in bones[:6] + [x for x in bones if x[0] in ('C_Head_a','L_Foot_a','R_Hand_a')]:
        print('  %-14s par %4d rot %s tr %s sc %s' % (b[0], b[1], [round(v,3) for v in b[2][0:4]], [round(v,3) for v in b[2][4:7]], [round(v,3) for v in b[2][7:10]]))
    big = [(b[0], [round(v,3) for v in b[2][7:10]]) for b in bones if any(abs(s-1) > 1e-3 for s in b[2][7:10])]
    print('  bones with scale != 1:', len(big), big[:12])
