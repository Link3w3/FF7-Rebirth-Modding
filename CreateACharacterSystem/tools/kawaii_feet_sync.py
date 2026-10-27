"""(3.17.0) Kawaii Dynamic Motions: feet colliders and sync bones for the coats (and skirts, mantles, pants) of a compat
file's "kawaii" entries, so a leg kicking out no longer goes through the cloth.

  * feet: each node whose chains hang below the knees gets the model's feet as tapered capsules (heel to toes, on the
    foot bone), measured from the model's mesh when one is given, else scaled from the skeleton;
  * sync bones (KawaiiPhysics' SyncBone, game mod 3.17.0): each chain of such a node follows the knee on its side (a chain
    down the middle follows both, half each), from nothing at its top to all of the knee's move at the knee's height
    and below: the chains in front of the legs when a knee comes forward (and up), the ones behind when it goes back,
    the side ones when it goes out to that side.

Library (used by make_kawaii_feet_sync.py) and a CLI:
    python3 kawaii_feet_sync.py in.json out.json --rig rig.json [--mesh body.npz] [--entry N] [--no-feet] [--no-sync]
                                [--front-scale 1] [--side-scale 0.7] [--back-scale 0.8] [--knee-rate auto]
The model's forward is +X, its left -Y, up +Z (component space, as the game's models are)."""
import argparse
import json
import math
import re
import sys

import numpy as np


# ---- quaternions (x, y, z, w) ------------------------------------------------------------------------------------------
def qmul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return [aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx, aw * bz + ax * by - ay * bx + az * bw,
            aw * bw - ax * bx - ay * by - az * bz]


def qinv(q):
    return [-q[0], -q[1], -q[2], q[3]]


def qrot(q, v):
    qv = q[:3]
    t = [2.0 * (qv[1] * v[2] - qv[2] * v[1]), 2.0 * (qv[2] * v[0] - qv[0] * v[2]), 2.0 * (qv[0] * v[1] - qv[1] * v[0])]
    c = [qv[1] * t[2] - qv[2] * t[1], qv[2] * t[0] - qv[0] * t[2], qv[0] * t[1] - qv[1] * t[0]]
    return [v[i] + q[3] * t[i] + c[i] for i in range(3)]


def from_rotator(pitch, yaw, roll):
    half = math.pi / 360.0
    p, y, r = pitch * half, yaw * half, roll * half
    sp, cp, sy, cy, sr, cr = math.sin(p), math.cos(p), math.sin(y), math.cos(y), math.sin(r), math.cos(r)
    return [cr * sp * sy - sr * cp * cy, -cr * sp * cy - sr * cp * sy, cr * cp * sy - sr * sp * cy, cr * cp * cy + sr * sp * sy]


def rot_for_z(d):
    """A rotator whose +Z axis is d (checked numerically)."""
    n = math.sqrt(sum(c * c for c in d))
    u = [c / n for c in d]
    best = None
    # Z axis of FRotator(p, y, 0): rotate (0,0,1) -> solve by search over the closed form candidates
    pitch = math.degrees(math.asin(max(-1.0, min(1.0, -math.sqrt(u[0] * u[0] + u[1] * u[1])))))
    for pv in (pitch, -pitch, 180.0 - pitch, pitch - 180.0):
        for yv in (math.degrees(math.atan2(u[1], u[0])), math.degrees(math.atan2(-u[1], -u[0]))):
            z = qrot(from_rotator(pv, yv, 0.0), [0.0, 0.0, 1.0])
            err = sum((z[i] - u[i]) ** 2 for i in range(3))
            if best is None or err < best[0]:
                best = (err, pv, yv)
    assert best[0] < 1e-6, (d, best)
    return [round(best[1], 3), round(best[2], 3), 0.0]


def rnd(x, n=3):
    return round(float(x), n)


class Rig:
    def __init__(self, path):
        data = json.load(open(path))
        self.bones = data['bones']
        self.by = {b['name']: b for b in self.bones}
        self.kids = {}
        for b in self.bones:
            if b.get('parent'):
                self.kids.setdefault(b['parent'], []).append(b['name'])

    def has(self, *names):
        return all(n in self.by for n in names)

    def t(self, name):
        return self.by[name]['t']

    def local_point(self, bone, p):
        b = self.by[bone]
        return qrot(qinv(b['q']), [p[i] - b['t'][i] for i in range(3)])

    def chain(self, root):
        """The bones of a chain from its root down (the first child each step)."""
        out = [root]
        while True:
            kids = [k for k in self.kids.get(out[-1], []) if k.endswith('_Phy')] or self.kids.get(out[-1], [])
            if not kids:
                return out
            out.append(kids[0])


