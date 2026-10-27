"""The transformed Sephiroth's wing on the Crisis Core model: Rebirth's PC0010_10 wing (its 94 R_Feather* bones and
C_KDIRoot, the parent of the wing's KineDriver bones; the faces of material slot PC0010_10_Wing out of the editor's
export of the game's PC0010_10, fpys/wing/wing_seph.npz) at full size on his back:
  * every wing bone keeps Sephiroth's frame and its offset from C_Spine_d (his C_Spine_d rests turned as Sephiroth's,
    so the wing only moves by the difference of the two C_Spine_d's: its root then sits as deep under his coat as
    under Sephiroth's), C_KDIRoot as Sephiroth's (on Trans);
  * the wing's faces, corner normals and three UV layers (Unreal's v) the same, its weights (C_Spine_d and the feather
    bones) on the new bones, tangents from UV 0; material slot PC0010_10_Wing (the forms' wing part).
    wing_add.py <face_rig npz> <PC0010_10 rig json> <wing npz> <out npz> <report json>"""
import json
import sys
import numpy as np
sys.path.insert(0, '/work/ccseph/tools')
from face_rig import qmul, qinv, qrot

SLOT = 'PC0010_10_Wing'
MAT = '/Game/Character/Player/PC0010_10_Sephiroth_Transform/Material/PC0010_10_Wing.PC0010_10_Wing'
MAXINF = 8


def qm(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def mq(m):
    tr = np.trace(m)
    if tr > 0:
        s = np.sqrt(tr + 1.0) * 2
        q = [(m[2, 1] - m[1, 2]) / s, (m[0, 2] - m[2, 0]) / s, (m[1, 0] - m[0, 1]) / s, 0.25 * s]
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        s = np.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2]) * 2
        q = [0.25 * s, (m[0, 1] + m[1, 0]) / s, (m[0, 2] + m[2, 0]) / s, (m[2, 1] - m[1, 2]) / s]
    elif m[1, 1] > m[2, 2]:
        s = np.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2]) * 2
        q = [(m[0, 1] + m[1, 0]) / s, 0.25 * s, (m[1, 2] + m[2, 1]) / s, (m[0, 2] - m[2, 0]) / s]
    else:
        s = np.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1]) * 2
        q = [(m[0, 2] + m[2, 0]) / s, (m[1, 2] + m[2, 1]) / s, 0.25 * s, (m[1, 0] - m[0, 1]) / s]
    q = np.array(q); q /= np.linalg.norm(q)
    return q if q[3] >= 0 else -q


def tangents(pos, nrm, uv, tri):
    """Per-vertex tangent (Gram-Schmidt against the normal) and handedness from UV 0 (Unreal's v)."""
    t = np.zeros_like(pos); b = np.zeros_like(pos)
    p0, p1, p2 = pos[tri[:, 0]], pos[tri[:, 1]], pos[tri[:, 2]]
    u0, u1, u2 = uv[tri[:, 0]], uv[tri[:, 1]], uv[tri[:, 2]]
    e1, e2 = p1 - p0, p2 - p0
    d1, d2 = u1 - u0, u2 - u0
    r = d1[:, 0] * d2[:, 1] - d2[:, 0] * d1[:, 1]
    ok = np.abs(r) > 1e-12
    f = np.where(ok, 1.0 / np.where(ok, r, 1), 0.0)[:, None]
    ft = (e1 * d2[:, 1:2] - e2 * d1[:, 1:2]) * f
    fb = (e2 * d1[:, 0:1] - e1 * d2[:, 0:1]) * f
    for k in range(3):
        np.add.at(t, tri[:, k], ft); np.add.at(b, tri[:, k], fb)
    t = t - nrm * (t * nrm).sum(1, keepdims=True)
    n = np.linalg.norm(t, axis=1, keepdims=True)
    bad = n[:, 0] < 1e-9
    if bad.any():                                       # (no UV direction: any vector across the normal)
        alt = np.cross(nrm[bad], np.array([0.0, 0.0, 1.0]))
        alt[np.linalg.norm(alt, axis=1) < 1e-6] = np.cross(nrm[bad][np.linalg.norm(alt, axis=1) < 1e-6], [1.0, 0, 0])
        t[bad] = alt; n = np.linalg.norm(t, axis=1, keepdims=True)
    t = t / n
    sign = np.where((np.cross(nrm, t) * b).sum(1) >= 0, 1.0, -1.0)
    return t, sign


