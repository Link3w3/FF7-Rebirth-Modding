"""Where a coat goes into the legs in a run (clip_check.py's test, broken down): by coat chain (the chain a vertex is
mostly skinned to), by leg part (thigh / calf), by place along the leg (tenths from its top joint) and side (front /
back / out / in, in the leg's reference axes: front = his +X), and how far the chain's own bones are inside the
node's leg capsules (the solver's own shapes) at the worst frames.
    clip_where.py body.npz rig.json frames.bin entry.json"""
import json, re, sys
from collections import defaultdict, Counter
import numpy as np
exec(open('/work/kawaii_preset/tests/clip_check.py').read().split("maps = {(s, p)")[0].replace('body_path, rig_path, frames_path = sys.argv[1:4]', 'body_path, rig_path, frames_path = sys.argv[1:4]\nentry_path = sys.argv[4]'))
maps = {(s, p): height_map(s, p) for s in 'LR' for p in ('thigh', 'calf')}
raw = np.fromfile(frames_path, dtype=np.float32)
nb, nf = int(raw[:1].view(np.int32)[0]), int(raw[1:2].view(np.int32)[0])
F = raw[2:].reshape(nf, nb, 7).astype(np.float64)
chain_of = []
for i, v in enumerate(coat_v):
    best = max(((n, w) for n, w in vw[v].items() if COAT.search(n)), key=lambda x: x[1])[0]
    chain_of.append(re.sub(r'_[a-z]_Phy$', '', best))
chain_of = np.array(chain_of)
by_chain = Counter(); by_part = Counter(); by_tenth = Counter(); by_side = Counter(); deep = []
fwd_ref = np.array([1.0, 0.0, 0.0])
for f in range(int(1.5 * 60), nf):
    q = F[f, :, :4]; t = F[f, :, 4:]
    qb = qmul(q[cb], qinv(refq[cb]))
    vv = qrot(qb, coat_ref[:, None, :] - reft[cb]) + t[cb]
    sk = (vv * cw[..., None]).sum(axis=1)
    for (s, p), (bi, length, ax, e1, e2, m) in maps.items():
        local = qrot(qinv(q[bi])[None, :], sk - t[bi])
        tt = local @ ax / length
        radial = local - np.outer(local @ ax, ax)
        r = np.linalg.norm(radial, axis=1)
        ang = np.arctan2(radial @ e2, radial @ e1)
        ok = (tt >= 0) & (tt <= 1)
        ti = np.clip((tt * m.shape[0]).astype(int), 0, m.shape[0] - 1); ai = ((ang + np.pi) / (2 * np.pi) * m.shape[1]).astype(int) % m.shape[1]
        depth = np.where(ok, m[ti, ai] - r, 0.0)
        hit = depth > 0.5
        if not hit.any():
            continue
        # the side, in the leg bone's own frame: the reference forward (+X) and outward (away from the body's middle) in it
        bq = refq[bi]
        f_l = qrot(qinv(bq), fwd_ref); f_l -= (f_l @ ax) * ax; f_l /= np.linalg.norm(f_l)
        o_l = qrot(qinv(bq), np.array([0.0, -1.0 if s == 'L' else 1.0, 0.0])); o_l -= (o_l @ ax) * ax; o_l /= np.linalg.norm(o_l)
        rd = radial[hit] / np.maximum(r[hit, None], 1e-6)
        cf, co = rd @ f_l, rd @ o_l
        side = np.where(np.abs(cf) >= np.abs(co), np.where(cf > 0, 'front', 'back'), np.where(co > 0, 'out', 'in'))
        for c, pp, tn, sd, dp in zip(chain_of[hit], [p] * hit.sum(), (tt[hit] * 10).astype(int), side, depth[hit]):
            by_chain[c] += 1; by_part[s + ' ' + pp] += 1; by_tenth[(pp, int(tn))] += 1; by_side[(pp, sd)] += 1
            deep.append(dp)
tot = sum(by_chain.values())
print('vertex-frames over 0.5 cm deep: %d' % tot)
print(' by chain:', ', '.join('%s %d%%' % (c, 100 * n // tot) for c, n in by_chain.most_common(8)))
print(' by leg:  ', ', '.join('%s %d%%' % (c, 100 * n // tot) for c, n in by_part.most_common()))
print(' by side: ', ', '.join('%s %s %d%%' % (c[0], c[1], 100 * n // tot) for c, n in by_side.most_common(8)))
print(' along:   ', ', '.join('%s %d/10 %d%%' % (c[0], c[1], 100 * n // tot) for c, n in sorted(by_tenth.items(), key=lambda x: -x[1])[:10]))
