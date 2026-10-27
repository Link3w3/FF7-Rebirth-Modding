"""Rebirth's face rig on the Dissidia NT Sephiroth (dnt_rerig2.py npz), the way the Crisis Core model got it
(ccseph/tools/face_rig.py), for a face that is not Rebirth's own:

  fit      his face (the PBB-ArIriNbSssWt mesh's front, brows to chin) onto Rebirth Sephiroth's (PC0010_00, mat 7's
           front) by a translation and one scale (trimmed nearest-point ICP), then a smooth correction (Gaussian RBF of
           the remaining nearest-point offsets), so each of his face vertices has a place on Rebirth's face;
  bones    every bone under Rebirth's C_FaceBase_a with Rebirth's names, parents and local rest (the game's facial
           animations and lip maps pose them as they pose Rebirth Sephiroth's), moved by the fit's translation onto
           his face; C_Head_a with them (Rebirth's pivot for the face). His own face joints were folded into C_Head_a
           by the re-rig.
  skin     his face, mouth and lash vertices take the weights of the Rebirth vertices nearest their place on Rebirth's
           face (6 nearest, inverse-distance; the same side of the eye and mouth openings: upper lids and lips from
           upper ones, lower from lower), faded into his own (C_Head_a) where the fit is far from Rebirth's surface;
           the mouth inside from Rebirth's mouth by part (tongue, lower teeth and jaw, upper); his eyes (iris and their
           shells) on L_Eye / R_Eye. The rest of him keeps his weights.

    dnt_face.py <rerig npz> <Rebirth rig json> <Rebirth mesh npz> <out npz> <report json>"""
import json
import re
import sys

import numpy as np
from scipy.spatial import cKDTree

sys.path.insert(0, '/work/ccseph/tools')
from face_rig import qmul, qinv, qrot, U_EYE, D_EYE, U_MOUTH, D_MOUTH, TONGUE, klass, side_sums   # noqa: E402

MAXINF = 8


def icp_scale_translation(src, dst, iters=80):
    """s, D with s * src + D on dst's points (trimmed nearest-point ICP, uniform scale about src's centroid)"""
    tree = cKDTree(dst)
    c = src.mean(0)
    s, D = 1.0, dst.mean(0) - c
    for _ in range(iters):
        x = (src - c) * s + c + D
        d, j = tree.query(x)
        keep = d <= np.percentile(d, 85)
        a = (src[keep] - c); b = dst[j[keep]] - D - c
        s_new = float(np.sum(a * b) / np.sum(a * a))
        s_new = min(max(s_new, 0.85), 1.15)
        x = (src - c) * s_new + c
        D_new = (dst[j[keep]] - x[keep]).mean(0)
        moved = abs(s_new - s) + np.linalg.norm(D_new - D)
        s, D = s_new, D_new
        if moved < 1e-6:
            break
    x = (src - c) * s + c + D
    d, _ = tree.query(x)
    return s, D, c, d


def rbf_correction(x, targets, sigma=1.5, lam=1e-2, max_pts=1500):
    """a smooth displacement field through the points x moving them to targets (Gaussian RBF, regularized)"""
    n = len(x)
    if n > max_pts:
        sel = np.random.RandomState(0).choice(n, max_pts, replace=False)
    else:
        sel = np.arange(n)
    c = x[sel]; disp = targets[sel] - x[sel]
    K = np.exp(-((c[:, None, :] - c[None, :, :]) ** 2).sum(-1) / (2 * sigma * sigma))
    w = np.linalg.solve(K + lam * np.eye(len(c)), disp)

    def f(p):
        out = np.zeros_like(p)
        for k in range(0, len(p), 4000):
            q = p[k:k + 4000]
            Kq = np.exp(-((q[:, None, :] - c[None, :, :]) ** 2).sum(-1) / (2 * sigma * sigma))
            out[k:k + 4000] = q + Kq @ w
        return out
    return f