def cap_points(rig, bone, p0, p1, r0, r1):
    """A tapered capsule on `bone` between two component-space points of the reference pose: r0 at p0, r1 at p1."""
    a = rig.local_point(bone, p0)
    b = rig.local_point(bone, p1)
    d = [b[i] - a[i] for i in range(3)]
    length = math.sqrt(sum(c * c for c in d))
    return {'bone': bone, 'offset': [rnd((a[i] + b[i]) / 2) for i in range(3)], 'rotation': rot_for_z(d), 'length': rnd(length, 2),
            'radius0': rnd(r1, 2), 'radius1': rnd(r0, 2)}   # (radius0: the +Z end, toward p1)


# ---- the feet -----------------------------------------------------------------------------------------------------------
def measure_feet(rig, mesh):
    """Each foot from the mesh's vertices skinned mostly to Foot_a / Toe_a: its heel and toe points (on the foot's line,
    halfway up), and its radius at each end (half its height and width there, the larger). None without a mesh."""
    if mesh is None:
        return None
    d = np.load(mesh, allow_pickle=True)
    pos = d['pos']
    names = [str(n) for n in d['bones']]
    n = len(pos)
    dom = np.zeros(n, dtype=np.int64)
    best = np.zeros(n)
    for b, v, w in zip(d['w_bone'], d['w_vert'], d['w_weight']):
        if w > best[v]:
            best[v] = w
            dom[v] = b
    domname = np.array(names)[dom]
    out = {}
    for s in 'LR':
        rx = re.compile(r'^%s_(Foot_a|Toe_a)$' % s)
        m = np.array([rx.search(x) is not None for x in domname])
        if m.sum() < 30:
            return None
        P = pos[m]
        heel_x, toe_x = np.percentile(P[:, 0], 1), np.percentile(P[:, 0], 99)
        def slab(x0, x1):
            q = P[(P[:, 0] >= x0) & (P[:, 0] <= x1)]
            if len(q) < 5:
                return None
            return q
        length = toe_x - heel_x
        heel = slab(heel_x, heel_x + 0.2 * length)
        toe = slab(toe_x - 0.2 * length, toe_x)
        if heel is None or toe is None:
            return None
        def ends(q, x):
            y = (np.percentile(q[:, 1], 5) + np.percentile(q[:, 1], 95)) / 2
            z0, z1 = np.percentile(q[:, 2], 2), np.percentile(q[:, 2], 98)
            w = np.percentile(q[:, 1], 95) - np.percentile(q[:, 1], 5)
            r = (w / 2 + (z1 - z0) / 2) / 2 + 0.5   # (a round capsule on a flat foot: between its half width and half height)
            return [float(x), float(y), float((z0 + z1) / 2)], float(r)
        hp, hr = ends(heel, heel_x)
        tp, tr = ends(toe, toe_x)
        # the capsule's ends are hemispheres: its axis points move in by their radius so it reaches the heel and the toes
        hp[0] += hr * 0.9
        tp[0] -= tr * 0.9
        out[s] = (hp, hr, tp, tr)
    return out


def default_feet(rig):
    """The feet scaled from the skeleton (Rebirth's Sephiroth's as measured, by his ankle-to-toe joint length)."""
    out = {}
    for s in 'LR':
        a = rig.t(s + '_Foot_a')
        t = rig.t(s + '_Toe_a')
        L = math.dist(a, t)
        k = L / 16.37   # (PC0010_00's ankle to toe joint)
        fwd = [t[0] - a[0], 0.0, 0.0]
        fwd = [1.0 if t[0] >= a[0] else -1.0, 0.0, 0.0]
        hp = [a[0] - 4.4 * k * fwd[0], a[1], 6.6 * k]
        tp = [t[0] + 4.0 * k * fwd[0], t[1], 4.4 * k]
        out[s] = (hp, 6.0 * k, tp, 4.6 * k)
    return out


def feet_shapes(rig, mesh=None, pad=1.0):
    if not rig.has('L_Foot_a', 'R_Foot_a', 'L_Toe_a', 'R_Toe_a'):
        return []
    feet = measure_feet(rig, mesh) or default_feet(rig)
    shapes = []
    for s in 'LR':
        hp, hr, tp, tr = feet[s]
        shapes.append(cap_points(rig, s + '_Foot_a', hp, tp, hr + pad, tr + pad))
    return shapes


