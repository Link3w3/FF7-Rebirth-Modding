"""Bahamut Fused Sephiroth (PC0010_17, the End editor's FBX export: bfs_load.py's npz) -> his model on FF7 Rebirth
Sephiroth's bones, keeping his own proportions:

  * his body bones (the Rebirth names his rig already has: hips, spine, shoulders, arms, hands, fingers, legs, feet) get
    Rebirth's own bone frames (PC0010_00's rest rotations, so Rebirth's animations turn them as they turn Sephiroth's)
    at his own joints (his proportions); his arms, hands, fingers and legs are posed into Rebirth's rest pose (the
    limbs pointing along Rebirth's bones, the palms facing as Rebirth's, the soles kept flat) so the animations bend
    him as they bend Sephiroth;
  * his head is Rebirth Sephiroth's head, face rig and eyes at Rebirth's own place: the neck, head, face base, the 103
    face bones and the eyes get Rebirth's exact transforms (the facial animations and eye turns as in Rebirth), the
    neck at the neck (his was at the back of his chest) and the head's pivot at the skull's base;
  * his helmet, chest armour and collar (weighted to the root bone, Trans: they did not move with his body) are weighted
    to his head (the helmet and the pieces inside it), his neck (the neck guard's sides), his chest (the chest and back
    plates, the collar) and between chest and neck (the throat plates), blended into the weights around them;
  * his own bones stay (the mantles, the blade wings, the tail, the muscle and roll helpers), following the body;
    helpers that sit on a joint (ShoulderSub, the W bones, FemorisA2, Knee1, KneeSid, FootRoll) share their weights
    half and half between the bones on each side of the joint, as their half-turns in his own game did;
  * Rebirth's C_CharaA_a, C_CharaExA_a and C_CharaExB_a added under Trans (the game puts effects on them).

    bfs_rerig.py <bfs17.npz> <rebirth rig.json> <out.npz> [report.json]"""
import json
import sys
import numpy as np
import scipy.sparse as sp
sys.path.insert(0, '/work/ccseph/tools')
from rerig import q2m, m2q, rot_between, axis_angle, signed_angle

SIDES = ('L', 'R')
FINGERS = ('Thumb', 'Index', 'Middle', 'Ring', 'Pinky')
# helper bones on a joint: their weights shared between the bones on either side
SPLIT = {'Spine1W': [('C_Hip_a', .5), ('C_Spine_a', .5)], 'Neck1W': [('C_Spine_d', .5), ('C_Neck_a', .5)]}
for _s in SIDES:
    SPLIT.update({
        _s + '_ShoulderSub': [(_s + '_Shoulder_a', .5), (_s + '_UpperArm_a', .5)],
        _s + '_FemorisA2': [('C_Hip_a', .5), (_s + '_UpperLeg_a', .5)],
        _s + '_Knee1': [(_s + '_UpperLeg_a', .5), (_s + '_Foreleg_a', .5)],
        _s + '_Knee2': [(_s + '_Foreleg_a', 1.0)],
        _s + '_KneeSidA': [(_s + '_UpperLeg_a', .5), (_s + '_Foreleg_a', .5)],
        _s + '_KneeSidB': [(_s + '_UpperLeg_a', .5), (_s + '_Foreleg_a', .5)],
        _s + '_FootRollA': [(_s + '_Foreleg_a', .5), (_s + '_Foot_a', .5)],
        _s + '_FootRollB': [(_s + '_Foreleg_a', .5), (_s + '_Foot_a', .5)],
    })
# the pieces weighted to Trans, by island (bfs_islands: welded mesh islands of the export): what each follows
HEAD_ISLANDS = (777, 778, 779, 838)          # the helmet; the pieces inside it beside the head
NECK_ISLANDS = (810, 811)                    # the neck guard's sides
THROAT_ISLANDS = (773, 774, 776, 781, 782)   # the plates in front of the throat: chest below, neck above
CHEST_ISLANDS = (771, 780, 768)              # the chest spike, the back plate, the main body's chest and collar


