"""Young Sephiroth (ch049_001) on Rebirth's bones: the skeleton of PC0010_13_Young_Sephiroth, so Create a Character
System's family plays Sephiroth's animations on him (bone by bone by name, each bone's parent the one Sephiroth's has).

  body      every bone of his that has a PC0010 equivalent takes its name and its parent (Trans, C_Hip_a, C_Spine_a-d,
            C_Neck_a, C_Head_a, shoulders, arms, hands, fingers, legs, feet, toes; his hand weapon bones L/R_Weapon_a),
            stays where his joint is, and rests turned the way Sephiroth's bone rests, turned again to point the way his
            own bone points (Sephiroth's rest frame x the arc from Sephiroth's bone direction to his): a Sephiroth pose
            then poses him the same way, his own limb lengths kept;
  helpers   his twist and joint helpers become Sephiroth's (L_Elbow_Spo, L_Knee_Spo, L_FemorisA-C_Spo, L_ForearmrollA-C_Spo,
            L_DeltoidA-C_Spo), each under the bone Sephiroth's is under, resting where his did;
  coat      his eleven coat tails are Sephiroth's eleven (C_CoatA at the back, L/R_CoatA-E around from the front), the
            tails' roots *_Spo, their joints *_a.._d_Phy, with Sephiroth's parents (C_CoatAA_Spo / C_CoatAA_a_Phy at the
            front, L/R_CoatBA_Spo added) and Sephiroth's turn: Sephiroth's animations key his coat, and now key Young
            Sephiroth's the same way;
  hair      his fourteen strands take the names of the nearest of Sephiroth's strands (C_HairA-M, L/R_HairA-F) under a
            C_HairBase_a, roots *_Spo where Sephiroth's strand has one; collar L/R_CollarA-B, shoulder pads
            L/R_ShoulderpadA (with their *_Spo): nothing animates these, his Bonamik moves them, so they keep his rest;
  added     C_CharaA_a, C_CharaExA_a, C_CharaExB_a (where the game holds a character he carries), C_FaceBase_a and
            C_Nose_A (the nose, for cameras);
  face      his face bones keep their names (Rebirth's face moves Sephiroth's face bones to Sephiroth's features);
  dropped   center (no weights; Sephiroth's spine hangs from C_Hip_a).
Positions and rotations are Unreal component space (cm), as CH049_001_Skeleton has them.
    rig_ys.py <out json>"""
import json, sys
sys.path[:0] = ['/work/acl', '/work/ch049anim', '/work/ys']
import numpy as np
import retarget_from_seph as RS

SE, CH, CV = RS.SE, RS.CH, RS.CV
qmul, qinv, qrot, qnorm, arc = CV.qmul, CV.qinv, CV.qrot, CV.qnorm, CV.arc
SCALE = 1.0 / RS.HIP_SCALE
ID = np.array([0, 0, 0, 1.0])


