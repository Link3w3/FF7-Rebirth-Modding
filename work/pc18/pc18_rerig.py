"""PC0010_18 (pc18_load.py's npz: Neo Bahamut BlackFeeler's skeleton and Whisper body under Rebirth Sephiroth's head and
hair) -> his model on FF7 Rebirth Sephiroth's bones, keeping his own proportions (as bfs_rerig.py did for PC0010_17):

  * the hierarchy as Rebirth's wherever a bone has Rebirth's name (8 bones moved: Neo Bahamut's spine runs a > b > c with
    the neck and shoulders on c, the user put Sephiroth's C_Spine_d between b and c; his head and C_FaceBase_b hung from
    Neo Bahamut's last neck bone): C_Spine_c under C_Spine_b, C_Spine_d under C_Spine_c, the neck, the shoulders and
    C_Neck1W_Spo under C_Spine_d, C_Head_a and C_FaceBase_b under C_Neck_a (Rebirth's animations drive a bone only where
    its parent is the one it has in Rebirth). Neo Bahamut's C_Neck_b / C_Neck_c stay under C_Neck_a (their frame
    C_Neck_a's: they turn with it); the head parts on them (the jaw, the horns, the tentacle) go under C_Head_a, so the
    headdress turns with Sephiroth's head;
  * his body bones (the Rebirth names: hips, spine, neck, shoulders, arms, hands, fingers, legs, feet, their helpers) get
    Rebirth's bone frames (PC0010_00's rest rotations) at his own joints; his arms, hands, fingers and legs are posed into
    Rebirth's rest pose first (the limbs along Rebirth's bones, the palms as Rebirth's, the soles kept flat);
  * Sephiroth's head, face rig, eyes and hair (the user's, at Rebirth's own place already) get Rebirth's exact transforms;
  * Neo Bahamut's own bones (wings, thrusters, tail, tentacle, horns, jaw, toes, the wing arms) keep Neo Bahamut's own
    frames (the game skeleton SU2050_00_Skeleton's, the armature's scale taken out), so Neo Bahamut's motions turn them
    as they turn his (pc18_motions.py), following the body;
  * helpers that sit on a joint (Spine1W, Neck1W, ShoulderSub, Elbow, Wrist, the last forearm roll, FemorisA, Hip, Knee)
    share their weights between the bones on each side of it (the game's KDI that turns them on Sephiroth does not run
    on a skin's model).
    pc18_rerig.py <pc18.npz> <rebirth rig.json> <out.npz> [report.json]"""
import json
import sys
import numpy as np
sys.path.insert(0, '/work/ccseph/tools')
from rerig import q2m, m2q, rot_between, axis_angle, signed_angle

SIDES = ('L', 'R')
FINGERS = ('Thumb', 'Middle', 'Ring', 'Pinky')     # (Neo Bahamut's claws: no index finger)
# Rebirth's parents for the bones the user's file has elsewhere
REPARENT = {'C_Spine_c': 'C_Spine_b', 'C_Spine_d': 'C_Spine_c', 'C_Neck_a': 'C_Spine_d', 'C_Neck1W_Spo': 'C_Spine_d',
            'L_Shoulder_a': 'C_Spine_d', 'R_Shoulder_a': 'C_Spine_d', 'C_Head_a': 'C_Neck_a', 'C_FaceBase_b': 'C_Neck_a',
            # the headdress with the head
            'C_Jaw_a': 'C_Head_a', 'C_Tentacle_Spo': 'C_Head_a',
            'L_HeadHornA_Spo': 'C_Head_a', 'L_HeadHornB_Spo': 'C_Head_a', 'L_HeadHornC_Spo': 'C_Head_a',
            'R_HeadHornA_Spo': 'C_Head_a', 'R_HeadHornB_Spo': 'C_Head_a', 'R_HeadHornC_Spo': 'C_Head_a'}
