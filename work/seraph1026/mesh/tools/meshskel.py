"""Reference skeleton (and what precedes it: ImportedBounds, Materials) of a cooked zen USkeletalMesh package.
    meshskel.py <mesh.uasset>"""
import struct, sys
sys.path[:0] = ['/work/cs', '/work/iostore']
from zen import Zen


def find_refskel(d, z, lo=None):
    nn = len(z.names)
    for p in range(lo or z.header_end + 4, len(d) - 24):
        n = struct.unpack_from('<i', d, p - 4)[0]
        if not 1 <= n <= 2000 or p + n * 12 + 4 + n * 40 > len(d):
            continue
        ni, num, parent = struct.unpack_from('<IIi', d, p)
        if parent != -1 or ni >= nn or num > 4:
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
        pose = [(struct.unpack_from('<4f', d, q + k * 40), struct.unpack_from('<3f', d, q + k * 40 + 16), struct.unpack_from('<3f', d, q + k * 40 + 28)) for k in range(n)]
        return p - 4, out, pose, q + n * 40
    raise ValueError('no reference skeleton found')


def main(path):
    d = open(path, 'rb').read()
    z = Zen(d)
    at, bones, pose, end = find_refskel(d, z)
    print(path.split('/')[-1], 'header_end', z.header_end, 'refskel at', at, '(%d after header)' % (at - z.header_end), 'bones', len(bones))
    for (name, parent), (q, t, s) in zip(bones, pose):
        print('  %-14s parent %2d  t=(%9.3f %9.3f %9.3f) q=(%6.3f %6.3f %6.3f %6.3f) s=(%5.2f %5.2f %5.2f)' % ((name, parent) + t + q + s))
    print('  bytes before the ref skeleton (64):', d[at - 128:at].hex())
    return d, z, at


if __name__ == '__main__':
    main(sys.argv[1])
