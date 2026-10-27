"""Dissidia NT Sephiroth, any outfit (dnt_model.py npz + its .swg) -> a mesh on FF7 Rebirth Sephiroth's bones (PC0010_00
names and rest rotations for the body, the model's own proportions), posed into Rebirth's rest pose (the Crisis Core
re-rig's steps: ccseph/tools/rerig.py); his face bones folded into C_Head_a (dnt_face.py puts Rebirth's face rig on
him after this); every other bone of his kept, under Rebirth's names:

  * physics chains (the outfit's swing bones, its .swg, the long hair under the head and the model layer's cloth
    joints): C_/L_/R_ + part + DNT + letters + _a.._Phy, the part from where the chain hangs (Hair, HairFront, Coat,
    Collar, Sleeve, Feather on the wing, Belt and Tassel for the default outfit's cloth strips), so Create a
    Character System's KawaiiPhysics preset finds and sorts them;
  * other bones with weights (the wing's arm, Safer's halo and wings...): C_/L_/R_ + WingDNT / ExDNT + their Dissidia
    NT id, posed only by animations that key them.

Dissidia NT is right-handed (Y up, facing +Z, +X his left), Unreal left-handed (Z up, facing +X, +Y his right):
positions go through the reflection M (x' = z, y' = -x, z' = y), rotations through M R M^T, tangent signs flip; the
triangles keep their order (Unreal's winding then).

    dnt_rerig2.py <dnt_model npz> <outfit .swg> <rebirth rig.json> <out.npz> [report.json]"""
import json
import re
import struct
import sys

import numpy as np

sys.path.insert(0, '/work/ccseph/tools')
from rerig import q2m, m2q, rot_between, axis_angle, signed_angle   # noqa: E402

