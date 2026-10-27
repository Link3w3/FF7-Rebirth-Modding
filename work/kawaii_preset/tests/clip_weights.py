"""The skin weights of the coat vertices that go into the legs in a run: how much of each one's weight is on coat bones
(the rest on bones the nodes do not move: the hips, the spine, spokes), on how many coat chains, and the bones."""
import json, re, sys
from collections import Counter
import numpy as np
exec(open('/work/kawaii_preset/tests/clip_check.py').read().split("maps = {(s, p)")[0])
maps = {(s, p): height_map(s, p) for s in 'LR' for p in ('thigh', 'calf')}
raw = np.fromfile(frames_path, dtype=np.float32)
nb, nf = int(raw[:1].view(np.int32)[0]), int(raw[1:2].view(np.int32)[0])
F = raw[2:].reshape(nf, nb, 7).astype(np.float64)
hits = Counter()
for f in range(90, nf):
    q = F[f, :, :4]; t = F[f, :, 4:]
    qb = qmul(q[cb], qinv(refq[cb]))
    vv = qrot(qb, coat_ref[:, None, :] - reft[cb]) + t[cb]
    sk = (vv * cw[..., None]).sum(axis=1)
    pen = np.zeros(len(coat_v))
    for (s, p), (bi, length, ax, e1, e2, m) in maps.items():
        local = qrot(qinv(q[bi])[None, :], sk - t[bi])
        tt = local @ ax / length
        radial = local - np.outer(local @ ax, ax)
        r = np.linalg.norm(radial, axis=1)
        ang = np.arctan2(radial @ e2, radial @ e1)
        ok = (tt >= 0) & (tt <= 1)
        ti = np.clip((tt * m.shape[0]).astype(int), 0, m.shape[0] - 1); ai = ((ang + np.pi) / (2 * np.pi) * m.shape[1]).astype(int) % m.shape[1]
        pen = np.maximum(pen, np.where(ok, m[ti, ai] - r, 0.0))
    for i in np.nonzero(pen > 1.0)[0]:
        hits[i] += 1
print('coat vertices over 1 cm deep in some frame: %d of %d' % (len(hits), len(coat_v)))
coat_share, nchains, other = [], [], Counter()
for i, cnt in hits.most_common():
    v = coat_v[i]
    ws = vw[v]; tot = sum(ws.values())
    c = sum(w for n, w in ws.items() if COAT.search(n)) / tot
    coat_share.append(c)
    nchains.append(len({re.sub(r'_[a-z]_Phy$', '', n) for n in ws if COAT.search(n)}))
    for n, w in ws.items():
        if not COAT.search(n):
            other[n] += w / tot * cnt
cs = np.array(coat_share)
print('their weight on coat bones: median %.2f, 10%% %.2f; under 0.9: %d%% of them' % (np.median(cs), np.percentile(cs, 10), 100 * (cs < 0.9).mean()))
print('on how many coat chains:', Counter(nchains).most_common())
print('their other bones (weighted by frames):', ', '.join('%s %.0f' % kv for kv in other.most_common(8)))
# where those vertices are at rest: their height (Z) and their distance in front of the thigh's axis