# ---- the chains: where each hangs -------------------------------------------------------------------------------------
def roots_of(node):
    roots = [node['root_bone']]
    for r in node.get('additional_root_bones', []):
        roots.append(r if isinstance(r, str) else r.get('root_bone', r.get('bone')))
    return roots


def chain_places(rig, root):
    """The chain's bones with their reference places and their length from the root (KawaiiPhysics' LengthFromRoot)."""
    bones = rig.chain(root)
    pts = [rig.t(b) for b in bones]
    acc = [0.0]
    for i in range(1, len(pts)):
        acc.append(acc[-1] + math.dist(pts[i], pts[i - 1]))
    return bones, pts, acc


def classify(rig, root):
    """(side 'L' / 'R' / 'C', place 'front' / 'side' / 'back', the knee's rate along the chain or None when the chain
    ends above the knee, the chain's lowest height)"""
    bones, pts, acc = chain_places(rig, root)
    knee_z = (rig.t('L_Foreleg_a')[2] + rig.t('R_Foreleg_a')[2]) / 2
    hip = rig.t('C_Hip_a') if rig.has('C_Hip_a') else [0.0, 0.0, 100.0]
    # the chain's place round the body: its bone nearest the knees' height (or its lowest)
    k = min(range(len(pts)), key=lambda i: abs(pts[i][2] - knee_z))
    x, y = pts[k][0] - hip[0], pts[k][1] - hip[1]
    ang = math.degrees(math.atan2(y, x))   # 0 front, -90 his left, +-180 back
    side = 'C' if abs(y) < 4.0 else ('L' if y < 0 else 'R')
    a = abs(ang)
    place = 'front' if a < 50 else ('back' if a > 130 else 'side')
    total = acc[-1] if acc[-1] > 0 else 1.0
    lowest = min(p[2] for p in pts)
    knee_rate = None
    if lowest < knee_z + 8.0:
        # the rate along the chain at the knees' height (between the two bones around it)
        for i in range(1, len(pts)):
            if pts[i][2] <= knee_z <= pts[i - 1][2]:
                f = (pts[i - 1][2] - knee_z) / max(pts[i - 1][2] - pts[i][2], 1e-6)
                knee_rate = (acc[i - 1] + f * (acc[i] - acc[i - 1])) / total
                break
        if knee_rate is None:
            knee_rate = 1.0
    else:
        # (it ends above the knee: the rate the knee would be at, past its end, so its bottom gets that part of the move;
        # a chain that does not hang down (its bottom less than 5 cm under its top) gets none)
        drop = pts[0][2] - lowest
        knee_rate = None if drop < 5.0 else max(1.0, (pts[0][2] - knee_z) / drop)
    return side, place, knee_rate, lowest


LEG_BONE = re.compile(r'(UpperLeg|Foreleg|Foot|Toe|Knee|Femoris|Calf)')


def under_leg(rig, bone):
    """A chain hung from a leg bone (pants: they move with the leg already; a sync bone would move them twice)."""
    at = rig.by[bone].get('parent')
    while at:
        if LEG_BONE.search(at):
            return True
        at = rig.by[at].get('parent') if at in rig.by else None
    return False


def scale_curve(knee_rate, peak=1.0):
    """0 at the chain's top, rising to `peak` at the knees' height and kept below it."""
    if knee_rate >= 1.0:
        top = peak / knee_rate
        return [[0.0, 0.0], [0.5, rnd(top * 0.4)], [1.0, rnd(top)]]
    return [[0.0, 0.0], [rnd(knee_rate * 0.5), rnd(peak * 0.35)], [rnd(knee_rate), rnd(peak)], [1.0, rnd(peak)]]


def sync_bones_for(rig, node, scales, places=('front', 'side', 'back')):
    """The node's sync bones: per knee and place (front, side, back) one sync bone with its chains as target roots."""
    groups = {}
    for root in roots_of(node):
        if root not in rig.by or under_leg(rig, root):
            continue
        side, place, knee_rate, lowest = classify(rig, root)
        if knee_rate is None or place not in places:
            continue
        sides = ['L', 'R'] if side == 'C' else [side]
        part = 0.5 if side == 'C' else 1.0
        for s in sides:
            groups.setdefault((s, place), []).append((root, knee_rate, part))
    out = []
    for (s, place), items in sorted(groups.items()):
        knee = s + '_Foreleg_a'
        if knee not in rig.by:
            continue
        peak = scales[place]
        sync = {'bone': knee, 'target_roots': []}
        for root, knee_rate, part in items:
            sync['target_roots'].append({'bone': root, 'scale_curve_by_bone_length_rate': scale_curve(knee_rate, peak * part)})
        out_y = 'negative' if s == 'L' else 'positive'
        if place == 'front':
            sync['apply_direction_x'] = 'positive'
            sync['apply_direction_z'] = 'positive'
        elif place == 'back':
            sync['apply_direction_x'] = 'negative'
            sync['apply_direction_z'] = 'positive'
        else:
            sync['apply_direction_y'] = out_y
            sync['apply_direction_z'] = 'positive'
        out.append(sync)
    return out