def unit(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-9 else v


# ---- names
BODY = dict(RS.INV)                     # CH049 -> Sephiroth (hips, spine, neck, head, arms, legs, fingers)
BODY.update({'root': 'Trans', 'left_hand_weapon': 'L_Weapon_a', 'right_hand_weapon': 'R_Weapon_a'})
HELPERS = {}
for s, u in (('L', 'left'), ('R', 'right')):
    HELPERS.update({
        'sub_%s_elbow' % u: ('%s_Elbow_Spo' % s, '%s_UpperArm_a' % s),
        'sub_%s_knee' % u: ('%s_Knee_Spo' % s, '%s_UpperLeg_a' % s),
        'sub_%s_upleg_01' % u: ('%s_FemorisA_Spo' % s, '%s_UpperLeg_a' % s),
        'sub_%s_upleg_02' % u: ('%s_FemorisB_Spo' % s, '%s_UpperLeg_a' % s),
        'sub_%s_upleg_03' % u: ('%s_FemorisC_Spo' % s, '%s_UpperLeg_a' % s),
        'sub_%s_forearm_01' % u: ('%s_ForearmrollA_Spo' % s, '%s_Forearm_a' % s),
        'sub_%s_forearm_02' % u: ('%s_ForearmrollB_Spo' % s, '%s_Forearm_a' % s),
        'sub_%s_forearm_03' % u: ('%s_ForearmrollC_Spo' % s, '%s_Forearm_a' % s),
        'sub_%s_arm_01' % u: ('%s_DeltoidA_Spo' % s, '%s_UpperArm_a' % s),
        'sub_%s_arm_02' % u: ('%s_DeltoidB_Spo' % s, '%s_UpperArm_a' % s),
        'sub_%s_arm_03' % u: ('%s_DeltoidC_Spo' % s, '%s_UpperArm_a' % s),
    })
MISC = {'main_weapon': ('C_WeaponMain_a', 'Trans'), 'sub_weapon': ('C_WeaponSub_a', 'Trans'), 'pos_center_01': ('C_PosCenter_a', 'Trans')}
DROP = {'center'}
SEG = 'abcdefghij'
MESH_BONES = '/work/ys/rig/outfit_bones.json'     # the bones of PC0010_00 (Sephiroth's model), from the editor


def ch(name):
    return CH.index[name]


def se(name):
    return SE.index[name]


def main(out_path):
    bones = {}        # new name -> dict(parent, q, t, src)
    order = []
    rename = {}       # CH049 name -> new name

    def add(name, parent, q, t, src=None):
        assert name not in bones, name
        assert parent is None or parent in bones, (name, parent)
        bones[name] = dict(parent=parent, q=qnorm(np.asarray(q, float)), t=np.asarray(t, float), src=src)
        order.append(name)
        if src:
            rename[src] = name

    # ---- body: Sephiroth's rest frame turned to point the way his bone points
    turn = {}

    def body_turn(c):
        s = BODY[c]
        if s in CV.AIM:
            s_child, c_child = CV.AIM[s]
            u = SE.gt[se(s_child)] - SE.gt[se(s)]
            v = CH.gt[ch(c_child)] - CH.gt[ch(c)]
            return arc(unit(u), unit(v))
        p = CH.parents[ch(c)]
        while p >= 0 and CH.names[p] not in BODY:
            p = CH.parents[p]
        return turn[CH.names[p]] if p >= 0 else ID

    # Sephiroth's order (parents first) for the body
    body_by_se = {s: c for c, s in BODY.items()}
    for s in SE.names:
        if s not in body_by_se:
            continue
        c = body_by_se[s]
        turn[c] = ID if s == 'Trans' else body_turn(c)
        sp = SE.parents[se(s)]
        parent = SE.names[sp] if sp >= 0 else None
        while parent is not None and parent not in bones:
            pp = SE.parents[se(parent)]
            parent = SE.names[pp] if pp >= 0 else None
        assert (parent is None) == (s == 'Trans'), (s, parent)
        add(s, parent, qmul(turn[c], SE.gq[se(s)]), CH.gt[ch(c)], src=c)

    def place_like_se(name, parent_new, along):
        """An added bone of Sephiroth's under parent_new (a renamed bone): its rest relative to Sephiroth's parent,
        scaled, turned with the parent's turn ('along': the CH049 bone whose turn applies)."""
        s, sp = se(name), se(SE.names[SE.parents[se(name)]])
        tq = turn[along]
        off = qrot(tq, SE.gt[s] - SE.gt[sp]) * SCALE
        return qmul(tq, SE.gq[s]), bones[parent_new]['t'] + off

    for n in ('C_CharaA_a', 'C_CharaExA_a', 'C_CharaExB_a'):
        q, t = place_like_se(n, 'Trans', 'root')
        add(n, 'Trans', q, t)
    q, t = place_like_se('C_FaceBase_a', 'C_Head_a', 'head')
    add('C_FaceBase_a', 'C_Head_a', q, t)
    add('C_Nose_A', 'C_FaceBase_a', qmul(turn['head'], SE.gq[se('C_Nose_A')]), CH.gt[ch('upper_nose')])

    # ---- helpers: under Sephiroth's parent, resting where his did
    for c, (n, parent) in HELPERS.items():
        add(n, parent, CH.gq[ch(c)], CH.gt[ch(c)], src=c)
    for c, (n, parent) in MISC.items():
        add(n, parent, CH.gq[ch(c)], CH.gt[ch(c)], src=c)

    # ---- coat: Sephiroth's tails (animated by his clips), turned like the body
    def chain_turns(cnames, snames):
        """arc from Sephiroth's segment direction to CH049's, per segment (the last takes the one before)."""
        out = []
        for k in range(len(cnames)):
            if k + 1 < len(cnames):
                u = SE.gt[se(snames[k + 1])] - SE.gt[se(snames[k])]
                v = CH.gt[ch(cnames[k + 1])] - CH.gt[ch(cnames[k])]
                if np.linalg.norm(u) > 1e-3 and np.linalg.norm(v) > 1e-3:
                    out.append(arc(unit(u), unit(v)))
                    continue
            out.append(None)
        # zero-length segments (root -> a) take the next one's turn, the last its predecessor's
        for k in range(len(out) - 1, -1, -1):
            if out[k] is None and k + 1 < len(out) and out[k + 1] is not None:
                out[k] = out[k + 1]
        for k in range(len(out)):
            if out[k] is None:
                out[k] = out[k - 1] if k > 0 else ID
        return out

    def coat_chain(ys_chain, se_chain, root_name, root_parent, extra_roots=()):
        cn = ['phy_%s_base' % ys_chain] + ['phy_%s_%02d' % (ys_chain, k) for k in range(1, 5)]
        sn = [root_name] + ['%s_%s_Phy' % (se_chain, SEG[k]) for k in range(4)]
        tr = chain_turns(cn, [root_name] + sn[1:])
        parent = root_parent
        for extra in extra_roots:        # (L/R_CoatBA_Spo: Sephiroth's second root, where the tail's root is)
            add(extra, parent, qmul(tr[0], SE.gq[se(extra)]), CH.gt[ch(cn[0])])
            parent = extra
        for k in range(5):
            add(sn[k], parent, qmul(tr[k], SE.gq[se(sn[k])]), CH.gt[ch(cn[k])], src=cn[k])
            parent = sn[k]

    # the front root C_CoatAA (Sephiroth's front flap, the front tails hang from it): between the two front tails
    fl, fr = ch('phy_left_coat_01_base'), ch('phy_right_coat_01_base')
    front = (CH.gt[fl] + CH.gt[fr]) / 2
    down = unit((CH.gt[ch('phy_left_coat_01_02')] - CH.gt[fl]) + (CH.gt[ch('phy_right_coat_01_02')] - CH.gt[fr]))
    u = unit(SE.gt[se('C_CoatAA_b_Phy')] - SE.gt[se('C_CoatAA_a_Phy')])
    taa = arc(u, down)
    seg_len = np.linalg.norm(SE.gt[se('C_CoatAA_b_Phy')] - SE.gt[se('C_CoatAA_a_Phy')]) * SCALE
    add('C_CoatAA_Spo', 'C_Hip_a', qmul(taa, SE.gq[se('C_CoatAA_Spo')]), front)
    add('C_CoatAA_a_Phy', 'C_CoatAA_Spo', qmul(taa, SE.gq[se('C_CoatAA_a_Phy')]), front)
    add('C_CoatAA_b_Phy', 'C_CoatAA_a_Phy', qmul(taa, SE.gq[se('C_CoatAA_b_Phy')]), front + down * seg_len)
    # back: phy_back_coat_base / _01.._04
    cn = ['phy_back_coat_base'] + ['phy_back_coat_%02d' % k for k in range(1, 5)]
    sn = ['C_CoatA_Spo'] + ['C_CoatA_%s_Phy' % SEG[k] for k in range(4)]
    tr = chain_turns(cn, sn)
    parent = 'C_Hip_a'
    for k in range(5):
        add(sn[k], parent, qmul(tr[k], SE.gq[se(sn[k])]), CH.gt[ch(cn[k])], src=cn[k])
        parent = sn[k]
    for side, u_ in (('L', 'left'), ('R', 'right')):
        coat_chain('%s_coat_01' % u_, '%s_CoatA' % side, '%s_CoatA_Spo' % side, 'C_CoatAA_a_Phy')
        coat_chain('%s_coat_02' % u_, '%s_CoatB' % side, '%s_CoatBB_Spo' % side, 'C_Hip_a', extra_roots=('%s_CoatBA_Spo' % side,))
        coat_chain('%s_coat_03' % u_, '%s_CoatC' % side, '%s_CoatC_Spo' % side, 'C_Hip_a')
        coat_chain('%s_coat_04' % u_, '%s_CoatD' % side, '%s_CoatD_Spo' % side, 'C_Hip_a')
        coat_chain('%s_coat_05' % u_, '%s_CoatE' % side, '%s_CoatE_Spo' % side, 'C_Hip_a')

    # ---- collar and shoulder pads: Sephiroth's names and parents, his rest
    for side, u_ in (('L', 'left'), ('R', 'right')):
        for k, letter in ((1, 'A'), (2, 'B')):
            base, j1 = 'phy_%s_collar_%02d_base' % (u_, k), 'phy_%s_collar_%02d_01' % (u_, k)
            add('%s_Collar%s_Spo' % (side, letter), 'C_Spine_d', CH.gq[ch(base)], CH.gt[ch(base)], src=base)
            add('%s_Collar%s_a_Phy' % (side, letter), '%s_Collar%s_Spo' % (side, letter), CH.gq[ch(j1)], CH.gt[ch(j1)], src=j1)
        pad = 'phy_%s_shoulder_pad' % u_
        add('%s_ShoulderpadA_Spo' % side, '%s_Shoulder_a' % side, CH.gq[ch(pad)], CH.gt[ch(pad)])
        add('%s_ShoulderpadA_a' % side, '%s_ShoulderpadA_Spo' % side, CH.gq[ch(pad)], CH.gt[ch(pad)], src=pad)

    # ---- hair: each strand the nearest of Sephiroth's (relative to the head, scaled), under C_HairBase_a
    hb = ch('head')
    add('C_HairBase_a', 'C_Head_a', bones['C_Head_a']['q'], CH.gt[hb])
    ys_strands = []
    for n in CH.names:
        if n.startswith('phy_') and 'hair' in n and n.endswith('_01'):
            stem = n[:-3]
            segs = [x for x in CH.names if x.startswith(stem + '_') and x[len(stem) + 1:].isdigit()]
            segs.sort()
            base = stem + '_base' if (stem + '_base') in CH.index else None
            ys_strands.append((stem, base, segs))
    se_strands = {}
    mesh_bones = {b[0] for b in json.load(open(MESH_BONES))['seph']}     # PC0010_00's own (not the other hair styles)
    for n in SE.names:
        if 'Hair' in n and n.endswith('_a_Phy') and SE.parents[se(n)] >= 0 and n in mesh_bones:
            stem = n[:-len('_a_Phy')]
            p = SE.names[SE.parents[se(n)]]
            spo = stem + '_Spo' if p == stem + '_Spo' else None
            if (spo and SE.names[SE.parents[se(spo)]] == 'C_HairBase_a') or (not spo and p == 'C_HairBase_a'):
                se_strands[stem] = spo
    hs = SE.gt[se('C_Head_a')]

    def rel_ys(c):
        return (CH.gt[ch(c)] - CH.gt[hb]) * RS.HIP_SCALE

    def rel_se(s):
        return SE.gt[se(s)] - hs
    pairs = []
    for stem, base, segs in ys_strands:
        for s_stem, spo in se_strands.items():
            d = np.linalg.norm(rel_ys(base or segs[0]) - rel_se(spo or (s_stem + '_a_Phy')))
            penalty = 0.0 if (base is None or spo is not None) else 1e6     # a strand with a root takes one with a root
            pairs.append((d + penalty, stem, s_stem))
    pairs.sort()
    taken_y, taken_s, assign = set(), set(), {}
    for d, stem, s_stem in pairs:
        if stem in taken_y or s_stem in taken_s:
            continue
        assign[stem] = s_stem
        taken_y.add(stem)
        taken_s.add(s_stem)
    for stem, base, segs in ys_strands:
        s_stem = assign[stem]
        spo = se_strands[s_stem]
        parent = 'C_HairBase_a'
        if spo:
            src = base or segs[0]
            add(spo, parent, CH.gq[ch(src)], CH.gt[ch(src)], src=base)
            parent = spo
        for k, c in enumerate(segs):
            add('%s_%s_Phy' % (s_stem, SEG[k]), parent, CH.gq[ch(c)], CH.gt[ch(c)], src=c)
            parent = '%s_%s_Phy' % (s_stem, SEG[k])

    # ---- the rest of his bones (his face): his name, under the renamed bone his parent became
    for i, c in enumerate(CH.names):
        if c in rename or c in DROP:
            continue
        p = CH.parents[i]
        while p >= 0 and CH.names[p] in DROP:
            p = CH.parents[p]
        parent = rename.get(CH.names[p], CH.names[p])
        assert parent in bones, (c, parent)
        add(c, parent, CH.gq[i], CH.gt[i], src=c)
    missing = [c for c in CH.names if c not in rename and c not in DROP]
    assert not missing, missing
    # every renamed bone of Sephiroth's has Sephiroth's parent (the family's chain test)
    for n, b in bones.items():
        if n in SE.index and SE.parents[se(n)] >= 0:
            assert b['parent'] == SE.names[SE.parents[se(n)]], (n, b['parent'], SE.names[SE.parents[se(n)]])
    out = dict(bones=[dict(name=n, parent=bones[n]['parent'], q=[float(x) for x in bones[n]['q']], t=[float(x) for x in bones[n]['t']],
                           src=bones[n]['src']) for n in order],
               rename=rename, drop=sorted(DROP), hair=assign, scale=SCALE)
    json.dump(out, open(out_path, 'w'), indent=1)
    shared = sum(1 for n in bones if n in SE.index)
    print('%d bones (%d of them Sephiroth\'s names), %d of his renamed, dropped %s' % (len(bones), shared, sum(1 for k, v in rename.items() if k != v), sorted(DROP)))
    print('hair:', assign)


if __name__ == '__main__':
    main(sys.argv[1])
