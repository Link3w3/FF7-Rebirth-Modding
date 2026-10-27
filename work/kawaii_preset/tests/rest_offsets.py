"""How far each chain's bones settle from their reference place when the character stands still (the last frame of a
standing ys_skirt run): per chain, the largest offset of its bones (cm) and where the offset points (out/in/down)."""
import json, re, sys
import numpy as np
rig = json.load(open(sys.argv[1])); frames = sys.argv[2]
names = [b['name'] for b in rig['bones']]; ref = np.array([b['t'] for b in rig['bones']])
raw = np.fromfile(frames, dtype=np.float32)
nb, nf = int(raw[:1].view(np.int32)[0]), int(raw[1:2].view(np.int32)[0])
F = raw[2:].reshape(nf, nb, 7)
last = F[-1, :, 4:].astype(np.float64)
groups = {}
for i, n in enumerate(names):
    m = re.match(r'^([LRC]_[A-Za-z]+?)_([a-z])_Phy$', n)
    if m:
        groups.setdefault(m.group(1), []).append(i)
rows = []
for g, idx in sorted(groups.items()):
    off = last[idx] - ref[idx]
    k = int(np.argmax(np.linalg.norm(off, axis=1)))
    i = idx[k]
    p = ref[i]
    outward = np.array([p[0], p[1], 0.0]); outward /= max(np.linalg.norm(outward), 1e-6)
    rows.append((g, float(np.linalg.norm(off[k])), float(off[k] @ outward), float(off[k][2])))
kinds = {}
for g, d, o, z in rows:
    kind = re.sub(r'^[LRC]_', '', g)
    kind = re.sub(r'[A-Z]+$', '', kind) if not kind.startswith('HairLong') else 'HairLong'
    kinds.setdefault(kind, []).append((d, o, z, g))
for kind, vals in kinds.items():
    a = np.array([v[:3] for v in vals])
    worst = max(vals)
    print('%-10s %2d chains: rest offset median %.1f cm, max %.1f (%s: outward %+.1f, down %+.1f)' % (kind, len(vals), np.median(a[:, 0]), worst[0], worst[3], worst[1], -worst[2]))
