import sys, struct
sys.path[:0] = ['/work/ys', '/work/ch049anim']
import numpy as np
import convert_ch049_anims as CV
import unity_anim as U
from film3d import film
import retarget_from_seph as RS


def read_cac(path):
    d = open(path, 'rb').read()
    assert d[:8] == b'CACANIM1'
    ver, fps, nf, flags, nt = struct.unpack_from('<IfiIi', d, 8)
    p = 28
    names, T, Q, S = [], [], [], []
    for _ in range(nt):
        ln = struct.unpack_from('<H', d, p)[0]; p += 2
        names.append(d[p:p + ln].decode()); p += ln
        nk = struct.unpack_from('<i', d, p)[0]; p += 4
        a = np.frombuffer(d, '<f4', nk * 10, p).reshape(nk, 10); p += nk * 40
        if nk == 1:
            a = np.repeat(a, nf, 0)
        T.append(a[:, :3]); Q.append(a[:, 3:7]); S.append(a[:, 7:])
    return names, fps, np.stack(T, 1).astype(float), np.stack(Q, 1).astype(float), np.stack(S, 1).astype(float), flags


def world_of(path):
    names, fps, T, Q, S, flags = read_cac(path)
    GQ, GT, _ = CV.fk(Q, T, S, RS.CH.parents)
    nf, n = GQ.shape[:2]
    W = np.zeros((nf, n, 4, 4))
    W[..., :3, :3] = U.qmat(GQ); W[..., :3, 3] = GT; W[..., 3, 3] = 1
    return W, fps


if __name__ == '__main__':
    for p in sys.argv[1:]:
        W, fps = world_of(p)
        name = p.rsplit('/', 1)[-1][:-8]
        print(film(name, 0, (len(W) - 1) / fps, max(1, len(W) // 16), W=W, fps=fps, out='film3d/cac_%s.png' % name))