NECK_BETWEEN = ('C_Neck_b', 'C_Neck_c')   # Neo Bahamut's neck bones between C_Neck_a and the head: C_Neck_a's frame
SPLIT = {'C_Spine1W_Spo': [('C_Hip_a', .5), ('C_Spine_a', .5)], 'C_Neck1W_Spo': [('C_Spine_d', .5), ('C_Neck_a', .5)]}
for _s in SIDES:
    SPLIT.update({
        _s + '_ShoulderSub_Spo': [(_s + '_Shoulder_a', .5), (_s + '_UpperArm_a', .5)],
        _s + '_Elbow_Spo': [(_s + '_UpperArm_a', .5), (_s + '_Forearm_a', .5)],
        _s + '_Wrist_Spo': [(_s + '_Forearm_a', .5), (_s + '_Hand_a', .5)],
        _s + '_ForearmrollC_Spo': [(_s + '_Forearm_a', .7), (_s + '_Hand_a', .3)],
        _s + '_FemorisA_Spo': [('C_Hip_a', .5), (_s + '_UpperLeg_a', .5)],
        _s + '_Hip_Spo': [('C_Hip_a', .5), (_s + '_UpperLeg_a', .5)],
        _s + '_Knee_Spo': [(_s + '_UpperLeg_a', .5), (_s + '_Foreleg_a', .5)],
    })


