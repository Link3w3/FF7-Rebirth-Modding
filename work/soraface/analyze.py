import json, os, glob, math
import numpy as np
SB = json.load(open('/work/sora1018/data/sora_bones.json'))
BY = {b['name']: b for b in SB}
NAMES = [b['name'] for b in SB]
PAR = [b['parent'] for b in SB]
def qmul(a, b):
    ax, ay, az, aw = np.moveaxis(a, -1, 0); bx, by, bz, bw = np.moveaxis(b, -1, 0)
    return np.stack([aw*bx + ax*bw + ay*bz - az*by, aw*by - ax*bz + ay*bw + az*bx, aw*bz + ax*by - ay*bx + az*bw, aw*bw - ax*bx - ay*by - az*bz], -1)
def qrot(q, v):
    x, y, z, w = np.moveaxis(q, -1, 0); vx, vy, vz = np.moveaxis(v, -1, 0)
    tx = 2*(y*vz - z*vy); ty = 2*(z*vx - x*vz); tz = 2*(x*vy - y*vx)
    return np.stack([vx + w*tx + (y*tz - z*ty), vy + w*ty + (z*tx - x*tz), vz + w*tz + (x*ty - y*tx)], -1)
FACIAL = BY['facial']['i']
SUB = [i for i in range(len(SB)) if i != FACIAL and FACIAL in (lambda i: [p for p in iter(lambda c=[i]: (c.append(PAR[c[-1]]) or c[-1]) if PAR[c[-1]] >= 0 else None, None)])(i)]
def descendants(root):
    out = []
    for i in range(len(SB)):
        p = PAR[i]
        while p >= 0 and p != root:
            p = PAR[p]
        if p == root:
            out.append(i)
    return out
SUB = descendants(FACIAL)
REFQ = np.array([b['q'] for b in SB]); REFT = np.array([b['t'] for b in SB])
FQ = np.array(BY['facial']['csq']); FT = np.array(BY['facial']['cst'])
def fk(tracks, nframes):
    """component-space positions of the face bones per frame, the facial bone held at its ref placement."""
    S = nframes
    LQ = {i: np.repeat(REFQ[i][None], S, 0) for i in SUB}; LT = {i: np.repeat(REFT[i][None], S, 0) for i in SUB}
    for name, tr in tracks.items():
        i = BY[name]['i'] if name in BY else None
        if i is None or i not in LQ: continue
        q = np.array(tr['q']); p = np.array(tr['p'])
        LQ[i] = q if len(q) == S else np.repeat(q[:1], S, 0)
        LT[i] = p if len(p) == S else np.repeat(p[:1], S, 0)
    GQ = {FACIAL: np.repeat(FQ[None], S, 0)}; GT = {FACIAL: np.repeat(FT[None], S, 0)}
    for i in sorted(SUB):
        p = PAR[i]
        GQ[i] = qmul(GQ[p], LQ[i]); GT[i] = GT[p] + qrot(GQ[p], LT[i])
    return {NAMES[i]: GT[i] for i in GT}, {NAMES[i]: GQ[i] for i in GQ}
REF_P, REF_Q = fk({}, 1)
def eye_dir(q):
    # the eye's look: its rest forward (+X in component space at ref) turned by the change from the ref
    return q
def features(P, Q):
    f = {}
    up = lambda n: P[n][:, 2] - REF_P[n][0, 2]
    gap = lambda a, b: np.linalg.norm(P[a] - P[b], axis=-1)
    rgap = lambda a, b: np.linalg.norm(REF_P[a][0] - REF_P[b][0])
    f['lidR'] = gap('RU_eyelid_b', 'RD_eyelid_b') / rgap('RU_eyelid_b', 'RD_eyelid_b')
    f['lidL'] = gap('LU_eyelid_b', 'LD_eyelid_b') / rgap('LU_eyelid_b', 'LD_eyelid_b')
    f['mouth'] = gap('CU_lip', 'CD_lip') - rgap('CU_lip', 'CD_lip')
    f['corner'] = (up('RU_cor') + up('LU_cor')) / 2
    f['cornerAsym'] = up('RU_cor') - up('LU_cor')
    f['wide'] = gap('RU_cor', 'LU_cor') - rgap('RU_cor', 'LU_cor')
    f['browIn'] = (up('R_brow_a') + up('L_brow_a')) / 2
    f['browOut'] = (up('R_brow_d') + up('L_brow_d')) / 2
    f['browAsym'] = (up('R_brow_a') + up('R_brow_d')) / 2 - (up('L_brow_a') + up('L_brow_d')) / 2
    f['cheek'] = (up('R_cheek_a') + up('L_cheek_a')) / 2
    f['upperLip'] = up('CU_lip')
    # eye look: rotation of R_eye/L_eye vs ref, as yaw/pitch of their rest forward (+X)
    def look(n):
        q = Q[n]; r = REF_Q[n][0]
        rel = qmul(q, np.array([-r[0], -r[1], -r[2], r[3]])[None].repeat(len(q), 0))
        v = qrot(rel, np.array([1.0, 0, 0])[None].repeat(len(q), 0))
        return np.degrees(np.arctan2(v[:, 1], v[:, 0])), np.degrees(np.arcsin(np.clip(v[:, 2], -1, 1)))
    yr, pr = look('R_eye'); yl, pl = look('L_eye')
    f['eyeYaw'] = (yr + yl) / 2; f['eyePitch'] = (pr + pl) / 2
    return f
rows = []
for path in sorted(glob.glob(os.environ.get('TRACKS','tracks') + '/*.json')):
    d = json.load(open(path))
    S = d['frames']
    P, Q = fk(d['bones'], S)
    f = features(P, Q)
    lid = np.minimum(f['lidR'], f['lidL'])
    summ = dict(name=d['name'], frames=S, secs=round(d['length'], 2))
    for k, v in f.items():
        summ[k] = (float(np.min(v)), float(np.mean(v)), float(np.max(v)))
    summ['blinks'] = int(np.sum((lid[1:] < 0.35) & (lid[:-1] >= 0.35)))
    rows.append(summ)
json.dump(rows, open('features.json', 'w'), indent=1)
def fm(t): return '%+5.2f/%+5.2f/%+5.2f' % t
print('%-9s %4s %5s %-18s %-18s %-18s %-18s %-18s %-18s %-18s %-12s %-12s %s' % ('name', 'frm', 'sec', 'lidR min/mean/max', 'mouth', 'corner', 'wide', 'browIn', 'browOut', 'cheek', 'eyeYaw', 'eyePitch', 'blinks'))
for r in rows:
    print('%-9s %4d %5.2f %-18s %-18s %-18s %-18s %-18s %-18s %-18s %-12s %-12s %d' % (r['name'][2:], r['frames'], r['secs'], fm(r['lidR']), fm(r['mouth']), fm(r['corner']), fm(r['wide']),
          fm(r['browIn']), fm(r['browOut']), fm(r['cheek']), '%+4.0f/%+4.0f' % (r['eyeYaw'][0], r['eyeYaw'][2]), '%+4.0f/%+4.0f' % (r['eyePitch'][0], r['eyePitch'][2]), r['blinks']))
