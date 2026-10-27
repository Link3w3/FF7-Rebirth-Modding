import sys; sys.path.insert(0, '/work/ys')
import numpy as np, json
from sheets import tip, ix, d, mw

def catalog(name, thr=14.0, gap=0.10):
    c = d['clips'][name]; W = c['W']; fps = c['fps']; nf = len(W)
    tp = tip(W)
    v = np.r_[np.zeros((1, 3)), np.diff(tp, axis=0) * fps] / 100.0
    sp = np.linalg.norm(v, axis=-1)
    root = W[:, ix['root'], :3, 3]
    hip = W[:, ix['hip'], 2, 3]
    out = []
    for f in range(1, nf - 1):
        if sp[f] >= thr and sp[f] >= sp[f - 1] and sp[f] > sp[f + 1]:
            t = f / fps
            if out and t - out[-1]['t'] < gap:
                if sp[f] > out[-1]['speed']:
                    out[-1] = None
                else:
                    continue
            if out and out[-1] is None:
                out.pop()
            # direction of the swing in the root's frame (yaw of the root)
            R = W[f, ix['root'], :3, :3]
            vl = R.T @ v[f]
            n = vl / (np.linalg.norm(vl) + 1e-9)
            dirn = []
            if n[2] < -0.5: dirn.append('down')
            if n[2] > 0.5: dirn.append('up')
            if n[1] > 0.5: dirn.append('left')
            if n[1] < -0.5: dirn.append('right')
            if n[0] > 0.5: dirn.append('fwd')
            if n[0] < -0.5: dirn.append('back')
            tl = R.T @ (tp[f] - root[f])
            out.append(dict(t=round(t, 2), speed=round(float(sp[f]), 1), dir='-'.join(dirn) or 'mixed', hip=round(float(hip[f])), tipz=round(float(tl[2])),
                            tipx=round(float(tl[0])), rootv=round(float(np.linalg.norm(root[min(f + 1, nf - 1), :2] - root[f - 1, :2]) * fps / 200), 1)))
    return [o for o in out if o]

if __name__ == '__main__':
    cat = {}
    for name in sorted(d['clips']):
        if name.startswith(('skill', 'win', '5star', 'chant', 'status', 'damage', 'longstep', 'step', 'die')):
            cat[name] = catalog(name)
    json.dump(cat, open('blows.json', 'w'), indent=0)
    for name in sorted(cat):
        if not name.startswith('skill'): continue
        L = (len(d['clips'][name]['W']) - 1) / 30
        print('%s %.2fs: ' % (name, L) + ' | '.join('%.2f %d %s h%d tip(%d,%d)%s' % (b['t'], b['speed'], b['dir'], b['hip'], b['tipx'], b['tipz'], (' run%.0f' % b['rootv']) if b['rootv'] > 1 else '') for b in cat[name]))
