"""Runtime wing bone locals (live link probe) against the rig's reference locals (rig_wing.json, component-space frames)."""
import json, sys
import numpy as np
rig = json.load(open('/work/fpys/wing/rig_wing.json'))
probe = json.load(open(sys.argv[1]))
B = {b['name']: b for b in rig['bones']}
def qmul(a, b):
    ax, ay, az, aw = a; bx, by, bz, bw = b
    return np.array([aw*bx + ax*bw + ay*bz - az*by, aw*by - ax*bz + ay*bw + az*bx, aw*bz + ax*by - ay*bx + az*bw, aw*bw - ax*bx - ay*by - az*bz])
def qinv(q): return np.array([-q[0], -q[1], -q[2], q[3]])
def qrot(q, v):
    p = qmul(qmul(q, [v[0], v[1], v[2], 0.0]), qinv(q)); return p[:3]
def ang(a, b):
    d = abs(float(np.dot(a / np.linalg.norm(a), b / np.linalg.norm(b))))
    return np.degrees(2 * np.arccos(min(1.0, d)))
def ref_local(name):
    b = B[name]; p = B[b['parent']] if b['parent'] else None
    q = np.array(b['q']); t = np.array(b['t'])
    if p is None: return q, t
    pq = np.array(p['q']); pt = np.array(p['t'])
    return qmul(qinv(pq), q), qrot(qinv(pq), t - pt)
rows = []
for r in probe['rows']:
    n = r['name']
    if n not in B or not isinstance(r['l'], list): continue
    lq, lt = ref_local(n)
    q = np.array(r['l'][3:7]); t = np.array(r['l'][0:3]); s = np.array(r['l'][7:10])
    a = ang(q, lq)
    dt = np.linalg.norm(t - lt); lt_n = np.linalg.norm(lt)
    rows.append((n, a, dt, lt_n, np.linalg.norm(t), s))
for n, a, dt, ln, rn, s in rows:
    flag = ' <<' if a > 20 or (ln > 1 and abs(rn / ln - 1) > 0.1) or abs(s - 1).max() > 0.02 else ''
    print('%-28s rot off %6.1f deg   len ref %7.2f now %7.2f (moved %6.2f)  scale %s%s' % (n, a, ln, rn, dt, np.round(s, 3), flag))
