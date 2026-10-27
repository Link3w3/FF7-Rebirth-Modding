"""PC0010_18's offline kawaii runs (anim_run's bins) against the animated pose without the physics (the clip on his bones,
Neo Bahamut's loop added on the wing and tail bones as the solver adds it): for each node, how far its bones move from
that pose (cm, the tips), the bones' length kept, the tail's height and its clearance from his legs, NaNs.
    analyze.py <rig.json> <compat.json> <samples.json> <clip> <run.bin> [--fps 60]"""
import json
import sys
import numpy as np


def qmul(a, b):
    ax, ay, az, aw = np.moveaxis(a, -1, 0)
    bx, by, bz, bw = np.moveaxis(b, -1, 0)
    return np.stack([aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx,
                     aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz], -1)


def qinv(q):
    return q * np.array([-1, -1, -1, 1.0])


def qrot(q, v):
    x, y, z, w = np.moveaxis(q, -1, 0)
    vx, vy, vz = np.moveaxis(v, -1, 0)
    tx = 2 * (y * vz - z * vy); ty = 2 * (z * vx - x * vz); tz = 2 * (x * vy - y * vx)
    return np.stack([vx + w * tx + (y * tz - z * ty), vy + w * ty + (z * tx - x * tz), vz + w * tz + (x * ty - y * tx)], -1)


def nlerp(a, b, t):
    if np.dot(a, b) < 0:
        b = -b
    q = a + (b - a) * t
    return q / np.linalg.norm(q)


def slerp(a, b, t):
    d = float(np.dot(a, b))
    if d < 0:
        b, d = -b, -d
    if d > 0.9995:
        return nlerp(a, b, t)
    th = np.arccos(d)
    return (np.sin((1 - t) * th) * a + np.sin(t * th) * b) / np.sin(th)


def load_run(path):
    raw = np.fromfile(path, dtype=np.float32)
    n, frames = raw[:2].view(np.int32)
    return raw[2:].reshape(frames, n, 7)


def kinematic(rig, entry, samples, clip, frames, fps):
    names = [b['name'] for b in rig['bones']]
    ix = {n: i for i, n in enumerate(names)}
    par = [ix[b['parent']] if b['parent'] else -1 for b in rig['bones']]
    lq0 = np.array([b['local_q'] for b in rig['bones']])
    lt0 = np.array([b['local_t'] for b in rig['bones']])
    c = samples[clip]
    cb = [ix.get(b, -1) for b in c['bones']]
    poses = np.array(c['poses'])
    nf = len(poses)
    length = c['length']
    trans = ix['Trans']
    hip = ix['C_Hip_a']
    tk = c['bones'].index('Trans') if 'Trans' in c['bones'] else -1
    travel = poses[-1, tk, 4:] - poses[0, tk, 4:] if tk >= 0 else np.zeros(3)
    anim = {}
    for node in entry['nodes']:
        pa = node.get('pose_animation')
        if not pa:
            continue
        for bone, keys in pa['tracks'].items():
            anim[ix[bone]] = (np.array(keys), pa['fps'] * pa.get('speed', 1.0), pa.get('additive', False))
    out = np.zeros((frames, len(names), 7))
    for f in range(frames):
        t = f / fps
        playing = max(0.0, t - 1.0)
        loops = np.floor(playing / length)
        at = (playing - loops * length) / length * (nf - 1)
        k0 = min(nf - 1, int(at)); k1 = min(nf - 1, k0 + 1); w = at - k0
        lq = lq0.copy(); lt = lt0.copy(); root = np.zeros(3)
        for k, b in enumerate(cb):
            if b < 0:
                continue
            a, d = poses[k0, k], poses[k1, k]
            tt = a[4:] + (d[4:] - a[4:]) * w
            if b == trans:
                root = tt - poses[0, k, 4:] + travel * loops
                continue
            lq[b] = nlerp(a[:4], d[:4], w)
            if b == hip:
                lt[b] = tt
        for b, (keys, kfps, additive) in anim.items():
            fr = (t * kfps) % len(keys)
            i0 = int(fr) % len(keys); i1 = (i0 + 1) % len(keys)
            key = slerp(keys[i0], keys[i1], fr - np.floor(fr))
            if additive:
                lq[b] = qmul(lq[b], qmul(qinv(keys[0]), key))
                lq[b] /= np.linalg.norm(lq[b])
            else:
                lq[b] = key
        R = np.zeros((len(names), 4)); P = np.zeros((len(names), 3))
        for i in range(len(names)):
            p = par[i]
            if p < 0:
                R[i] = lq[i]; P[i] = lt[i]
            else:
                R[i] = qmul(R[p], lq[i]); P[i] = qrot(R[p], lt[i]) + P[p]
        out[f, :, :4] = R
        out[f, :, 4:] = P   # (component space, as anim_run writes it)
    return out, names, par


def chain(rig_by_kids, root):
    out, stack = [], [root]
    while stack:
        x = stack.pop()
        out.append(x)
        stack.extend(rig_by_kids.get(x, []))
    return out


def main():
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    fps = 60.0
    rig = json.load(open(a[0]))
    entry = json.load(open(a[1]))['kawaii'][0]
    samples = json.load(open(a[2]))
    clip = a[3]
    run = load_run(a[4])
    frames = run.shape[0]
    kin, names, par = kinematic(rig, entry, samples, clip, frames, fps)
    ix = {n: i for i, n in enumerate(names)}
    kids = {}
    for i, p in enumerate(par):
        if p >= 0:
            kids.setdefault(names[p], []).append(names[i])
    print('%s: %d frames, NaN %s' % (clip, frames, bool(np.isnan(run).any())))
    ref = np.array([b['t'] for b in rig['bones']])
    settle = int(fps * 1.0)
    for node in entry['nodes']:
        bones = [ix[b] for b in chain(kids, node['root_bone'])]
        sim = [b for b in bones if b != ix[node['root_bone']]]
        if not sim:
            continue
        d = np.linalg.norm(run[settle:, sim, 4:] - kin[settle:, sim, 4:], axis=2)
        # bone lengths (each simulated bone from its parent)
        L0 = np.linalg.norm(ref[sim] - ref[[par[b] for b in sim]], axis=1)
        L = np.linalg.norm(run[:, sim, 4:] - run[:, [par[b] for b in sim], 4:], axis=2)
        stretch = np.abs(L - L0[None]) / np.maximum(L0[None], 1e-3)
        stretch = stretch[:, L0 > 0.5]
        worst = int(np.argmax(d.max(0)))
        print('  %-26s off pose: mean %5.1f  p95 %5.1f  max %5.1f cm (%s)  stretch max %.3f' % (
            node['name'][:26], d.mean(), np.percentile(d, 95), d.max(), names[sim[worst]], stretch.max() if stretch.size else 0))
    # the tail: its lowest point above the floor (the component's z), its clearance from the legs' axes
    tail = [ix[b] for b in chain(kids, 'C_Tail_a')]
    z = run[:, tail, 6]
    zk = kin[:, tail, 6]
    print('  tail lowest z: sim %.1f  pose %.1f' % (z[settle:].min(), zk[settle:].min()))
    for b in ('C_Hip_a', 'C_Head_a', 'L_Hand_a', 'L_Foot_a'):
        print('  check %s: run vs pose %.3f cm' % (b, np.abs(run[:, ix[b], 4:] - kin[:, ix[b], 4:]).max()))


if __name__ == '__main__':
    main()
