"""Flattens a scaled root bone in cooked skeletal mesh / skeleton packages (zen, UE 4.26).

A mesh imported with a scaled armature keeps the scale on its root bone's reference pose (Trans x1.4) and its vertices
are built around that scale. The game holds a player's root bone at its reference pose, so the whole character is drawn
at that scale. Flattening keeps every other bone as it is (their local transforms are the skeleton's) and moves the root's
scale into the geometry:
  * the root bone's reference scale becomes 1 (the mesh's RefSkeleton, the skeleton's ReferenceSkeleton);
  * every vertex position v -> R (R^-1 (v - t) / s) + t, with R, t, s the root's rotation, translation and scale (each
    vertex keeps where it sits relative to its bones);
  * the mesh's imported bounds and its materials' UV densities (world size per UV unit) scale the same way.
Sizes do not change: the package is patched in place.

    flatroot.py <zen package> [out]
"""
import struct, sys
import numpy as np
sys.path[:0] = ['/work/iostore', '/work/cs']
from zen import Zen

MATERIAL_ENTRY = 40      # FSkeletalMaterial as this game cooks it: interface, slot name, 4 bytes, UV channel info


def _find_refskel(names, d, nb=None):
    """(offset of the bone info array, bone count) of a FReferenceSkeleton: int32 count, (FName, parent) x count, then
    int32 count, FTransform x count."""
    counts = [nb] if nb else None
    for p in range(0, min(len(d), 1 << 20) - 16):
        n = struct.unpack_from('<i', d, p)[0]
        if n < 2 or n > 65535 or (counts and n not in counts):
            continue
        q = p + 4 + 12 * n
        if q + 4 + 40 * n > len(d) or struct.unpack_from('<i', d, q)[0] != n:
            continue
        ok = True
        for k in range(n):
            ni, nn, par = struct.unpack_from('<IIi', d, p + 4 + 12 * k)
            if ni >= len(names) or not (-1 <= par < k) or (k == 0) != (par == -1):
                ok = False
                break
        if ok:
            return p, n
    return None, None


def _root(d, p, n):
    q = p + 4 + 12 * n + 4
    rot = np.array(struct.unpack_from('<4f', d, q), np.float64)
    tr = np.array(struct.unpack_from('<3f', d, q + 16), np.float64)
    sc = np.array(struct.unpack_from('<3f', d, q + 28), np.float64)
    return q, rot, tr, sc


def flatten_export(d, names, kind):
    """kind 'mesh' or 'skeleton' -> (patched bytes, report)."""
    d = bytearray(d)
    p, n = _find_refskel(names, d)
    if p is None:
        raise ValueError('no reference skeleton found')
    q, rot, tr, sc = _root(d, p, n)
    s = float(sc[0])
    if not np.allclose(sc, s, rtol=1e-5):
        raise ValueError('the root scale is not uniform: %s' % sc)
    report = dict(bones=n, root_name=names[struct.unpack_from('<I', d, p + 4)[0]], root_scale=s, root_translation=tr.tolist())
    if abs(s - 1.0) < 1e-6:
        report['changed'] = False
        return bytes(d), report
    struct.pack_into('<3f', d, q + 28, 1.0, 1.0, 1.0)
    report['changed'] = True
    if kind != 'mesh':
        return bytes(d), report

    # vertex positions: every FPositionVertexBuffer (stride 12, count, element size 12, count, data)
    bufs = []
    for o in range(0, len(d) - 16):
        a, cnt, b, m = struct.unpack_from('<iiii', d, o)
        if a == 12 and b == 12 and cnt == m and 3 <= cnt <= 4000000 and o + 16 + 12 * cnt <= len(d):
            bufs.append((o, cnt))
    if not bufs:
        raise ValueError('no vertex positions found')
    rinv = _matrix(rot).T
    rmat = _matrix(rot)
    for o, cnt in bufs:
        v = np.frombuffer(bytes(d[o + 16:o + 16 + 12 * cnt]), '<f4').reshape(-1, 3).astype(np.float64)
        v = ((v - tr) @ rinv.T) / s @ rmat.T + tr
        d[o + 16:o + 16 + 12 * cnt] = v.astype('<f4').tobytes()
    report['position_buffers'] = [(o, cnt) for o, cnt in bufs]
    # materials (right before the reference skeleton) and the imported bounds (right before them)
    mat = None
    for c in range(1, 256):
        o = p - 4 - MATERIAL_ENTRY * c
        if o >= 28 and struct.unpack_from('<i', d, o)[0] == c:
            mat = (o, c)
            break
    if mat is None:
        raise ValueError('the materials array was not found before the reference skeleton')
    o, c = mat
    for k in range(c):
        e = o + 4 + MATERIAL_ENTRY * k
        dens = struct.unpack_from('<4f', d, e + 24)
        struct.pack_into('<4f', d, e + 24, *[x / s for x in dens])
    b = o - 28
    origin = np.array(struct.unpack_from('<3f', d, b), np.float64)
    ext = np.array(struct.unpack_from('<3f', d, b + 12), np.float64)
    rad = struct.unpack_from('<f', d, b + 24)[0]
    origin2 = ((origin - tr) @ rinv.T) / s @ rmat.T + tr
    struct.pack_into('<7f', d, b, *origin2, *(ext / s), rad / s)
    report.update(materials=c, bounds_before=[origin.round(3).tolist(), ext.round(3).tolist(), round(rad, 3)],
                  bounds_after=[origin2.round(3).tolist(), (ext / s).round(3).tolist(), round(rad / s, 3)])
    return bytes(d), report


def _matrix(qv):
    x, y, z, w = qv
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def flatten_package(data, export_name, kind):
    z = Zen(data)
    k = [i for i, e in enumerate(z.exports) if e['name'] == export_name]
    if len(k) != 1:
        raise ValueError('export %s not found' % export_name)
    start, size = z.bundle_positions()[k[0]]
    new, report = flatten_export(data[start:start + size], z.names, kind)
    assert len(new) == size
    return data[:start] + new + data[start + size:], report


if __name__ == '__main__':
    data = open(sys.argv[1], 'rb').read()
    z = Zen(data)
    name = z.mapped(z.name_mapped).rsplit('/', 1)[-1]
    out, rep = flatten_package(data, name, 'skeleton' if name.endswith('_Skeleton') else 'mesh')
    print(rep)
    if len(sys.argv) > 2:
        open(sys.argv[2], 'wb').write(out)
