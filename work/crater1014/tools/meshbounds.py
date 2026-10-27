"""Finds a cooked StaticMesh's position vertex buffers (stride 12) and prints the bounds of each.  meshbounds.py <pkg>..."""
import struct, sys
sys.path.insert(0, '/work/aura1014/tools')
import zx
for f in sys.argv[1:]:
    z = zx.load(f)
    for i in z.order:
        if z.exports[i]['name'].startswith('BodySetup'):
            continue
        b = z.exp(i)
        o = 0
        found = 0
        while True:
            o = b.find(b'\x0c\x00\x00\x00', o)
            if o < 0 or o + 16 > len(b):
                break
            n = struct.unpack_from('<I', b, o + 4)[0]
            if 3 <= n < 200000 and b[o + 8:o + 12] == b'\x0c\x00\x00\x00' and struct.unpack_from('<I', b, o + 12)[0] == n and o + 16 + 12 * n <= len(b):
                pts = [struct.unpack_from('<3f', b, o + 16 + 12 * k) for k in range(n)]
                mn = [min(p[a] for p in pts) for a in range(3)]
                mx = [max(p[a] for p in pts) for a in range(3)]
                print('%s: %d verts  min (%.1f, %.1f, %.1f)  max (%.1f, %.1f, %.1f)  size (%.1f x %.1f x %.1f)' % (
                    f.split('__')[-1], n, *mn, *mx, mx[0] - mn[0], mx[1] - mn[1], mx[2] - mn[2]))
                found += 1
                o += 16 + 12 * n
            else:
                o += 1
        if not found:
            print(f.split('__')[-1], 'no position buffer found (export %d, %d bytes)' % (i, len(b)))
