"""How far a model's hair (its vertices skinned to Hair chain bones) goes into its body in an offline run (preset_run's
frames, with its battle-run lean, arm swing and chest twist): the hair's vertices skinned with each frame's bone
transforms, against height maps of the torso (C_Spine_a up to the neck, its shoulder pads included), the upper arms and
the forearms: each part's vertices' farthest reach from the part's axis, by place along it and angle round it, in the
part's bone space. A hair vertex that starts inside a map (the reference pose: the maps' bins are coarse) counts only
by how much deeper it goes.
    hair_check.py body.npz rig.json frames.bin [label]"""
import json, os, re, sys
from collections import defaultdict
import numpy as np

body_path, rig_path, frames_path = sys.argv[1:4]
label = sys.argv[4] if len(sys.argv) > 4 else frames_path
d = np.load(body_path, allow_pickle=True)
pos = d['pos']; wb = d['w_bone']; wv = d['w_vert']; ww = d['w_weight']; bnames = [str(b) for b in d['bones']]
rig = json.load(open(rig_path))
names = [b['name'] for b in rig['bones']]
index = {n: i for i, n in enumerate(names)}
parent = {b['name']: b.get('parent') for b in rig['bones']}
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


def under(bone, top):
    while bone:
        if bone == top:
            return True
        bone = parent.get(bone)
    return False


nv = len(pos)
vw = defaultdict(dict)
for b, v, w in zip(wb, wv, ww):
    vw[int(v)][bnames[b]] = vw[int(v)].get(bnames[b], 0.0) + float(w)
dominant = [max(vw[v].items(), key=lambda x: x[1])[0] if vw[v] else '' for v in range(nv)]

HAIR = re.compile(r'Hair[A-Za-z]*_[a-z]_Phy$')
hair_v = np.array([v for v in range(nv) if sum(w for n, w in vw[v].items() if HAIR.search(n)) > 0.5])
K = 8
hb = np.zeros((len(hair_v), K), dtype=np.int64); hw = np.zeros((len(hair_v), K))
for i, v in enumerate(hair_v):
    items = [(n, w) for n, w in sorted(vw[v].items(), key=lambda x: -x[1]) if n in index][:K]
    s = sum(w for _, w in items)
    for k, (n, w) in enumerate(items):
        hb[i, k] = index[n]; hw[i, k] = w / s
hair_ref = pos[hair_v]
hair_root = [names[hb[i, 0]] for i in range(len(hair_v))]


def part_vertices(kind, side=''):
    out = []
    for v in range(nv):
        n = dominant[v]
        if not n or n not in index or n.endswith('_Phy'):
            continue
        if kind == 'torso':
            if under(n, 'C_Spine_a') and not under(n, 'C_Head_a') and not re.search(r'UpperArm|Forearm|Hand|Elbow|Deltoid|Wrist|Finger|Thumb|Index|Middle|Ring|Pinky', n) \
                    and not any(under(n, s + '_UpperArm_a') for s in 'LR'):
                out.append(v)
        elif kind == 'upperarm':
            if under(n, side + '_UpperArm_a') and not under(n, side + '_Forearm_a'):
                out.append(v)
        elif kind == 'forearm':
            if under(n, side + '_Forearm_a') and not under(n, side + '_Hand_a'):
                out.append(v)
    return np.array(out)


