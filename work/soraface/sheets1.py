import json, numpy as np, os, sys
import facerender as fr, feats
F = fr.Face()
FACEB = set(feats.FACE)
OUT = '/tmp/scratch/'
names = sorted(os.listdir('all/tracks'))
ims = []
pick = {}
for fn in names:
    tr = json.load(open('all/tracks/' + fn))
    f = feats.features(tr)
    e = (np.abs(f['upLid']) * 0.6 + np.abs(f['loLid']) + np.abs(f['browIn']) + np.abs(f['browOut']) + np.abs(f['corner']) * 1.5
         + np.abs(f['cheek']) + 0.25 * np.abs(f['jaw']) + np.abs(f['browAsym']))
    k = int(np.argmax(e))
    pick[tr['name']] = k
    p = {b: v for b, v in fr.pose_from_track(tr, k).items() if b in FACEB}
    ims.append(F.render(p, scale=11, label='%s f%d/%d' % (tr['name'][2:], k, tr['frames'])))
json.dump(pick, open('peak_frames.json', 'w'))
for s in range(0, len(ims), 40):
    fr.sheet(ims[s:s + 40], 10, OUT + 'overview_%d.png' % (s // 40))
print(len(ims))
