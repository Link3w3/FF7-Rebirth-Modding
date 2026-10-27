"""Bahamut Fused Sephiroth's KawaiiPhysics: Create a Character System's "kawaii" entry for his model on Rebirth's bones
(PC0010_17_Compat), from the re-rig (bfs_rerig.py's npz):

  * his tail: one chain from its root at the hips (Tail1) to its tip (Tail28), heavy and held in its curve near the root,
    looser toward the tip, kept out of his legs and off the floor;
  * his mantles: each side's four long strips (A, B, the C strip that forks into C and E, D) as one node, the strips tied
    to the strips beside them (bone constraints along their length) so they hang and move as one cloth; kept out of his
    legs, his hips and back, the root of his tail and the floor; the four short shoulder strips each side as one more node;
  * his blade wings: each of the thirty blades turns toward a dummy bone along it that swings behind his moves (the
    blades sway and tilt about their hilts), a node for each bone axis that runs along the blades (their bones are
    turned every way);
  * his hair (PC0010_10's, out of the helmet's back and from under its mask): each strand chain its own node with the
    settings tuned for that chain on Sephiroth (the Rebirth preset's PC0010_10 entry), kept off his back and collar, his
    shoulders, chest, hips, legs and the root of his tail. The model's Bonamik is switched off (his hair bones have
    Sephiroth's names: Sephiroth's own Bonamik would take them).

The shapes are sized from his mesh in the reference pose (the 85 % distance of the leg, back and tail vertices from their
bones' axes), then shrunk where a chain's bone sits inside one at rest (so nothing is pushed out standing still).

    make_bfs_kawaii.py <rerig.npz> <model object path> <out dir>
        writes rig.json (component space, for the offline runs), body.npz, entry.json (the compat file's one entry)"""
import json
import math
import os
import sys
import numpy as np
sys.path[:0] = ['/work/kawaii_preset/tools', '/work/ccseph/tools']
from make_kawaii_preset import Rig, capsule, cap_points, sphere, rotator_for_z, r, qrot, qinv, from_rotator
from rerig import q2m

SIDES = ('L', 'R')
LARGE = ('MantLgA', 'MantLgB', 'MantLgC', 'MantLgD')
SMALL = ('MantSmA', 'MantSmB', 'MantSmC', 'MantSmD')

TAIL = dict(damping=0.25, stiffness=0.22, world_damping_location=0.9, world_damping_rotation=0.9, radius=10.0,
            radius_curve=[[0, 1.1], [1, 0.75]], limit_angle=20, limit_angle_curve=[[0, 0.6], [1, 1.6]],
            stiffness_curve=[[0, 1.6], [1, 0.6]], damping_curve=[[0, 1.0], [1, 0.8]], dummy_bone_length=6,
            bone_forward_axis='x_negative', gravity=[0, 0, -400], teleport_rotation_threshold=30, use_fixed_substepping=False)
# (2026-10-26) light, flowing mantles: a fifth of the gravity (was -980: the train dragged along the floor walking), less
# damping (more toward the tips: no whip at the ends), more lag behind his moves; in the offline runs the train lifts off
# the floor (walking 18 % of it lying, was 94 %; running none, its tips 50 cm up) and goes into his legs no more
MANTLE = dict(damping=0.09, damping_curve=[[0, 1.0], [1, 1.8]], stiffness=0.04, world_damping_location=0.97,
              world_damping_rotation=0.95, radius=4.0, radius_curve=[[0, 0.8], [0.4, 1.0], [1, 2.0]], limit_angle=45,
              limit_angle_curve=[[0, 0.5], [1, 1.2]], stiffness_curve=[[0, 2.0], [1, 0.8]], dummy_bone_length=10,
              bone_forward_axis='z_negative', gravity=[0, 0, -200], teleport_rotation_threshold=30, use_fixed_substepping=False,
              bone_subdivision_count=1, bone_subdivision_collision_only=True)
SHOULDER = dict(damping=0.15, stiffness=0.1, world_damping_location=0.92, world_damping_rotation=0.9, radius=2.5,
                limit_angle=35, stiffness_curve=[[0, 1.6], [1, 0.7]], dummy_bone_length=6, bone_forward_axis='z_negative',
                gravity=[0, 0, -300], teleport_rotation_threshold=30, use_fixed_substepping=False)
