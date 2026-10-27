"""A cooked skeletal mesh's bones (zen package, UE 4.26 as FF7 Rebirth cooks it): its FReferenceSkeleton (RawRefBoneInfo:
name + parent; RawRefBonePose: rotation, translation, scale) found in the mesh export, as a rig JSON in component space
(the format of ys/rig/rig.json: bones [{name, parent, q, t, local_q, local_t}] in parent-first order).
    mesh_bones.py <package.uasset> <out.json> [export name]"""
import json, struct, sys
sys.path[:0] = ['/work/cs']
from zen import Zen


def name_text(z, idx, num):
    s = z.names[idx]
    return s if num == 0 else '%s_%d' % (s, num - 1)


def find_ref_skeleton(z, data):
    """[(name, parent, (qx,qy,qz,qw), (tx,ty,tz), (sx,sy,sz))] of the longest valid bone table in `data`."""
    N = len(z.names)
    best = None
    for p in range(0, len(data) - 16, 1):
        n = struct.unpack_from('<i', data, p)[0]
        if not (2 <= n <= 4096) or (best and n <= len(best[1])):
            continue
        end = p + 4 + 12 * n
        if end + 4 > len(data):
            continue
        ok = True
        infos = []
        for k in range(n):
            ni, num, par = struct.unpack_from('<iii', data, p + 4 + 12 * k)
            if not (0 <= ni < N) or not (0 <= num < 1000) or not (-1 <= par < k) or (k == 0) != (par == -1):
                ok = False
                break
            infos.append((name_text(z, ni, num), par))
        if not ok:
            continue
        if struct.unpack_from('<i', data, end)[0] != n or end + 4 + 40 * n > len(data):
            continue
        poses = [struct.unpack_from('<10f', data, end + 4 + 40 * k) for k in range(n)]
        if not all(abs(sum(c * c for c in v[:4]) - 1.0) < 1e-3 for v in poses):
            continue
        best = (p, [(infos[k][0], infos[k][1], poses[k][:4], poses[k][4:7], poses[k][7:10]) for k in range(n)])
    return best


def qmul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx, aw * bz + ax * by - ay * bx + az * bw,
            aw * bw - ax * bx - ay * by - az * bz)


def qrot(q, v):
    qv = q[:3]
    t = [2 * (qv[1] * v[2] - qv[2] * v[1]), 2 * (qv[2] * v[0] - qv[0] * v[2]), 2 * (qv[0] * v[1] - qv[1] * v[0])]
    c = [qv[1] * t[2] - qv[2] * t[1], qv[2] * t[0] - qv[0] * t[2], qv[0] * t[1] - qv[1] * t[0]]
    return [v[i] + q[3] * t[i] + c[i] for i in range(3)]


def to_rig(bones):
    cs = []
    out = []
    for name, par, q, t, s in bones:
        if par < 0:
            Q, T, S = tuple(q), list(t), list(s)
        else:
            PQ, PT, PS = cs[par]
            Q = qmul(PQ, q)
            T = [a + b for a, b in zip(qrot(PQ, [t[i] * PS[i] for i in range(3)]), PT)]
            S = [PS[i] * s[i] for i in range(3)]
        n = sum(c * c for c in Q) ** 0.5
        Q = tuple(c / n for c in Q)
        cs.append((Q, T, S))
        out.append(dict(name=name, parent=bones[par][0] if par >= 0 else None, q=list(Q), t=T, local_q=list(q), local_t=list(t),
                        scale=list(s)))
    return out


def main(path, out_path, want=None):
    d = open(path, 'rb').read()
    z = Zen(d)
    cands = [i for i, e in enumerate(z.exports) if (want is None or e['name'] == want)]
    best = None
    for i in cands:
        data = z.export_bytes(i)
        r = find_ref_skeleton(z, data)
        if r and (best is None or len(r[1]) > len(best[2])):
            best = (i, r[0], r[1])
    assert best, 'no bone table found'
    i, at, bones = best
    rig = dict(source=path, export=z.exports[i]['name'], at=at, bones=to_rig(bones))
    json.dump(rig, open(out_path, 'w'), indent=0)
    print('%s: export %d %s, %d bones (table at %d)' % (path.split('/')[-1], i, z.exports[i]['name'], len(bones), at))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
