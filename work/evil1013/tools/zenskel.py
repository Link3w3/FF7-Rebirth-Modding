"""Bones of a cooked (Zen) USkeleton package: finds FReferenceSkeleton (RawRefBoneInfo: FName + parent, then
RawRefBonePose) after the package header. Returns [(name, parent, (tx, ty, tz), (qx, qy, qz, qw))]."""
import struct, sys
sys.path.insert(0, '/work/cs')
from zen import Zen

def bones(d):
    z = Zen(d)
    nn = len(z.names)
    for p in range(z.header_end + 4, len(d) - 24):
        n = struct.unpack_from('<i', d, p - 4)[0]
        if not 20 <= n <= 5000 or p + n * 12 + 4 + n * 40 > len(d):
            continue
        ni, num, parent = struct.unpack_from('<IIi', d, p)
        if parent != -1 or ni >= nn or num != 0:
            continue
        out = []; ok = True
        for k in range(n):
            ni, num, parent = struct.unpack_from('<IIi', d, p + k * 12)
            if ni >= nn or num > 100 or (k and not 0 <= parent < k):
                ok = False; break
            out.append((z.names[ni] if num == 0 else '%s_%d' % (z.names[ni], num - 1), parent))
        q = p + n * 12
        if not ok or struct.unpack_from('<i', d, q)[0] != n:
            continue
        q += 4
        return [(out[k][0], out[k][1], struct.unpack_from('<3f', d, q + k * 40 + 16), struct.unpack_from('<4f', d, q + k * 40)) for k in range(n)]
    raise ValueError('no reference skeleton found')
