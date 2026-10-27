"""(3.17.0) A kick run's chosen bones in a leg shape's own space, frame by frame: the side of the shape's axis they are on
(the angle round it from the shape's local +X, and the distance from the axis less the shape's radius there).
    python3 kick_trace.py rig.json entry.json frames.bin shape-bone bone[,bone...] first last"""
import json, math, sys
import numpy as np
sys.path.insert(0, '/work/cacs3151/tools')
from kawaii_feet_sync import qrot, qinv, qmul, from_rotator
rig_path, entry_path, frames_path, shape_bone, bones, f0, f1 = sys.argv[1:8]
bones = bones.split(','); f0 = int(f0); f1 = int(f1)
rig = json.load(open(rig_path)); names = [b['name'] for b in rig['bones']]; index = {n: i for i, n in enumerate(names)}
entry = json.load(open(entry_path))['kawaii'][0]
shape = None
for n in entry['nodes']:
    for s in n.get('tapered_capsules', []):
        if s['bone'] == shape_bone: shape = s; break
    if shape: break
raw = np.fromfile(frames_path, dtype=np.float32)
nb, nf = int(raw[:1].view(np.int32)[0]), int(raw[1:2].view(np.int32)[0])
F = raw[2:].reshape(nf, nb, 7).astype(np.float64)
for f in range(f0, f1 + 1):
    q = list(F[f, index[shape_bone], :4]); t = F[f, index[shape_bone], 4:]
    qs = qmul(q, from_rotator(*shape['rotation']))
    c = np.array(t) + np.array(qrot(q, shape['offset']))
    ax = np.array(qrot(qs, [0, 0, 1]))
    a = c + ax * shape['length'] / 2; b = c - ax * shape['length'] / 2
    row = []
    for bn in bones:
        p = F[f, index[bn], 4:]
        seg = b - a; tt = np.clip((p - a) @ seg / (seg @ seg), 0, 1)
        cl = a + seg * tt; rr = shape['radius0'] + (shape['radius1'] - shape['radius0']) * tt
        rel = np.array(qrot(qinv(qs), list(p - cl)))
        ang = math.degrees(math.atan2(rel[1], rel[0]))
        row.append('%s %+5.0fdeg %+5.1f' % (bn.replace('_Phy', ''), ang, np.linalg.norm(p - cl) - rr))
    print('f%3d  ' % f + '   '.join(row))
