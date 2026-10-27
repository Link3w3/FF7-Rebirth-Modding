"""Bahamut Fused Sephiroth's KawaiiPhysics in an offline run (anim_run's frames): how far his mantles and tail go into his
legs (their vertices skinned with each frame's bones, against height maps of his thighs and calves: the leg vertices'
farthest reach round each leg bone) and below the floor, and whether anything ran away (bones far from where the
animation puts them, NaN).
    bfs_sim_check.py body.npz rig.json frames.bin [label]"""
import json, re, sys
from collections import defaultdict
import numpy as np

def qrot(q, v):
    qv = q[..., :3]; t = 2.0 * np.cross(qv, v)
    return v + q[..., 3:4] * t + np.cross(qv, t)

def qinv(q):
    return np.concatenate([-q[..., :3], q[..., 3:4]], axis=-1)

def qmul(a, b):
    ax, ay, az, aw = np.moveaxis(a, -1, 0); bx, by, bz, bw = np.moveaxis(b, -1, 0)
    return np.stack([aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx, aw * bz + ax * by - ay * bx + az * bw,
                     aw * bw - ax * bx - ay * by - az * bz], axis=-1)

body_path, rig_path, frames_path = sys.argv[1:4]
label = sys.argv[4] if len(sys.argv) > 4 else frames_path
d = np.load(body_path, allow_pickle=True)
pos = d['pos']; wb = d['w_bone']; wv = d['w_vert']; ww = d['w_weight']; bnames = [str(b) for b in d['bones']]
rig = json.load(open(rig_path))
names = [b['name'] for b in rig['bones']]; index = {n: i for i, n in enumerate(names)}
refq = np.array([b['q'] for b in rig['bones']]); reft = np.array([b['t'] for b in rig['bones']])
nv = len(pos)
vw = defaultdict(dict)
for b, v, w in zip(wb, wv, ww):
    vw[int(v)][bnames[b]] = vw[int(v)].get(bnames[b], 0.0) + float(w)

def verts_of(rx):
    return np.array([v for v in range(nv) if sum(w for n, w in vw[v].items() if rx.search(n)) > 0.5])

def skin_setup(vs):
    K = 8
    cb = np.zeros((len(vs), K), dtype=np.int64); cw = np.zeros((len(vs), K))
    for i, v in enumerate(vs):
        items = sorted(vw[v].items(), key=lambda x: -x[1])[:K]; s = sum(w for _, w in items)
        for k, (n, w) in enumerate(items):
            cb[i, k] = index[n]; cw[i, k] = w / s
    return cb, cw

groups = {'mantle': verts_of(re.compile(r'_MantLg')), 'shoulder mantle': verts_of(re.compile(r'_MantSm')), 'tail': verts_of(re.compile(r'^Tail\d'))}
setups = {k: skin_setup(v) for k, v in groups.items()}

def height_map(side, part):
    if part == 'thigh':
        bone, child = side + '_UpperLeg_a', side + '_Foreleg_a'
        group = re.compile(r'^%s_(UpperLeg_a|Femoris[A-Z]|FemorisSub|KneeSid[AB]|Knee1)$' % side)
    else:
        bone, child = side + '_Foreleg_a', side + '_Foot_a'
        group = re.compile(r'^%s_(Foreleg_a|Knee2|FootRoll[AB]|AnkleKdi)$' % side)
    bi = index[bone]
    sel = [v for v in range(nv) if sum(w for n, w in vw[v].items() if group.search(n)) > 0.5]
    P = pos[sel]
    local = qrot(qinv(refq[bi]), P - reft[bi])
    axis = qrot(qinv(refq[bi]), reft[index[child]] - reft[bi])
    length = np.linalg.norm(axis); ax = axis / length
    up = np.array([0.0, 0.0, 1.0]) if abs(ax[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    e1 = np.cross(ax, up); e1 /= np.linalg.norm(e1); e2 = np.cross(ax, e1)
    t = local @ ax / length
    radial = local - np.outer(local @ ax, ax)
    r = np.linalg.norm(radial, axis=1); ang = np.arctan2(radial @ e2, radial @ e1)
    TB, AB = 20, 16
    m = np.zeros((TB, AB))
    ti = np.clip((t * TB).astype(int), 0, TB - 1); ai = ((ang + np.pi) / (2 * np.pi) * AB).astype(int) % AB
    inside = (t >= 0) & (t <= 1)
    for a, b, rr in zip(ti[inside], ai[inside], r[inside]):
        m[a, b] = max(m[a, b], rr)
    for _ in range(4):
        z = m == 0
        if not z.any(): break
        nb = np.maximum.reduce([np.roll(m, 1, 1), np.roll(m, -1, 1), np.roll(m, 1, 0), np.roll(m, -1, 0)])
        m[z] = nb[z]
    return bi, length, ax, e1, e2, m

maps = {(s, p): height_map(s, p) for s in 'LR' for p in ('thigh', 'calf')}
raw = np.fromfile(frames_path, dtype=np.float32)
nb, nf = int(raw[:1].view(np.int32)[0]), int(raw[1:2].view(np.int32)[0])
F = raw[2:].reshape(nf, nb, 7).astype(np.float64)
assert nb == len(names)
print('%s: %d frames; NaN: %s' % (label, nf, bool(np.isnan(F).any())))
start = int(nf / 7.0 * 1.5)
for g, vs in groups.items():
    cb, cw = setups[g]
    ref = pos[vs]
    pens, floor = [], []
    for f in range(start, nf):
        q = F[f, :, :4]; t = F[f, :, 4:]
        qb = qmul(q[cb], qinv(refq[cb]))
        sk = ((qrot(qb, ref[:, None, :] - reft[cb]) + t[cb]) * cw[..., None]).sum(axis=1)
        pen = np.zeros(len(vs))
        for (s, p), (bi, length, ax, e1, e2, m) in maps.items():
            local = qrot(qinv(q[bi])[None, :], sk - t[bi])
            tt = local @ ax / length
            radial = local - np.outer(local @ ax, ax)
            r = np.linalg.norm(radial, axis=1); ang = np.arctan2(radial @ e2, radial @ e1)
            ok = (tt >= 0) & (tt <= 1)
            ti = np.clip((tt * m.shape[0]).astype(int), 0, m.shape[0] - 1); ai = ((ang + np.pi) / (2 * np.pi) * m.shape[1]).astype(int) % m.shape[1]
            pen = np.maximum(pen, np.where(ok, m[ti, ai] - r, 0.0))
        pens.append(pen)
        floor.append(sk[:, 2].min())
    P = np.concatenate(pens)
    print('  %-16s verts %6d: in a leg %.2f%% of vertex-frames, depth 99%% %.2f cm, max %.2f; lowest point %.1f cm (rest %.1f)' % (
        g, len(vs), 100 * (P > 0).mean(), np.percentile(P, 99), P.max(), min(floor), ref[:, 2].min()))