# (2026-10-26) the blades tilt behind his moves: each blade bone (near its hilt) the root of a chain whose one bone is a
# dummy bone along the blade (on the bone axis that runs along it: the blades' bones are turned every way, so a node per
# axis), which the blade turns toward
WINGS = dict(damping=0.12, stiffness=0.08, world_damping_location=0.9, world_damping_rotation=0.9, radius=3.0, limit_angle=25,
             dummy_bone_length=80, gravity=[0, 0, -60], teleport_rotation_threshold=30, use_fixed_substepping=False)
# (2026-10-26, game mod 3.15.0: pose_waves) the blade wings' slow beat: each side's blades turn up and down together
# about the model's front axis (mirrored), a ripple from the top blade (A) to the bottom one (O); the tail's sway: a wave
# from side to side down the tail, more toward its tip. Each wave turns the pose: the physics swings on top of it.
WING_BEAT = dict(degrees=9.0, seconds=3.5, ripple=12.0)
TAIL_WAVES = [dict(axis=[0, 0, 1], degrees=4.0, seconds=3.2, phase_per_bone=16.0, degrees_curve=[[0, 0.4], [1, 1.0]])]

HAIR_PRESET = '/work/kawaii_preset/out/SephirothKawaii.json'
HAIR_FRONT = ('C_HairA', 'C_HairB')     # (L/R_HairA lie on his chest: held to his head and chest, no physics)
HAIR_BACK = ('C_HairM', 'L_HairE', 'R_HairE', 'L_HairC', 'R_HairC', 'C_HairL', 'L_HairD', 'R_HairD')
SHAPE_KEYS = ('spheres', 'capsules', 'tapered_capsules', 'boxes', 'planes', 'bone_constraints')


def hair_settings():
    """the PC0010_10 entry's node for each hair chain (its root bone), shapes left out"""
    d = json.load(open(HAIR_PRESET))
    e = [x for x in d['kawaii'] if 'PC0010_10' in x['name']][0]
    out = {}
    for n in e['nodes']:
        out[n['root_bone']] = {k: v for k, v in n.items() if k not in SHAPE_KEYS}
    return out


def write_rig(m, path):
    names = [str(n) for n in m['bone_names']]
    par = [int(p) for p in m['bone_parents']]
    bones = []
    for i, n in enumerate(names):
        bones.append(dict(name=n, parent=names[par[i]] if par[i] >= 0 else None, q=[float(x) for x in m['bone_cq'][i]],
                          t=[float(x) for x in m['bone_ct'][i]], local_q=[float(x) for x in m['bone_lq'][i]],
                          local_t=[float(x) for x in m['bone_lt'][i]], scale=[1.0, 1.0, 1.0]))
    json.dump(dict(source='bfs_rerig.py', bones=bones), open(path, 'w'), indent=0)
    return names


def write_body(m, names, path):
    wb, ww = m['wbone'], m['wweight']
    v, k = np.nonzero(ww > 0)
    tri, tm = m['tri'], m['tmat']
    vmat = np.zeros(len(m['pos']), dtype=np.int32)
    vmat[tri[:, 0]] = tm
    vmat[tri[:, 1]] = tm
    vmat[tri[:, 2]] = tm
    np.savez_compressed(path, pos=m['pos'], w_bone=wb[v, k], w_vert=v, w_weight=ww[v, k], bones=np.array(names), vmat=vmat,
                        mats=np.array([str(s) for s in m['slots']]))


class Body:
    def __init__(self, m, names):
        self.pos = m['pos']
        wb, ww = m['wbone'], m['wweight']
        self.dom = np.array(names)[wb[np.arange(len(wb)), np.argmax(ww, axis=1)]]
        tri, tm = m['tri'], m['tmat']
        self.mat = np.zeros(len(self.pos), dtype=np.int32)
        for c in range(3):
            self.mat[tri[:, c]] = tm
        self.slots = [str(s) for s in m['slots']]

    def mask(self, bones, slot='PC0010_17_Body_Inst'):
        sel = np.isin(self.dom, list(bones))
        if slot:
            sel &= self.mat == self.slots.index(slot)
        return sel

    def radii(self, a, b, sel, pct=85, ends=0.25, toward=None):
        """the pct % distance from the segment a -> b of the selected vertices near each end (the first and last quarter)"""
        a, b = np.asarray(a, float), np.asarray(b, float)
        d = b - a
        L = np.linalg.norm(d)
        u = d / L
        rel = self.pos - a
        t = rel @ u / L
        rad = rel - np.outer(rel @ u, u)
        rr = np.linalg.norm(rad, axis=1)
        ok = sel & (t >= -0.05) & (t <= 1.05)
        if toward is not None:
            w = np.asarray(toward, float)
            w = w - (w @ u) * u
            w /= np.linalg.norm(w)
            ok &= (rad @ w) > 0.2 * rr
        lo = ok & (t < ends)
        hi = ok & (t > 1 - ends)
        ra = float(np.percentile(rr[lo], pct)) if lo.sum() > 20 else None
        rb = float(np.percentile(rr[hi], pct)) if hi.sum() > 20 else None
        return ra, rb