def main(src, rig_path, out_path, report_path=None):
    m = np.load(src)
    names = [str(n) for n in m['names']]
    old_par = [int(p) for p in m['parents']]
    NB = len(names)
    ix = {n: i for i, n in enumerate(names)}
    par = list(old_par)
    for n, p in REPARENT.items():
        par[ix[n]] = ix[p]
    # parents first again (a bone's index before its children's)
    order, seen = [], set()

    def visit(i):
        if i in seen:
            return
        if par[i] >= 0:
            visit(par[i])
        seen.add(i)
        order.append(i)
    for i in range(NB):
        visit(i)
    R0 = m['R'].copy()
    P0 = m['P'].copy()
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

    def align(c, c_child, r, r_child):
        cur = P[ix[c_child]] - P[ix[c]]
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

    # ---- 1. his limbs into Rebirth's rest pose
    for s in SIDES:
        align(s + '_UpperArm_a', s + '_Forearm_a', s + '_UpperArm_a', s + '_Forearm_a')
        align(s + '_Forearm_a', s + '_Hand_a', s + '_Forearm_a', s + '_Hand_a')
        sgn = 1.0 if s == 'L' else -1.0

        def palm(get):
            return sgn * np.cross(get('Middle') - get('H'), get('Pinky') - get('H'))
        hp = lambda k: P[ix[s + '_Hand_a']] if k == 'H' else P[ix['%s_%s_a' % (s, k)]]
        rpalm = palm(lambda k: rp(s + '_Hand_a') if k == 'H' else rp('%s_%s_a' % (s, k)))
        twist(s + '_Forearm_a', P[ix[s + '_Hand_a']] - P[ix[s + '_Forearm_a']], palm(hp), rpalm)
        align(s + '_Hand_a', s + '_Middle_a', s + '_Hand_a', s + '_Middle_a')
        twist(s + '_Hand_a', P[ix[s + '_Middle_a']] - P[ix[s + '_Hand_a']], palm(hp), rpalm)
        for f in FINGERS:
            a, b, c, e = ('%s_%s_%s' % (s, f, k) for k in ('a', 'b', 'c', 'End'))
            align(a, b, a, b)
            align(b, c, b, c)
            align(c, e, c, e)
    for s in SIDES:
        align(s + '_UpperLeg_a', s + '_Foreleg_a', s + '_UpperLeg_a', s + '_Foreleg_a')
        align(s + '_Foreleg_a', s + '_Foot_a', s + '_Foreleg_a', s + '_Foot_a')
        unturn(s + '_Foot_a')

    # ---- 2. the new skeleton
    head_group = {'C_Head_a', 'C_FaceBase_a', 'C_FaceBase_b'}
    for root in ('C_Head_a', 'C_FaceBase_b'):
        head_group |= {names[j] for j in subtree(ix[root]) if names[j] in RB}
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
    for n in NECK_BETWEEN:
        newR[ix[n]] = newR[ix['C_Neck_a']]
        kind[n] = "C_Neck_a's frame"
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
    # the output order: parents first (the moved bones' children after them)
    out_order = order + list(range(NB, NN))
    remap = {old: k for k, old in enumerate(out_order)}

    # ---- 3. pose the mesh (linear blend from the bind pose to the posed one)
    pos0 = m['cp']
    wb = m['wb']
    ww = m['ww'].astype(np.float64)
    V = len(pos0)
    newpos = np.zeros_like(pos0)
    Mv = np.zeros((V, 3, 3))
    wsum = ww.sum(1)
    for j in range(wb.shape[1]):
        b = wb[:, j]
        w = ww[:, j][:, None]
        Mr = np.einsum('vij,vkj->vik', R[b], R0[b])
        newpos += w * (np.einsum('vij,vj->vi', Mr, pos0 - P0[b]) + P[b])
        Mv += w[:, :, None] * Mr
    newpos /= wsum[:, None]
    # the corners' normals: by their control point's blend of turns
    cc = m['corner_cp']
    nrm = np.einsum('cij,cj->ci', Mv[cc], m['nrm'])
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-12

    # ---- 4. weights (helpers on joints shared), top 8
    bidx = {n: k for k, n in enumerate(bone_names)}
    NW = 8
    wbone = np.zeros((V, NW), dtype=np.int64)
    wweight = np.zeros((V, NW))
    split_used = {}
    for v in range(V):
        d = {}
        for b, w in zip(wb[v], ww[v]):
            if w <= 0:
                continue
            n = names[b]
            for bn, sh in SPLIT.get(n, [(n, 1.0)]):
                d[bidx[bn]] = d.get(bidx[bn], 0.0) + w * sh
            if n in SPLIT:
                split_used[n] = split_used.get(n, 0) + 1
        items = sorted(d.items(), key=lambda kv: -kv[1])[:NW]
        items = [(b, w) for b, w in items if w > 1e-4]
        tot = sum(w for _, w in items)
        for k, (b, w) in enumerate(items):
            wbone[v, k] = remap[b]
            wweight[v, k] = w / tot

    # ---- 5. local transforms, in the output order
    newR_o = newR[out_order]
    newP_o = newP[out_order]
    names_o = [bone_names[i] for i in out_order]
    par_o = [remap[bone_par[i]] if bone_par[i] >= 0 else -1 for i in out_order]
    loc_q, loc_t = [], []
    for k in range(NN):
        p = par_o[k]
        assert p < k
        if p < 0:
            loc_q.append(m2q(newR_o[k]))
            loc_t.append(newP_o[k])
        else:
            loc_q.append(m2q(newR_o[p].T @ newR_o[k]))
            loc_t.append(newR_o[p].T @ (newP_o[k] - newP_o[p]))
    np.savez(out_path, pos=newpos, corner_cp=cc, tri=m['tri'], nz=nrm, uv0=m['uv0'], uv1=m['uv1'], uv2=m['uv2'], col=m['col'],
             tmat=m['tmat'], slots=m['mat_names'], wbone=wbone, wweight=wweight, bone_names=np.array(names_o),
             bone_parents=np.array(par_o), bone_lq=np.array(loc_q), bone_lt=np.array(loc_t),
             bone_cq=np.array([m2q(r) for r in newR_o]), bone_ct=newP_o,
             # for the motions: each bone's frame before the posing (Neo Bahamut's own) and after it
             bind_R0=np.concatenate([R0, np.array([e[0] for e in extra]).reshape(-1, 3, 3)])[out_order],
             posed_R=np.concatenate([R, np.array([e[0] for e in extra]).reshape(-1, 3, 3)])[out_order])
    moved_v = np.linalg.norm(newpos - pos0, axis=1)
    rep = dict(bones=NN, vertices=int(V), corners=int(len(cc)), triangles=int(len(m['tri'])), aligned=log, reparented=REPARENT,
               head_group=len(head_group), split_helpers=split_used, max_vertex_move=round(float(moved_v.max()), 2),
               kinds={k: sum(1 for v in kind.values() if v == k) for k in set(kind.values())},
               weapon={s: [round(float(x), 2) for x in newP[ix[s + '_Weapon_a']]] for s in SIDES})
    print(json.dumps(rep, indent=1)[:6000])
    if report_path:
        json.dump(rep, open(report_path, 'w'), indent=1)


if __name__ == '__main__':
    a = sys.argv[1:]
    main(a[0], a[1], a[2], a[3] if len(a) > 3 else None)
