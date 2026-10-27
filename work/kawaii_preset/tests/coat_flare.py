"""How far the coat flares out standing (the last frame of a standing preset_run): for each coat chain, how far its lower
half's bones sit out from (+) or in toward (-) the body's vertical axis compared with their reference places, horizontally
(cm); the median over the chains of each chain's mean, and the hem's (the last bones') median and largest.
    coat_flare.py rig.json frames.bin"""
import json, re, sys
import numpy as np
rig = json.load(open(sys.argv[1])); frames = sys.argv[2]
names = [b['name'] for b in rig['bones']]; ref = np.array([b['t'] for b in rig['bones']])
raw = np.fromfile(frames, dtype=np.float32)
nb, nf = int(raw[:1].view(np.int32)[0]), int(raw[1:2].view(np.int32)[0])
F = raw[2:].reshape(nf, nb, 7)
last = F[-1, :, 4:].astype(np.float64)
hip = ref[names.index('C_Hip_a')]
groups = {}
for i, n in enumerate(names):
    m = re.match(r'^([LRC]_(?:Coat|Skirt)[A-Z]+)_([a-z])_Phy$', n)
    if m:
        groups.setdefault(m.group(1), []).append((m.group(2), i))
lower, hem = [], []
for g, items in sorted(groups.items()):
    items.sort()
    idx = [i for _, i in items]
    half = idx[len(idx) // 2:]
    def out(i, p):
        h = p[:2] - hip[:2]
        r0 = ref[i][:2] - hip[:2]
        return np.linalg.norm(h) - np.linalg.norm(r0)
    lower.append(np.mean([out(i, last[i]) for i in half]))
    hem.append(out(idx[-1], last[idx[-1]]))
print('coat flare standing: lower halves %+.1f cm (median of %d chains), hem median %+.1f, largest %+.1f' % (
    float(np.median(lower)), len(lower), float(np.median(hem)), float(np.max(hem))))