def main(npz, rig_path, wing_path, out_path, report_path):
    m = dict(np.load(npz))
    rig = json.load(open(rig_path))['bones']
    W = np.load(wing_path, allow_pickle=True)
    rep = {}
    names = [str(n) for n in m['bone_names']]; par = [int(p) for p in m['bone_parents']]
    cq, ct = list(m['bone_cq']), list(m['bone_ct']); src = [str(s) for s in m['bone_src']]
    R = {b['name']: b for b in rig}
    assert not any('Feather' in n for n in names), 'the model has wing bones already'

    # ---- where the wing goes: Sephiroth's offset from C_Spine_d, turned with his C_Spine_d's frame
    i_sd = names.index('C_Spine_d')
    Rs, ts = qm(R['C_Spine_d']['q']), np.array(R['C_Spine_d']['t'])
    Rc, tc = qm(cq[i_sd]), ct[i_sd]
    turn = Rc @ Rs.T
    rep['spine_d_turn_deg'] = float(np.degrees(np.arccos(np.clip((np.trace(turn) - 1) / 2, -1, 1))))
    rep['moved_by'] = (tc - ts).round(4).tolist()

    def place(p):
        return tc + turn @ (np.asarray(p) - ts)
    wing_bones = [b['name'] for b in rig if 'Feather' in b['name']]
    add = ['C_KDIRoot'] + wing_bones
    ix = {n: i for i, n in enumerate(names)}
    for n in add:
        b = R[n]
        p = b['parent']
        assert p in ix, (n, p)
        ix[n] = len(names)
        names.append(n); par.append(ix[p]); src.append('Rebirth PC0010_10:' + n)
        if n == 'C_KDIRoot':
            cq.append(np.array(b['q'])); ct.append(np.array(b['t']))
        else:
            cq.append(mq(turn @ qm(b['q']))); ct.append(place(b['t']))
    cq, ct = np.array(cq), np.array(ct)
    nb = len(names)
    lq = np.zeros((nb, 4)); lt = np.zeros((nb, 3))
    for i in range(nb):
        p = par[i]
        if p < 0:
            lq[i], lt[i] = cq[i], ct[i]
        else:
            lq[i] = qmul(qinv(cq[p]), cq[i]); lt[i] = qrot(qinv(cq[p]), ct[i] - ct[p])
        lq[i] /= np.linalg.norm(lq[i])
    rep['bones_added'] = len(add)
    rep['wing_root'] = ct[ix['R_FeatherShoulder_a']].round(3).tolist()

    # ---- the wing's vertices: one per distinct (vertex, normal, uvs) corner
    fv = W['face_verts']; nrm = W['normals']; uvs = W['uvs']        # uvs: Blender's v
    pos0 = np.array([place(p) for p in W['pos']])
    keyarr = np.c_[fv, np.round(nrm, 4), np.round(uvs.transpose(1, 0, 2).reshape(len(fv), -1), 5)]
    uniq, inv = np.unique(keyarr, axis=0, return_inverse=True)
    inv = inv.ravel()
    first = np.zeros(len(uniq), int); first[inv[::-1]] = np.arange(len(fv))[::-1]
    v_of = fv[first]
    wpos = pos0[v_of]
    wn = nrm[first] @ turn.T
    wn /= np.linalg.norm(wn, axis=1, keepdims=True)
    wuv = uvs[:, first, :].transpose(1, 0, 2).copy()
    wuv[:, :, 1] = 1.0 - wuv[:, :, 1]                                  # Unreal's v
    wtri = inv.reshape(-1, 3)
    fn = np.cross(wpos[wtri[:, 1]] - wpos[wtri[:, 0]], wpos[wtri[:, 2]] - wpos[wtri[:, 0]])
    agree = (fn * wn[wtri].mean(1)).sum(1)
    if np.mean(agree > 0) > 0.5:                                       # (Unreal: normal = -cross(e1, e2))
        wtri = wtri[:, ::-1].copy(); rep['wing_winding'] = 'flipped'
    else:
        rep['wing_winding'] = 'kept'
    wt, wsign = tangents(wpos, wn, wuv[:, 0, :], wtri)
    # weights
    wb_names = [str(b) for b in W['bones']]
    per = [dict() for _ in range(len(W['pos']))]
    for v, b, w in zip(W['w_vert'], W['w_bone'], W['w_weight']):
        per[v][wb_names[b]] = per[v].get(wb_names[b], 0.0) + float(w)
    WB = np.zeros((len(v_of), MAXINF), int); WW = np.zeros((len(v_of), MAXINF))
    for k, v in enumerate(v_of):
        items = sorted(((w, b) for b, w in per[v].items() if w > 1e-6), reverse=True)[:MAXINF]
        s = sum(w for w, _ in items) or 1.0
        for j, (w, b) in enumerate(items):
            WB[k, j] = ix[b]; WW[k, j] = w / s
    rep['wing_vertices'] = int(len(v_of)); rep['wing_triangles'] = int(len(wtri))
    rep['wing_unweighted'] = int((WW.sum(1) == 0).sum())

    # ---- merged
    nv = len(m['pos'])
    slots = [str(s) for s in m['slots']] + [SLOT]
    mats = [str(s) for s in m['mat_paths']] + [MAT]
    uv = m['uv']
    if uv.shape[1] < 3:
        uv = np.concatenate([uv, np.zeros((nv, 3 - uv.shape[1], 2))], 1)
    out = dict(m)
    out.update(pos=np.r_[m['pos'], wpos], nz=np.r_[m['nz'], wn], nx=np.r_[m['nx'], wt], tsign=np.r_[m['tsign'], wsign],
               uv=np.r_[uv[:, :3], wuv[:, :3]], tri=np.r_[m['tri'], wtri + nv],
               tmat=np.r_[m['tmat'], np.full(len(wtri), len(slots) - 1)], slots=np.array(slots), mat_paths=np.array(mats),
               wbone=np.r_[m['wbone'], WB], wweight=np.r_[m['wweight'], WW], bone_names=np.array(names),
               bone_parents=np.array(par), bone_lq=lq, bone_lt=lt, bone_cq=cq, bone_ct=ct, bone_src=np.array(src))
    np.savez(out_path, **out)
    json.dump(rep, open(report_path, 'w'), indent=1)
    print(json.dumps(rep, indent=1))


if __name__ == '__main__':
    main(*sys.argv[1:6])
