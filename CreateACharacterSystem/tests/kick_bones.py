"""(3.17.0) A kick run's coat BONES against the legs' capsules (the entry's own thigh / calf / feet shapes, placed with each
frame's leg bones): how deep a bone is in one (less its radius), and the frames a bone went through one (its place
relative to the shape's axis on the other side, without being inside it in either frame: tunneling).
    python3 kick_bones.py rig.json entry.json frames.bin [node-name-part = coat] [start frame = 90]"""
import json, math, sys
import numpy as np
sys.path.insert(0, '/work/cacs3180/tools')
from kawaii_feet_sync import qrot, qinv, qmul, from_rotator

rig_path, entry_path, frames_path = sys.argv[1:4]
part = sys.argv[4] if len(sys.argv) > 4 else 'coat'
start = int(sys.argv[5]) if len(sys.argv) > 5 else 90
rig = json.load(open(rig_path)); names = [b['name'] for b in rig['bones']]; index = {n: i for i, n in enumerate(names)}
kids = {}
for b in rig['bones']:
    if b.get('parent'): kids.setdefault(b['parent'], []).append(b['name'])
entry = json.load(open(entry_path))['kawaii'][0]
raw = np.fromfile(frames_path, dtype=np.float32)
nb, nf = int(raw[:1].view(np.int32)[0]), int(raw[1:2].view(np.int32)[0])
F = raw[2:].reshape(nf, nb, 7).astype(np.float64)

def chain(root):
    out, st = [], [root]
    while st:
        x = st.pop(); out.append(x); st.extend(kids.get(x, []))
    return out

nodes = [n for n in entry['nodes'] if part in (n.get('name') or '')]
bones = set()
shapes = []
for n in nodes:
    roots = [n['root_bone']] + [r if isinstance(r, str) else r.get('root_bone') for r in n.get('additional_root_bones', [])]
    for r in roots: bones.update(chain(r))
    for s in n.get('tapered_capsules', []) + [dict(c, radius0=c['radius'], radius1=c['radius']) for c in n.get('capsules', [])]:
        key = (s['bone'], tuple(s['offset']), tuple(s.get('rotation', [0, 0, 0])))
        if key not in [k for k, _ in shapes]: shapes.append((key, s))
roots_all = set()
for n in nodes:
    roots_all.update([n['root_bone']] + [r if isinstance(r, str) else r.get('root_bone') for r in n.get('additional_root_bones', [])])
bones = sorted(b for b in bones if b in index and b not in roots_all)
radius = 2.2
def place(f, s):
    q = list(F[f, index[s['bone']], :4]); t = F[f, index[s['bone']], 4:]
    off = qrot(q, s['offset'])
    c = np.array([t[i] + off[i] for i in range(3)])
    qs = qmul(q, from_rotator(*s.get('rotation', [0, 0, 0])))
    ax = np.array(qrot(qs, [0, 0, 1]))
    return c + ax * s['length'] / 2, c - ax * s['length'] / 2, s['radius0'], s['radius1']
def dist(p, sh):
    a, b, r0, r1 = sh
    seg = b - a; t = np.clip(((p - a) @ seg) / (seg @ seg), 0, 1)
    cl = a + np.outer(t, seg); rr = r0 + (r1 - r0) * t
    return np.linalg.norm(p - cl, axis=1) - rr - radius, cl
bi = np.array([index[b] for b in bones])
deep = 0.0; through = 0; inside_bf = 0; total = 0
prev = None
for f in range(start, nf):
    P = F[f, bi, 4:]
    now = []
    for key, s in shapes:
        sh = place(f, s)
        d, cl = dist(P, sh)
        now.append((sh, d, P - cl))
        inside_bf += int((d < -0.5).sum()); deep = max(deep, float(-d.min()))
    if prev is not None:
        for (sh, d, rel), (psh, pd, prel) in zip(now, prev):
            # went to the axis's other side (the radial direction flipped) while outside in both frames
            flip = (np.einsum('ij,ij->i', rel, prel) < 0) & (d > -0.5) & (pd > -0.5) & (np.linalg.norm(rel, axis=1) < 40)
            through += int(flip.sum())
    prev = now
    total += len(bones)
# at rest (the second before the kicks)
rest_in = 0
for f in range(30, 60):
    P = F[f, bi, 4:]
    for key, sh0 in shapes:
        d, cl = dist(P, place(f, sh0)); rest_in += int((d < -0.5).sum())
print('at rest: inside a shape %d bone-frames of %d' % (rest_in, 30 * len(bones)))
from collections import Counter
worst = Counter()
for f in range(start, nf):
    P = F[f, bi, 4:]
    for k, (key, sh0) in enumerate(shapes):
        d, cl = dist(P, place(f, sh0))
        for j in np.where(d < -3.0)[0]: worst[(bones[j], key[0])] += 1
print('deeper than 3 cm (bone, shape bone): frames', worst.most_common(12))
print('%d coat bones, %d shapes: inside a shape %d bone-frames (deepest %.1f cm); through one %d bone-frames' % (len(bones), len(shapes), inside_bf, deep, through))