M = np.array([[0.0, 0.0, 1.0], [-1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])

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
# the body joints' Rebirth names (the spine's two joints: C_Spine_b / C_Spine_d, their weights spread by height)
BODY_NAME = {'b2': 'C_Hip_a', 'b9': 'C_Spine_b', 'b10': 'C_Spine_d', 'b11': 'C_Neck_a', 'b12': 'C_Head_a'}
for _cs, _rs in SIDES:
    BODY_NAME.update({DNT_BODY[_cs + 'Shoulder']: _rs + '_Shoulder_a', DNT_BODY[_cs + 'Arm']: _rs + '_UpperArm_a',
                      DNT_BODY[_cs + 'ForeArm']: _rs + '_Forearm_a', DNT_BODY[_cs + 'Hand']: _rs + '_Hand_a',
                      DNT_BODY[_cs + 'UpLeg']: _rs + '_UpperLeg_a', DNT_BODY[_cs + 'Leg']: _rs + '_Foreleg_a',
                      DNT_BODY[_cs + 'Foot']: _rs + '_Foot_a', DNT_BODY[_cs + 'ToeBase']: _rs + '_Toe_a'})
    for _cf, _rf in FINGERS:
        for _k, _c in (('a', '1'), ('b', '2'), ('c', '3')):
            BODY_NAME[DNT_BODY['%sHand%s%s' % (_cs, _cf, _c)]] = '%s_%s_%s' % (_rs, _rf, _k)
# helper joints (twists, muscles) folded into body bones: id -> [(Rebirth bone, share)]; any other helper (b300 - b399,
# b0, b1, b21 - b26 and the like) folds into its nearest body ancestor
HELPERS = {
    'b304': [('L_UpperArm_a', .5), ('L_Forearm_a', .5)], 'b305': [('R_UpperArm_a', .5), ('R_Forearm_a', .5)],
    'b314': [('L_UpperLeg_a', .5), ('L_Foreleg_a', .5)], 'b315': [('R_UpperLeg_a', .5), ('R_Foreleg_a', .5)],
    'b320': [('C_Hip_a', .5), ('L_UpperLeg_a', .5)], 'b321': [('C_Hip_a', .5), ('R_UpperLeg_a', .5)],
    'b318': [('C_Spine_b', 1)], 'b319': [('C_Spine_b', 1)], 'b331': [('C_Spine_a', 1)], 'b322': [('C_Spine_c', 1)],
    'b323': [('C_Spine_d', 1)], 'b324': [('C_Spine_d', 1)], 'b325': [('C_Spine_d', 1)], 'b326': [('C_Spine_d', 1)],
    'b327': [('C_Neck_a', 1)], 'b328': [('C_Neck_a', 1)], 'b329': [('L_Shoulder_a', 1)], 'b330': [('R_Shoulder_a', 1)],
    'b0': [('C_Hip_a', 1)], 'b1': [('C_Hip_a', 1)], 'b399': [('C_Hip_a', 1)], 'd_0': [('C_Hip_a', 1)],
}
FACE_IDS = set(range(100, 207)) | {468, 469}
HAIR_MAIN = set(range(400, 411))
# the default outfit's cloth strips (model layer, NUNO): their parts by first joint
LAYER_PARTS = {'d_28': 'HairFront', 'd_34': 'HairFront', 'd_40': 'HairFront', 'd_45': 'HairFront',
               'd_11': 'Belt', 'd_16': 'Belt', 'd_21': 'Belt', 'd_1': 'Tassel'}
WING_ARM = set(range(456, 468))
COLLAR_IDS = set(range(339, 346))
COAT_IDS = {332, 333, 334, 335, 336, 337, 338, 331}
LEVELS = 'abcdefghijklmnopqrstuvwxyz'


def gid(n):
    m = re.match(r'^b(\d+)$', n)
    return int(m.group(1)) if m else None


def swing_ids(path):
    b = open(path, 'rb').read()
    count = struct.unpack_from('<I', b, 8)[0]
    return {'b%d' % struct.unpack_from('<HH', b, 20 + 72 * i)[1] for i in range(count)}


def main(src_path, swg_path, rig_path, out_path, report_path=None):
    m = np.load(src_path)
    names = [str(n) for n in m['bone_names']]
    par = [int(p) for p in m['bone_parents']]
    NB = len(names)
    ix = {n: i for i, n in enumerate(names)}
    children = [[] for _ in range(NB)]
    for i, p in enumerate(par):
        if p >= 0:
            children[p].append(i)

    def subtree(i):
        out = [i]; k = 0
        while k < len(out):
            out += children[out[k]]; k += 1
        return out

    def ancestors(i):
        p = par[i]
        while p >= 0:
            yield p
            p = par[p]
    # weights per joint
    used = np.zeros(NB)
    for k in range(m['wbone'].shape[1]):
        np.add.at(used, m['wbone'][:, k], m['wweight'][:, k])
    swing = swing_ids(swg_path)
    body = set(DNT_BODY.values())

    def is_face(n):
        g = gid(n)
        return g is not None and g in FACE_IDS

    def is_helper(n):
        g = gid(n)
        if n in HELPERS:
            return True
        return g is not None and (300 <= g < 400 and g not in COLLAR_IDS | COAT_IDS or g in (21, 22, 25, 26))

    def is_phys(n):
        g = gid(n)
        if n in swing:
            return True
        if g is not None and g in HAIR_MAIN:
            return True
        return n.startswith('d_') and n != 'd_0'
    # kept bones: physics joints with weights (or above weighted physics joints), other weighted bones and their
    # ancestors (not body / face / helper)
    keep = set()
    for i, n in enumerate(names):
        if n in body or is_face(n) or (is_helper(n) and not is_phys(n)):
            continue
        under_used = any(used[j] > 0 for j in subtree(i))
        if under_used:
            keep.add(i)
    # the bind pose in Unreal's space
    R0 = np.array([M @ q2m(q) @ M.T for q in m['bone_wq']])
    P0 = np.array([M @ t for t in m['bone_wt']])
    R = R0.copy(); P = P0.copy()

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
        ang = np.degrees(np.arccos(np.clip(np.dot(cur / np.linalg.norm(cur), tgt / np.linalg.norm(tgt)), -1, 1)))
        apply(cc[c], rot_between(cur, tgt)); log.append(('swing', c, round(float(ang), 2)))

    def twist(c, axis, cur, tgt):
        a = signed_angle(cur, tgt, axis)
        apply(cc[c], axis_angle(axis, a)); log.append(('twist', c, round(float(np.degrees(a)), 2)))
    cur = P[cc['Neck']] - P[cc['Spine']]; tgt = rp('C_Neck_a') - rp('C_Hip_a')
    apply(cc['Spine'], rot_between(cur, tgt))
    log.append(('swing', 'Spine', round(float(np.degrees(np.arccos(np.clip(np.dot(cur, tgt) / np.linalg.norm(cur) / np.linalg.norm(tgt), -1, 1)))), 2)))
    align('Neck', 'Head', 'C_Neck_a', 'C_Head_a')
    A = R[cc['Head']] @ R0[cc['Head']].T
    apply(cc['Head'], A.T); log.append(('unturn', 'Head', round(float(np.degrees(np.arccos(np.clip((np.trace(A) - 1) / 2, -1, 1)))), 2)))
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
            tip = P[i3] + (P[i3] - P[i2]) * 0.8
            align('%sHand%s3' % (cs, cf), None, '%s_%s_c' % (rs, rf), '%s_%s_End' % (rs, rf), child_point=tip)
    for cs, rs in SIDES:
        align(cs + 'UpLeg', cs + 'Leg', rs + '_UpperLeg_a', rs + '_Foreleg_a')
        align(cs + 'Leg', cs + 'Foot', rs + '_Foreleg_a', rs + '_Foot_a')
        A = R[cc[cs + 'Foot']] @ R0[cc[cs + 'Foot']].T
        apply(cc[cs + 'Foot'], A.T); log.append(('unturn', cs + 'Foot', round(float(np.degrees(np.arccos(np.clip((np.trace(A) - 1) / 2, -1, 1)))), 2)))

    bones = []

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
    for rs in ('L', 'R'):
        add(rs + '_Eye', 'C_FaceBase_a', rq(rs + '_Eye'), P[cc['Head']])
    placed = {b[0] for b in bones}

    # ---- names of the kept bones
    rename = {}
    head_z = P[cc['Head']][2]
    shoulder_z = (P[cc['LeftShoulder']][2] + P[cc['RightShoulder']][2]) / 2

    def side(p):
        return 'L' if p[1] < -2.0 else ('R' if p[1] > 2.0 else 'C')

    def attach_of(i):
        """the nearest ancestor that is not a kept physics joint"""
        for a in ancestors(i):
            if not (a in keep and is_phys(names[a])):
                return a
        return -1

    def part_of(root):
        n = names[root]
        if n in LAYER_PARTS:
            return LAYER_PARTS[n]
        a = attach_of(root)
        an = names[a] if a >= 0 else ''
        g = gid(an)
        under_wing = any(gid(names[x]) in WING_ARM for x in [a] + list(ancestors(a)) if gid(names[x]) is not None) if a >= 0 else False
        if under_wing:
            return 'Feather'
        if g in COLLAR_IDS:
            return 'Collar'
        if g in COAT_IDS or an in ('b2', 'b3', 'b4') or (g is not None and 310 <= g <= 321):
            return 'Coat'
        if an in ('b17', 'b18', 'b15', 'b16', 'b19', 'b20') or (g is not None and 300 <= g <= 309):
            return 'Sleeve'
        if an == 'b12' or is_face(an) or (an == 'b11' and P[root][2] > shoulder_z):
            # in front of the face and hanging onto the chest: front hair
            return 'HairFront' if P[root][0] > P[cc['Head']][0] + 6.0 and P[root][2] < head_z + 3 else 'Hair'
        if g is not None and g in HAIR_MAIN:
            return 'Hair'
        return 'Ex'
    phys_roots = [i for i in sorted(keep) if is_phys(names[i]) and not (par[i] in keep and is_phys(names[par[i]]))]
    groups = {}
    for r in phys_roots:
        key = (side(P[r]), part_of(r))
        groups.setdefault(key, []).append(r)
    chain_of = {}
    for (s, part), roots in groups.items():
        roots.sort(key=lambda r: (-P[r][2], P[r][1], -P[r][0]))
        for k, r in enumerate(roots):
            letters = ''
            q = k
            while True:
                letters = chr(ord('A') + q % 26) + letters
                q = q // 26 - 1
                if q < 0:
                    break
            stem = '%s_%sDNT%s' % (s, part, letters)
            # depth-first through the chain: the level is the depth from the root; a branch point's children past the
            # first get a sub-stem of their own (a tree reads as several chains to the preset)
            stack = [(r, 0, stem)]
            branches = [0]
            while stack:
                j, depth, st = stack.pop()
                if depth >= len(LEVELS):
                    depth = len(LEVELS) - 1
                rename[names[j]] = '%s_%s_Phy' % (st, LEVELS[depth])
                kids = [c for c in children[j] if c in keep and is_phys(names[c])]
                kids.sort(key=lambda c: -len(subtree(c)))
                for b_i, c in enumerate(kids):
                    if b_i == 0:
                        stack.append((c, depth + 1, st))
                    else:
                        branches[0] += 1          # a branch: the root's stem + a letter of its own (unique in the tree)
                        q, tag = branches[0] - 1, ''
                        while True:
                            tag = chr(ord('A') + q % 26) + tag
                            q = q // 26 - 1
                            if q < 0:
                                break
                        stack.append((c, depth + 1, '%sX%s' % (stem, tag)))
            chain_of[r] = stem
    for i in sorted(keep):
        n = names[i]
        if n in rename:
            continue
        g = gid(n)
        if g is not None and g in WING_ARM:
            rename[n] = '%s_WingDNT_b%d' % (side(P[i]), g)
        else:
            rename[n] = '%s_ExDNT_%s' % (side(P[i]), n)
    # collisions: a name used twice gets its id
    seen = {}
    for k, v in list(rename.items()):
        if v in seen or v in placed:
            rename[k] = v.replace('_Phy', '') + '_' + k + ('_Phy' if v.endswith('_Phy') else '')
        seen[rename[k]] = k

    def new_parent(j):
        for a in ancestors(j):
            n = names[a]
            if n in rename and a in keep:
                return rename[n]
            if n in BODY_NAME:
                return BODY_NAME[n]
            if n in HELPERS:
                return HELPERS[n][0][0]
            if is_face(n):
                return 'C_Head_a'
        return 'C_Hip_a'
    pending = sorted(keep)
    while pending:
        rest = []
        for j in pending:
            pn = new_parent(j)
            if pn in placed:
                add(rename[names[j]], pn, R[j], P[j], names[j]); placed.add(rename[names[j]])
            else:
                rest.append(j)
        assert len(rest) < len(pending), [names[j] for j in rest]
        pending = rest
    bidx = {b[0]: k for k, b in enumerate(bones)}

    # ---- weights
    sp_names = ['C_Spine_a', 'C_Spine_b', 'C_Spine_c', 'C_Spine_d']
    sp_z = np.array([bones[bidx[n]][3][2] for n in sp_names])

    def spine_shares(z):
        if z <= sp_z[0]:
            return [(sp_names[0], 1.0)]
        if z >= sp_z[-1]:
            return [(sp_names[-1], 1.0)]
        k = int(np.searchsorted(sp_z, z) - 1); u = (z - sp_z[k]) / (sp_z[k + 1] - sp_z[k])
        return [(sp_names[k], 1 - u), (sp_names[k + 1], u)]

    def fold(n, j):
        """a joint that is not kept: its body bone (helpers by HELPERS or their nearest body ancestor)"""
        if n in HELPERS:
            return HELPERS[n]
        if is_face(n):
            return [('C_Head_a', 1.0)]
        for a in [j] + list(ancestors(j)):
            if names[a] in BODY_NAME:
                return [(BODY_NAME[names[a]], 1.0)]
            if a in keep:
                return [(rename[names[a]], 1.0)]
        return [('C_Hip_a', 1.0)]
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
        newpos += w * (np.einsum('vij,vj->vi', Mr, pos0 - P0[b]) + P[b])
        newnz += w * np.einsum('vij,vj->vi', Mr, nz); newnx += w * np.einsum('vij,vj->vi', Mr, nx)
    newnz /= np.linalg.norm(newnz, axis=1, keepdims=True) + 1e-12
    newnx -= newnz * np.sum(newnx * newnz, axis=1, keepdims=True)
    newnx /= np.linalg.norm(newnx, axis=1, keepdims=True) + 1e-12
    shares_of = {}
    W = np.zeros((V, 8), dtype=np.int64); Wt = np.zeros((V, 8))
    for v in range(V):
        acc = {}
        for j in range(wb.shape[1]):
            w = ww[v, j]
            if w <= 0:
                continue
            bi = wb[v, j]; n = names[bi]
            if n in ('b9', 'b10'):
                shares = spine_shares(newpos[v, 2])
            elif bi in keep:
                shares = [(rename[n], 1.0)]
            elif n in BODY_NAME:
                shares = [(BODY_NAME[n], 1.0)]
            else:
                if n not in shares_of:
                    shares_of[n] = fold(n, bi)
                shares = shares_of[n]
            for bn, s in shares:
                acc[bidx[bn]] = acc.get(bidx[bn], 0) + w * s
        items = sorted(acc.items(), key=lambda kv: -kv[1])[:8]
        tot = sum(w for _, w in items)
        for k, (b, w) in enumerate(items):
            W[v, k] = b; Wt[v, k] = w / tot
    loc_q, loc_t = [], []
    for n, p, Rm, t, src in bones:
        if p is None:
            loc_q.append(m2q(Rm)); loc_t.append(t)
        else:
            pb = bones[bidx[p]]
            loc_q.append(m2q(pb[2].T @ Rm)); loc_t.append(pb[2].T @ (t - pb[3]))
    mats = [json.loads(s) for s in m['materials']]
    slots = ['DNT_M%02d_%s' % (i, (mt['shader_names'][0] if mt['shader_names'] else 'none').replace('-', '_'))
             for i, mt in enumerate(mats)]
    np.savez(out_path, pos=newpos, nz=newnz, nx=newnx, tsign=tsign, uv=m['uv'], col=m['col'], tri=m['tri'],
             tmat=m['tmat'], slots=np.array(slots), mat_paths=np.array([''] * len(slots)), materials=m['materials'],
             submeshes=m['submeshes'],
             wbone=W, wweight=Wt, bone_names=np.array([b[0] for b in bones]),
             bone_parents=np.array([bidx[b[1]] if b[1] else -1 for b in bones]),
             bone_lq=np.array(loc_q), bone_lt=np.array(loc_t),
             bone_cq=np.array([m2q(b[2]) for b in bones]), bone_ct=np.array([b[3] for b in bones]),
             bone_src=np.array([b[4] or '' for b in bones]),
             dnt_names=np.array(names), dnt_parents=np.array(par), dnt_R0=R0, dnt_P0=P0, dnt_R=R, dnt_P=P, conv=M)
    chains = {}
    for k, v in rename.items():
        if v.endswith('_Phy'):
            stem = v.rsplit('_', 2)[0]
            chains.setdefault(stem, []).append(k)
    rep = dict(bones=len(bones), vertices=int(V), triangles=int(len(m['tri'])), slots=slots, aligned=log,
               chains={k: len(v) for k, v in sorted(chains.items())},
               plain=sorted(v for v in rename.values() if not v.endswith('_Phy')),
               folded={k: v for k, v in shares_of.items()},
               max_vertex_move=float(np.abs(newpos - pos0).max()))
    print('%d bones (%d kept: %d in %d chains, %d plain), %d vertices, %d triangles, vertex move max %.1f cm' % (
        len(bones), len(rename), sum(len(v) for v in chains.values()), len(chains), len(rep['plain']), V,
        len(m['tri']), rep['max_vertex_move']))
    if report_path:
        json.dump(rep, open(report_path, 'w'), indent=1)


if __name__ == '__main__':
    main(*sys.argv[1:6])
