"""Dissidia NT Sephiroth (dnt_model.py npz) -> a mesh on FF7 Rebirth Sephiroth's bones (PC0010_00 names and rest
rotations for the body, the model's own proportions), posed into Rebirth's rest pose; his hair, coat, collar, belt flaps
and wrist tassel keep their own bones (renamed the Rebirth way for the Kawaii preset: C_/L_/R_ + part + _a.._Phy).

Works like the Crisis Core re-rig (ccseph/tools/rerig.py, whose alignment steps it repeats), with Dissidia NT's
space turned into Unreal's: Dissidia NT is right-handed (Y up, the character facing +Z, +X his left), Unreal
left-handed (Z up, facing +X, +Y his right): positions go through the reflection M (x' = z, y' = -x, z' = y),
rotations through M R M^T, tangent signs flip; the triangles keep their order (Unreal's winding then, as the Crisis
Core output's).

    dnt_rerig.py <dnt_model npz> <rebirth rig.json> <out.npz> [report.json]

Bone names (Dissidia NT ships none): the base skeleton's joints by global id (b<id>), the model layer's d_<local>;
the map below was read off the bind pose (see DNT_BODY)."""
import json
import sys

import numpy as np

sys.path.insert(0, '/work/ccseph/tools')
from rerig import q2m, m2q, rot_between, axis_angle, signed_angle   # noqa: E402

