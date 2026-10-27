"""Bahamut Fused Sephiroth's hair in an offline run (anim_run's frames): how far it goes into his torso armour and his legs
(height maps of their vertices round the spine and each leg bone, in the bone's space), counted only by how much deeper
than at rest (the maps' bins are coarse and the hair rests on the armour); how far the strands swing from where the
animation alone puts them; NaN.
    bfs_hair_sim_check.py body.npz rig.json frames.bin [label]"""
import json, re, sys
from collections import defaultdict
import numpy as np
sys.path.insert(0, '/work/bfs17')

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
mats = [str(m) for m in d['mats']]; vmat = d['vmat']
rig = json.load(open(rig_path))
names = [b['name'] for b in rig['bones']]; index = {n: i for i, n in enumerate(names)}
refq = np.array([b['q'] for b in rig['bones']]); reft = np.array([b['t'] for b in rig['bones']])
nv = len(pos)
vw = defaultdict(dict)
for b, v, w in zip(wb, wv, ww):
    vw[int(v)][bnames[b]] = vw[int(v)].get(bnames[b], 0.0) + float(w)

def verts_of(rx, need=0.5):
    return np.array([v for v in range(nv) if sum(w for n, w in vw[v].items() if rx.search(n)) > need])

def skin_setup(vs):
    K = 8
    cb = np.zeros((len(vs), K), dtype=np.int64); cw = np.zeros((len(vs), K))
    for i, v in enumerate(vs):
        items = sorted(vw[v].items(), key=lambda x: -x[1])[:K]; s = sum(w for _, w in items)
        for k, (n, w) in enumerate(items):
            cb[i, k] = index[n]; cw[i, k] = w / s
    return cb, cw

groups = {'front strands': verts_of(re.compile(r'^(C_HairA|C_HairB|[LR]_HairA)_[a-z]_Phy$')),
          'long hair': verts_of(re.compile(r'^(C_HairM|C_HairL|[LR]_Hair[CDE])_[a-z]_Phy$'))}
setups = {k: skin_setup(v) for k, v in groups.items()}
body_slot = mats.index('PC0010_17_Body_Inst')

def height_map(bone, child, group, pct=None):
    bi = index[bone]
    sel = [v for v in range(nv) if vmat[v] == body_slot and sum(w for n, w in vw[v].items() if group.search(n)) > 0.5]
    P = pos[sel]
    local = qrot(qinv(refq[bi]), P - reft[bi])
    axis = qrot(qinv(refq[bi]), reft[index[child]] - reft[bi])
    length = np.linalg.norm(axis); ax = axis / length
    up = np.array([0.0, 0.0, 1.0]) if abs(ax[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    e1 = np.cross(ax, up); e1 /= np.linalg.norm(e1); e2 = np.cross(ax, e1)
    t = local @ ax / length
    radial = local - np.outer(local @ ax, ax)
    r = np.linalg.norm(radial, axis=1); ang = np.arctan2(radial @ e2, radial @ e1)
    TB, AB = 24, 24
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

maps = {'torso': height_map('C_Spine_a', 'C_Neck_a', re.compile(r'^(C_Hip_a|C_Spine_[a-d]|Spine1W|Abs\d|NeckSub|C_Neck_a)$'))}
for s in 'LR':
    maps[s + ' thigh'] = height_map(s + '_UpperLeg_a', s + '_Foreleg_a', re.compile(r'^%s_(UpperLeg_a|Femoris[A-Z]|FemorisSub|KneeSid[AB]|Knee1)$' % s))
    maps[s + ' calf'] = height_map(s + '_Foreleg_a', s + '_Foot_a', re.compile(r'^%s_(Foreleg_a|Knee2|FootRoll[AB]|AnkleKdi)$' % s))

def penetration(sk, q, t):
    pen = {}
    for k, (bi, length, ax, e1, e2, m) in maps.items():
        local = qrot(qinv(q[bi])[None, :], sk - t[bi])
        tt = local @ ax / length
        radial = local - np.outer(local @ ax, ax)
        r = np.linalg.norm(radial, axis=1); ang = np.arctan2(radial @ e2, radial @ e1)
        ok = (tt >= 0) & (tt <= 1)
        ti = np.clip((tt * m.shape[0]).astype(int), 0, m.shape[0] - 1); ai = ((ang + np.pi) / (2 * np.pi) * m.shape[1]).astype(int) % m.shape[1]
        pen[k] = np.where(ok, m[ti, ai] - r, -1e9)
    return pen

raw = np.fromfile(frames_path, dtype=np.float32)
nb_, nf = int(raw[:1].view(np.int32)[0]), int(raw[1:2].view(np.int32)[0])
F = raw[2:].reshape(nf, nb_, 7).astype(np.float64)
assert nb_ == len(names)
print('%s: %d frames; NaN: %s' % (label, nf, bool(np.isnan(F).any())))
start = int(nf / 7.0 * 1.5)
for g, vs in groups.items():
    cb, cw = setups[g]
    ref = pos[vs]
    pen0 = penetration(ref, refq, reft)
    deeper = defaultdict(list); lowest = []
    for f in range(start, nf):
        q = F[f, :, :4]; t = F[f, :, 4:]
        qb = qmul(q[cb], qinv(refq[cb]))
        sk = ((qrot(qb, ref[:, None, :] - reft[cb]) + t[cb]) * cw[..., None]).sum(axis=1)
        pen = penetration(sk, q, t)
        for k in pen:
            p0 = np.maximum(pen0[k], 0)
            dd = np.where(pen[k] > 0, pen[k] - p0, 0)
            deeper[k].append(dd)
        lowest.append(sk[:, 2].min())
    line = '  %-14s verts %6d:' % (g, len(vs))
    for k in deeper:
        D = np.concatenate(deeper[k])
        if (D > 0.5).any():
            line += ' %s %.2f%% >0.5cm deeper (max %.1f);' % (k, 100 * (D > 0.5).mean(), D.max())
    line += ' lowest %.1f cm (rest %.1f)' % (min(lowest), ref[:, 2].min())
    print(line)