def blade_axes(m, names, rig, blades):
    """each blade's bone axis (x/y/z, positive/negative) that runs along the blade toward its tip: the blade's vertices'
    main direction, from the bone toward the blade's far end"""
    ix = {n: i for i, n in enumerate(names)}
    pos, wb, ww = m['pos'], m['wbone'], m['wweight']
    out = {}
    for b in blades:
        v = np.nonzero(((wb == ix[b]) & (ww > 0.9)).any(axis=1))[0]
        P = pos[v]
        c = P.mean(0)
        ax = np.linalg.svd(P - c, full_matrices=False)[2][0]
        t = np.array(rig.by[b]['t'])
        proj = (P - t) @ ax
        if -proj.min() > proj.max():
            ax = -ax
        R = q2m(np.array(rig.by[b]['q']))
        loc = R.T @ ax
        k = int(np.argmax(np.abs(loc)))
        out[b] = '%s_%s' % ('xyz'[k], 'positive' if loc[k] > 0 else 'negative')
    return out


def chain_bones(rig, root):
    out, stack = [], [root]
    while stack:
        x = stack.pop()
        out.append(x)
        stack.extend(rig.kids.get(x, []))
    return out


def ties(rig, a_bones, b_bones, every=2, max_dist=45.0):
    """bone constraints between two neighbouring strips: each of a's bones (every other one, from the third) with the
    nearest of b's at rest, when it is within max_dist cm"""
    P = {n: np.array(rig.by[n]['t']) for n in a_bones + b_bones}
    out = []
    for k, x in enumerate(a_bones):
        if k < 2 or (k % every):
            continue
        y = min(b_bones, key=lambda n: np.linalg.norm(P[n] - P[x]))
        if np.linalg.norm(P[y] - P[x]) <= max_dist:
            out.append([x, y])
    return out


def shape_dist(rig, shape, kind, p):
    """how far a component-space point is outside a shape at rest (negative: inside)"""
    b = rig.by[shape['bone']] if shape.get('bone') else None
    q = b['q'] if b else [0, 0, 0, 1]
    t = b['t'] if b else [0, 0, 0]
    c = np.array(t) + np.array(qrot(q, shape['offset']))
    if kind == 'spheres':
        return float(np.linalg.norm(p - c) - shape['radius'])
    if kind == 'planes':
        n = np.array(qrot(q, qrot(from_rotator(*shape['rotation']), [0, 0, 1])))
        return float((p - c) @ n)
    ax = np.array(qrot(q, qrot(from_rotator(*shape['rotation']), [0, 0, 1])))
    h = shape['length'] / 2
    s = float(np.clip((p - c) @ ax, -h, h))
    rad = shape.get('radius')
    if rad is None:   # tapered: radius0 at +Z, radius1 at -Z
        f = (s + h) / (2 * h) if h > 0 else 0.5
        rad = shape['radius1'] + (shape['radius0'] - shape['radius1']) * f
    return float(np.linalg.norm(p - (c + ax * s)) - rad)


def fit_to_rest(rig, node, bones, margin=1.0, least=0.5):
    """shrink each shape a chain bone sits inside at rest (bone radius + margin clear), not below `least` of its size;
    drop it when that is not enough"""
    rad = node.get('radius', 0.0)
    pts = [np.array(rig.by[n]['t']) for n in bones if n in rig.by]
    for kind in ('spheres', 'capsules', 'tapered_capsules'):
        keep = []
        for sh in node.get(kind, []):
            worst = min(shape_dist(rig, sh, kind, p) for p in pts) - rad - margin
            if worst >= 0:
                keep.append(sh)
                continue
            keys = ['radius'] if 'radius' in sh else ['radius0', 'radius1']
            sh = dict(sh)
            ok = True
            for k in keys:
                new = sh[k] + worst
                if new < least * sh[k]:
                    ok = False
                sh[k] = r(max(new, least * sh[k]), 2)
            if ok and min(shape_dist(rig, sh, kind, p) for p in pts) - rad - margin >= -0.01:
                keep.append(sh)
        if keep:
            node[kind] = keep
        elif kind in node:
            del node[kind]
    return node