M = np.array([[0.0, 0.0, 1.0], [-1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])    # Dissidia NT -> Unreal (det -1)

# Dissidia NT body joints (base skeleton global ids) under the Crisis Core re-rig's names
DNT_BODY = {
    'Hips': 'b2', 'Spine': 'b9', 'Spine1': 'b10', 'Neck': 'b11', 'Head': 'b12',
    'LeftShoulder': 'b13', 'LeftArm': 'b15', 'LeftForeArm': 'b17', 'LeftHand': 'b19',
    'RightShoulder': 'b14', 'RightArm': 'b16', 'RightForeArm': 'b18', 'RightHand': 'b20',
    'LeftUpLeg': 'b3', 'LeftLeg': 'b5', 'LeftFoot': 'b7', 'LeftToeBase': 'b23',
    'RightUpLeg': 'b4', 'RightLeg': 'b6', 'RightFoot': 'b8', 'RightToeBase': 'b24',
    'LeftHandThumb1': 'b51', 'LeftHandThumb2': 'b53', 'LeftHandThumb3': 'b55',
    'LeftHandIndex1': 'b27', 'LeftHandIndex2': 'b29', 'LeftHandIndex3': 'b31',
    'LeftHandMiddle1': 'b33', 'LeftHandMiddle2': 'b35', 'LeftHandMiddle3': 'b37',
    'LeftHandRing1': 'b39', 'LeftHandRing2': 'b41', 'LeftHandRing3': 'b43',
    'LeftHandPinky1': 'b45', 'LeftHandPinky2': 'b47', 'LeftHandPinky3': 'b49',
    'RightHandThumb1': 'b52', 'RightHandThumb2': 'b54', 'RightHandThumb3': 'b56',
    'RightHandIndex1': 'b28', 'RightHandIndex2': 'b30', 'RightHandIndex3': 'b32',
    'RightHandMiddle1': 'b34', 'RightHandMiddle2': 'b36', 'RightHandMiddle3': 'b38',
    'RightHandRing1': 'b40', 'RightHandRing2': 'b42', 'RightHandRing3': 'b44',
    'RightHandPinky1': 'b46', 'RightHandPinky2': 'b48', 'RightHandPinky3': 'b50',
}
FINGERS = [('Thumb', 'Thumb'), ('Index', 'Index'), ('Middle', 'Middle'), ('Ring', 'Ring'), ('Pinky', 'Pinky')]
SIDES = [('Left', 'L'), ('Right', 'R')]
# helper joints folded into the Rebirth body bones: name -> [(Rebirth bone, share)]
HELPERS = {
    'b300': [('L_UpperArm_a', 1)], 'b302': [('L_UpperArm_a', 1)], 'b301': [('R_UpperArm_a', 1)], 'b303': [('R_UpperArm_a', 1)],
    'b304': [('L_UpperArm_a', .5), ('L_Forearm_a', .5)], 'b305': [('R_UpperArm_a', .5), ('R_Forearm_a', .5)],
    'b306': [('L_Forearm_a', 1)], 'b308': [('L_Forearm_a', 1)], 'b307': [('R_Forearm_a', 1)], 'b309': [('R_Forearm_a', 1)],
    'b310': [('L_UpperLeg_a', 1)], 'b312': [('L_UpperLeg_a', 1)], 'b311': [('R_UpperLeg_a', 1)], 'b313': [('R_UpperLeg_a', 1)],
    'b314': [('L_UpperLeg_a', .5), ('L_Foreleg_a', .5)], 'b315': [('R_UpperLeg_a', .5), ('R_Foreleg_a', .5)],
    'b316': [('L_Foreleg_a', 1)], 'b317': [('R_Foreleg_a', 1)],
    'b320': [('C_Hip_a', .5), ('L_UpperLeg_a', .5)], 'b321': [('C_Hip_a', .5), ('R_UpperLeg_a', .5)],
    'b318': [('C_Spine_b', 1)], 'b319': [('C_Spine_b', 1)], 'b331': [('C_Spine_a', 1)], 'b322': [('C_Spine_c', 1)],
    'b323': [('C_Spine_d', 1)], 'b324': [('C_Spine_d', 1)], 'b325': [('C_Spine_d', 1)], 'b326': [('C_Spine_d', 1)],
    'b327': [('C_Neck_a', 1)], 'b328': [('C_Neck_a', 1)], 'b329': [('L_Shoulder_a', 1)], 'b330': [('R_Shoulder_a', 1)],
    'b21': [('L_Hand_a', 1)], 'b22': [('R_Hand_a', 1)], 'b25': [('L_Hand_a', 1)], 'b26': [('R_Hand_a', 1)],
    'b468': [('C_Head_a', 1)], 'b469': [('C_Head_a', 1)], 'b0': [('C_Hip_a', 1)], 'b1': [('C_Hip_a', 1)],
    'b399': [('C_Hip_a', 1)], 'd_0': [('C_Hip_a', 1)],
}
# his own bones kept (renamed): chains by their first joint -> part name; every joint down the chain is kept
CHAINS = [
    # long hair: the centre strand and its side strands
    ('b400', 'C_HairLongDNT'), ('b1130', 'C_HairLongDNTB'), ('b1140', 'L_HairLongDNTB'), ('b1145', 'R_HairLongDNTB'),
    ('b1100', 'C_HairLongDNTA'), ('b1110', 'L_HairLongDNTA'), ('b1120', 'R_HairLongDNTA'),
    ('b1200', 'R_HairSideDNT'), ('b1201', 'L_HairSideDNT'),
    # front hair strands (the model layer)
    ('d_28', 'L_HairFrontDNTA'), ('d_34', 'R_HairFrontDNTA'), ('d_40', 'L_HairFrontDNTB'), ('d_45', 'R_HairFrontDNTB'),
    # coat tails: roots on the hips, five joints each
    ('b1000', 'R_CoatDNTF'), ('b1010', 'R_CoatDNTS'), ('b1080', 'L_CoatDNTF'), ('b1070', 'L_CoatDNTS'),
    ('b1020', 'R_CoatDNTB'), ('b1060', 'L_CoatDNTB'), ('b1030', 'R_CoatDNTK'), ('b1050', 'L_CoatDNTK'),
    ('b1040', 'C_CoatDNTK'),
    # belt flaps over the front, the wrist tassel
    ('d_11', 'R_BeltDNTA'), ('d_16', 'L_BeltDNTA'), ('d_21', 'L_BeltDNTB'), ('d_1', 'R_TasselDNT'),
]
# single joints kept (collar flaps and the coat roots), with their Rebirth parent
SINGLES = {'b339': ('C_CollarDNT_Spo', 'C_Spine_d'), 'b340': ('C_CollarDNTF_a_Phy', 'C_CollarDNT_Spo'),
           'b341': ('L_CollarDNTF_a_Phy', 'C_CollarDNT_Spo'), 'b342': ('R_CollarDNTF_a_Phy', 'C_CollarDNT_Spo'),
           'b343': ('L_CollarDNTB_a_Phy', 'C_CollarDNT_Spo'), 'b344': ('R_CollarDNTB_a_Phy', 'C_CollarDNT_Spo'),
           'b345': ('C_CollarDNTB_a_Phy', 'C_CollarDNT_Spo'),
           'b332': ('C_CoatDNTK_Spo', 'C_Hip_a'), 'b333': ('L_CoatDNTB_Spo', 'C_Hip_a'), 'b334': ('R_CoatDNTB_Spo', 'C_Hip_a'),
           'b335': ('L_CoatDNTF_Spo', 'C_Hip_a'), 'b336': ('R_CoatDNTF_Spo', 'C_Hip_a'), 'b337': ('L_CoatDNTK_Spo', 'C_Hip_a'),
           'b338': ('R_CoatDNTK_Spo', 'C_Hip_a')}
LEVELS = 'abcdefghijklmnop'


def main(src_path, rig_path, out_path, report_path=None):
    m = np.load(src_path)
    names = [str(n) for n in m['bone_names']]
    par = [int(p) for p in m['bone_parents']]
    NB = len(names)
    ix = {n: i for i, n in enumerate(names)}
    # the bind pose in Unreal's space
    R0 = np.array([M @ q2m(q) @ M.T for q in m['bone_wq']])
    P0 = np.array([M @ t for t in m['bone_wt']])
    R = R0.copy(); P = P0.copy()
    children = [[] for _ in range(NB)]
    for i, p in enumerate(par):
        if p >= 0:
            children[p].append(i)

    def subtree(i):
        out = [i]; k = 0
        while k < len(out):
            out += children[out[k]]; k += 1
        return out

    def apply(i, Mr):
        o = P[i].copy()
        for j in subtree(i):
            P[j] = o + Mr @ (P[j] - o); R[j] = Mr @ R[j]

    cc = {k: ix[v] for k, v in DNT_BODY.items()}
    rig = json.load(open(rig_path))
    RB = {b['name']: b for b in rig['bones']}
    rp = lambda n: np.array(RB[n]['t'], dtype=float)
    rq = lambda n: q2m(RB[n]['q'])
    log = []

    def align(c, c_child, r, r_child, child_point=None):
        cur = (child_point if child_point is not None else P[cc[c_child]]) - P[cc[c]]
        tgt = rp(r_child) - rp(r)
        Mr = rot_between(cur, tgt)
        ang = np.degrees(np.arccos(np.clip(np.dot(cur / np.linalg.norm(cur), tgt / np.linalg.norm(tgt)), -1, 1)))
        apply(cc[c], Mr); log.append(('swing', c, round(float(ang), 2)))

    def twist(c, axis, cur, tgt):
        a = signed_angle(cur, tgt, axis)
        apply(cc[c], axis_angle(axis, a)); log.append(('twist', c, round(float(np.degrees(a)), 2)))

    # 1. upper body: hips -> neck as Rebirth's hip -> neck line
    cur = P[cc['Neck']] - P[cc['Spine']]; tgt = rp('C_Neck_a') - rp('C_Hip_a')
    apply(cc['Spine'], rot_between(cur, tgt))
    log.append(('swing', 'Spine', round(float(np.degrees(np.arccos(np.clip(np.dot(cur, tgt) / np.linalg.norm(cur) / np.linalg.norm(tgt), -1, 1)))), 2)))
    align('Neck', 'Head', 'C_Neck_a', 'C_Head_a')
    A = R[cc['Head']] @ R0[cc['Head']].T
    apply(cc['Head'], A.T); log.append(('unturn', 'Head', round(float(np.degrees(np.arccos(np.clip((np.trace(A) - 1) / 2, -1, 1)))), 2)))
    # 2. arms, hands, fingers
    for cs, rs in SIDES:
        align(cs + 'Shoulder', cs + 'Arm', rs + '_Shoulder_a', rs + '_UpperArm_a')
        align(cs + 'Arm', cs + 'ForeArm', rs + '_UpperArm_a', rs + '_Forearm_a')
        align(cs + 'ForeArm', cs + 'Hand', rs + '_Forearm_a', rs + '_Hand_a')
        sgn = 1.0 if cs == 'Left' else -1.0

        def palm(get):
            return sgn * np.cross(get('Index') - get('H'), get('Pinky') - get('H'))
        cpalm = palm(lambda k: P[cc[cs + 'Hand']] if k == 'H' else P[cc[cs + 'Hand' + k + '1']])
        rpalm = palm(lambda k: rp(rs + '_Hand_a') if k == 'H' else rp(rs + '_' + k + '_a'))
        twist(cs + 'ForeArm', P[cc[cs + 'Hand']] - P[cc[cs + 'ForeArm']], cpalm, rpalm)
        align(cs + 'Hand', cs + 'HandMiddle1', rs + '_Hand_a', rs + '_Middle_a')
        cpalm = palm(lambda k: P[cc[cs + 'Hand']] if k == 'H' else P[cc[cs + 'Hand' + k + '1']])
        twist(cs + 'Hand', P[cc[cs + 'HandMiddle1']] - P[cc[cs + 'Hand']], cpalm, rpalm)
        for cf, rf in FINGERS:
            align('%sHand%s1' % (cs, cf), '%sHand%s2' % (cs, cf), '%s_%s_a' % (rs, rf), '%s_%s_b' % (rs, rf))
            align('%sHand%s2' % (cs, cf), '%sHand%s3' % (cs, cf), '%s_%s_b' % (rs, rf), '%s_%s_c' % (rs, rf))
            i2, i3 = cc['%sHand%s2' % (cs, cf)], cc['%sHand%s3' % (cs, cf)]
            tip = P[i3] + (P[i3] - P[i2]) * 0.8          # the last segment continues the one before it
            align('%sHand%s3' % (cs, cf), None, '%s_%s_c' % (rs, rf), '%s_%s_End' % (rs, rf), child_point=tip)
    # 3. legs; the feet keep their soles as the model has them
    for cs, rs in SIDES:
        align(cs + 'UpLeg', cs + 'Leg', rs + '_UpperLeg_a', rs + '_Foreleg_a')
        align(cs + 'Leg', cs + 'Foot', rs + '_Foreleg_a', rs + '_Foot_a')
        A = R[cc[cs + 'Foot']] @ R0[cc[cs + 'Foot']].T
        apply(cc[cs + 'Foot'], A.T); log.append(('unturn', cs + 'Foot', round(float(np.degrees(np.arccos(np.clip((np.trace(A) - 1) / 2, -1, 1)))), 2)))

    # the new skeleton
    bones = []          # (name, parent, CS rotation, CS position, source joint or None)

    def add(n, p, Rm, t, src=None):
        bones.append((n, p, Rm, np.array(t, dtype=float), src))
    add('Trans', None, rq('Trans'), [0, 0, 0])
    for n in ('C_CharaA_a', 'C_CharaExA_a', 'C_CharaExB_a'):
        add(n, 'Trans', rq(n), [0, 0, 0])
    legmid = (P[cc['LeftUpLeg']] + P[cc['RightUpLeg']]) / 2
    rlegmid = (rp('L_UpperLeg_a') + rp('R_UpperLeg_a')) / 2
    hip = legmid + (rp('C_Hip_a') - rlegmid)
    add('C_Hip_a', 'Trans', rq('C_Hip_a'), hip, 'b2')
    poly = np.array([hip, P[cc['Spine1']], P[cc['Neck']]])

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
    add('C_Neck_a', 'C_Spine_d', rq('C_Neck_a'), P[cc['Neck']], 'b11')
    add('C_Head_a', 'C_Neck_a', rq('C_Head_a'), P[cc['Head']], 'b12')
    add('C_FaceBase_a', 'C_Head_a', rq('C_FaceBase_a'), P[cc['Head']])
    for cs, rs in SIDES:
        add(rs + '_Shoulder_a', 'C_Spine_d', rq(rs + '_Shoulder_a'), P[cc[cs + 'Shoulder']], DNT_BODY[cs + 'Shoulder'])
        add(rs + '_UpperArm_a', rs + '_Shoulder_a', rq(rs + '_UpperArm_a'), P[cc[cs + 'Arm']], DNT_BODY[cs + 'Arm'])
        add(rs + '_Forearm_a', rs + '_UpperArm_a', rq(rs + '_Forearm_a'), P[cc[cs + 'ForeArm']], DNT_BODY[cs + 'ForeArm'])
        add(rs + '_Hand_a', rs + '_Forearm_a', rq(rs + '_Hand_a'), P[cc[cs + 'Hand']], DNT_BODY[cs + 'Hand'])
        hs = np.linalg.norm(P[cc[cs + 'HandMiddle1']] - P[cc[cs + 'Hand']]) / np.linalg.norm(rp(rs + '_Middle_a') - rp(rs + '_Hand_a'))
        wt = P[cc[cs + 'Hand']] + rq(rs + '_Hand_a') @ (np.array(RB[rs + '_Weapon_a']['local_t']) * hs)
        add(rs + '_Weapon_a', rs + '_Hand_a', rq(rs + '_Weapon_a'), wt)
        for cf, rf in FINGERS:
            prevb = rs + '_Hand_a'
            for k, c in (('a', '1'), ('b', '2'), ('c', '3')):
                n = '%s_%s_%s' % (rs, rf, k)
                src = DNT_BODY['%sHand%s%s' % (cs, cf, c)]
                add(n, prevb, rq(n), P[ix[src]], src); prevb = n
        add(rs + '_UpperLeg_a', 'C_Hip_a', rq(rs + '_UpperLeg_a'), P[cc[cs + 'UpLeg']], DNT_BODY[cs + 'UpLeg'])
        add(rs + '_Foreleg_a', rs + '_UpperLeg_a', rq(rs + '_Foreleg_a'), P[cc[cs + 'Leg']], DNT_BODY[cs + 'Leg'])
        add(rs + '_Foot_a', rs + '_Foreleg_a', rq(rs + '_Foot_a'), P[cc[cs + 'Foot']], DNT_BODY[cs + 'Foot'])
        add(rs + '_Toe_a', rs + '_Foot_a', rq(rs + '_Toe_a'), P[cc[cs + 'ToeBase']], DNT_BODY[cs + 'ToeBase'])
    # eyes: placed by face_rig later (Rebirth's eyes); here on the head
    for rs in ('L', 'R'):
        add(rs + '_Eye', 'C_FaceBase_a', rq(rs + '_Eye'), P[cc['Head']])

    # his own bones: chains and singles
    rename = {}
    for first, part in CHAINS:
        if first not in ix:
            continue
        j = ix[first]; k = 0
        chain = [j]
        while True:
            kids = [c for c in children[j] if names[c] not in rename]
            # follow the child farthest down the chain (the strand), side chains start their own entries
            kids = [c for c in kids if not any(names[c] == f for f, _ in CHAINS)]
            if not kids:
                break
            j = kids[0] if len(kids) == 1 else max(kids, key=lambda c: len(subtree(c)))
            chain.append(j)
        for k, j in enumerate(chain):
            rename[names[j]] = '%s_%s_Phy' % (part, LEVELS[k])
    for src, (n, p) in SINGLES.items():
        if src in ix:
            rename[src] = n
    # parents of the kept joints in the new skeleton
    body_of = {v: None for v in DNT_BODY.values()}
    newname_of_body = {'b2': 'C_Hip_a', 'b9': 'C_Spine_b', 'b10': 'C_Spine_d', 'b11': 'C_Neck_a', 'b12': 'C_Head_a'}
    for cs, rs in SIDES:
        newname_of_body.update({DNT_BODY[cs + 'Shoulder']: rs + '_Shoulder_a', DNT_BODY[cs + 'Arm']: rs + '_UpperArm_a',
                                DNT_BODY[cs + 'ForeArm']: rs + '_Forearm_a', DNT_BODY[cs + 'Hand']: rs + '_Hand_a',
                                DNT_BODY[cs + 'UpLeg']: rs + '_UpperLeg_a', DNT_BODY[cs + 'Leg']: rs + '_Foreleg_a',
                                DNT_BODY[cs + 'Foot']: rs + '_Foot_a', DNT_BODY[cs + 'ToeBase']: rs + '_Toe_a'})

    def new_parent(j):
        """the kept joint's parent in the new skeleton: its own parent when that is kept, else the body bone it hangs
        under (helpers fold up to their body bone)"""
        if names[j] in SINGLES and SINGLES[names[j]][1] in [b[0] for b in bones] + list(rename.values()):
            if SINGLES[names[j]][1] != 'C_CollarDNT_Spo':
                pass
        p = par[j]
        while p >= 0:
            if names[p] in rename:
                return rename[names[p]]
            if names[p] in newname_of_body:
                return newname_of_body[names[p]]
            if names[p] in HELPERS:
                return HELPERS[names[p]][0][0]
            p = par[p]
        return 'C_Hip_a'
    placed = {b[0] for b in bones}
    pending = [ix[s] for s in rename]
    while pending:
        rest = []
        for j in pending:
            pn = new_parent(j)
            if names[j] in SINGLES:
                pn = SINGLES[names[j]][1] if SINGLES[names[j]][1] in placed else pn
            if pn in placed:
                add(rename[names[j]], pn, R[j], P[j], names[j]); placed.add(rename[names[j]])
            else:
                rest.append(j)
        assert len(rest) < len(pending), [names[j] for j in rest]
        pending = rest
    bidx = {b[0]: k for k, b in enumerate(bones)}

    # skin weights: Dissidia NT joint -> [(new bone, share)]
    direct = dict(newname_of_body)
    for cs, rs in SIDES:
        for cf, rf in FINGERS:
            for k, c in (('a', '1'), ('b', '2'), ('c', '3')):
                direct[DNT_BODY['%sHand%s%s' % (cs, cf, c)]] = '%s_%s_%s' % (rs, rf, k)
    direct.update(rename)
    for k, v in HELPERS.items():
        direct.setdefault(k, None)
    face = set()
    for i, n in enumerate(names):          # every other joint under the head (the face rig) folds into C_Head_a
        p = par[i]
        while p >= 0 and names[p] != 'b12':
            p = par[p]
        if p >= 0 and n not in rename and n not in HELPERS:
            face.add(n)
    pos0 = m['pos'] @ M.T
    nz = m['nrm'] @ M.T
    nx = m['tan'] @ M.T
    tsign = -m['tsign']
    wb = m['wbone']; ww = m['wweight']
    V = len(pos0)
    newpos = np.zeros_like(pos0); newnz = np.zeros_like(nz); newnx = np.zeros_like(nx)
    for j in range(wb.shape[1]):
        b = wb[:, j]; w = ww[:, j][:, None]
        Mr = np.einsum('vij,vkj->vik', R[b], R0[b])
        d = pos0 - P0[b]
        newpos += w * (np.einsum('vij,vj->vi', Mr, d) + P[b])
        newnz += w * np.einsum('vij,vj->vi', Mr, nz); newnx += w * np.einsum('vij,vj->vi', Mr, nx)
    newnz /= np.linalg.norm(newnz, axis=1, keepdims=True) + 1e-12
    newnx -= newnz * np.sum(newnx * newnz, axis=1, keepdims=True)
    newnx /= np.linalg.norm(newnx, axis=1, keepdims=True) + 1e-12
    sp_names = ['C_Spine_a', 'C_Spine_b', 'C_Spine_c', 'C_Spine_d']
    sp_z = np.array([bones[bidx[n]][3][2] for n in sp_names])

    def spine_shares(z):
        if z <= sp_z[0]:
            return [(sp_names[0], 1.0)]
        if z >= sp_z[-1]:
            return [(sp_names[-1], 1.0)]
        k = int(np.searchsorted(sp_z, z) - 1); u = (z - sp_z[k]) / (sp_z[k + 1] - sp_z[k])
        return [(sp_names[k], 1 - u), (sp_names[k + 1], u)]
    newW = []
    missing = {}
    for v in range(V):
        acc = {}
        for j in range(wb.shape[1]):
            w = ww[v, j]
            if w <= 0:
                continue
            n = names[wb[v, j]]
            if n in ('b9', 'b10'):
                shares = spine_shares(newpos[v, 2])
            elif n in HELPERS:
                shares = HELPERS[n]
            elif direct.get(n):
                shares = [(direct[n], 1.0)]
            elif n in face:
                shares = [('C_Head_a', 1.0)]
            else:
                missing[n] = missing.get(n, 0) + w
                shares = [('C_Hip_a', 1.0)]
            for bn, s in shares:
                acc[bidx[bn]] = acc.get(bidx[bn], 0) + w * s
        items = sorted(acc.items(), key=lambda kv: -kv[1])[:8]
        tot = sum(w for _, w in items)
        newW.append([(b, w / tot) for b, w in items])
    loc_q, loc_t = [], []
    for n, p, Rm, t, src in bones:
        if p is None:
            loc_q.append(m2q(Rm)); loc_t.append(t)
        else:
            pb = bones[bidx[p]]
            loc_q.append(m2q(pb[2].T @ Rm)); loc_t.append(pb[2].T @ (t - pb[3]))
    W = np.zeros((V, 8), dtype=np.int64); Wt = np.zeros((V, 8))
    for k in range(V):
        for j, (b, w) in enumerate(newW[k]):
            W[k, j] = b; Wt[k, j] = w
    mats = [json.loads(s) for s in m['materials']]
    slots = ['DNT_M%02d_%s' % (i, (mt['shader_names'][0] if mt['shader_names'] else 'none').replace('-', '_'))
             for i, mt in enumerate(mats)]
    np.savez(out_path, pos=newpos, nz=newnz, nx=newnx, tsign=tsign, uv=m['uv'], col=m['col'], tri=m['tri'],
             tmat=m['tmat'], slots=np.array(slots), mat_paths=np.array([''] * len(slots)), materials=m['materials'],
             wbone=W, wweight=Wt, bone_names=np.array([b[0] for b in bones]),
             bone_parents=np.array([bidx[b[1]] if b[1] else -1 for b in bones]),
             bone_lq=np.array(loc_q), bone_lt=np.array(loc_t),
             bone_cq=np.array([m2q(b[2]) for b in bones]), bone_ct=np.array([b[3] for b in bones]),
             bone_src=np.array([b[4] or '' for b in bones]),
             dnt_names=np.array(names), dnt_parents=np.array(par), dnt_R0=R0, dnt_P0=P0, dnt_R=R, dnt_P=P, conv=M)
    rep = dict(bones=len(bones), vertices=int(V), triangles=int(len(m['tri'])), slots=slots, aligned=log,
               kept={k: v for k, v in sorted(rename.items(), key=lambda kv: kv[1])},
               unmapped_weights={k: round(float(v), 2) for k, v in missing.items()},
               max_vertex_move=float(np.abs(newpos - pos0).max()))
    print(json.dumps({k: rep[k] for k in ('bones', 'vertices', 'triangles', 'unmapped_weights', 'max_vertex_move')}, indent=1))
    if report_path:
        json.dump(rep, open(report_path, 'w'), indent=1)


if __name__ == '__main__':
    main(*sys.argv[1:5])