def solid(frame, a, b, sel, h=0.8, shell=3):
    """The part as a solid in the frame bone's space: its vertices in a grid aligned with the a -> b axis (h cm cells),
    each marked with the cells within `shell` cells of it (closing the surface), and each slice across the axis filled
    inside its closed rings (an open slice, where an excluded part joined it, stays a shell); a cell's depth is its
    distance to the outside less the shell's."""
    from scipy import ndimage
    bi = index[frame]
    local = qrot(qinv(refq[bi]), pos[sel] - reft[bi])
    origin = qrot(qinv(refq[bi]), reft[index[a]] - reft[bi])
    axis = qrot(qinv(refq[bi]), reft[index[b]] - reft[index[a]])
    length = np.linalg.norm(axis); ax = axis / length
    up = np.array([0.0, 0.0, 1.0]) if abs(ax[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    e1 = np.cross(ax, up); e1 /= np.linalg.norm(e1); e2 = np.cross(ax, e1)
    basis = np.stack([e1, e2, ax])   # rows: the grid's axes in the bone's space
    g = (local - origin) @ basis.T
    keep = (g[:, 2] >= -2.0) & (g[:, 2] <= length + 2.0)
    g = g[keep]
    lo = g.min(0) - 3 * h * (shell + 2); hi = g.max(0) + 3 * h * (shell + 2)
    dims = np.ceil((hi - lo) / h).astype(int) + 1
    occ = np.zeros(dims, dtype=bool)
    ix = np.floor((g - lo) / h).astype(int)
    occ[ix[:, 0], ix[:, 1], ix[:, 2]] = True
    ball = ndimage.generate_binary_structure(3, 3)
    occ = ndimage.binary_dilation(occ, structure=ball, iterations=shell)
    filled = np.zeros_like(occ)
    for k in range(dims[2]):
        filled[:, :, k] = ndimage.binary_fill_holes(occ[:, :, k])
    depth = ndimage.distance_transform_edt(filled) * h - shell * h
    if os.environ.get('HC_DEBUG'):
        closed = sum(1 for k in range(dims[2]) if filled[:, :, k].sum() > occ[:, :, k].sum() * 1.5)
        print('  %s: %d vertices, grid %s, slices filled inside %d of %d, deepest %.1f cm' % (frame, len(g), tuple(dims), closed, dims[2], depth.max()))
    return bi, origin, basis, lo, h, depth


maps = {'torso': solid('C_Spine_b', 'C_Spine_a', 'C_Neck_a', part_vertices('torso'))}
for s in 'LR':
    if s + '_UpperArm_a' in index and s + '_Forearm_a' in index and s + '_Hand_a' in index:
        maps[s + ' upper arm'] = solid(s + '_UpperArm_a', s + '_UpperArm_a', s + '_Forearm_a', part_vertices('upperarm', s))
        maps[s + ' forearm'] = solid(s + '_Forearm_a', s + '_Forearm_a', s + '_Hand_a', part_vertices('forearm', s))


def depths(q, t, sk):
    out = {}
    for name, (bi, origin, basis, lo, h, depth) in maps.items():
        local = qrot(qinv(q[bi])[None, :], sk - t[bi]) - origin
        g = local @ basis.T
        ix = np.floor((g - lo) / h).astype(int)
        ok = np.all((ix >= 0) & (ix < np.array(depth.shape)), axis=1)
        dd = np.full(len(sk), -1e9)
        dd[ok] = depth[ix[ok, 0], ix[ok, 1], ix[ok, 2]]
        dd[ok & (dd <= -shell_floor)] = -1e9
        out[name] = dd
    return out


shell_floor = 1e8


raw = np.fromfile(frames_path, dtype=np.float32)
nb, nf = int(raw[:1].view(np.int32)[0]), int(raw[1:2].view(np.int32)[0])
F = raw[2:].reshape(nf, nb, 7).astype(np.float64)
assert nb == len(names), (nb, len(names))
fps_guess = nf / 6.0
rest = depths(refq, reft, hair_ref)
rest_depth = {k: np.maximum(v, 0.0) for k, v in rest.items()}
per_part = {k: [] for k in maps}
pen_all = []
worst = (0.0, None, None)
for f in range(nf):
    q = F[f, :, :4]; t = F[f, :, 4:]
    qb = qmul(q[hb], qinv(refq[hb]))
    vv = qrot(qb, hair_ref[:, None, :] - reft[hb]) + t[hb]
    sk = (vv * hw[..., None]).sum(axis=1)
    if f < int(1.5 * fps_guess):
        continue
    dd = depths(q, t, sk)
    pen = np.zeros(len(hair_v))
    for k, v in dd.items():
        p = np.maximum(0.0, v - rest_depth[k])
        per_part[k].append(p)
        pen = np.maximum(pen, p)
    pen_all.append(pen)
    if pen.max() > worst[0]:
        i = int(np.argmax(pen))
        worst = (pen.max(), f, hair_root[i])
P = np.concatenate(pen_all)
if os.environ.get('HC_CHAINS'):
    A = np.stack(pen_all)   # frames x vertices
    chain = np.array([re.sub(r'_[a-z]_Phy$', '', h) for h in hair_root])
    rows = []
    for c in sorted(set(chain)):
        m = chain == c
        sub = A[:, m]
        rows.append((float((sub > 2.0).mean()), float(sub.max()), c, int(m.sum())))
    for share, mx, c, k in sorted(rows, reverse=True)[:8]:
        if mx > 0.5:
            print('    %-18s %5d verts: > 2 cm %.2f%% of its vertex-frames, max %.1f cm' % (c, k, 100 * share, mx))
inside = P > 0.25
parts = ', '.join('%s %.2f%%' % (k, 100.0 * (np.concatenate(v) > 0.25).mean()) for k, v in per_part.items())
print('%-24s hair verts %d, frames %d: inside the body %.2f%% of vertex-frames (%s); depth 95%% %.2f cm, 99%% %.2f, max %.2f (frame %s, %s); frames with any > 2 cm: %d of %d' % (
    label, len(hair_v), len(pen_all), 100.0 * inside.mean(), parts, np.percentile(P, 95), np.percentile(P, 99), P.max(), worst[1], worst[2],
    sum(1 for p in pen_all if p.max() > 2.0), len(pen_all)))
