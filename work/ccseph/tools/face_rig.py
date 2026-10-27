"""The Crisis Core Reunion Sephiroth on Rebirth's face rig.

Reunion's Sephiroth has Rebirth Sephiroth's own face: after one translation (ICP, about 6.1 cm forward and 0.36 cm down)
81 % of his head's vertices sit within 0.2 mm of the game's PC0010_00 face (the rest are the back of his head, his neck,
and a few lid and lip corners cut differently). So the face takes Rebirth's rig whole:

  bones    every bone under Rebirth's C_FaceBase_a (104: brows, lids, lashes, eyes, nose, cheeks, lips, corners, teeth,
           tongue, chin, throat...), with Rebirth's names, parents and rest frames, moved by that translation; C_Head_a
           moves with them (Rebirth's pivot for this face, about 2.3 cm in front of Reunion's), so C_FaceBase_a and every
           face bone keep Rebirth's local rest and the game's facial animations and lip maps (absolute local transforms)
           pose this face exactly as they pose Rebirth Sephiroth's. Reunion's own face bones (hi_*) go.
  skin     each head vertex on Rebirth's face takes that vertex's weights; the others take the nearest Rebirth face
           vertices' weights (inverse-distance, 6 nearest) from the same side of the eye and mouth openings as Reunion's
           own weights put them, faded into his own weights (hi_* folded into C_Head_a / the jaw) from 0.5 to 1 cm away;
           mouth inside: teeth and tongue the same way from Rebirth's mouth (upper, lower/jaw, tongue); eyelashes from
           Rebirth's lid and lash vertices (upper or lower as his are); eyeballs on L_Eye / R_Eye.
           Rebirth bones he has no such bone for (neck twist helpers, the throat) fold into their nearest ancestor he has.
Positions and rotations are Unreal component space (cm), the rerig.py npz's conventions.
    face_rig.py <rerig npz> <Rebirth rig json> <Rebirth mesh npz> <out npz> <report json>"""
import json
import re
import sys
import numpy as np
from scipy.spatial import cKDTree

MAXINF = 8


def qmul(a, b):
    x1, y1, z1, w1 = a; x2, y2, z2, w2 = b
    return np.array([w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2, w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
                     w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2, w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2])


def qinv(q):
    return np.array([-q[0], -q[1], -q[2], q[3]])


def qrot(q, v):
    u = np.asarray(q[:3]); w = q[3]; v = np.asarray(v, float)
    return v + 2 * np.cross(u, np.cross(u, v) + w * v)


def icp_translation(src, dst, start, iters=60):
    """The translation D with src - D on dst's points (nearest-point ICP, trimmed to the closest 90 %)."""
    tree = cKDTree(dst)
    D = np.array(start, float)
    for _ in range(iters):
        d, j = tree.query(src - D)
        keep = d <= np.percentile(d, 90)
        step = ((src - D)[keep] - dst[j[keep]]).mean(0)
        D = D + step
        if np.linalg.norm(step) < 1e-6:
            break
    d, _ = tree.query(src - D)
    return D, d


# Rebirth's face bones by the opening they sit on (upper or lower side of the eyes and the mouth)
U_EYE = re.compile(r'^[LR]_U(lid|lash)_')
D_EYE = re.compile(r'^[LR]_D(lid|lash)_')
U_MOUTH = re.compile(r'^(C_Ulip|[LR]_Ulip|C_Uteeth|[LR]_Ucor)')
D_MOUTH = re.compile(r'^(C_Dlip|[LR]_Dlip|C_Dteeth|[LR]_Dcor|C_Chin|C_Tong)')
TONGUE = re.compile(r'^C_Tong')
JAW = 'C_Dteeth'


def side_sums(wdict, upper, lower):
    u = sum(w for b, w in wdict.items() if upper(b))
    d = sum(w for b, w in wdict.items() if lower(b))
    return u, d


def klass(u, d, margin=0.1):
    if u > d + margin:
        return 1
    if d > u + margin:
        return -1
    return 0


