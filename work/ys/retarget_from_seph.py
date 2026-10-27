"""Sephiroth's own animations (the game's PC0010_Sephiroth clips, ACL) -> key animations (.cacanim) on Young Sephiroth's
CH049_001_Skeleton, for the moves Young Sephiroth has no animation of (walks, turns, guards, falls, most reactions):

  * Sephiroth's body is taken with Trans at rest (the game poses the body against Trans at rest; Trans only carries the
    root motion as yaw * the exporter's axis change (-0.5, 0.5, -0.5, 0.5));
  * each mapped body bone of CH049 (hips, spine, neck, head, arms, hands, fingers, legs, feet, toes) gets Sephiroth's
    component-space rotation change from his rest pose, applied to CH049's rest bone first turned to point the way
    Sephiroth's rest bone points (both stand facing +X);
  * the hips move as Sephiroth's do from his rest, scaled down to CH049's height (hip heights 116.7 / 102.8 cm);
  * the sword (main_weapon, the bone CH049's own clips carry the sword on) turns exactly as Sephiroth's (L_Weapon_a:
    blade +Z, edge +Y) with CH049's axes (blade +Y, edge -Z), held where CH049's left hand holds it;
  * the root (identity at rest, as CH049's own clips) carries the root motion: Trans's yaw and its travel from the first
    frame, scaled down the same way (shorter legs, shorter strides);
  * every other bone (face, hair, coat, helper bones) keeps its rest pose (the Bonamik moves hair and coat).
    retarget_from_seph.py <out dir> <key> [<key> ...]      (keys of /Game/Motion/Player/PC0010_Sephiroth/Battle00)"""
import json, os, sys
sys.path[:0] = ['/work/acl', '/work/ch049anim', '/work/ys']
import numpy as np
import pose
import convert_ch049_anims as CV

PKG = '/work/seph1013/pkgs/Motion__Player__PC0010_Sephiroth__Battle00__%s.uasset'
G = np.array([-0.5, 0.5, -0.5, 0.5])
qmul, qinv, qrot, qnorm, arc, fk = CV.qmul, CV.qinv, CV.qrot, CV.qnorm, CV.arc, CV.fk

# ---- skeletons
SE = CV.Skel(list(pose.NAMES), list(pose.PARENTS), pose.REF_Q, pose.REF_T, np.ones((len(pose.NAMES), 3)))
_bones = json.load(open('/work/unityrip/out/model/model.json'))['bones']
_names = [b['name'] for b in _bones]
_parents = [b['parent'] for b in _bones]
_is_root = [p < 0 for p in _parents]
_Wb = np.array([np.array(b['world']) for b in _bones])
_Wr = np.zeros_like(_Wb)
for k in range(len(_bones)):
    R, tt = _Wb[k, :3, :3], _Wb[k, :3, 3]
    if not _is_root[k]:
        R, tt = CV.TZ @ R, CV.TZ @ tt
    _Wr[k, :3, :3] = CV.M @ R @ CV.M
    _Wr[k, :3, 3] = CV.M @ tt * 100.0
    _Wr[k, 3, 3] = 1
_rT, _rQ, _rS = CV.locals_of(_Wr[None], _parents)
CH = CV.Skel(_names, _parents, _rQ[0], _rT[0], _rS[0])
HIP_SCALE = SE.gt[SE.index['C_Hip_a']][2] / CH.gt[CH.index['hip']][2]

# ch049 bone -> Sephiroth bone, and the child each aims at (CH049 names)
INV = {c: s for s, c in CV.MAP.items()}
AIM_CH = {}
for s, (s_child, c_child) in CV.AIM.items():
    AIM_CH[CV.MAP[s]] = (c_child, s_child)

# CH049's rest bone turned to point the way Sephiroth's rest bone points
MATCHED = {}
for c, s in INV.items():
    ci, si = CH.index[c], SE.index[s]
    if c in AIM_CH:
        c_child, s_child = AIM_CH[c]
        u = CH.gt[CH.index[c_child]] - CH.gt[ci]
        v = SE.gt[SE.index[s_child]] - SE.gt[si]
        turn = arc(u, v)
    else:
        turn = None
    MATCHED[c] = turn
# bones without an aim take their parent's turn
for c in CH.names:
    if c in MATCHED and MATCHED[c] is None:
        p = CH.parents[CH.index[c]]
        while p >= 0 and (CH.names[p] not in MATCHED or MATCHED[CH.names[p]] is None):
            p = CH.parents[p]
        MATCHED[c] = MATCHED[CH.names[p]] if p >= 0 else np.array([0, 0, 0, 1.0])
MATCHED = {c: qnorm(qmul(t, CH.gq[CH.index[c]])) for c, t in MATCHED.items()}

# the sword: L_Weapon_a (blade +Z, edge +Y) -> main_weapon (blade +Y, edge -Z): R_mw = R_LW . KC
B_S = np.array([[0, 0, 1.0], [0, 1.0, 0], [-1.0, 0, 0]]).T     # columns: blade, edge, blade x edge (Sephiroth's)
B_C = np.array([[0, 1.0, 0], [0, 0, -1.0], [-1.0, 0, 0]]).T     # (CH049's)
KC = B_S @ B_C.T
KQ = CV.mat2quat(KC)