def main(src, model, out):
    os.makedirs(out, exist_ok=True)
    m = np.load(src)
    names = write_rig(m, os.path.join(out, 'rig.json'))
    write_body(m, names, os.path.join(out, 'body.npz'))
    rig = Rig(os.path.join(out, 'rig.json'))
    body = Body(m, names)
    T = lambda n: np.array(rig.by[n]['t'])
    report = {}

    # ---- shapes from his mesh
    legs = []
    for s in SIDES:
        thigh_set = [s + '_UpperLeg_a', s + '_FemorisB', s + '_FemorisC', s + '_FemorisSub', s + '_KneeSidA', s + '_KneeSidB', s + '_Knee1']
        calf_set = [s + '_Foreleg_a', s + '_Knee2', s + '_FootRollA', s + '_FootRollB', s + '_AnkleKdi']
        ra, rb = body.radii(T(s + '_UpperLeg_a'), T(s + '_Foreleg_a'), body.mask(thigh_set))
        ca, cb = body.radii(T(s + '_Foreleg_a'), T(s + '_Foot_a'), body.mask(calf_set))
        report[s + ' leg radii'] = [r(x or 0, 1) for x in (ra, rb, ca, cb)]
        legs.append(capsule(rig, s + '_UpperLeg_a', s + '_Foreleg_a', (ra or 14) + 1.0, r_b=(rb or 11) + 1.0, skip=6.0))
        legs.append(capsule(rig, s + '_Foreleg_a', s + '_Foot_a', (ca or 11) + 1.0, r_b=(cb or 9) + 1.0))
    back_set = ['C_Hip_a', 'C_Spine_a', 'C_Spine_b', 'C_Spine_c', 'C_Spine_d', 'Spine1W', 'Abs1', 'Abs2', 'Abs3', 'Abs4', 'Abs5']
    ba, bb = body.radii(T('C_Hip_a'), T('C_Spine_d'), body.mask(back_set), toward=[-1, 0, 0])
    report['back radii'] = [r(ba or 0, 1), r(bb or 0, 1)]
    back = [capsule(rig, 'C_Hip_a', 'C_Spine_d', (ba or 16), r_b=(bb or 18))]
    tailcaps = []
    for a, b in (('Tail1', 'Tail4'), ('Tail4', 'Tail8'), ('Tail8', 'Tail12'), ('Tail12', 'Tail16')):
        seg = chain_bones(rig, a)
        seg_set = [n for n in seg if n.startswith('Tail') and int(n[4:]) >= int(a[4:]) and int(n[4:]) <= int(b[4:])]
        ta, tb = body.radii(T(a), T(b), body.mask(seg_set), pct=80)
        report['tail %s-%s radii' % (a, b)] = [r(ta or 0, 1), r(tb or 0, 1)]
        tailcaps.append(cap_points(rig, a, T(a), T(b), (ta or 8), (tb or 7)))
    floor = [{'offset': [0.0, 0.0, 0.5], 'rotation': [0.0, 0.0, 0.0]}]

    nodes = []
    # ---- the tail (first: the mantles collide with it as it swings)
    tail = dict(name='tail', root_bone='Tail1', **TAIL)
    if TAIL_WAVES:
        tail['pose_waves'] = [dict(w) for w in TAIL_WAVES]
    tail['tapered_capsules'] = [dict(x) for x in legs]
    tail['planes'] = floor
    nodes.append(fit_to_rest(rig, tail, [n for n in chain_bones(rig, 'Tail1') if n != 'Tail1']))
    # ---- the mantles
    for s in SIDES:
        roots = ['%s_%sKdi' % (s, c) for c in LARGE]
        strips = {c: [n for n in chain_bones(rig, '%s_%sKdi' % (s, c))[1:]] for c in LARGE}
        # the C strip forks: C6 - C10 and E1 - E14 (the outer, longer part)
        cmain = [n for n in strips['MantLgC'] if '%s_MantLgC' % s in n]
        cfork = [n for n in strips['MantLgC'] if '%s_MantLgE' % s in n]
        order = lambda lst: sorted(lst, key=lambda n: int(''.join(ch for ch in n.split('Mant')[1] if ch.isdigit())))
        A, B, D = order(strips['MantLgA']), order(strips['MantLgB']), order(strips['MantLgD'])
        C, E = order(cmain), order(cfork)
        cons = ties(rig, A, B) + ties(rig, B, C + E) + ties(rig, E, D) + ties(rig, C, D)
        n = dict(name='mantle ' + s, root_bone=roots[0], additional_root_bones=[{'root_bone': x} for x in roots[1:]], **MANTLE)
        n['bone_constraints'] = [{'bone1': a, 'bone2': b} for a, b in cons]
        n['tapered_capsules'] = [dict(x) for x in legs + back + tailcaps]
        n['planes'] = floor
        report['mantle %s ties' % s] = len(cons)
        nodes.append(fit_to_rest(rig, n, A + B + C + D + E))
    for s in SIDES:
        roots = ['%s_%sKdi' % (s, c) for c in SMALL]
        sb = [x for c in SMALL for x in chain_bones(rig, '%s_%sKdi' % (s, c))[1:]]
        n = dict(name='shoulder mantle ' + s, root_bone=roots[0], additional_root_bones=[{'root_bone': x} for x in roots[1:]], **SHOULDER)
        arm = [capsule(rig, s + '_UpperArm_a', s + '_Forearm_a', 9.0, r_b=7.0)]
        n['tapered_capsules'] = [dict(x) for x in back + arm]
        nodes.append(fit_to_rest(rig, n, sb))
    # ---- the blade wings: every blade a point on the chest bone with a dummy bone along it, a node per bone axis that
    # runs along the blades; the chest's other bones left out
    blades = ['%s_SwordWing%s' % (s, c) for s in SIDES for c in 'ABCDEFGHIJKLMNO']
    axes = blade_axes(m, names, rig, blades)
    report['blade axes'] = {a: len([b for b in blades if axes[b] == a]) for a in sorted(set(axes.values()))}
    for side in SIDES:
        for a in sorted(set(axes[b] for b in blades if b.startswith(side + '_'))):
            group = [b for b in blades if b.startswith(side + '_') and axes[b] == a]
            # (each blade its own chain's root with a dummy bone as its one child: the blade turns toward it. The chest bone
            # is not the root: a root with one child is turned too, and the chest would turn with a blade. A node per side
            # and axis: the beat turns each side's blades the mirrored way)
            n = dict(name='blade wings %s %s' % (side, a), root_bone=group[0], additional_root_bones=[{'root_bone': b} for b in group[1:]], **WINGS)
            n['bone_forward_axis'] = a
            if WING_BEAT and WING_BEAT['degrees']:
                n['pose_waves'] = [dict(axis=[1.0 if side == 'L' else -1.0, 0.0, 0.0], degrees=WING_BEAT['degrees'], seconds=WING_BEAT['seconds'],
                                        root_phases=[WING_BEAT['ripple'] * 'ABCDEFGHIJKLMNO'.index(b[-1]) for b in group])]
            nodes.append(n)
    # ---- the hair (when the model has it)
    if 'C_HairBase_a' in rig.by:
        preset = hair_settings()
        na, nb_ = body.radii(T('C_Spine_d'), T('C_Neck_a'), body.mask(['C_Spine_d', 'C_Neck_a', 'NeckSub']), toward=[-1, 0, 0])
        ca_, cb_ = body.radii(T('C_Spine_b'), T('C_Spine_d'), body.mask(['C_Spine_b', 'C_Spine_c', 'C_Spine_d']), toward=[1, 0, 0])
        report['collar radii'] = [r(na or 0, 1), r(nb_ or 0, 1)]
        report['chest radii'] = [r(ca_ or 0, 1), r(cb_ or 0, 1)]
        collar = [capsule(rig, 'C_Spine_d', 'C_Neck_a', (na or 14), r_b=(nb_ or 10))]
        chest = [capsule(rig, 'C_Spine_b', 'C_Spine_d', (ca_ or 16), r_b=(cb_ or 18))]
        shoulders, arms = [], []
        for s in SIDES:
            sh_set = [s + '_Shoulder_a', s + '_DeltoidX', s + '_ShldZKdi3', s + '_UpperArm_a']
            ra, rb = body.radii(T(s + '_Shoulder_a'), T(s + '_UpperArm_a'), body.mask(sh_set))
            report[s + ' shoulder radii'] = [r(ra or 0, 1), r(rb or 0, 1)]
            shoulders.append(capsule(rig, s + '_Shoulder_a', s + '_UpperArm_a', (ra or 10), r_b=(rb or 12)))
            arms.append(capsule(rig, s + '_UpperArm_a', s + '_Forearm_a', 9.0, r_b=7.0))
        # the armour's own surface under the hair: spheres just inside it, touching it where the hair lies on it at rest
        # (the chest under the front strands, the back under the long hair), on the chest and spine bones
        torso_set = ['C_Spine_a', 'C_Spine_b', 'C_Spine_c', 'C_Spine_d', 'C_Neck_a', 'NeckSub', 'Spine1W', 'Abs1', 'Abs2', 'Abs3',
                     'Abs4', 'Abs5', 'C_Hip_a']
        tmask = body.mask(torso_set)
        TP = body.pos[tmask]

        def surface_spheres(points, side, R):
            out = []
            for p in points:
                win = (np.abs(TP[:, 1] - p[1]) < 2.5) & (np.abs(TP[:, 2] - p[2]) < 2.5)
                win &= (TP[:, 0] < p[0]) if side > 0 else (TP[:, 0] > p[0])
                if win.sum() < 3:
                    continue
                xs = TP[win, 0].max() if side > 0 else TP[win, 0].min()
                ctr = np.array([xs - side * R, p[1], p[2]])
                bone = 'C_Spine_d' if p[2] > 150 else 'C_Spine_c' if p[2] > 138 else 'C_Spine_b'
                out.append(sphere(rig, bone, ctr, R))
            return out
        chest_pts = []
        for c in HAIR_FRONT:
            root = c + '_a_Phy'
            if root in rig.by:
                chest_pts += [T(x) for x in chain_bones(rig, root) if T(x)[2] < 172]
        chest_spheres = surface_spheres(chest_pts, +1, 7.0)
        back_pts = [np.array([0.0, y, z]) for z in range(176, 112, -8) for y in (-9.0, 0.0, 9.0)]
        back_spheres = surface_spheres([np.array([-5.0, p[1], p[2]]) for p in back_pts], -1, 8.0)
        report['hair surface spheres'] = [len(chest_spheres), len(back_spheres)]
        for c in HAIR_FRONT + HAIR_BACK:
            root = c + '_a_Phy'
            if root not in rig.by:
                continue
            bones = [x for x in chain_bones(rig, root) if x != root]
            n = dict(preset.get(root, {}))
            n['name'] = ('front hair ' if c in HAIR_FRONT else 'long hair ') + c
            n['root_bone'] = root
            if c in HAIR_FRONT:
                n['radius'] = 1.2           # (thin strands lying on the armour: the preset's 2.4 would hold them off it)
                n['tapered_capsules'] = [dict(x) for x in chest + shoulders + arms]
                n['spheres'] = [sphere(rig, 'C_Head_a', T('C_Head_a') + np.array([0.0, 0.0, 5.0]), 12.0)] + [dict(x) for x in chest_spheres]
            else:
                n['tapered_capsules'] = [dict(x) for x in back + collar + shoulders + legs + tailcaps[:2]]
                n['spheres'] = [dict(x) for x in back_spheres]
            nodes.append(fit_to_rest(rig, n, bones))
    has_hair = 'C_HairBase_a' in rig.by
    entry = dict(name="Bahamut Fused Sephiroth (PC0010_17_Compat): his tail, his mantles, his blade wings" + (" and his hair" if has_hair else ""),
                 models=[model], preset='bahamut fused sephiroth', nodes=nodes)
    if has_hair:
        entry['disable_bonamik'] = True
    json.dump({'kawaii': [entry]}, open(os.path.join(out, 'entry.json'), 'w'), indent=1)
    report['nodes'] = [(x['name'], len(x.get('tapered_capsules', [])), len(x.get('bone_constraints', []))) for x in nodes]
    print(json.dumps(report, indent=1))


if __name__ == '__main__':
    main(*sys.argv[1:4])
