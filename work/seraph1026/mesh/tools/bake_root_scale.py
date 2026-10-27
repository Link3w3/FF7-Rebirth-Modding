"""A cooked (zen, UE 4.26) skeletal mesh, skeleton or physics asset of a model whose root bone carries a uniform scale S
(a Blender FBX: the armature at 100x, every bone 1/100 as far apart): the scale baked out, in place, the package size
the same. Mesh / skeleton: the reference skeleton's root scale made 1 and every other bone's translation made S times as
long (each bone stays where it was in the model: the mesh in its bind pose is the same; animated, the game's root of
scale 1 no longer shrinks it to 1/S). Physics asset: its bodies' shapes (capsules, spheres, boxes) S times as large
(they were made in the bones' 1/S space). Sockets are not touched (made for the game's bones of scale 1, as the game's
own, they are right once the root is 1).
    bake_root_scale.py mesh|skeleton <in> <out>
    bake_root_scale.py physics <in> <out> <S>"""
import math, struct, sys
sys.path[:0] = ['/work/seraph1026/mesh/tools', '/work/cs', '/work/iostore']
from zen import Zen
import meshskel
import tagdump


def qmul(a, b):
    ax, ay, az, aw = a; bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz)


def qrot(q, v):
    x, y, z, w = q
    u = (x, y, z)
    def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
    t = tuple(2 * c for c in cross(u, v))
    c2 = cross(u, t)
    return tuple(v[i] + w * t[i] + c2[i] for i in range(3))


def component_space(bones, pose):
    """UE FTransform composition (child * parent): [(rotation, translation, scale)] in component space."""
    out = []
    for (name, parent), (q, t, s) in zip(bones, pose):
        if parent < 0:
            out.append((q, t, s))
            continue
        pq, pt, ps = out[parent]
        st = tuple(t[i] * ps[i] for i in range(3))
        r = qrot(pq, st)
        out.append((qmul(pq, q), tuple(pt[i] + r[i] for i in range(3)), tuple(s[i] * ps[i] for i in range(3))))
    return out


def bake_skeleton(d):
    z = Zen(d)
    at, bones, pose, end = meshskel.find_refskel(d, z)
    n = len(bones)
    pose_at = at + 4 + n * 12 + 4
    q0, t0, s0 = pose[0]
    S = s0[0]
    assert abs(s0[1] - S) < 1e-4 * S and abs(s0[2] - S) < 1e-4 * S, 'the root scale is not uniform: %s' % (s0,)
    assert abs(S - 1.0) > 1e-3, 'the root has no scale to bake (%g)' % S
    before = component_space(bones, pose)
    out = bytearray(d)
    struct.pack_into('<3f', out, pose_at + 28, 1.0, 1.0, 1.0)
    for k in range(1, n):
        q, t, s = pose[k]
        struct.pack_into('<3f', out, pose_at + k * 40 + 16, *(c * S for c in t))
    out = bytes(out)
    at2, bones2, pose2, end2 = meshskel.find_refskel(out, Zen(out))
    assert (at2, bones2, end2) == (at, bones, end)
    after = component_space(bones2, pose2)
    for (name, _), b, a in zip(bones, before, after):
        assert max(abs(b[1][i] - a[1][i]) for i in range(3)) < 1e-3 * max(1.0, max(abs(c) for c in b[1])), (name, b[1], a[1])
        assert max(abs(b[0][i] - a[0][i]) for i in range(4)) < 1e-6, (name, b[0], a[0])
        assert max(abs(c - 1.0) for c in a[2]) < 1e-5, (name, a[2])
    print('root scale %g baked out of %d bones:' % (S, n))
    for (name, parent), (q, t, s), (cq, ct, cs) in zip(bones2, pose2, after):
        print('  %-12s t=(%9.3f %9.3f %9.3f) s=(%g %g %g)  component position (%9.3f %9.3f %9.3f)' % ((name,) + t + s + ct))
    return out, S


SHAPES = {'SphylElems': ('Center', 'Radius', 'Length'), 'SphereElems': ('Center', 'Radius'),
          'BoxElems': ('Center', 'X', 'Y', 'Z'), 'TaperedCapsuleElems': ('Center', 'Radius0', 'Radius1', 'Length')}


def bake_physics(d, S):
    z = Zen(d)
    out = bytearray(d)
    done = []
    for idx, e in enumerate(z.exports):
        start, size = z.bundle_positions()[idx]
        x = d[start:start + size]
        t = tagdump.T(z.names, x, z.imports)
        o = 0
        while True:
            p = t.tag(o)
            if p['name'] == 'None':
                break
            if p['name'] == 'AggGeom':
                u = p['value']
                while True:
                    a = t.tag(u)
                    if a['name'] == 'None':
                        break
                    if a['name'] in SHAPES:
                        count = struct.unpack_from('<i', x, a['value'])[0]
                        if count:
                            inner = t.tag(a['value'] + 4)
                            r = inner['value']
                            for k in range(count):
                                while True:
                                    f = t.tag(r)
                                    if f['name'] == 'None':
                                        r = f['end']
                                        break
                                    if f['name'] in SHAPES[a['name']]:
                                        at = start + f['value']
                                        if f['type'] == 'StructProperty':
                                            v = struct.unpack_from('<3f', d, at)
                                            struct.pack_into('<3f', out, at, *(c * S for c in v))
                                        else:
                                            v = struct.unpack_from('<f', d, at)[0]
                                            struct.pack_into('<f', out, at, v * S)
                                        done.append('%s %s[%d].%s %s -> x%g' % (e['name'], a['name'], k, f['name'], v, S))
                                    r = f['end']
                    elif a['name'] == 'ConvexElems':
                        assert struct.unpack_from('<i', x, a['value'])[0] == 0, 'convex shapes: not handled'
                    u = a['end']
            o = p['end']
    for line in done:
        print(' ', line)
    assert done, 'no shapes found'
    return bytes(out)


def main():
    kind, src, dst = sys.argv[1:4]
    d = open(src, 'rb').read()
    if kind in ('mesh', 'skeleton'):
        out, S = bake_skeleton(d)
    elif kind == 'physics':
        out = bake_physics(d, float(sys.argv[4]))
    else:
        raise SystemExit(__doc__)
    assert len(out) == len(d)
    open(dst, 'wb').write(out)
    print('%s -> %s (%d bytes, %d changed)' % (src.split('/')[-1], dst, len(out), sum(1 for a, b in zip(d, out) if a != b)))


if __name__ == '__main__':
    main()
