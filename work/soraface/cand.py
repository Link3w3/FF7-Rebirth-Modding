import json, sys, numpy as np
import facerender as fr, feats
OUT = '/tmp/scratch/'
_F = None
_T = {}
FACEB = set(feats.FACE)
def face():
    global _F
    if _F is None: _F = fr.Face()
    return _F
def track(name):
    if name not in _T: _T[name] = json.load(open('all/tracks/%s.json' % name))
    return _T[name]
def pose(name, f):
    if name == 'ref': return {}
    return {b: v for b, v in fr.pose_from_track(track(name), f).items() if b in FACEB}
def frames(name, n=6):
    k = track(name)['frames']
    return sorted(set(int(round(x)) for x in np.linspace(0, k - 1, min(n, k))))
def sheet(items, path, cols=8, scale=14):
    ims = []
    for name, f in items:
        lab = 'ref' if name == 'ref' else '%s f%d' % (name[2:], f)
        ims.append(face().render(pose(name, f), scale=scale, label=lab))
    return fr.sheet(ims, cols, OUT + path)
if __name__ == '__main__':
    spec = json.loads(sys.argv[1]); path = sys.argv[2]
    items = []
    for x in spec:
        if isinstance(x, list): items.append((x[0], x[1]))
        else: items += [(x, f) for f in frames(x, 6)]
    print(sheet(items, path))
