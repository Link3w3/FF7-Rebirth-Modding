"""Bones of an editor-saved (uncooked, UE 4.26) skeleton or skeletal mesh package: its FReferenceSkeleton, whose bone
infos carry their ExportName (an FString) in editor packages: [(name, parent, (qx,qy,qz,qw), (tx,ty,tz), (sx,sy,sz))].
As a rig JSON in component space (tools/mesh_bones.py's format) with -o.
    editor_bones.py <package.uasset> [-o rig.json]"""
import json, struct, sys
sys.path[:0] = ['/work/run1013/tools', '/work/kawaii_preset/tools']
from pkg426 import Pkg


def fstring(d, p):
    n = struct.unpack_from('<i', d, p)[0]
    if n == 0:
        return '', p + 4
    if n < 0:
        if -n > 512: raise ValueError
        return d[p + 4:p + 4 - 2 * n].decode('utf-16-le').rstrip('\0'), p + 4 - 2 * n
    if n > 512: raise ValueError
    return d[p + 4:p + 4 + n].decode('latin-1').rstrip('\0'), p + 4 + n


def find(d, names):
    N = len(names)
    best = None
    for p in range(0, len(d) - 16):
        n = struct.unpack_from('<i', d, p)[0]
        if not (2 <= n <= 4096) or (best and n <= len(best[1])):
            continue
        q = p + 4
        infos = []
        try:
            for k in range(n):
                ni, num, par = struct.unpack_from('<iii', d, q)
                if not (0 <= ni < N) or not (0 <= num < 1000) or not (-1 <= par < k) or (k == 0) != (par == -1):
                    raise ValueError
                export, q = fstring(d, q + 12)
                infos.append((names[ni] if num == 0 else '%s_%d' % (names[ni], num - 1), par, export))
        except (ValueError, struct.error, UnicodeDecodeError):
            continue
        if struct.unpack_from('<i', d, q)[0] != n:
            continue
        pose = [struct.unpack_from('<10f', d, q + 4 + 40 * k) for k in range(n)]
        best = (p, infos, pose)
    return best


def qmul(a, b):
    ax, ay, az, aw = a; bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx, aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz)


def qrot(q, v):
    x, y, z, w = q
    u = (x, y, z)
    def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
    t = tuple(2 * c for c in cross(u, v)); c2 = cross(u, t)
    return tuple(v[i] + w * t[i] + c2[i] for i in range(3))


def rig(path):
    d = open(path, 'rb').read()
    P = Pkg(d)
    p, infos, pose = find(d, P.names)
    bones = []
    cs = []
    for k, ((name, par, export), tr) in enumerate(zip(infos, pose)):
        q = tr[0:4]; t = tr[4:7]; s = tr[7:10]
        if par < 0:
            cq, ct, csc = q, t, s
        else:
            pq, pt, ps = cs[par]
            st = tuple(t[i] * ps[i] for i in range(3))
            r = qrot(pq, st)
            cq, ct, csc = qmul(pq, q), tuple(pt[i] + r[i] for i in range(3)), tuple(s[i] * ps[i] for i in range(3))
        cs.append((cq, ct, csc))
        bones.append(dict(name=name, parent=infos[par][0] if par >= 0 else None, q=list(cq), t=list(ct), local_q=list(q), local_t=list(t), scale=list(s)))
    return dict(source=path, export=None, at=p, bones=bones)


if __name__ == '__main__':
    r = rig(sys.argv[1])
    print('%s: %d bones (table at %d)' % (sys.argv[1], len(r['bones']), r['at']))
    if '-o' in sys.argv:
        json.dump(r, open(sys.argv[sys.argv.index('-o') + 1], 'w'), indent=0)
