"""Neo Bahamut's animation sets for the End editor's preview of Kawaii Dynamic Motions (Create a Character System 3.20.0):
his three sets' animations (Neutral00, Battle00, Battle00_Boss: the game's cooked ACL clips) as key animations (.cacanim,
every bone of SU2050_00_Skeleton, his reference pose for bones without tracks) for Import Key Animations, and his skeleton
as a small FBX (a tiny triangle at each bone, weighted to it, so every bone is in the imported skeleton) to import them on.
The game's additive animations (*_Add) are written as full poses (his reference pose with the additive on it), to be
marked Local Space Additive on the Reference Pose after the import (Unreal then keeps the same additive).
    make_nb_preview.py <out dir>"""
import hashlib
import json
import os
import struct
import sys

import numpy as np

sys.path[:0] = ['/work/acl', '/work/pc18', '/work/bfs17']
import acl13  # noqa: E402
import pc18_fbx  # noqa: E402

SKEL = '/work/pc18/nb/su2050_skel.json'
SETS = '/work/pc18/offline/nb_sets.json'


def qmul(a, b):
    ax, ay, az, aw = np.moveaxis(a, -1, 0)
    bx, by, bz, bw = np.moveaxis(b, -1, 0)
    return np.stack([aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx,
                     aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz], -1)


def qrot(q, v):
    u = q[..., :3]
    w = q[..., 3:4]
    t = 2.0 * np.cross(u, v)
    return v + w * t + np.cross(u, t)


def qnorm(q):
    return q / np.linalg.norm(q, axis=-1, keepdims=True)


class Skeleton:
    def __init__(self, path):
        d = json.load(open(path))
        self.names = d['names']
        self.parents = d['parents']
        self.q = qnorm(np.array(d['q'], dtype=np.float64))
        self.t = np.array(d['t'], dtype=np.float64)
        self.s = np.array(d['s'], dtype=np.float64)
        assert all(p < i for i, p in enumerate(self.parents))
        n = len(self.names)
        self.gq = np.zeros((n, 4))
        self.gt = np.zeros((n, 3))
        for i, p in enumerate(self.parents):
            if p < 0:
                self.gq[i], self.gt[i] = self.q[i], self.t[i]
            else:
                self.gq[i] = qmul(self.gq[p], self.q[i])
                self.gt[i] = self.gt[p] + qrot(self.gq[p], self.t[i])


def track_map(data, n, bones):
    """The clip's tracks' bones (CompressedTrackToSkeletonMapTable: n int32 after its count, the root first)."""
    pat = struct.pack('<i', n)
    p = data.find(pat)
    while p >= 0:
        if p + 4 + 4 * n <= len(data):
            vals = struct.unpack_from('<%di' % n, data, p + 4)
            if all(0 <= v < bones for v in vals) and len(set(vals)) == n and vals[0] == 0:
                return list(vals)
        p = data.find(pat, p + 1)
    raise ValueError('no track map')


def decode(data, sk):
    c = acl13.Clip(data)
    rot, trans, scale = c.decompress()
    bones = track_map(data, c.num_bones, len(sk.names))
    S = c.num_samples
    LQ = np.repeat(sk.q[None], S, 0)
    LT = np.repeat(sk.t[None], S, 0)
    LS = np.repeat(sk.s[None], S, 0)
    for k, b in enumerate(bones):
        LQ[:, b] = rot[:, k]
        LT[:, b] = trans[:, k]
        if c.has_scale:
            LS[:, b] = scale[:, k]
    return c, bones, qnorm(LQ), LT, LS


def write_cacanim(path, fps, names, LQ, LT, LS, loop):
    """'CACANIM1', u32 version 1, f32 fps, i32 frames, u32 flags (1 = loop), i32 tracks, then per track u16 name length +
    name, i32 keys (1 or frames), keys x (T xyz, Q xyzw, S xyz) float32 (Unreal axes, local to the parent bone)."""
    S = LQ.shape[0]
    for i in range(LQ.shape[1]):   # one hemisphere along each track
        q = LQ[:, i]
        for f in range(1, S):
            if np.dot(q[f], q[f - 1]) < 0:
                q[f] = -q[f]
    tracks = []
    for i, n in enumerate(names):
        T, Q, Sc = LT[:, i], LQ[:, i], LS[:, i]
        if np.abs(T - T[:1]).max() < 1e-4 and np.abs(Q - Q[:1]).max() < 1e-6 and np.abs(Sc - Sc[:1]).max() < 1e-6:
            T, Q, Sc = T[:1], Q[:1], Sc[:1]
        tracks.append((n, T, Q, Sc))
    with open(path, 'wb') as f:
        f.write(b'CACANIM1')
        f.write(struct.pack('<IfiIi', 1, float(fps), S, 1 if loop else 0, len(tracks)))
        for n, T, Q, Sc in tracks:
            nb = n.encode('ascii')
            f.write(struct.pack('<H', len(nb)) + nb)
            f.write(struct.pack('<i', len(T)))
            f.write(np.concatenate([T, Q, Sc], -1).astype('<f4').tobytes())


