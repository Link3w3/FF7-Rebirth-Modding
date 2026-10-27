"""Crisis Core Sephiroth (game mesh, ccmesh.py npz) -> a mesh on FF7 Rebirth Sephiroth's bones (PC0010_00 names and rest
rotations for the body, the model's own proportions), posed into Rebirth's rest pose; hair, coat and face keep their bones.
    rerig.py <cc.npz> <rebirth rig.json> <out.npz> [report.json]"""
import sys, json
import numpy as np

def q2m(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])

def m2q(m):
    t = np.trace(m)
    if t > 0:
        s = np.sqrt(t + 1.0) * 2; w = 0.25 * s
        x = (m[2, 1] - m[1, 2]) / s; y = (m[0, 2] - m[2, 0]) / s; z = (m[1, 0] - m[0, 1]) / s
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        s = np.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2]) * 2; w = (m[2, 1] - m[1, 2]) / s
        x = 0.25 * s; y = (m[0, 1] + m[1, 0]) / s; z = (m[0, 2] + m[2, 0]) / s
    elif m[1, 1] > m[2, 2]:
        s = np.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2]) * 2; w = (m[0, 2] - m[2, 0]) / s
        x = (m[0, 1] + m[1, 0]) / s; y = 0.25 * s; z = (m[1, 2] + m[2, 1]) / s
    else:
        s = np.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1]) * 2; w = (m[1, 0] - m[0, 1]) / s
        x = (m[0, 2] + m[2, 0]) / s; y = (m[1, 2] + m[2, 1]) / s; z = 0.25 * s
    q = np.array([x, y, z, w]); q /= np.linalg.norm(q)
    return q if q[3] >= 0 else -q

def rot_between(a, b):
    a = a / np.linalg.norm(a); b = b / np.linalg.norm(b)
    v = np.cross(a, b); c = float(np.dot(a, b))
    if c > 1 - 1e-12: return np.eye(3)
    if c < -1 + 1e-12:
        ax = np.cross(a, [1, 0, 0]);
        if np.linalg.norm(ax) < 1e-6: ax = np.cross(a, [0, 1, 0])
        ax /= np.linalg.norm(ax); return axis_angle(ax, np.pi)
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + vx + vx @ vx * (1 / (1 + c))

def axis_angle(ax, ang):
    ax = ax / np.linalg.norm(ax); x, y, z = ax; c, s = np.cos(ang), np.sin(ang); C = 1 - c
    return np.array([[c + x * x * C, x * y * C - z * s, x * z * C + y * s], [y * x * C + z * s, c + y * y * C, y * z * C - x * s],
                     [z * x * C - y * s, z * y * C + x * s, c + z * z * C]])

def signed_angle(a, b, axis):
    axis = axis / np.linalg.norm(axis)
    a = a - axis * np.dot(a, axis); b = b - axis * np.dot(b, axis)
    a /= np.linalg.norm(a); b /= np.linalg.norm(b)
    return np.arctan2(np.dot(np.cross(a, b), axis), np.dot(a, b))

FINGERS = [('Thumb', 'Thumb'), ('Index', 'Index'), ('Middle', 'Middle'), ('Ring', 'Ring'), ('Pinky', 'Pinky')]
SIDES = [('Left', 'L'), ('Right', 'R')]

