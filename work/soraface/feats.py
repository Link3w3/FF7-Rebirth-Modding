"""Per-frame facial features of every KH3 face animation (all/tracks/*.json), relative to Sora's reference pose."""
import glob
import json
import os
import numpy as np
import facerender as fr

FACE = None
FACIAL = fr.IDX['facial']


def under_facial(i):
    p = fr.PAR[i]
    while p >= 0:
        if p == FACIAL:
            return True
        p = fr.PAR[p]
    return False


SUB = [i for i in range(len(fr.NAMES)) if under_facial(i)]
FACE = [fr.NAMES[i] for i in SUB]


def cs_frames(track):
    """component-space positions and rotations of the face bones per frame (head held at the reference)."""
    S = track['frames']
    LQ = {i: np.repeat(fr.REFQ[i][None], S, 0) for i in SUB}
    LT = {i: np.repeat(fr.REFT[i][None], S, 0) for i in SUB}
    for name, tr in track['bones'].items():
        i = fr.IDX.get(name)
        if i is None or i not in LQ:
            continue
        q = np.array(tr['q']); p = np.array(tr['p'])
        LQ[i] = q if len(q) == S else np.repeat(q[:1], S, 0)
        LT[i] = p if len(p) == S else np.repeat(p[:1], S, 0)
    CQ = {FACIAL: np.repeat(fr.REF_CQ[FACIAL][None], S, 0)}
    CT = {FACIAL: np.repeat(fr.REF_CT[FACIAL][None], S, 0)}
    for i in SUB:
        p = fr.PAR[i]
        CQ[i] = fr.qmul(CQ[p], LQ[i]); CT[i] = CT[p] + fr.qrot(CQ[p], LT[i])
    return CQ, CT


def disp(CT, n):
    return CT[fr.IDX[n]] - fr.REF_CT[fr.IDX[n]][None]


def eye_angles(CQ, n):
    i = fr.IDX[n]
    rel = fr.qmul(CQ[i], np.repeat(fr.qinv(fr.REF_CQ[i])[None], len(CQ[i]), 0))
    v = fr.qrot(rel, np.repeat(np.array([[1.0, 0, 0]]), len(rel), 0))
    return np.degrees(np.arctan2(v[:, 1], v[:, 0])), np.degrees(np.arcsin(np.clip(v[:, 2], -1, 1)))


def features(track):
    CQ, CT = cs_frames(track)
    z = lambda n: disp(CT, n)[:, 2]
    y = lambda n: disp(CT, n)[:, 1]
    f = {}
    f['upLid'] = np.mean([z(n) for n in ('RU_eyelid_a', 'RU_eyelid_b', 'RU_eyelid_c', 'LU_eyelid_a', 'LU_eyelid_b', 'LU_eyelid_c')], 0)
    f['upLidR'] = np.mean([z(n) for n in ('RU_eyelid_a', 'RU_eyelid_b', 'RU_eyelid_c')], 0)
    f['upLidL'] = np.mean([z(n) for n in ('LU_eyelid_a', 'LU_eyelid_b', 'LU_eyelid_c')], 0)
    f['loLid'] = np.mean([z(n) for n in ('RD_eyelid_a', 'RD_eyelid_b', 'RD_eyelid_c', 'LD_eyelid_a', 'LD_eyelid_b', 'LD_eyelid_c')], 0)
    f['browIn'] = (z('R_brow_a') + z('L_brow_a')) / 2
    f['browMid'] = (z('R_brow_b') + z('L_brow_b') + z('R_brow_c') + z('L_brow_c')) / 4
    f['browOut'] = (z('R_brow_d') + z('L_brow_d')) / 2
    f['browAsym'] = (z('R_brow_a') + z('R_brow_b') + z('R_brow_c') + z('R_brow_d') - z('L_brow_a') - z('L_brow_b') - z('L_brow_c') - z('L_brow_d')) / 4
    f['browSqueeze'] = (-y('R_brow_a') + y('L_brow_a')) / 2          # inner brows toward the centre
    f['jaw'] = -z('CD_lip')
    f['upLip'] = z('CU_lip')
    f['corner'] = (z('RU_cor') + z('LU_cor')) / 2
    f['cornerAsym'] = z('RU_cor') - z('LU_cor')
    f['wide'] = (y('RU_cor') - y('LU_cor')) / 2
    f['cheek'] = (z('R_cheek_a') + z('L_cheek_a')) / 2
    f['nose'] = z('C_nose')
    yr, pr = eye_angles(CQ, 'R_eye'); yl, pl = eye_angles(CQ, 'L_eye')
    f['eyeYaw'] = (yr + yl) / 2; f['eyePitch'] = (pr + pl) / 2
    return f


def all_features(folder='all/tracks'):
    out = {}
    for path in sorted(glob.glob(os.path.join(folder, '*.json'))):
        tr = json.load(open(path))
        out[tr['name']] = features(tr)
    return out


if __name__ == '__main__':
    F = all_features()
    keys = list(next(iter(F.values())).keys())
    np.savez_compressed('feats.npz', **{'%s|%s' % (a, k): v for a, f in F.items() for k, v in f.items()})
    print('%-9s %4s ' % ('anim', 'frm') + ' '.join('%-11s' % k[:11] for k in keys))
    for a, f in F.items():
        n = len(f['upLid'])
        print('%-9s %4d ' % (a[2:], n) + ' '.join('%+5.2f/%+5.2f' % (f[k].min(), f[k].max()) if 'eye' not in k else '%+5.0f/%+5.0f' % (f[k].min(), f[k].max()) for k in keys))
