"""Key animations (.cacanim) of Sora's KH2 moves for Create a Character System's Import Key Animations: every bone's
keys as the editor has them (the KH2 FBX imports on his skeleton), played at KH2's 60 fps (the imports say 24), with
the root as the game's own animations carry it: rotation GAME_ROOT_Q (times the move's own turn, if it turns) and its
travel forward on +X (the imports keep the root turned -90 degrees about X with its travel on +Y; the body under it is
already the game's: Z up, facing +X).
    make_keys.py <out folder> [names...]   (default: every dumped animation)"""
import json, os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from kh2raw import Anim, RAW
import fk

FPS = 60.0
GAME_ROOT_Q = np.array([-0.5, 0.5, -0.5, 0.5])
R0 = np.array([-0.70710678, 0.0, 0.0, 0.70710678])
ROOT = 'kh_sk'


def qconj(q):
    return np.array([-q[0], -q[1], -q[2], q[3]])


def qnorm(q):
    q = q / np.linalg.norm(q)
    return -q if q[3] < 0 else q


def root_track(a):
    pos, rot, scl = a.tracks[ROOT]
    n = a.frames
    P = np.repeat(pos, n, 0) if len(pos) == 1 else pos
    Q = np.repeat(rot, n, 0) if len(rot) == 1 else rot
    T = np.stack([P[:, 1], -P[:, 0], P[:, 2]], 1)               # travel: +Y -> +X (a yaw of -90 degrees)
    out_q = []
    worst = 0.0
    for q in Q:
        turn = qnorm(fk.qmul(qnorm(q), qconj(R0)))               # the move's own turn, in component space
        axis_tilt = np.degrees(np.arcsin(min(1.0, np.linalg.norm(turn[:2]))) * 2)
        worst = max(worst, axis_tilt)
        out_q.append(qnorm(fk.qmul(turn, GAME_ROOT_Q)))
    return T, np.array(out_q), worst


def write(a, path, loop=False):
    tracks = []
    for t, (pos, rot, scl) in a.tracks.items():
        if t == ROOT:
            T, Q, tilt = root_track(a)
            S = np.ones_like(T)
            if np.ptp(T, 0).max() < 1e-4 and np.ptp(Q, 0).max() < 1e-6:
                T, Q, S = T[:1], Q[:1], S[:1]
            tracks.append((t, T, Q, S))
            continue
        n = max(len(pos), len(rot), len(scl) if scl is not None else 0)
        if n not in (1, a.frames):
            raise ValueError('%s %s: %d keys' % (a.name, t, n))
        P = pos if len(pos) == n else np.repeat(pos[:1], n, 0)
        Q = rot if len(rot) == n else np.repeat(rot[:1], n, 0)
        S = (scl if scl is not None and len(scl) == n else (np.repeat(scl[:1], n, 0) if scl is not None and len(scl) else np.ones((n, 3))))
        Q = np.array([qnorm(q) for q in Q])
        tracks.append((t, P, Q, S))
    with open(path, 'wb') as f:
        f.write(b'CACANIM1')
        f.write(struct.pack('<IfiIi', 1, FPS, a.frames, 1 if loop else 0, len(tracks)))
        for bone, T, Q, S in tracks:
            nb = bone.encode('ascii')
            f.write(struct.pack('<H', len(nb)) + nb)
            f.write(struct.pack('<i', len(T)))
            f.write(np.concatenate([T, Q, S], -1).astype('<f4').tobytes())
    return len(tracks)


def read_back(path):
    d = open(path, 'rb').read()
    assert d[:8] == b'CACANIM1'
    ver, fps, frames, flags, ntracks = struct.unpack_from('<IfiIi', d, 8)
    p = 28
    out = {}
    for _ in range(ntracks):
        ln, = struct.unpack_from('<H', d, p); p += 2
        name = d[p:p + ln].decode('ascii'); p += ln
        keys, = struct.unpack_from('<i', d, p); p += 4
        arr = np.frombuffer(d, '<f4', keys * 10, p).reshape(keys, 10); p += keys * 40
        out[name] = arr
    assert p == len(d)
    return fps, frames, flags, out


LOOPS = {'1015', '1017', '1017L', '1017R', '0040', '0042'}

if __name__ == '__main__':
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    names = sys.argv[2:] or sorted(f[:-5] for f in os.listdir(RAW) if f.endswith('.json'))
    manifest = []
    for n in names:
        a = Anim(n)
        path = os.path.join(out, 'KH2_%s.cacanim' % n)
        k = write(a, path, loop=n in LOOPS)
        fps, frames, flags, back = read_back(path)
        T, Q, tilt = root_track(a)
        assert frames == a.frames and abs(fps - FPS) < 1e-6 and len(back) == k
        manifest.append(dict(name=n, asset='KH2_' + n, frames=a.frames, seconds=round((a.frames - 1) / FPS, 4), tracks=k,
                             travel=[round(float(v), 1) for v in T[-1] - T[0]], turn_tilt_deg=round(tilt, 3), loop=n in LOOPS))
        print('%-16s %3d frames %.2fs %3d tracks travel %s tilt %.3f' % ('KH2_' + n, a.frames, (a.frames - 1) / FPS, k, manifest[-1]['travel'], tilt))
    json.dump(manifest, open(os.path.join(out, 'manifest.json'), 'w'), indent=1)
