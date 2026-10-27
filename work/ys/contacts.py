import sys; sys.path.insert(0, '/work/ys')
import numpy as np, json
from sheets import ix, d, mw

def contacts(name, x0=60, x1=280, ylim=90, z0=20, z1=210, vmin=8.0):
    c = d['clips'][name]; W = c['W']; fps = c['fps']; nf = len(W)
    L = np.array([60, 100, 140, 180.0])
    base = W[:, mw, :3, 3]; ax = W[:, mw, :3, 1]
    pts = base[:, None, :] + ax[:, None, :] * L[None, :, None]          # f, k, 3
    root = W[:, ix['root'], :3, 3]; R = W[:, ix['root'], :3, :3]
    loc = np.einsum('fji,fkj->fki', R, pts - root[:, None, :])            # in the root's frame
    vel = np.r_[np.zeros((1, 4, 3)), np.diff(pts, axis=0) * fps] / 100.0
    sp = np.linalg.norm(vel, axis=-1).max(-1)
    inside = ((loc[..., 0] > x0) & (loc[..., 0] < x1) & (np.abs(loc[..., 1]) < ylim) & (loc[..., 2] > z0) & (loc[..., 2] < z1)).any(-1)
    hit = inside & (sp > vmin)
    # intervals
    out = []
    f = 0
    while f < nf:
        if hit[f]:
            g = f
            while g + 1 < nf and hit[g + 1]:
                g += 1
            k = f + int(np.argmax(sp[f:g + 1]))
            out.append((round(f / fps, 2), round(g / fps, 2), round(k / fps, 2), round(float(sp[k]), 1)))
            f = g + 1
        else:
            f += 1
    return out

if __name__ == '__main__':
    res = {}
    for name in sorted(d['clips']):
        if name.startswith(('skill', 'win', '5star', 'chant', 'step', 'longstep', 'status', 'run')):
            res[name] = contacts(name)
    json.dump(res, open('contacts.json', 'w'))
    for name, cs in res.items():
        if cs:
            print('%-16s %s' % (name, ' '.join('[%.2f-%.2f peak %.2f %.0f]' % c for c in cs)))
