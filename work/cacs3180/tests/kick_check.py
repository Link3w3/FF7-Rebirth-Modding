"""(3.17.0) How Young Sephiroth's coat fares against his legs in a kick run (kick_run's frames): ys_skirt_check's measure
(coat vertices skinned with each frame's bones, against height maps of his thighs and calves) plus the passes THROUGH a
leg: between two frames, a vertex whose path (in the leg's own space, the leg's move taken out) goes through the leg
while neither end is in it (the leg went past the cloth in one frame: the coat ends up on the leg's other side).
    python3 kick_check.py body.npz rig.json frames.bin [label] [seconds = 6] [skip seconds = 1.5]"""
import json
import sys
from collections import defaultdict
import numpy as np

body_path, rig_path, frames_path = sys.argv[1:4]
label = sys.argv[4] if len(sys.argv) > 4 else frames_path
seconds = float(sys.argv[5]) if len(sys.argv) > 5 else 6.0
skip_s = float(sys.argv[6]) if len(sys.argv) > 6 else 1.5
d = np.load(body_path, allow_pickle=True)
pos = d['pos']; wb = d['w_bone']; wv = d['w_vert']; ww = d['w_weight']; bnames = list(d['bones']); vmat = d['vmat']; mats = list(d['mats'])
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
    vw[int(v)][str(bnames[b])] = float(w)
import re
YS = any(str(m).startswith('body_geo') for m in mats)   # (Young Sephiroth's npz: its body section; else a cooked model's)
if YS:
    isbody = np.array([mats[m].startswith('body_geo') if m >= 0 else False for m in vmat])
    coat_v = np.array([v for v in range(nv) if isbody[v] and any('Coat' in n for n in vw[v])])
else:
    isbody = np.ones(nv, dtype=bool)
    COAT = re.compile(r'((Coat|Skirt|Mantle|Cape)[A-Z]*_[a-z]_Phy|MantLg[A-Z][0-9]+)$')
    coat_v = np.array([v for v in range(nv) if sum(w for n, w in vw[v].items() if COAT.search(n)) > 0.5])
K = 6
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
    elif part == 'calf':
        bone, child = side + '_Foreleg_a', side + '_Foot_a'
        group = re.compile(r'^%s_(Foreleg_a|Calf[A-Z]?_Spo|Knee_Spo|Foot_a)$' % side)
    else:
        bone, child = side + '_Foot_a', side + '_Toe_a'
        group = re.compile(r'^%s_(Foot_a|Toe_a)$' % side)
    bi = index[bone]
    sel = [v for v in range(nv) if isbody[v] and sum(w for n, w in vw[v].items() if group.search(n)) > 0.5 and not any('Coat' in n for n in vw[v])]
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


def depth_of(local, length, ax, e1, e2, m):
    tt = local @ ax / length
    radial = local - np.outer(local @ ax, ax)
    r = np.linalg.norm(radial, axis=1)
    ang = np.arctan2(radial @ e2, radial @ e1)
    ok = (tt >= 0) & (tt <= 1)
    ti = np.clip((tt * m.shape[0]).astype(int), 0, m.shape[0] - 1); ai = ((ang + np.pi) / (2 * np.pi) * m.shape[1]).astype(int) % m.shape[1]
    return np.where(ok, m[ti, ai] - r, -1e9)


maps = {(s, p): height_map(s, p) for s in 'LR' for p in ('thigh', 'calf', 'foot') if s + '_Toe_a' in index or p != 'foot'}
raw = np.fromfile(frames_path, dtype=np.float32)
nb, nf = int(raw[:1].view(np.int32)[0]), int(raw[1:2].view(np.int32)[0])
F = raw[2:].reshape(nf, nb, 7).astype(np.float64)
assert nb == len(names), (nb, len(names))
fps = nf / seconds
start = int(skip_s * fps)
prev_local = {}
import os
DETAIL = os.environ.get('DETAIL')
DETAILS = {}
inside_vf = 0; through_vf = 0; total_vf = 0
frames_through = 0; frames_inside = 0
max_depth = 0.0
for f in range(nf):
    q = F[f, :, :4]; t = F[f, :, 4:]
    qb = qmul(q[cb], qinv(refq[cb]))
    vv = qrot(qb, coat_ref[:, None, :] - reft[cb]) + t[cb]
    sk = (vv * cw[..., None]).sum(axis=1)
    locals_now = {}
    pen = np.full(len(coat_v), -1e9)
    thr = np.zeros(len(coat_v), dtype=bool)
    for key, (bi, length, ax, e1, e2, m) in maps.items():
        local = qrot(qinv(q[bi])[None, :], sk - t[bi])
        locals_now[key] = local
        dnow = depth_of(local, length, ax, e1, e2, m)
        pen = np.maximum(pen, dnow)
        if f > start and key in prev_local:
            before = prev_local[key]
            dbefore = depth_of(before, length, ax, e1, e2, m)
            crossed = np.zeros(len(coat_v), dtype=bool)
            for a in np.linspace(0.125, 0.875, 7):
                mid = before + (local - before) * a
                crossed |= depth_of(mid, length, ax, e1, e2, m) > 0.5
            thr |= crossed & (dnow <= 0) & (dbefore <= 0)
    prev_local = locals_now
    if f < start:
        continue
    total_vf += len(coat_v)
    inside_vf += int((pen > 0).sum())
    through_vf += int(thr.sum())
    if thr.any() and DETAIL:
        for v in np.where(thr)[0][:400]:
            dom = max(vw[coat_v[v]].items(), key=lambda x: x[1])[0]
            DETAILS.setdefault(dom, []).append((f, round(float(sk[v][2]), 1)))
    frames_through += int(thr.any())
    frames_inside += int((pen > 1.0).any())
    for key in maps:
        pass
    max_depth = max(max_depth, float(pen.max()))
print('%-30s inside a leg %.2f%% of vertex-frames (max %.1f cm, %d frames > 1 cm); THROUGH a leg %d vertex-frames in %d frames of %d' % (
    label, 100.0 * inside_vf / max(total_vf, 1), max_depth, frames_inside, through_vf, frames_through, nf - start))
if DETAIL:
    for dom, items in sorted(DETAILS.items(), key=lambda x: -len(x[1]))[:15]:
        fr = sorted(set(f for f, _ in items))
        print('   %-18s %4d vertex-frames, frames %s, heights %.0f - %.0f' % (dom, len(items), fr[:12], min(z for _, z in items), max(z for _, z in items)))