def main(rr_path, rig_path, mesh_path, out_path, report_path):
    rr = dict(np.load(rr_path))
    rig = json.load(open(rig_path))['bones']
    rmesh = np.load(mesh_path)
    rep = {}
    names = [str(n) for n in rr['bone_names']]
    parents = [int(p) for p in rr['bone_parents']]
    cq, ct = rr['bone_cq'].copy(), rr['bone_ct'].copy()
    src = [str(s) for s in rr['bone_src']]
    P = rr['pos']; tri = rr['tri']; tmat = rr['tmat']
    mats = [json.loads(s) for s in rr['materials']]
    subs = [json.loads(s) for s in rr['submeshes']]
    vsub = np.zeros(len(P), int)
    for k, s in enumerate(subs):
        vsub[s['vstart']:s['vstart'] + s['vcount']] = k

    def verts_named(pred):
        return np.concatenate([np.arange(s['vstart'], s['vstart'] + s['vcount']) for s in subs if pred(s['name'])] or
                              [np.zeros(0, int)])
    face_v = verts_named(lambda n: n == 'PBB-ArIriNbSssWt')
    eye_v = verts_named(lambda n: n in ('PBB-ArGfPmSssWt', 'PBB-ArGfNWt', 'PBB-ArNWt'))
    mouth_v = verts_named(lambda n: n == 'PBB-ArNSssWt')
    lash_v = verts_named(lambda n: n.endswith('Zc') or n.endswith('Zd'))
    rep['parts'] = dict(face=int(len(face_v)), eyes=int(len(eye_v)), mouth=int(len(mouth_v)), lashes=int(len(lash_v)))

    rnames = [b['name'] for b in rig]; ridx = {n: i for i, n in enumerate(rnames)}
    rpar = [ridx[b['parent']] if b['parent'] else -1 for b in rig]
    rq = {b['name']: np.array(b['q']) for b in rig}; rt = {b['name']: np.array(b['t']) for b in rig}
    RP, rv = rmesh['pos'], rmesh['vmat']
    rbones = [str(b) for b in rmesh['bones']]

    # ---- the fit: his face front onto Rebirth's face front
    face_r = (rv == 7) & (RP[:, 0] > 6.5) & (RP[:, 2] > 177.5) & (RP[:, 2] < 191.5)
    eyes_r = RP[rv == 2].mean(0)
    eyes_d = P[eye_v].mean(0)
    cand = P[face_v]
    sel = (cand[:, 0] > eyes_d[0] - 3.5) & (cand[:, 2] > eyes_d[2] - 10.5) & (cand[:, 2] < eyes_d[2] + 3.5)
    s, D, c, dres = icp_scale_translation(cand[sel], RP[face_r])
    D[1] = 0.0
    rep['scale'] = round(s, 4); rep['offset'] = D.round(4).tolist()
    rep['icp_residual_cm'] = dict(median=float(np.median(dres)), p90=float(np.percentile(dres, 90)))

    def sim(p):
        return (p - c) * s + c + D
    # the smooth correction from his face front's points to their nearest Rebirth points
    tree_r = cKDTree(RP[face_r])
    x0 = sim(cand[sel])
    d0, j0 = tree_r.query(x0)
    ok = d0 < 1.5
    warp = rbf_correction(x0[ok], RP[face_r][j0[ok]])

    def place(p):
        return warp(sim(p))
    # ---- skeleton: his bones (no face rig), then Rebirth's face rig moved by D onto his face, C_Head_a with it
    def under(i, a):
        while i >= 0:
            if i == a:
                return True
            i = rpar[i]
        return False
    fb = ridx['C_FaceBase_a']
    rface = [rnames[i] for i in range(len(rnames)) if under(i, fb)]
    drop = {'C_FaceBase_a', 'L_Eye', 'R_Eye'}
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
            new_ct[-1] = rt['C_Head_a'] - D
            rep['head_moved_to'] = new_ct[-1].round(3).tolist()
            for n in rface:
                pr = rnames[rpar[ridx[n]]]
                pos_of[n] = len(new_names)
                new_names.append(n); new_par.append(pos_of[pr])
                new_cq.append(rq[n]); new_ct.append(rt[n] - D); new_src.append('Rebirth:' + n)
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
    # (the bones sit at Rebirth's place - D: his face is at (place - D) of Rebirth's, the bones go with the shift alone)

    def to_new(rn):
        i = ridx[rn]
        while i >= 0 and rnames[i] not in pos_of:
            i = rpar[i]
        return rnames[i] if i >= 0 else 'C_Head_a'
    rmap = {n: to_new(n) for n in set(rbones)}
    wv, wbn, ww = rmesh['w_vert'], rmesh['w_bone'], rmesh['w_weight']
    rw = {}
    selw = np.isin(rv[wv], [2, 3, 4, 7, 8])
    for v, b, w in zip(wv[selw].tolist(), wbn[selw].tolist(), ww[selw].tolist()):
        d = rw.setdefault(v, {}); mm = rmap[rbones[b]]; d[mm] = d.get(mm, 0.0) + w

    def rclass(v):
        d = rw.get(v, {})
        return (klass(*side_sums(d, U_EYE.match, D_EYE.match)), klass(*side_sums(d, U_MOUTH.match, D_MOUTH.match)))
    rver = np.arange(len(RP))
    rcls = {v: rclass(v) for v in rw}

    wb, wwt = rr['wbone'], rr['wweight']

    def own(v):
        d = {}
        for b, w in zip(wb[v], wwt[v]):
            if w > 0:
                n = names[b]
                n = 'C_Head_a' if n in drop else n
                d[n] = d.get(n, 0.0) + float(w)
        return d

    def blend(ds, ws):
        out = {}
        for d, sh in zip(ds, ws):
            for b, w in d.items():
                out[b] = out.get(b, 0.0) + w * sh
        return out

    def knn(x, pool, tree, k=6):
        dd, jj = tree.query(x, k=min(k, len(pool)))
        dd = np.atleast_1d(dd); jj = np.atleast_1d(jj)
        sh = 1.0 / np.maximum(dd, 0.01) ** 2
        sh /= sh.sum()
        return blend([rw.get(pool[j], {}) for j in jj], sh), float(dd.min())
    pools = {}

    def pool_for(key, mats_r, eye_c, mouth_c):
        if key not in pools:
            vs = np.array([v for v in rver[np.isin(rv, mats_r)] if v in rw
                           and not (eye_c != 0 and rcls[v][0] == -eye_c) and not (mouth_c != 0 and rcls[v][1] == -mouth_c)], int)
            pools[key] = (vs, cKDTree(RP[vs] if len(vs) else np.zeros((1, 3))))
        return pools[key]
    # his openings: eyes (each side's eye centre) and mouth (between the lips) in the fitted space
    eyeL = place(P[eye_v][P[eye_v][:, 1] < 0].mean(0)[None])[0]
    eyeR = place(P[eye_v][P[eye_v][:, 1] > 0].mean(0)[None])[0]
    mouth_c = place(P[mouth_v].mean(0)[None])[0] if len(mouth_v) else None
    new_w = [None] * len(P)
    how = {}
    X_face = place(P[face_v])
    tree_all = cKDTree(RP[rv == 7])
    dist_surf, _ = tree_all.query(X_face)
    for k, v in enumerate(face_v.tolist()):
        x = X_face[k]
        eye = eyeL if x[1] < 0 else eyeR
        ec = 0
        if abs(x[1] - eye[1]) < 2.2 and abs(x[2] - eye[2]) < 1.6:
            ec = 1 if x[2] > eye[2] else -1
        mc = 0
        if mouth_c is not None and abs(x[1]) < 3.2 and abs(x[2] - mouth_c[2]) < 1.2:
            mc = 1 if x[2] > mouth_c[2] else -1
        pool, tree = pool_for(('face', ec, mc), [7], ec, mc)
        tw, dmin = knn(x, pool, tree)
        mine = own(v)
        dsurf = dist_surf[k]
        if dsurf <= 0.6:
            new_w[v] = tw; how[v] = 'near'
        elif dsurf >= 1.6:
            new_w[v] = mine; how[v] = 'own'
        else:
            t = (dsurf - 0.6) / 1.0
            new_w[v] = blend([tw, mine], [1 - t, t]); how[v] = 'faded'
    # mouth inside: by Rebirth's mouth parts
    def rmouth_kind(v):
        d = rw.get(v, {})
        t = sum(w for b, w in d.items() if TONGUE.match(b))
        lo = sum(w for b, w in d.items() if D_MOUTH.match(b) and not TONGUE.match(b))
        return 'tongue' if t > 0.5 else ('lower' if lo > 0.5 else 'upper')
    if len(mouth_v):
        rm = np.array([v for v in rver[rv == 8] if v in rw], int)
        rkind = np.array([rmouth_kind(v) for v in rm])
        X_m = place(P[mouth_v])
        tree_m = cKDTree(RP[rm])
        dd, jj = tree_m.query(X_m, k=1)
        kinds = rkind[jj]
        mk = {kd: (rm[rkind == kd], cKDTree(RP[rm[rkind == kd]])) for kd in ('tongue', 'lower', 'upper') if (rkind == kd).any()}
        for k, v in enumerate(mouth_v.tolist()):
            tw, _ = knn(X_m[k], *mk[kinds[k]])
            new_w[v] = tw; how[v] = 'mouth_' + kinds[k]
    # lashes: upper ones from Rebirth's upper lid and lash vertices, lower from the lower
    if len(lash_v):
        X_l = place(P[lash_v])
        for k, v in enumerate(lash_v.tolist()):
            x = X_l[k]
            eye = eyeL if x[1] < 0 else eyeR
            ec = 1 if x[2] > eye[2] - 0.2 else -1
            key = ('lash', ec)
            if key not in pools:
                vs = np.array([u for u in rver[np.isin(rv, [4, 7])] if u in rw and rcls[u][0] == ec], int)
                pools[key] = (vs, cKDTree(RP[vs]))
            tw, _ = knn(x, *pools[key], k=4)
            new_w[v] = tw; how[v] = 'lash_%s' % ('upper' if ec > 0 else 'lower')
    for v in eye_v.tolist():
        new_w[v] = {('L_Eye' if P[v][1] < 0 else 'R_Eye'): 1.0}; how[v] = 'eye'
    # Rebirth's eye bones on his eyes: their place minus D is where his eyeballs' centres are (the eyes keep Rebirth's
    # pivot otherwise); the eyeball shells' centre is the mean of the iris mesh
    for v in range(len(P)):
        if new_w[v] is None:
            new_w[v] = own(v); how[v] = how.get(v, 'kept')
    idx_of = {n: i for i, n in enumerate(new_names)}
    WB = np.zeros((len(P), MAXINF), int); WW = np.zeros((len(P), MAXINF))
    dropped = 0.0
    for v, d in enumerate(new_w):
        items = sorted(((w, b) for b, w in d.items() if w > 1e-6), reverse=True)
        dropped = max(dropped, sum(w for w, _ in items[MAXINF:]))
        items = items[:MAXINF]
        ssum = sum(w for w, _ in items)
        for k, (w, b) in enumerate(items):
            WB[v, k] = idx_of[b]; WW[v, k] = w / ssum
    from collections import Counter
    rep['vertices'] = dict(Counter(how.values()))
    rep['max_weight_dropped_by_8_cap'] = round(dropped, 4)
    used = np.zeros(nb)
    for k in range(MAXINF):
        np.add.at(used, WB[:, k], WW[:, k])
    rep['face_bones_without_weights'] = len([n for n in rface if used[idx_of[n]] == 0])
    rep['eyes_his'] = [np.round(P[eye_v][P[eye_v][:, 1] < 0].mean(0), 3).tolist(), np.round(P[eye_v][P[eye_v][:, 1] > 0].mean(0), 3).tolist()]
    rep['eyes_bones'] = [np.round(rt['L_Eye'] - D, 3).tolist(), np.round(rt['R_Eye'] - D, 3).tolist()]
    out = dict(rr)
    out.update(wbone=WB, wweight=WW, bone_names=np.array(new_names), bone_parents=np.array(new_par), bone_lq=lq,
               bone_lt=lt, bone_cq=new_cq, bone_ct=new_ct, bone_src=np.array(new_src), face_offset=D, face_scale=s)
    np.savez(out_path, **out)
    json.dump(rep, open(report_path, 'w'), indent=1)
    print(json.dumps(rep, indent=1)[:3000])


if __name__ == '__main__':
    main(*sys.argv[1:6])