def main(src, rig_path, out_path, report_path=None, islands_path=None):
    m = np.load(src)
    names = [str(n) for n in m['names']]
    par = [int(p) for p in m['parents']]
    NB = len(names)
    ix = {n: i for i, n in enumerate(names)}
    G = m['glob']
    R0 = G[:, :3, :3].copy()
    P0 = G[:, :3, 3].copy()
    R = R0.copy()
    P = P0.copy()
    children = [[] for _ in range(NB)]
    for i, p in enumerate(par):
        if p >= 0:
            children[p].append(i)

    def subtree(i):
        out = [i]
        k = 0
        while k < len(out):
            out += children[out[k]]
            k += 1
        return out

    def apply(i, M):
        o = P[i].copy()
        for j in subtree(i):
            P[j] = o + M @ (P[j] - o)
            R[j] = M @ R[j]

    rig = json.load(open(rig_path))
    RB = {b['name']: b for b in rig['bones']}
    rp = lambda n: np.array(RB[n]['t'], dtype=float)
    rq = lambda n: q2m(RB[n]['q'])
    log = []

    def deg(a, b):
        return round(float(np.degrees(np.arccos(np.clip(np.dot(a, b) / np.linalg.norm(a) / np.linalg.norm(b), -1, 1)))), 2)

    def align(c, c_child, r, r_child, child_point=None):
        cur = (child_point if child_point is not None else P[ix[c_child]]) - P[ix[c]]
        tgt = rp(r_child) - rp(r)
        apply(ix[c], rot_between(cur, tgt))
        log.append(('swing', c, deg(cur, tgt)))

    def twist(c, axis, cur, tgt):
        a = signed_angle(cur, tgt, axis)
        apply(ix[c], axis_angle(axis, a))
        log.append(('twist', c, round(float(np.degrees(a)), 2)))

    def unturn(c):
        A = R[ix[c]] @ R0[ix[c]].T
        apply(ix[c], A.T)
        log.append(('unturn', c, round(float(np.degrees(np.arccos(np.clip((np.trace(A) - 1) / 2, -1, 1)))), 2)))

    DRAPE_FLOOR = 9.0    # the strips' bones lie this high (the physics' floor holds them a bone radius over it)
    DRAPE_R = 25.0       # the bend from hanging to lying: a quarter circle about this high

    def drape(path):
        """lay the part of a strip below DRAPE_FLOOR + DRAPE_R along the floor behind him (each bone turned about its joint
        so the next joint lands on the path: the strip's own line down to the bend, a circular bend, then straight back)"""
        idx = [ix[n] for n in path]
        zs = [P[i][2] for i in idx]
        top = DRAPE_FLOOR + DRAPE_R
        if min(zs) >= top:
            return None
        k0 = next(k for k, z in enumerate(zs) if z < top)
        a, b = P[idx[k0 - 1]].copy(), P[idx[k0]].copy()
        S = a + (a[2] - top) / (a[2] - b[2]) * (b - a)
        din = (b - a) / np.linalg.norm(b - a)
        dout = np.array([-1.0, 0.004 * S[1], 0.0])
        dout /= np.linalg.norm(dout)
        nrm = dout - (dout @ din) * din
        nrm /= np.linalg.norm(nrm)
        theta = float(np.arccos(np.clip(din @ dout, -1, 1)))
        rho = -DRAPE_R / (nrm[2] * (1 - np.cos(theta)) + din[2] * np.sin(theta))
        # the path as a fine polyline: S, the bend, then straight on for as long as the rest of the strip
        rest = sum(np.linalg.norm(P[idx[k + 1]] - P[idx[k]]) for k in range(k0 - 1, len(idx) - 1)) + 50.0
        pts = [S + rho * (nrm * (1 - np.cos(t)) + din * np.sin(t)) for t in np.linspace(0, theta, 64)]
        end, n_straight = pts[-1], int(rest / 0.5) + 1
        pts += [end + dout * (0.5 * k) for k in range(1, n_straight)]
        path_pts = np.array([a] + pts)
        at = 0
        for k in range(k0 - 1, len(idx) - 1):
            i, j = idx[k], idx[k + 1]
            seg = np.linalg.norm(P[j] - P[i])
            d = np.linalg.norm(path_pts[at:] - P[i], axis=1)
            hit = np.nonzero(d >= seg)[0]
            if not len(hit):
                break
            h = at + int(hit[0])
            # between path samples h - 1 and h: the point at distance seg from the joint
            p0, p1 = path_pts[max(h - 1, 0)], path_pts[h]
            lo, hi = 0.0, 1.0
            for _ in range(30):
                mid = (lo + hi) / 2
                if np.linalg.norm(p0 + mid * (p1 - p0) - P[i]) < seg:
                    lo = mid
                else:
                    hi = mid
            target = p0 + lo * (p1 - p0)
            apply(i, rot_between(P[j] - P[i], target - P[i]))
            at = h
        return path[k0]

    def length_axis(n):
        """his bones point down their local -Y (an export from Blender): the last finger bones' own length"""
        i = ix[n]
        p = par[i]
        return float(np.linalg.norm(P0[i] - P0[p]))

    # the fingertips: the mean of the 10 vertices farthest from each last finger joint among those mostly on its bone
    tip_bind = {}
    for s in SIDES:
        for f in FINGERS:
            c = '%s_%s_c' % (s, f)
            wc = np.where(m['wb'] == ix[c], m['ww'], 0).sum(1)
            sel = np.nonzero(wc > 0.5)[0]
            d = np.linalg.norm(m['pos'][sel] - P0[ix[c]], axis=1)
            tip_bind[c] = m['pos'][sel[np.argsort(d)[-10:]]].mean(0)

    # ---- 1. pose his limbs into Rebirth's rest pose
    for s in SIDES:
        align(s + '_UpperArm_a', s + '_Forearm_a', s + '_UpperArm_a', s + '_Forearm_a')
        align(s + '_Forearm_a', s + '_Hand_a', s + '_Forearm_a', s + '_Hand_a')
        sgn = 1.0 if s == 'L' else -1.0

        def palm(get):
            return sgn * np.cross(get('Index') - get('H'), get('Pinky') - get('H'))
        hp = lambda k: P[ix[s + '_Hand_a']] if k == 'H' else P[ix['%s_%s_a' % (s, k)]]
        rpalm = palm(lambda k: rp(s + '_Hand_a') if k == 'H' else rp('%s_%s_a' % (s, k)))
        twist(s + '_Forearm_a', P[ix[s + '_Hand_a']] - P[ix[s + '_Forearm_a']], palm(hp), rpalm)
        align(s + '_Hand_a', s + '_Middle_a', s + '_Hand_a', s + '_Middle_a')
        twist(s + '_Hand_a', P[ix[s + '_Middle_a']] - P[ix[s + '_Hand_a']], palm(hp), rpalm)
        for f in FINGERS:
            a, b, c = ('%s_%s_%s' % (s, f, k) for k in 'abc')
            align(a, b, a, b)
            align(b, c, b, c)
            # (the last bones' own axes are not along the finger: the tip from the mesh, as the pose has carried it)
            ic = ix[c]
            tip = P[ic] + R[ic] @ R0[ic].T @ (tip_bind[c] - P0[ic])
            align(c, None, c, '%s_%s_End' % (s, f), child_point=tip)
    for s in SIDES:
        align(s + '_UpperLeg_a', s + '_Foreleg_a', s + '_UpperLeg_a', s + '_Foreleg_a')
        align(s + '_Foreleg_a', s + '_Foot_a', s + '_Foreleg_a', s + '_Foot_a')
        unturn(s + '_Foot_a')

    # ---- 1b. his long mantles reach 2.4 m below his feet (in his own game he hovers): what is below the floor is laid
    # along it behind him, bent over a quarter circle of DRAPE_R cm, so the strips start the game on the floor (the
    # physics' floor only holds what comes down onto it)
    drape_log = []
    for s in SIDES:
        for strip, path in (('A', ['%s_MantLgA%d' % (s, k) for k in range(1, 22)]),
                            ('B', ['%s_MantLgB%d' % (s, k) for k in range(1, 21)]),
                            ('C', ['%s_MantLgC%d' % (s, k) for k in range(1, 11)]),
                            ('E', ['%s_MantLgC%d' % (s, k) for k in range(1, 6)] + ['%s_MantLgE%d' % (s, k) for k in range(1, 15)]),
                            ('D', ['%s_MantLgD%d' % (s, k) for k in range(1, 12)])):
            moved = drape(path)
            if moved:
                drape_log.append('%s_%s from %s' % (s, strip, moved))
    log.append(('drape', ', '.join(drape_log), len(drape_log)))

    # ---- 2. the new skeleton
    face_root = ix['C_FaceBase_a']
    head_group = {'C_Neck_a', 'C_Head_a', 'C_FaceBase_a'} | {names[j] for j in subtree(face_root) if names[j] in RB}
    newR = np.zeros((NB, 3, 3))
    newP = np.zeros((NB, 3))
    kind = {}
    for i, n in enumerate(names):
        if n == 'Trans':
            newR[i], newP[i], kind[n] = rq('Trans'), np.zeros(3), 'rebirth'
        elif n in head_group:
            newR[i], newP[i], kind[n] = rq(n), rp(n), 'rebirth exact'
        elif n in RB:
            newR[i], newP[i], kind[n] = rq(n), P[i], 'rebirth frame'
        else:
            newR[i], newP[i], kind[n] = R[i], P[i], 'his own'
    for s in SIDES:
        h = ix[s + '_Hand_a']
        hs = np.linalg.norm(P[ix[s + '_Middle_a']] - P[h]) / np.linalg.norm(rp(s + '_Middle_a') - rp(s + '_Hand_a'))
        w = ix[s + '_Weapon_a']
        newR[w] = rq(s + '_Weapon_a')
        newP[w] = newP[h] + rq(s + '_Hand_a') @ (np.array(RB[s + '_Weapon_a']['local_t']) * hs)
        kind[s + '_Weapon_a'] = 'rebirth frame (hand-scaled place)'
    bone_names = list(names)
    bone_par = list(par)
    extra = []
    for n in ('C_CharaA_a', 'C_CharaExA_a', 'C_CharaExB_a'):
        if n in RB and n not in ix:
            bone_names.append(n)
            bone_par.append(ix['Trans'])
            extra.append((rq(n), rp(n)))
            kind[n] = 'rebirth exact'
    if extra:
        newR = np.concatenate([newR, np.array([e[0] for e in extra])])
        newP = np.concatenate([newP, np.array([e[1] for e in extra])])
    NN = len(bone_names)

    # ---- 3. pose the mesh (linear blend from his bind pose to the posed one; the head group does not move)
    pos0 = m['pos']
    nrm0 = m['normals']
    wb = m['wb']
    ww = m['ww'].astype(np.float64)
    V = len(pos0)
    newpos = np.zeros_like(pos0)
    newn = np.zeros_like(nrm0)
    for j in range(wb.shape[1]):
        b = wb[:, j]
        w = ww[:, j][:, None]
        Mr = np.einsum('vij,vkj->vik', R[b], R0[b])
        newpos += w * (np.einsum('vij,vj->vi', Mr, pos0 - P0[b]) + P[b])
        newn += w * np.einsum('vij,vj->vi', Mr, nrm0)
    wsum = ww.sum(1)[:, None]
    newpos /= wsum
    newn /= np.linalg.norm(newn, axis=1, keepdims=True) + 1e-12

    # ---- 4. weights
    tri = m['tri']
    lab = np.load(islands_path) if islands_path else None
    T = ix['Trans']
    bidx = {n: k for k, n in enumerate(bone_names)}
    Wd = [dict() for _ in range(V)]
    on_trans = np.zeros(V)
    for v in range(V):
        d = Wd[v]
        for b, w in zip(wb[v], ww[v]):
            if w <= 0:
                continue
            n = names[b]
            if b == T:
                on_trans[v] += w
                continue
            for bn, sh in SPLIT.get(n, [(n, 1.0)]):
                d[bidx[bn]] = d.get(bidx[bn], 0.0) + w * sh
    rules = {}
    for il in HEAD_ISLANDS:
        rules[il] = lambda p: {bidx['C_Head_a']: 1.0}
    for il in NECK_ISLANDS:
        rules[il] = lambda p: {bidx['C_Neck_a']: 1.0}

    def throat(p):
        u = float(np.clip((p[2] - 164.0) / (176.0 - 164.0), 0.0, 1.0))
        u = u * u * (3 - 2 * u)
        return {bidx['C_Spine_d']: 1 - u, bidx['C_Neck_a']: u}
    for il in THROAT_ISLANDS:
        rules[il] = throat
    for il in CHEST_ISLANDS:
        rules[il] = lambda p: {bidx['C_Spine_d']: 1.0}
    unruled = 0
    for v in np.nonzero(on_trans > 0)[0]:
        rule = rules.get(int(lab[v])) if lab is not None else None
        if rule is None:
            unruled += 1
            continue
        for b, w in rule(newpos[v]).items():
            Wd[v][b] = Wd[v].get(b, 0.0) + on_trans[v] * w
    # neighbours (mesh edges and welded duplicates)
    rows = np.concatenate([tri[:, 0], tri[:, 1], tri[:, 2], tri[:, 1], tri[:, 2], tri[:, 0]])
    cols = np.concatenate([tri[:, 1], tri[:, 2], tri[:, 0], tri[:, 0], tri[:, 1], tri[:, 2]])
    key = np.round(pos0 * 100).astype(np.int64)
    _, inv = np.unique(key, axis=0, return_inverse=True)
    inv = inv.ravel()
    Wl = sp.coo_matrix((np.ones(V), (np.arange(V), inv)), shape=(V, inv.max() + 1)).tocsr()
    A = (sp.coo_matrix((np.ones(len(rows)), (rows, cols)), shape=(V, V)) + Wl @ Wl.T).tocsr()
    A.setdiag(0)
    A.eliminate_zeros()
    # Trans vertices no rule covers: their neighbours' weights (breadth first)
    todo = {int(v) for v in np.nonzero(on_trans > 0)[0] if not Wd[v]}
    rounds = 0
    while todo and rounds < 50:
        done = {}
        for v in todo:
            nb = A.indices[A.indptr[v]:A.indptr[v + 1]]
            acc = {}
            for u in nb:
                if Wd[u] and u not in todo:
                    for b, w in Wd[u].items():
                        acc[b] = acc.get(b, 0.0) + w
            if acc:
                done[v] = acc
        for v, acc in done.items():
            Wd[v] = acc
        todo -= set(done)
        rounds += 1
    # blend the re-weighted chest into the weights around it: a band of 3 edge rings on the re-weighted side
    moved = on_trans > 0.5
    fixed = ~moved
    band = np.zeros(V, dtype=bool)
    front = fixed.copy()
    for ring in range(3):
        nxt = (A @ front.astype(np.float64)) > 0
        nxt &= moved & ~band
        band |= nxt
        front = nxt
    bv = np.nonzero(band)[0]
    for it in range(12):
        upd = {}
        for v in bv:
            nb = A.indices[A.indptr[v]:A.indptr[v + 1]]
            acc = {}
            for u in list(nb) + [v]:
                for b, w in Wd[u].items():
                    acc[b] = acc.get(b, 0.0) + w
            tot = sum(acc.values())
            upd[v] = {b: w / tot for b, w in acc.items()}
        for v, d in upd.items():
            Wd[v] = d
    # top 8, normalised
    NW = 8
    wbone = np.zeros((V, NW), dtype=np.int64)
    wweight = np.zeros((V, NW))
    for v in range(V):
        items = sorted(Wd[v].items(), key=lambda kv: -kv[1])[:NW]
        items = [(b, w) for b, w in items if w > 1e-4]
        tot = sum(w for _, w in items)
        for k, (b, w) in enumerate(items):
            wbone[v, k] = b
            wweight[v, k] = w / tot
    # ---- 5. local transforms
    loc_q, loc_t = [], []
    for i in range(NN):
        p = bone_par[i]
        if p < 0:
            loc_q.append(m2q(newR[i]))
            loc_t.append(newP[i])
        else:
            loc_q.append(m2q(newR[p].T @ newR[i]))
            loc_t.append(newR[p].T @ (newP[i] - newP[p]))
    uv = np.stack([m['uv0'], m['uv1'], m['uv2'], m['uv3']][:int(m['nuv'])], axis=1)
    np.savez(out_path, pos=newpos, nz=newn, uv=uv, tri=tri, tmat=m['mat'], slots=m['mat_names'],
             wbone=wbone, wweight=wweight, bone_names=np.array(bone_names), bone_parents=np.array(bone_par),
             bone_lq=np.array(loc_q), bone_lt=np.array(loc_t), bone_cq=np.array([m2q(r) for r in newR]), bone_ct=newP,
             bind_R0=R0, bind_P0=P0, posed_R=R, posed_P=P)
    moved_v = np.linalg.norm(newpos - pos0, axis=1)
    rep = dict(bones=NN, vertices=int(V), triangles=int(len(tri)), aligned=log,
               head_group=len(head_group), on_trans_before=int((on_trans > 0).sum()), unruled_trans=int(unruled),
               blend_band=int(band.sum()), max_vertex_move=round(float(moved_v.max()), 2),
               kinds={k: sum(1 for v in kind.values() if v == k) for k in set(kind.values())},
               moved={n: round(float(np.linalg.norm(newP[ix[n]] - P0[ix[n]])), 2) for n in
                      ('C_Neck_a', 'C_Head_a', 'L_Eye', 'R_Eye', 'L_Weapon_a', 'R_Weapon_a', 'L_Hand_a', 'R_Hand_a', 'L_Foot_a', 'L_Toe_a')})
    print(json.dumps(rep, indent=1)[:5000])
    if report_path:
        json.dump(rep, open(report_path, 'w'), indent=1)


if __name__ == '__main__':
    a = sys.argv[1:]
    main(a[0], a[1], a[2], a[3] if len(a) > 3 else None, a[4] if len(a) > 4 else None)
