"""Prints a cooked SkeletalMesh's materials list (FSkeletalMaterial: import index, slot FName, flag, [imported FName], UV data).  meshmats.py <pkg>..."""
import struct, sys
sys.path.insert(0, '/work/aura1014/tools')
import zx
for f in sys.argv[1:]:
    z = zx.load(f)
    print('==', f.split('__')[-1], 'names', len(z.names), 'imports', len(z.imports), 'exports', len(z.exports))
    for i, e in enumerate(z.exports):
        print('  export', i, e['name'], 'size', e['serial_size'])
    # find the mesh export (the biggest)
    big = max(z.order, key=lambda i: z.exports[i]['serial_size'])
    b = z.exp(big)
    nn = len(z.names)
    ni = len(z.imports)
    best = []
    # scan for: count N (1..64), then N elements starting with negative import index and an FName with valid index
    for o in range(0, min(len(b), 4000000) - 8, 1):
        n = struct.unpack_from('<i', b, o)[0]
        if not (2 <= n <= 40):
            continue
        p = o + 4
        ok = True
        elems = []
        for k in range(n):
            if p + 12 > len(b):
                ok = False; break
            imp, nidx, nnum = struct.unpack_from('<iii', b, p)
            if not (-ni <= imp < 0 or imp == 0) or not (0 <= nidx < nn) or not (0 <= nnum < 50):
                ok = False; break
            p += 12
            flag = struct.unpack_from('<I', b, p)[0]
            if flag not in (0, 1):
                ok = False; break
            p += 4
            imported = None
            if flag == 1:
                a, c = struct.unpack_from('<ii', b, p); p += 8
                if not (0 <= a < nn):
                    ok = False; break
                imported = z.names[a]
            init, over = struct.unpack_from('<II', b, p)
            if init not in (0, 1) or over not in (0, 1):
                ok = False; break
            dens = struct.unpack_from('<4f', b, p + 8)
            p += 8 + 16
            elems.append((imp, z.names[nidx] + ('' if nnum == 0 else '_%d' % (nnum - 1)), flag, imported, init, over, dens))
        if ok:
            best.append((o, elems))
    for o, elems in best:
        print('  materials at +%d (%d):' % (o, len(elems)))
        for k, el in enumerate(elems):
            print('    %2d imp %d slot %-28s flag %d imported %s uv %d/%d %s' % (k, el[0], el[1], el[2], el[3], el[4], el[5], ' '.join('%.1f' % x for x in el[6])))