def skeleton_fbx(sk, path):
    """His skeleton with a 1 cm triangle at each bone (weighted to it)."""
    n = len(sk.names)
    pos = np.zeros((3 * n, 3))
    for i in range(n):
        p = sk.gt[i]
        pos[3 * i] = p
        pos[3 * i + 1] = p + (1.0, 0.0, 0.0)
        pos[3 * i + 2] = p + (0.0, 0.0, 1.0)
    corners = np.arange(3 * n)
    m = {
        'bone_names': np.array(sk.names), 'bone_parents': np.array(sk.parents),
        'bone_lq': sk.q, 'bone_lt': sk.t,
        'pos': pos, 'corner_cp': corners, 'tri': corners.reshape(n, 3),
        'nz': np.tile([0.0, -1.0, 0.0], (3 * n, 1)),
        'uv0': np.zeros((3 * n, 2)), 'uv1': np.zeros((3 * n, 2)), 'uv2': np.zeros((3 * n, 2)),
        'col': np.ones((3 * n, 4)), 'tmat': np.zeros(n, dtype=np.int64), 'slots': np.array(['NeoBahamutPreview']),
        'wbone': np.repeat(np.arange(n), 3)[:, None], 'wweight': np.ones((3 * n, 1)),
    }
    pc18_fbx.write(m, path, 'SU2050_00_Preview')


def md5(path):
    return hashlib.md5(open(path, 'rb').read()).hexdigest()


def main(out):
    sk = Skeleton(SKEL)
    sets = json.load(open(SETS))['sets']
    os.makedirs(out, exist_ok=True)
    manifest = {'skeleton_fbx': 'SU2050_00_Preview.fbx', 'sets': {}, 'files': {}}
    skeleton_fbx(sk, os.path.join(out, 'SU2050_00_Preview.fbx'))
    manifest['files']['SU2050_00_Preview.fbx'] = md5(os.path.join(out, 'SU2050_00_Preview.fbx'))
    for path, entries in sets.items():
        set_name = path.rsplit('/', 1)[1].split('.')[0]
        folder = os.path.join(out, 'cacanim', set_name)
        os.makedirs(folder, exist_ok=True)
        rows = {}
        for name, file in sorted(entries.items()):
            data = open(file, 'rb').read()
            try:
                c, bones, LQ, LT, LS = decode(data, sk)
            except ValueError as e:
                # not a sequence with its own ACL clip (an AnimComposite, or a part linked to another sequence): the
                # game's Kawaii Dynamic Motions do not play it either; its name stays in the set (with no animation)
                kind = 'AnimComposite' if b'AnimComposite' in data[:6000] else ('AnimSequence' if b'AnimSequence' in data[:6000] else 'other')
                rows[name] = {'skip': '%s without its own ACL clip (%s)' % (kind, e)}
                continue
            additive = name.endswith('_Add')
            if additive:
                # the additive as Unreal keeps it (rotation additive * base, translation additive + base, scale
                # (additive + 1) * base) on his reference pose: a full pose whose additive on the reference pose is it
                S = LQ.shape[0]
                dq = np.repeat(np.array([0.0, 0.0, 0.0, 1.0])[None, None], S, 0).repeat(len(sk.names), 1)
                dt = np.zeros((S, len(sk.names), 3))
                ds = np.zeros((S, len(sk.names), 3))
                rot, trans, scale = c.decompress()
                for k, b in enumerate(bones):
                    dq[:, b] = rot[:, k]
                    dt[:, b] = trans[:, k]
                    if c.has_scale:
                        ds[:, b] = scale[:, k]
                still = float(np.abs(qnorm(dq)[..., 3]).min())
                LQ = qnorm(qmul(qnorm(dq), sk.q[None]))
                LT = dt + sk.t[None]
                LS = (ds + 1.0) * sk.s[None]
            first = LQ[0]
            last = LQ[-1]
            dots = np.abs(np.sum(first * last, -1))
            loop = bool(LQ.shape[0] > 2 and dots.min() > 0.99996 and np.abs(LT[0] - LT[-1]).max() < 0.05)
            target = os.path.join(folder, name + '.cacanim')
            write_cacanim(target, c.sample_rate, sk.names, LQ, LT, LS, loop)
            rel = os.path.relpath(target, out).replace(os.sep, '/')
            manifest['files'][rel] = md5(target)
            rows[name] = {'frames': int(c.num_samples), 'fps': float(c.sample_rate), 'tracks': len(bones), 'loop': loop,
                          'additive': additive}
            if additive:
                rows[name]['least_w'] = still
        manifest['sets'][path] = rows
        print(set_name, len(rows), 'entries', sum(1 for r in rows.values() if r.get('additive')), 'additive', sum(1 for r in rows.values() if 'skip' in r), 'not sequences')
    json.dump(manifest, open(os.path.join(out, 'manifest.json'), 'w'), indent=1)


if __name__ == '__main__':
    main(sys.argv[1])
