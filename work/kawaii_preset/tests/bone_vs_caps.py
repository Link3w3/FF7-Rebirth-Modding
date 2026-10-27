"""How far a node's chain bones go into its tapered capsules (the solver's own leg shapes) over a run: for each coat
chain, each bone's least clearance (cm: its distance from the capsule's surface less the bone's collision radius;
negative = inside), the frames where any is inside, and the frame/leg of the worst.
    bone_vs_caps.py rig.json frames.bin entry.json [chain regex]"""
import json, re, sys, math
import numpy as np
rig = json.load(open(sys.argv[1])); frames = sys.argv[2]; entry = json.load(open(sys.argv[3]))['kawaii'][0]
want = re.compile(sys.argv[4] if len(sys.argv) > 4 else r'Skirt|Coat')
names = [b['name'] for b in rig['bones']]; idx = {n: i for i, n in enumerate(names)}
raw = np.fromfile(frames, dtype=np.float32)
nb, nf = int(raw[:1].view(np.int32)[0]), int(raw[1:2].view(np.int32)[0])
F = raw[2:].reshape(nf, nb, 7).astype(np.float64)
def qrot(q, v):
    qv = q[..., :3]; t = 2.0 * np.cross(qv, v); return v + q[..., 3:4] * t + np.cross(qv, t)
def from_rotator(p, y, r):
    h = math.pi / 360.0; sp, cp, sy, cy, sr, cr = math.sin(p*h), math.cos(p*h), math.sin(y*h), math.cos(y*h), math.sin(r*h), math.cos(r*h)
    return np.array([cr*sp*sy - sr*cp*cy, -cr*sp*cy - sr*cp*sy, cr*cp*sy - sr*sp*cy, cr*cp*cy + sr*sp*sy])
def curve(c, x):
    if not c: return 1.0
    for (x0, y0), (x1, y1) in zip(c, c[1:]):
        if x <= x1: return y0 + (y1 - y0) * (x - x0) / max(x1 - x0, 1e-9)
    return c[-1][1]
for node in entry['nodes']:
    if not want.search(node['name']):
        continue
    root = node['root_bone']; chain = [root]
    while True:
        kids = [b['name'] for b in rig['bones'] if b['parent'] == chain[-1] and b['name'].endswith('_Phy')]
        if not kids: break
        chain.append(kids[0])
    rads = [node.get('radius', 0) * curve(node.get('radius_curve'), k / max(1, len(chain) - 1)) for k in range(len(chain))]
    caps = node.get('tapered_capsules', [])
    worst = (1e9, None, None, None); inside_frames = 0
    per_bone = [1e9] * len(chain)
    for f in range(90, nf):
        q = F[f, :, :4]; t = F[f, :, 4:]
        any_in = False
        for c in caps:
            bi = idx[c['bone']]; rq = from_rotator(*c['rotation'])
            cen = t[bi] + qrot(q[bi], np.array(c['offset'])); ax = qrot(q[bi], qrot(rq, np.array([0.0, 0.0, 1.0])))
            half = c['length'] / 2.0
            r0, r1 = c['radius1'], c['radius0']   # (-Z end radius1, +Z end radius0)
            for k, b in enumerate(chain):
                p = t[idx[b]] - cen
                s = np.clip(p @ ax, -half, half)
                rr = r0 + (r1 - r0) * (s + half) / (2 * half)
                d = np.linalg.norm(p - s * ax) - rr - rads[k]
                per_bone[k] = min(per_bone[k], d)
                if d < -0.5: any_in = True
                if d < worst[0]: worst = (d, f, c['bone'], b)
        inside_frames += any_in
    print('%-18s bones %d: least clearance by bone %s; frames with a bone > 0.5 cm in: %d of %d; worst %.1f cm (frame %s, %s on %s)' % (
        node['name'], len(chain), ' '.join('%.1f' % v for v in per_bone), inside_frames, nf - 90, worst[0], worst[1], worst[3], worst[2]))