def main(cc_path, rig_path, mesh_path, out_path, report_path):
    cc = dict(np.load(cc_path))
    rig = json.load(open(rig_path))['bones']
    rmesh = np.load(mesh_path)
    rep = {}

    names = [str(n) for n in cc['bone_names']]
    parents = [int(p) for p in cc['bone_parents']]
    cq, ct = cc['bone_cq'].copy(), cc['bone_ct'].copy()
    src = [str(s) for s in cc['bone_src']]
    P = cc['pos']; tri = cc['tri']; tmat = cc['tmat']; slots = [str(s) for s in cc['slots']]
    vslot = np.zeros(len(P), int); vslot[tri.ravel()] = np.repeat(tmat, 3)

    rnames = [b['name'] for b in rig]; ridx = {n: i for i, n in enumerate(rnames)}
    rpar = [ridx[b['parent']] if b['parent'] else -1 for b in rig]
    rq = {b['name']: np.array(b['q']) for b in rig}; rt = {b['name']: np.array(b['t']) for b in rig}
    RP, rv = rmesh['pos'], rmesh['vmat']
    rbones = [str(b) for b in rmesh['bones']]

    # ---- the translation that puts Rebirth's face on his (front of the face: brows to chin)
    face_r = (rv == 7) & (RP[:, 0] > 6.5) & (RP[:, 2] > 177.5) & (RP[:, 2] < 191.5)
    head_v = np.nonzero(vslot == slots.index('CH_head'))[0]
    start = (P[vslot == slots.index('CH_eye')].mean(0) - RP[rv == 2].mean(0))
    cand = P[head_v]
    cand = cand[(cand[:, 0] - start[0] > 6.5) & (cand[:, 2] - start[2] > 177.5) & (cand[:, 2] - start[2] < 191.5)]
    D, dres = icp_translation(cand, RP[face_r], start)
    D[1] = 0.0                                       # (both faces are symmetric about y = 0)
    rep['offset'] = D.round(4).tolist()
    rep['icp_residual_cm'] = dict(median=float(np.median(dres)), p90=float(np.percentile(dres, 90)))

    # ---- skeleton: his bones without his face rig, then Rebirth's face rig moved by D, C_Head_a moved with it
    def under(i, a):
        while i >= 0:
            if i == a:
                return True
            i = rpar[i]
        return False
    fb = ridx['C_FaceBase_a']
    rface = [rnames[i] for i in range(len(rnames)) if under(i, fb)]      # C_FaceBase_a first (rig order)
    drop = {n for n in names if (n.startswith('hi_') and n != 'hi_hair') or n in ('C_FaceBase_a', 'L_Eye', 'R_Eye')}
    keep = [i for i, n in enumerate(names) if n not in drop]
    new_names, new_par, new_cq, new_ct, new_src = [], [], [], [], []
    pos_of = {}
    for i in keep:
        p = parents[i]
        while p >= 0 and names[p] in drop:
            p = parents[p]
        pos_of[names[i]] = len(new_names)
        new_names.append(names[i]); new_par.append(pos_of[names[p]] if p >= 0 else -1)
        new_cq.append(cq[i]); new_ct.append(ct[i]); new_src.append(src[i])
        if names[i] == 'C_Head_a':
            rep['head_moved_from'] = ct[i].round(3).tolist()
            new_ct[-1] = rt['C_Head_a'] + D
            rep['head_moved_to'] = new_ct[-1].round(3).tolist()
            for n in rface:                           # the face rig right under the head (parents before children)
                pr = rnames[rpar[ridx[n]]]
                pos_of[n] = len(new_names)
                new_names.append(n); new_par.append(pos_of[pr])
                new_cq.append(rq[n]); new_ct.append(rt[n] + D); new_src.append('Rebirth:' + n)
    new_cq = np.array(new_cq); new_ct = np.array(new_ct)
    nb = len(new_names)
    lq = np.zeros((nb, 4)); lt = np.zeros((nb, 3))
    for i in range(nb):
        p = new_par[i]
        if p < 0:
            lq[i], lt[i] = new_cq[i], new_ct[i]
        else:
            lq[i] = qmul(qinv(new_cq[p]), new_cq[i]); lt[i] = qrot(qinv(new_cq[p]), new_ct[i] - new_ct[p])
        lq[i] /= np.linalg.norm(lq[i])
    rep['bones'] = dict(before=len(names), after=nb, dropped=sorted(drop), face_bones=len(rface))

    # ---- Rebirth bone -> his bone (itself, else its nearest ancestor he has)
    def to_new(rn):
        i = ridx[rn]
        while i >= 0 and rnames[i] not in pos_of:
            i = rpar[i]
        return rnames[i] if i >= 0 else 'C_Head_a'
    rmap = {n: to_new(n) for n in set(rbones)}
    folded = sorted({n for n, m in rmap.items() if n != m})

    # Rebirth's weights per vertex (dicts), for the parts we read from
    wv, wbn, ww = rmesh['w_vert'], rmesh['w_bone'], rmesh['w_weight']
    rw = {}
    sel = np.isin(rv[wv], [2, 3, 4, 7, 8])
    for v, b, w in zip(wv[sel].tolist(), wbn[sel].tolist(), ww[sel].tolist()):
        d = rw.setdefault(v, {}); m = rmap[rbones[b]]; d[m] = d.get(m, 0.0) + w

    def rclass(v):
        d = rw.get(v, {})
        return (klass(*side_sums(d, U_EYE.match, D_EYE.match)), klass(*side_sums(d, U_MOUTH.match, D_MOUTH.match)))

    # his own weights per vertex (dicts, by name), his face bones folded for where his own weights stay
    wb, wwt = cc['wbone'], cc['wweight']
    own = []
    for v in range(len(P)):
        d = {}
        for b, w in zip(wb[v], wwt[v]):
            if w > 0:
                d[names[b]] = d.get(names[b], 0.0) + float(w)
        own.append(d)

    def fold_own(d, side):
        out = {}
        for b, w in d.items():
            if b in pos_of:
                m = b
            elif b in ('hi_chin', 'hi_underlip_L1', 'hi_underlip_R1', 'hi_tongue'):
                m = JAW
            elif b.startswith('hi_eye_'):
                m = 'L_Eye' if b.endswith('_L') else 'R_Eye'
            else:
                m = 'C_Head_a'
            out[m] = out.get(m, 0.0) + w
        return out

    def cc_class(d):
        ue = sum(w for b, w in d.items() if b.startswith('hi_uppereyelid')); de = sum(w for b, w in d.items() if b.startswith('hi_undereyelid'))
        um = sum(w for b, w in d.items() if b.startswith('hi_upperlip'))
        dm = sum(w for b, w in d.items() if b.startswith('hi_underlip') or b in ('hi_chin', 'hi_tongue'))
        return klass(ue, de), klass(um, dm)

    new_w = [None] * len(P)
    how = {}

    def blend(ds, ws):
        out = {}
        for d, s in zip(ds, ws):
            for b, w in d.items():
                out[b] = out.get(b, 0.0) + w * s
        return out

    def knn_weights(x, pool, pool_tree, k=6):
        dd, jj = pool_tree.query(x, k=min(k, len(pool)))
        dd = np.atleast_1d(dd); jj = np.atleast_1d(jj)
        s = 1.0 / np.maximum(dd, 0.01) ** 2
        s /= s.sum()
        return blend([rw.get(pool[j], {}) for j in jj], s), float(dd.min())

    # pools of Rebirth vertices by class, for the constrained searches
    rver = np.arange(len(RP))
    rcls = {}
    for v in rw:
        rcls[v] = rclass(v)

    def pool_for(mats, eye_c, mouth_c, extra=None):
        vs = [v for v in rver[np.isin(rv, mats)] if v in rw
              and not (eye_c != 0 and rcls[v][0] == -eye_c) and not (mouth_c != 0 and rcls[v][1] == -mouth_c)
              and (extra is None or extra(v))]
        vs = np.array(vs, int)
        return vs, cKDTree(RP[vs] if len(vs) else np.zeros((1, 3)))
    pools = {}

    def get_pool(key, *a, **kw):
        if key not in pools:
            pools[key] = pool_for(*a, **kw)
        return pools[key]

    # ---- head skin
    exact_tree = cKDTree(RP[rv == 7]); exact_ids = rver[rv == 7]
    d0, j0 = exact_tree.query(P[head_v] - D)
    for v, dist, j in zip(head_v.tolist(), d0.tolist(), j0.tolist()):
        if dist < 0.02 and exact_ids[j] in rw:
            new_w[v] = dict(rw[exact_ids[j]]); how[v] = 'copied'
            continue
        ec, mc = cc_class(own[v])
        pool, tree = get_pool(('head', ec, mc), [7], ec, mc)
        tw, dmin = knn_weights(P[v] - D, pool, tree)
        mine = fold_own(own[v], None)
        if dmin <= 0.5:
            new_w[v] = tw; how[v] = 'near'
        elif dmin >= 1.0:
            new_w[v] = mine; how[v] = 'own'
        else:
            s = (dmin - 0.5) / 0.5
            new_w[v] = blend([tw, mine], [1 - s, s]); how[v] = 'faded'

    # ---- mouth inside: tongue, lower (jaw) and upper, each from the same part of Rebirth's mouth
    mouth_v = np.nonzero(vslot == slots.index('CH_mouth'))[0]
    def rmouth_kind(v):
        d = rw.get(v, {})
        t = sum(w for b, w in d.items() if TONGUE.match(b))
        lo = sum(w for b, w in d.items() if D_MOUTH.match(b) and not TONGUE.match(b))
        return 'tongue' if t > 0.5 else ('lower' if lo > 0.5 else 'upper')
    mk = {}
    for kind in ('tongue', 'lower', 'upper'):
        vs = np.array([v for v in rver[rv == 8] if v in rw and rmouth_kind(v) == kind], int)
        mk[kind] = (vs, cKDTree(RP[vs]))
    rep['rebirth_mouth_parts'] = {k: int(len(v[0])) for k, v in mk.items()}
    for v in mouth_v.tolist():
        d = own[v]
        t = d.get('hi_tongue', 0.0)
        lo = sum(w for b, w in d.items() if b == 'hi_chin' or b.startswith('hi_underlip'))
        kind = 'tongue' if t > 0.5 else ('lower' if lo > 0.5 else 'upper')
        tw, dmin = knn_weights(P[v] - D, *mk[kind])
        new_w[v] = tw; how[v] = 'mouth_' + kind

    # ---- eyelashes: upper ones from Rebirth's upper lid and lash vertices, lower from the lower
    lash_v = np.nonzero(vslot == slots.index('CH_eyelash'))[0]
    for v in lash_v.tolist():
        ec, _ = cc_class(own[v])
        if ec == 0:
            ec = 1 if P[v][2] - D[2] > 188.0 else -1
        pool, tree = get_pool(('lash', ec), [4, 7], ec, 0,
                              extra=lambda u, ec=ec: (rcls[u][0] == ec))
        tw, dmin = knn_weights(P[v] - D, pool, tree, k=4)
        new_w[v] = tw; how[v] = 'lash_%s' % ('upper' if ec > 0 else 'lower')

    # ---- eyeballs
    eye_v = np.nonzero(vslot == slots.index('CH_eye'))[0]
    for v in eye_v.tolist():
        new_w[v] = {('L_Eye' if P[v][1] < 0 else 'R_Eye'): 1.0}; how[v] = 'eye'

    # ---- everything else keeps its weights (any face bone folded)
    for v in range(len(P)):
        if new_w[v] is None:
            new_w[v] = fold_own(own[v], None); how[v] = how.get(v, 'kept')

    # ---- to arrays: the 8 largest per vertex, normalised
    idx_of = {n: i for i, n in enumerate(new_names)}
    WB = np.zeros((len(P), MAXINF), int); WW = np.zeros((len(P), MAXINF))
    dropped_mass = 0.0
    for v, d in enumerate(new_w):
        items = sorted(((w, b) for b, w in d.items() if w > 1e-6), reverse=True)
        dropped_mass = max(dropped_mass, sum(w for w, _ in items[MAXINF:]))
        items = items[:MAXINF]
        s = sum(w for w, _ in items)
        for k, (w, b) in enumerate(items):
            WB[v, k] = idx_of[b]; WW[v, k] = w / s
    from collections import Counter
    rep['vertices'] = dict(Counter(how.values()))
    rep['max_weight_dropped_by_8_cap'] = round(dropped_mass, 4)
    rep['rebirth_bones_folded'] = folded
    used = np.zeros(nb)
    for k in range(MAXINF):
        np.add.at(used, WB[:, k], WW[:, k])
    rep['face_bones_without_weights'] = [n for n in rface if used[idx_of[n]] == 0]

    out = dict(cc)
    out.update(wbone=WB, wweight=WW, bone_names=np.array(new_names), bone_parents=np.array(new_par), bone_lq=lq, bone_lt=lt,
               bone_cq=new_cq, bone_ct=new_ct, bone_src=np.array(new_src), face_offset=D)
    np.savez(out_path, **out)
    json.dump(rep, open(report_path, 'w'), indent=1)
    print(json.dumps({k: v for k, v in rep.items() if k != 'rebirth_bones_folded'}, indent=1)[:4000])


if __name__ == '__main__':
    main(*sys.argv[1:6])
