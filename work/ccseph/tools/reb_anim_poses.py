"""Rebirth Sephiroth cooked animations (ACL) -> local poses {anim: {frames: [{bone: [qx,qy,qz,qw,tx,ty,tz]}]}} for the bones
the re-rig uses (decoded with the earlier pure-Python ACL reader)."""
import sys, json, numpy as np
sys.path[:0] = ['/work/acl']
import pose
names = json.load(open('/work/ccseph/reb_bones.json'))
out = {}
for a in sys.argv[2:]:
    data = open(a + '.uexp', 'rb').read()
    try:
        c, bones, LQ, LT = pose.load(open(a + '.uasset', 'rb').read() + data)
    except Exception as e:
        try:
            c, bones, LQ, LT = pose.load(data)
        except Exception as e2:
            print(a, 'FAILED', e2); continue
    S = LQ.shape[0]
    frames = []
    for k in np.linspace(0, S - 1, 6).astype(int):
        fr = {}
        for n in names:
            i = pose.IDX.get(n)
            if i is None: continue
            fr[n] = list(map(float, LQ[k, i])) + list(map(float, LT[k, i]))
        frames.append(dict(time=float(k), bones=fr))
    out[a.rsplit('/', 1)[1]] = dict(length=float(S), frames=frames)
    print(a.rsplit('/', 1)[1], S, 'samples', len(bones), 'tracks')
json.dump(out, open(sys.argv[1], 'w'))