def main(cc_path, rig_path, out_path, report_path=None):
    m = np.load(cc_path, allow_pickle=True)
    names = [str(n) for n in m['bone_names']]; par = [int(p) for p in m['bone_parents']]
    NB = len(names); ix = {n: i for i, n in enumerate(names)}
    # CC bind pose in component space, turned into Rebirth's frame (CC faces +Y with +X to its left; Rebirth faces +X)
    conv = q2m([0, 0, -np.sqrt(0.5), np.sqrt(0.5)])
    Rl = [q2m(q) for q in m['bone_q']]; tl = [np.array(t) for t in m['bone_t']]
    R0 = [None] * NB; P0 = [None] * NB
    for i in range(NB):
        if par[i] < 0: R0[i] = conv @ Rl[i]; P0[i] = conv @ tl[i]
        else: R0[i] = R0[par[i]] @ Rl[i]; P0[i] = P0[par[i]] + R0[par[i]] @ tl[i]
    R0 = np.array(R0); P0 = np.array(P0)
    R = R0.copy(); P = P0.copy()
    children = [[] for _ in range(NB)]
    for i, p in enumerate(par):
        if p >= 0: children[p].append(i)
    def subtree(i):
        out = [i]; k = 0
        while k < len(out):
            out += children[out[k]]; k += 1
        return out
    def apply(i, M):
        """rotate bone i's subtree by M about bone i's joint"""
        o = P[i].copy()
        for j in subtree(i):
            P[j] = o + M @ (P[j] - o); R[j] = M @ R[j]
    rig = json.load(open(rig_path))
    RB = {b['name']: b for b in rig['bones']}
    rp = lambda n: np.array(RB[n]['t'], dtype=float)
    rq = lambda n: q2m(RB[n]['q'])
    log = []
    def align(c, c_child, r, r_child, child_point=None):
        cur = (child_point if child_point is not None else P[ix[c_child]]) - P[ix[c]]
        tgt = rp(r_child) - rp(r)
        M = rot_between(cur, tgt)
        ang = np.degrees(np.arccos(np.clip(np.dot(cur / np.linalg.norm(cur), tgt / np.linalg.norm(tgt)), -1, 1)))
        apply(ix[c], M); log.append(('swing', c, round(float(ang), 2)))
    def twist(c, axis, cur, tgt):
        a = signed_angle(cur, tgt, axis)
        apply(ix[c], axis_angle(axis, a)); log.append(('twist', c, round(float(np.degrees(a)), 2)))
    # 1. the upper body: hip -> neck
    align('Spine', None, 'C_Hip_a', 'C_Neck_a', child_point=P[ix['Neck']]) if False else None
    cur = P[ix['Neck']] - P[ix['Spine']]; tgt = rp('C_Neck_a') - rp('C_Hip_a')
    apply(ix['Spine'], rot_between(cur, tgt)); log.append(('swing', 'Spine', round(float(np.degrees(np.arccos(np.clip(np.dot(cur, tgt) / np.linalg.norm(cur) / np.linalg.norm(tgt), -1, 1)))), 2)))
    # 2. neck, then the head so its brow line faces as Rebirth's does
    align('Neck', 'Head', 'C_Neck_a', 'C_Head_a')
    # the head keeps the face as the model has it (looking straight ahead, as Rebirth's rest pose does): undo what the
    # spine and neck turns did to it (its joint stays where they put it)
    A = R[ix['Head']] @ R0[ix['Head']].T
    apply(ix['Head'], A.T); log.append(('unturn', 'Head', round(float(np.degrees(np.arccos(np.clip((np.trace(A) - 1) / 2, -1, 1)))), 2)))
    # 3. arms and hands
    for cs, rs in SIDES:
        align(cs + 'Shoulder', cs + 'Arm', rs + '_Shoulder_a', rs + '_UpperArm_a')
        align(cs + 'Arm', cs + 'ForeArm', rs + '_UpperArm_a', rs + '_Forearm_a')
        align(cs + 'ForeArm', cs + 'Hand', rs + '_Forearm_a', rs + '_Hand_a')
        sgn = 1.0 if cs == 'Left' else -1.0
        def palm(get):
            return sgn * np.cross(get('Index') - get('H'), get('Pinky') - get('H'))
        cpalm = palm(lambda k: P[ix[cs + 'Hand']] if k == 'H' else P[ix[cs + 'Hand' + k + '1']])
        rpalm = palm(lambda k: rp(rs + '_Hand_a') if k == 'H' else rp(rs + '_' + k + '_a'))
        twist(cs + 'ForeArm', P[ix[cs + 'Hand']] - P[ix[cs + 'ForeArm']], cpalm, rpalm)
        align(cs + 'Hand', cs + 'HandMiddle1', rs + '_Hand_a', rs + '_Middle_a')
        cpalm = palm(lambda k: P[ix[cs + 'Hand']] if k == 'H' else P[ix[cs + 'Hand' + k + '1']])
        twist(cs + 'Hand', P[ix[cs + 'HandMiddle1']] - P[ix[cs + 'Hand']], cpalm, rpalm)
        for cf, rf in FINGERS:
            align('%sHand%s1' % (cs, cf), '%sHand%s2' % (cs, cf), '%s_%s_a' % (rs, rf), '%s_%s_b' % (rs, rf))
            align('%sHand%s2' % (cs, cf), '%sHand%s3' % (cs, cf), '%s_%s_b' % (rs, rf), '%s_%s_c' % (rs, rf))
            # the last segment along its own x axis (CC bones point down x)
            i3 = ix['%sHand%s3' % (cs, cf)]
            tip = P[i3] + R[i3] @ np.array([2.5, 0, 0])
            align('%sHand%s3' % (cs, cf), None, '%s_%s_c' % (rs, rf), '%s_%s_End' % (rs, rf), child_point=tip)
    # 4. legs and feet
    for cs, rs in SIDES:
        align(cs + 'UpLeg', cs + 'Leg', rs + '_UpperLeg_a', rs + '_Foreleg_a')
        align(cs + 'Leg', cs + 'Foot', rs + '_Foreleg_a', rs + '_Foot_a')
        # the feet stay as the model has them: soles flat on the ground, as in Rebirth's rest pose (their joint-to-joint
        # lines differ only because the rigs put the ball joint elsewhere); the knee and hip turns above are undone on them
        A = R[ix[cs + 'Foot']] @ R0[ix[cs + 'Foot']].T
        apply(ix[cs + 'Foot'], A.T); log.append(('unturn', cs + 'Foot', round(float(np.degrees(np.arccos(np.clip((np.trace(A) - 1) / 2, -1, 1)))), 2)))
    # the new skeleton
    bones = []   # (name, parent name, CS rotation matrix, CS position, source CC bone or None)
    def add(n, p, Rm, t, src=None):
        bones.append((n, p, Rm, np.array(t, dtype=float), src))
    add('Trans', None, rq('Trans'), [0, 0, 0])
    for n in ('C_CharaA_a', 'C_CharaExA_a', 'C_CharaExB_a'):
        add(n, 'Trans', rq(n), [0, 0, 0])
    legmid = (P[ix['LeftUpLeg']] + P[ix['RightUpLeg']]) / 2
    rlegmid = (rp('L_UpperLeg_a') + rp('R_UpperLeg_a')) / 2
    hip = legmid + (rp('C_Hip_a') - rlegmid)
    add('C_Hip_a', 'Trans', rq('C_Hip_a'), hip)
    # the spine joints along the model's torso, at Rebirth's fractions of the hip -> neck height
    poly = np.array([hip, P[ix['Spine1']], P[ix['Neck']]])
    def at_height(f):
        z = poly[0, 2] + f * (poly[2, 2] - poly[0, 2])
        for k in range(2):
            if z <= poly[k + 1, 2] or k == 1:
                u = (z - poly[k, 2]) / (poly[k + 1, 2] - poly[k, 2])
                return poly[k] + u * (poly[k + 1] - poly[k])
    h0 = rp('C_Hip_a')[2]; h1 = rp('C_Neck_a')[2]
    prev = 'C_Hip_a'
    for n in ('C_Spine_a', 'C_Spine_b', 'C_Spine_c', 'C_Spine_d'):
        add(n, prev, rq(n), at_height((rp(n)[2] - h0) / (h1 - h0))); prev = n
    add('C_Neck_a', 'C_Spine_d', rq('C_Neck_a'), P[ix['Neck']], 'Neck')
    add('C_Head_a', 'C_Neck_a', rq('C_Head_a'), P[ix['Head']], 'Head')
    add('C_FaceBase_a', 'C_Head_a', rq('C_FaceBase_a'), P[ix['Head']])
    for cs, rs in SIDES:
        add(rs + '_Shoulder_a', 'C_Spine_d', rq(rs + '_Shoulder_a'), P[ix[cs + 'Shoulder']], cs + 'Shoulder')
        add(rs + '_UpperArm_a', rs + '_Shoulder_a', rq(rs + '_UpperArm_a'), P[ix[cs + 'Arm']], cs + 'Arm')
        add(rs + '_Forearm_a', rs + '_UpperArm_a', rq(rs + '_Forearm_a'), P[ix[cs + 'ForeArm']], cs + 'ForeArm')
        add(rs + '_Hand_a', rs + '_Forearm_a', rq(rs + '_Hand_a'), P[ix[cs + 'Hand']], cs + 'Hand')
        hs = np.linalg.norm(P[ix[cs + 'HandMiddle1']] - P[ix[cs + 'Hand']]) / np.linalg.norm(rp(rs + '_Middle_a') - rp(rs + '_Hand_a'))
        wt = P[ix[cs + 'Hand']] + rq(rs + '_Hand_a') @ (np.array(RB[rs + '_Weapon_a']['local_t']) * hs)
        add(rs + '_Weapon_a', rs + '_Hand_a', rq(rs + '_Weapon_a'), wt)
        for cf, rf in FINGERS:
            prevb = rs + '_Hand_a'
            for k, c in (('a', '1'), ('b', '2'), ('c', '3')):
                n = '%s_%s_%s' % (rs, rf, k)
                add(n, prevb, rq(n), P[ix['%sHand%s%s' % (cs, cf, c)]], '%sHand%s%s' % (cs, cf, c)); prevb = n
        add(rs + '_UpperLeg_a', 'C_Hip_a', rq(rs + '_UpperLeg_a'), P[ix[cs + 'UpLeg']], cs + 'UpLeg')
        add(rs + '_Foreleg_a', rs + '_UpperLeg_a', rq(rs + '_Foreleg_a'), P[ix[cs + 'Leg']], cs + 'Leg')
        add(rs + '_Foot_a', rs + '_Foreleg_a', rq(rs + '_Foot_a'), P[ix[cs + 'Foot']], cs + 'Foot')
        add(rs + '_Toe_a', rs + '_Foot_a', rq(rs + '_Toe_a'), P[ix[cs + 'ToeBase']], cs + 'ToeBase')
        add(rs + '_Eye', 'C_FaceBase_a', rq(rs + '_Eye'), P[ix['hi_eye_' + rs]], 'hi_eye_' + rs)
    # the model's own bones kept: hair, face, coat
    keep = []
    for i, n in enumerate(names):
        if n in ('hi_hair',) or 'Hair' in n or n.endswith('_hair'):
            if n.endswith('_eff') or n.endswith('_chn'): continue
            keep.append(i)
        elif n.startswith('hi_') and n not in ('hi_face', 'hi_eye_L', 'hi_eye_R', 'hi_hair'):
            keep.append(i)
        elif 'Coat' in n and not (n.endswith('_eff') or n.endswith('_chn')):
            keep.append(i)
    newparent = {}
    for i in keep:
        p = names[par[i]]
        if p in ('Head', 'hi_face'): newparent[i] = 'C_Head_a'
        elif p == 'Hips': newparent[i] = 'C_Hip_a'
        else: newparent[i] = p
    placed = {b[0] for b in bones}
    pending = list(keep)
    while pending:
        rest = []
        for i in pending:
            if newparent[i] in placed:
                add(names[i], newparent[i], R[i], P[i], names[i]); placed.add(names[i])
            else:
                rest.append(i)
        assert len(rest) < len(pending), [names[i] for i in rest]
        pending = rest
    bidx = {b[0]: k for k, b in enumerate(bones)}
    # skin weights: CC bone -> [(new bone, share)]
    direct = {'Hips': 'C_Hip_a', 'Neck': 'C_Neck_a', 'Head': 'C_Head_a'}
    for cs, rs in SIDES:
        direct.update({cs + 'Shoulder': rs + '_Shoulder_a', cs + 'Arm': rs + '_UpperArm_a', cs + 'ForeArm': rs + '_Forearm_a', cs + 'Hand': rs + '_Hand_a',
                       cs + 'UpLeg': rs + '_UpperLeg_a', cs + 'Leg': rs + '_Foreleg_a', cs + 'Foot': rs + '_Foot_a', cs + 'ToeBase': rs + '_Toe_a',
                       'hi_eye_' + rs: rs + '_Eye',
                       cs + 'ArmRoll1': rs + '_UpperArm_a', cs + 'ArmRoll2': rs + '_UpperArm_a',
                       cs + 'ForeArmRoll1': rs + '_Forearm_a', cs + 'ForeArmRoll2': rs + '_Forearm_a', cs + 'ForeArmRoll3': rs + '_Forearm_a',
                       cs + 'WristAcce': rs + '_Forearm_a', cs + 'LegRoll': rs + '_Foreleg_a', cs + 'UpLegRoll': rs + '_UpperLeg_a'})
        for cf, rf in FINGERS:
            for k, c in (('a', '1'), ('b', '2'), ('c', '3')):
                direct['%sHand%s%s' % (cs, cf, c)] = '%s_%s_%s' % (rs, rf, k)
    split = {}
    for cs, rs in SIDES:
        split[cs + 'ArmSub'] = [(rs + '_Shoulder_a', .5), (rs + '_UpperArm_a', .5)]
        split[cs + 'ForeArmSub'] = [(rs + '_UpperArm_a', .5), (rs + '_Forearm_a', .5)]
        split[cs + 'HandSub'] = [(rs + '_Forearm_a', .5), (rs + '_Hand_a', .5)]
        split[cs + 'LegSub'] = [(rs + '_UpperLeg_a', .5), (rs + '_Foreleg_a', .5)]
        split[cs + 'UpLegSub'] = [('C_Hip_a', .5), (rs + '_UpperLeg_a', .5)]
        g = 'left' if cs == 'Left' else 'right'
        split[g + '_shoulder_guard1'] = [(rs + '_Shoulder_a', .5), (rs + '_UpperArm_a', .5)]
        split[g + '_shoulder_guard2'] = [(rs + '_Shoulder_a', .5), (rs + '_UpperArm_a', .5)]
    for c in ('LeftCollar', 'RightCollar', 'LeftCollar1', 'RightCollar1', 'BackCollar'):
        split[c] = [('C_Spine_d', 1.0)]
    for i in keep:
        direct[names[i]] = names[i]
    # vertices: drop the sword section (its own weapon replaces it)
    slots = [str(s) for s in m['mat_slots']]
    drop_mats = {slots.index('CH_wepA')}
    tri = m['tri']; tmat = m['tmat']
    keep_t = ~np.isin(tmat, list(drop_mats))
    used_v = np.unique(tri[keep_t].ravel())
    remap = -np.ones(len(m['pos']), dtype=np.int64); remap[used_v] = np.arange(len(used_v))
    pos0 = m['pos'] @ conv.T
    nz = m['tangz'][:, :3] @ conv.T; nx = m['tangx'][:, :3] @ conv.T
    wb = m['wbone']; ww = m['wweight']
    # pose the mesh (linear blend from the bind pose to the aligned pose)
    V = len(pos0)
    newpos = np.zeros_like(pos0); newnz = np.zeros_like(nz); newnx = np.zeros_like(nx)
    for j in range(wb.shape[1]):
        b = wb[:, j]; w = ww[:, j][:, None]
        Mr = np.einsum('vij,vkj->vik', R[b], R0[b])     # R_posed * R_bind^T
        d = pos0 - P0[b]
        newpos += w * (np.einsum('vij,vj->vi', Mr, d) + P[b])
        newnz += w * np.einsum('vij,vj->vi', Mr, nz); newnx += w * np.einsum('vij,vj->vi', Mr, nx)
    newnz /= np.linalg.norm(newnz, axis=1, keepdims=True) + 1e-12
    newnx -= newnz * np.sum(newnx * newnz, axis=1, keepdims=True)
    newnx /= np.linalg.norm(newnx, axis=1, keepdims=True) + 1e-12
    # spine weights by height over the four spine joints
    sp_names = ['C_Spine_a', 'C_Spine_b', 'C_Spine_c', 'C_Spine_d']
    sp_z = np.array([bones[bidx[n]][3][2] for n in sp_names])
    def spine_shares(z):
        if z <= sp_z[0]: return [(sp_names[0], 1.0)]
        if z >= sp_z[-1]: return [(sp_names[-1], 1.0)]
        k = int(np.searchsorted(sp_z, z) - 1); u = (z - sp_z[k]) / (sp_z[k + 1] - sp_z[k])
        return [(sp_names[k], 1 - u), (sp_names[k + 1], u)]
    newW = []
    missing = {}
    for v in range(V):
        acc = {}
        for j in range(wb.shape[1]):
            w = ww[v, j]
            if w <= 0: continue
            n = names[wb[v, j]]
            if n in ('Spine', 'Spine1'):
                shares = spine_shares(newpos[v, 2])
            elif n in split:
                shares = split[n]
            elif n in direct:
                shares = [(direct[n], 1.0)]
            else:
                missing[n] = missing.get(n, 0) + w
                shares = [('C_Hip_a', 1.0)]
            for bn, s in shares:
                acc[bidx[bn]] = acc.get(bidx[bn], 0) + w * s
        items = sorted(acc.items(), key=lambda kv: -kv[1])[:8]
        tot = sum(w for _, w in items)
        newW.append([(b, w / tot) for b, w in items])
    # local transforms of the new skeleton
    loc_q, loc_t = [], []
    for n, p, Rm, t, src in bones:
        if p is None:
            loc_q.append(m2q(Rm)); loc_t.append(t)
        else:
            pb = bones[bidx[p]]
            Lr = pb[2].T @ Rm; Lt = pb[2].T @ (t - pb[3])
            loc_q.append(m2q(Lr)); loc_t.append(Lt)
    # outputs (the kept vertices only)
    keepv = used_v
    W = np.zeros((len(keepv), 8), dtype=np.int64); Wt = np.zeros((len(keepv), 8))
    for k, v in enumerate(keepv):
        for j, (b, w) in enumerate(newW[v]):
            W[k, j] = b; Wt[k, j] = w
    new_tri = remap[tri[keep_t]]
    mat_keep = [k for k in range(len(slots)) if k not in drop_mats and (tmat[keep_t] == k).any()]
    mremap = {k: i for i, k in enumerate(mat_keep)}
    new_tmat = np.array([mremap[k] for k in tmat[keep_t]])
    np.savez(out_path, pos=newpos[keepv], nz=newnz[keepv], nx=newnx[keepv], tsign=m['tangz'][keepv, 3], uv=m['uv'][keepv],
             tri=new_tri, tmat=new_tmat, slots=np.array([slots[k] for k in mat_keep]),
             mat_paths=np.array([str(m['mat_paths'][k]) for k in mat_keep]),
             wbone=W, wweight=Wt, bone_names=np.array([b[0] for b in bones]),
             bone_parents=np.array([bidx[b[1]] if b[1] else -1 for b in bones]),
             bone_lq=np.array(loc_q), bone_lt=np.array(loc_t),
             bone_cq=np.array([m2q(b[2]) for b in bones]), bone_ct=np.array([b[3] for b in bones]),
             bone_src=np.array([b[4] or '' for b in bones]),
             # the Crisis Core bones' bind pose (R0, P0, in Rebirth's frame) and the pose the re-rig moved them to (R, P):
             # what the animation retarget needs to carry Crisis Core motion onto the new bones
             cc_names=np.array(names), cc_parents=np.array(par), cc_R0=R0, cc_P0=P0, cc_R=R, cc_P=P, cc_conv=conv)
    rep = dict(bones=len(bones), vertices=int(len(keepv)), triangles=int(len(new_tri)), slots=[slots[k] for k in mat_keep],
               aligned=log, unmapped_weights={k: round(float(v), 2) for k, v in missing.items()},
               max_vertex_move=float(np.abs(newpos - pos0).max()),
               subs={n: [round(float(c), 2) for c in P0[ix[n]]] for n in names if n.endswith('Sub') or 'guard' in n})
    print(json.dumps(rep, indent=1)[:6000])
    if report_path:
        json.dump(rep, open(report_path, 'w'), indent=1)

if __name__ == '__main__':
    main(*sys.argv[1:5])