def is_leg_cloth(rig, node):
    """A node whose chains hang over the legs: any chain reaching below the hips' joints, in front, at the sides or
    behind the legs (coats, skirts, mantles, pants; not hair down the back above the hips)."""
    hips_z = max(rig.t('L_UpperLeg_a')[2], rig.t('R_UpperLeg_a')[2])
    name = (node.get('name') or node['root_bone']).lower()
    if any(k in name for k in ('hair', 'wing', 'collar', 'feather', 'tail', 'blade')):
        return False
    for root in roots_of(node):
        if root not in rig.by or under_leg(rig, root):
            continue
        bones, pts, acc = chain_places(rig, root)
        if min(p[2] for p in pts) < hips_z - 10.0:
            return True
    return False


def reaches_knees(rig, node):
    knee_z = (rig.t('L_Foreleg_a')[2] + rig.t('R_Foreleg_a')[2]) / 2
    for root in roots_of(node):
        if root not in rig.by or under_leg(rig, root):
            continue
        bones, pts, acc = chain_places(rig, root)
        if min(p[2] for p in pts) < knee_z:
            return True
    return False


def apply(entry, rig, mesh=None, feet=True, sync=True, scales=None, pad=1.0, log=None, places=('front', 'side', 'back')):
    scales = scales or {'front': 1.0, 'side': 0.7, 'back': 0.8}
    shapes = feet_shapes(rig, mesh, pad) if feet else []
    changed = []
    for node in entry['nodes']:
        if not is_leg_cloth(rig, node):
            continue
        what = []
        if shapes and reaches_knees(rig, node):
            have = node.setdefault('tapered_capsules', [])
            # (an earlier run's feet replaced)
            have[:] = [s for s in have if not s.get('bone', '').endswith('_Foot_a')]
            have.extend(json.loads(json.dumps(shapes)))
            what.append('feet')
        if sync:
            sb = sync_bones_for(rig, node, scales, places)
            if sb:
                node['sync_bones'] = sb
                what.append('%d sync bone(s)' % len(sb))
        if what:
            changed.append((node.get('name') or node['root_bone'], what))
    if log:
        for n, w in changed:
            log('  %s: %s' % (n, ', '.join(w)))
            if VERBOSE:
                node = next(x for x in entry['nodes'] if (x.get('name') or x['root_bone']) == n)
                for root in roots_of(node):
                    if root in rig.by:
                        side, place, kr, low = classify(rig, root)
                        log('      %-22s %s %-5s knee rate %s, lowest %.0f cm%s' % (root, side, place, '%.2f' % kr if kr is not None else '-', low,
                                                                            ' (on a leg: left alone)' if under_leg(rig, root) else ''))
    return changed


VERBOSE = False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('inp')
    ap.add_argument('out')
    ap.add_argument('--rig', required=True)
    ap.add_argument('--mesh')
    ap.add_argument('--entry', type=int, action='append')
    ap.add_argument('--no-feet', action='store_true')
    ap.add_argument('--no-sync', action='store_true')
    ap.add_argument('--front-scale', type=float, default=1.0)
    ap.add_argument('--side-scale', type=float, default=0.7)
    ap.add_argument('--back-scale', type=float, default=0.8)
    ap.add_argument('--pad', type=float, default=1.0)
    ap.add_argument('--verbose', action='store_true')
    ap.add_argument('--places', default='front,side,back', help='the chains given sync bones, by where they hang')
    a = ap.parse_args()
    global VERBOSE
    VERBOSE = a.verbose
    data = json.load(open(a.inp, encoding='utf-8-sig'))
    rig = Rig(a.rig)
    entries = data['kawaii']
    which = a.entry if a.entry else range(len(entries))
    for i in which:
        print('entry %d: %s' % (i, entries[i].get('name', '')))
        apply(entries[i], rig, a.mesh, not a.no_feet, not a.no_sync,
              {'front': a.front_scale, 'side': a.side_scale, 'back': a.back_scale}, a.pad, log=print, places=tuple(a.places.split(',')))
    json.dump(data, open(a.out, 'w'), indent=1)


if __name__ == '__main__':
    main()
