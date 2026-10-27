"""How far a model's coat (its vertices skinned to Coat/Skirt/Belt chain bones) goes into its legs in an offline run
(ys_skirt's frames): the coat's vertices skinned with each frame's bone transforms, against height maps of the thighs and
calves (the leg vertices' farthest reach from the leg's axis, by place along it and angle round it, in the leg bone's
space). Generalized from cacs3143/tests/ys_skirt_check.py for tools/cooked_mesh.py's npz.
    clip_check.py body.npz rig.json frames.bin [label]"""
import json, re, sys
from collections import defaultdict
import numpy as np

body_path, rig_path, frames_path = sys.argv[1:4]
label = sys.argv[4] if len(sys.argv) > 4 else frames_path
d = np.load(body_path, allow_pickle=True)
pos = d['pos']; wb = d['w_bone']; wv = d['w_vert']; ww = d['w_weight']; bnames = [str(b) for b in d['bones']]
rig = json.load(open(rig_path))
names = [b['name'] for b in rig['bones']]
index = {n: i for i, n in enumerate(names)}
refq = np.array([b['q'] for b in rig['bones']], dtype=np.float64)
reft = np.array([b['t'] for b in rig['bones']], dtype=np.float64)


def qrot(q, v):
    qv = q[..., :3]
    t = 2.0 * np.cross(qv, v)
    return v + q[..., 3:4] * t + np.cross(qv, t)


def qinv(q):
    return np.concatenate([-q[..., :3], q[..., 3:4]], axis=-1)


def qmul(a, b):
    ax, ay, az, aw = np.moveaxis(a, -1, 0)
    bx, by, bz, bw = np.moveaxis(b, -1, 0)
    return np.stack([aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx, aw * bz + ax * by - ay * bx + az * bw,
                     aw * bw - ax * bx - ay * by - az * bz], axis=-1)


nv = len(pos)
vw = defaultdict(dict)
for b, v, w in zip(wb, wv, ww):
    vw[int(v)][bnames[b]] = vw[int(v)].get(bnames[b], 0.0) + float(w)
COAT = re.compile(r'(Coat|Skirt)[A-Z]*_[a-z]_Phy$')
coat_v = np.array([v for v in range(nv) if sum(w for n, w in vw[v].items() if COAT.search(n)) > 0.5])
K = 8
cb = np.zeros((len(coat_v), K), dtype=np.int64); cw = np.zeros((len(coat_v), K))
for i, v in enumerate(coat_v):
    items = sorted(vw[v].items(), key=lambda x: -x[1])[:K]
    s = sum(w for _, w in items)
    for k, (n, w) in enumerate(items):
        cb[i, k] = index[n]; cw[i, k] = w / s
coat_ref = pos[coat_v]


def height_map(side, part):
    if part == 'thigh':
        bone, child = side + '_UpperLeg_a', side + '_Foreleg_a'
        group = re.compile(r'^%s_(UpperLeg_a|Femoris[A-Z]_Spo|Knee_Spo)$' % side)
    else:
        bone, child = side + '_Foreleg_a', side + '_Foot_a'
        group = re.compile(r'^%s_(Foreleg_a|Calf[A-Z]?_Spo|Knee_Spo|Foot_a)$' % side)
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
    r = np.linalg.norm(radial, axis=1)
    ang = np.arctan2(radial @ e2, radial @ e1)
    TB, AB = 20, 16
    m = np.zeros((TB, AB))
    ti = np.clip((t * TB).astype(int), 0, TB - 1); ai = ((ang + np.pi) / (2 * np.pi) * AB).astype(int) % AB
    inside = (t >= 0) & (t <= 1)
    for a, b, rr in zip(ti[inside], ai[inside], r[inside]):
        m[a, b] = max(m[a, b], rr)
    for _ in range(4):
        z = m == 0
        if not z.any():
            break
        nb = np.maximum.reduce([np.roll(m, 1, 1), np.roll(m, -1, 1), np.roll(m, 1, 0), np.roll(m, -1, 0)])
        m[z] = nb[z]
    return bi, length, ax, e1, e2, m


maps = {(s, p): height_map(s, p) for s in 'LR' for p in ('thigh', 'calf')}
raw = np.fromfile(frames_path, dtype=np.float32)
nb, nf = int(raw[:1].view(np.int32)[0]), int(raw[1:2].view(np.int32)[0])
F = raw[2:].reshape(nf, nb, 7).astype(np.float64)
assert nb == len(names), (nb, len(names))
fps_guess = nf / 6.0
pen_all = []
worst = (0.0, None)
for f in range(nf):
    q = F[f, :, :4]; t = F[f, :, 4:]
    qb = qmul(q[cb], qinv(refq[cb]))
    vv = qrot(qb, coat_ref[:, None, :] - reft[cb]) + t[cb]
    sk = (vv * cw[..., None]).sum(axis=1)
    if f < int(1.5 * fps_guess):
        continue
    pen = np.zeros(len(coat_v))
    for (s, p), (bi, length, ax, e1, e2, m) in maps.items():
        local = qrot(qinv(q[bi])[None, :], sk - t[bi])
        tt = local @ ax / length
        radial = local - np.outer(local @ ax, ax)
        r = np.linalg.norm(radial, axis=1)
        ang = np.arctan2(radial @ e2, radial @ e1)
        ok = (tt >= 0) & (tt <= 1)
        ti = np.clip((tt * m.shape[0]).astype(int), 0, m.shape[0] - 1); ai = ((ang + np.pi) / (2 * np.pi) * m.shape[1]).astype(int) % m.shape[1]
        depth = np.where(ok, m[ti, ai] - r, 0.0)
        pen = np.maximum(pen, depth)
    pen_all.append(pen)
    if pen.max() > worst[0]:
        worst = (pen.max(), f)
P = np.concatenate(pen_all)
inside = P > 0
print('%-30s coat verts %d, frames %d: inside a leg %.2f%% of vertex-frames; depth 95%% %.2f cm, 99%% %.2f, max %.2f (frame %s); frames with any > 1 cm: %d of %d' % (
    label, len(coat_v), len(pen_all), 100.0 * inside.mean(), np.percentile(P, 95), np.percentile(P, 99), P.max(), worst[1],
    sum(1 for p in pen_all if p.max() > 1.0), len(pen_all)))