def grip():
    """main_weapon relative to left_hand_weapon in CH049's own clips (position in left_hand_weapon's frame)."""
    import clipdata
    d = clipdata.load()
    ix = {n: i for i, n in enumerate(d['names'])}
    W = d['clips']['idle_001_02_lp']['W']
    lw, mw = ix['left_hand_weapon'], ix['main_weapon']
    off = np.einsum('fji,fj->fi', W[:, lw, :3, :3], W[:, mw, :3, 3] - W[:, lw, :3, 3]).mean(0)
    return off


GRIP = grip()


def retarget(LQs, LTs):
    """Sephiroth's local tracks [f, 1072, 4/3] -> CH049 local tracks (T, Q, S) [f, 216, ...]"""
    nf = LQs.shape[0]
    tr = SE.index['Trans']
    Qb, Tb = LQs.copy(), LTs.copy()
    Qb[:, tr] = SE.q[tr]; Tb[:, tr] = SE.t[tr]                  # the body against Trans at rest
    GQs, GTs, _ = fk(Qb, Tb, np.ones(Tb.shape), SE.parents)
    n = len(CH.names)
    GQ = np.zeros((nf, n, 4)); GT = np.zeros((nf, n, 3))
    for i, c in enumerate(CH.names):
        p = CH.parents[i]
        if p < 0:
            GQ[:, i] = CH.q[i]; GT[:, i] = CH.t[i]
            continue
        if c in INV:
            s = SE.index[INV[c]]
            D = qmul(GQs[:, s], qinv(SE.gq[s])[None])
            GQ[:, i] = qnorm(qmul(D, np.repeat(MATCHED[c][None], nf, 0)))
        elif c == 'main_weapon':
            GQ[:, i] = qnorm(qmul(GQs[:, SE.index['L_Weapon_a']], np.repeat(KQ[None], nf, 0)))
        else:
            GQ[:, i] = qnorm(qmul(GQ[:, p], np.repeat(CH.q[i][None], nf, 0)))
        if c == 'hip':
            h = SE.index['C_Hip_a']
            GT[:, i] = CH.gt[i] + (GTs[:, h] - SE.gt[h]) / HIP_SCALE
        elif c == 'main_weapon':
            lw = CH.index['left_hand_weapon']
            GT[:, i] = GT[:, lw] + qrot(GQ[:, lw], np.repeat(GRIP[None], nf, 0))
        else:
            GT[:, i] = GT[:, p] + qrot(GQ[:, p], np.repeat(CH.t[i][None], nf, 0))
    # back to local
    LQ = np.zeros_like(GQ); LT = np.zeros_like(GT)
    for i in range(n):
        p = CH.parents[i]
        if p < 0:
            LQ[:, i] = GQ[:, i]; LT[:, i] = GT[:, i]
        else:
            LQ[:, i] = qnorm(qmul(qinv(GQ[:, p]), GQ[:, i]))
            LT[:, i] = qrot(qinv(GQ[:, p]), GT[:, i] - GT[:, p])
    # the root: Trans's yaw and travel
    r = CH.index['root']
    q = qmul(LQs[:, tr], qinv(G)[None].repeat(nf, 0))
    fwd = qrot(q, np.array([1.0, 0, 0])[None].repeat(nf, 0))
    yaw = np.arctan2(fwd[:, 1], fwd[:, 0])
    LQ[:, r] = np.stack([np.zeros(nf), np.zeros(nf), np.sin(yaw / 2), np.cos(yaw / 2)], -1)
    LT[:, r] = (LTs[:, tr] - LTs[:1, tr]) / HIP_SCALE
    return LT, CV.hemisphere(LQ), np.ones((nf, n, 3)), dict(yaw_deg=np.degrees(yaw), off_axis=float(np.abs(fwd[:, 2]).max()))


def main(out, keys):
    os.makedirs(out, exist_ok=True)
    report = {}
    for key in keys:
        c, bones, LQs, LTs = pose.load(open(PKG % key, 'rb').read())
        fps = 30.0
        LT, LQ, LS, info = retarget(LQs, LTs)
        nf = LQ.shape[0]
        loop = bool(np.abs(LQ[0] - LQ[-1]).max() < 0.02 and np.abs(LT[0, 1:] - LT[-1, 1:]).max() < 1.0)
        CV.write_cacanim(os.path.join(out, 'YS_' + key + '.cacanim'), CH.names, fps, LQ, LT, LS, loop)
        travel = LT[-1, 0] - LT[0, 0]
        report[key] = dict(frames=nf, seconds=round((nf - 1) / fps, 3), loop=loop, travel=[round(float(x), 1) for x in travel],
                           turn=round(float(info['yaw_deg'][-1] - info['yaw_deg'][0]), 1), root_off_axis=round(info['off_axis'], 3))
    json.dump(report, open(os.path.join(out, 'report.json'), 'w'), indent=1)
    return report


if __name__ == '__main__':
    r = main(sys.argv[1], sys.argv[2:])
    for k, v in r.items():
        print(k, v)
