"""The DISSIDIA NT form's moves (pack Battle12): Dissidia NT Sephiroth's own motions (tools/g2a.py), retargeted onto
Rebirth Sephiroth's skeleton (PC0010_00) with the Dissidia NT proportions and the Masamune as Dissidia NT holds it
(tools/dnt_anim.py), as key animations (.cacanim, folder keys/) for Create a Character System's Import Key Animations
into /Game/Motion/Player/PC0010_19_DissidiaNT_Sephiroth/DNTRoot, and the plan (plan.json, the CRISIS CORE form's format)
that Build Moves builds them from: each move with the gameplay notifies of Sephiroth's move of that name (combo, cancel
and dodge windows, damage on the Masamune), the damage on Dissidia NT's blows (the blade's fastest moment in each
slash), Rebirth's sword trail and swing sound on every slash.

  combo (Square)  1-4  600A-600D: his four ground Bravery attacks (each a dash in, the cuts, back to his stance);
                       Dissidia NT dashes 4.5-7 m into each one: the way is kept to TRAVEL_CM (root motion)
  hold Square          740A + 740D: the low lunge stance, then its strongest release
  Triangle 9           710A: the crouch, the dash and the cut through
  limit                700A in two halves: the wind-up (the Masamune whirled overhead), then the dash and the cuts
  spells               950A / 950B / 950C: the cast's start, its loop and its end
  idle, damage         000A (his battle stance), 1001A + 1001B (struck, then back in his stance)
  victory              R300 (the results screen's flourish)
Everything else stays Sephiroth's own (Battle00 as Battle12).
    make_dnt_moves.py <motion root (character/p_sev200)> <model face npz> <base g1m> <out folder>"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import g2a        # noqa: E402
import dnt_anim   # noqa: E402
from ccretarget import q2m, m2q, continuous, write_cacanim, GAME_ROOT_Q   # noqa: E402,F401

SET = 'Battle12'
ANIM_FOLDER = '/Game/Motion/Player/PC0010_19_DissidiaNT_Sephiroth/DNTRoot'
SEPH = '/Game/Motion/Player/PC0010_Sephiroth/Battle00/'
TR00 = '/Game/Motion/Player/PC0010_Sephiroth_Transform/Battle00/'
SE = '/Game/Sound/SE/Character/Player/SE_PC0010_00_Sephiroth_Standard.SE_PC0010_00_Sephiroth_Standard'
TRAIL = '/Game/Effect/Character/Player/PC0010_Sephiroth/Particle/FX_PC0010_Weapon_Trail_01.FX_PC0010_Weapon_Trail_01'
TRAVEL_CM = 250.0

# animation -> (Dissidia NT clips played one after the other, loop, travel kept to (cm; None: as it is))
CLIPS = {
    'DNT_000A': (['mot_00/000A'], True, None),
    'DNT_600A': (['mot_00/600A'], False, TRAVEL_CM),
    'DNT_600B': (['mot_00/600B'], False, TRAVEL_CM),
    'DNT_600C': (['mot_00/600C'], False, TRAVEL_CM),
    'DNT_600D': (['mot_00/600D'], False, TRAVEL_CM),
    'DNT_740A_740D': (['mot_00/740A', 'mot_00/740D'], False, TRAVEL_CM),
    'DNT_710A': (['mot_00/710A'], False, 300.0),
    'DNT_700A': (['mot_00/700A'], False, 300.0),
    'DNT_950A': (['mot_00/950A'], False, None),
    'DNT_950B': (['mot_00/950B'], True, None),
    'DNT_950C': (['mot_00/950C'], False, None),
    'DNT_1001A_1001B': (['mot_00/1001A', 'mot_00/1001B'], False, 60.0),
    'DNT_R300': (['mot_10/R300'], False, None),
}
LIMIT_SPLIT = 'dash'      # B_AtkLimit01_0 ends where 700A's dash starts

# name -> (animation, start, end (0: its end), speed, notifies from (None: Sephiroth's Battle00 move of that name), slashes used)
MOVES = {
    'B_NAttack01_0': ('DNT_600A', 0.0, 0.0, 1.0, None, None),
    'B_NAttack02_0': ('DNT_600B', 0.0, 0.0, 1.0, None, None),
    'B_NAttack03_0': ('DNT_600C', 0.0, 0.0, 1.0, None, None),
    'B_NAttack04_0': ('DNT_600D', 0.0, 0.0, 1.0, None, None),
    'B_NPAttack01': ('DNT_740A_740D', 0.0, 0.0, 1.0, None, None),
    'B_SAttack09_0': ('DNT_710A', 0.0, 0.0, 1.0, None, None),
    'B_AtkLimit01_0': ('DNT_700A', 0.0, 'split', 1.0, None, None),
    'B_AtkLimit01_1': ('DNT_700A', 'split', 0.0, 1.0, None, None),
    'B_MagAttack01_0': ('DNT_950A', 0.0, 0.0, 1.0, None, []),
    'B_MagAttack01_1': ('DNT_950B', 0.0, 0.0, 1.0, None, []),
    'B_MagAttack01_2': ('DNT_950C', 0.0, 0.0, 1.0, None, []),
    'B_AtkMag01_0': ('DNT_950A', 0.0, 0.0, 1.0, TR00 + 'B_AtkMag01_0', []),
    'B_AtkMag01_1': ('DNT_950B', 0.0, 0.0, 1.0, TR00 + 'B_AtkMag01_1', []),
    'B_AtkMag01_2': ('DNT_950C', 0.0, 0.0, 1.0, TR00 + 'B_AtkMag01_2', []),
    'B_Idle01_1': ('DNT_000A', 0.0, 0.0, 1.0, None, []),
    'B_Idle01_1_EnemyBook': ('DNT_000A', 0.0, 0.0, 1.0, SEPH + 'B_Idle01_1', []),
    'B_DmgF01': ('DNT_1001A_1001B', 0.0, 0.0, 1.0, None, []),
    'B_Win01': ('DNT_R300', 0.0, 0.0, 1.0, None, []),
}
# the spell's release (no slash of its own): its middle
BLOWS = {'DNT_950C': [0.25]}
# seconds at the start of an animation that hold no blow (the wind-up out of his stance; 740A: dropping into the lunge)
SKIP = {'DNT_600A': 0.2, 'DNT_600B': 0.2, 'DNT_600C': 0.2, 'DNT_600D': 0.15, 'DNT_740A_740D': 1.4, 'DNT_710A': 0.5}
BLEND_FRAMES = 8          # a join of two clips eased over this many frames


def joined(root, skel, parts):
    """the clips' world rotations / positions one after the other (a clip's first frame left out when it is the frame
    before it), their frame rate, and how far apart they met (degrees, cm)"""
    WR, WP, fps, gap = None, None, None, []
    for p in parts:
        sub, clip = p.split('/')
        mot = g2a.read(os.path.join(root, 'p_sev200_' + sub, clip + '.g1a'))
        R, P = skel.world(mot)
        if WR is None:
            WR, WP, fps = R, P, mot.fps
            continue
        assert abs(mot.fps - fps) < 1e-3, (p, mot.fps, fps)
        # each Dissidia NT motion starts where the game put the character after the one before (its root moved on by
        # that one's way): the next clip turned about the vertical and moved across the ground so that its centre (b1)
        # starts where and as the last one's ended
        c = skel.names.index('b1')
        f1 = WR[-1, c] @ np.array([0.0, 0.0, 1.0]); f2 = R[0, c] @ np.array([0.0, 0.0, 1.0])
        yaw = np.arctan2(f1[0], f1[2]) - np.arctan2(f2[0], f2[2])
        cy, sy = np.cos(yaw), np.sin(yaw)
        Y = np.array([[cy, 0.0, sy], [0.0, 1.0, 0.0], [-sy, 0.0, cy]])
        R = np.einsum('ij,fbjk->fbik', Y, R)
        P = np.einsum('ij,fbj->fbi', Y, P)
        t = WP[-1, c] - P[0, c]
        t[1] = 0.0
        P = P + t
        d = WR[-1].transpose(0, 2, 1) @ R[0]
        ang = np.degrees(np.arccos(np.clip((np.trace(d, axis1=1, axis2=2) - 1) / 2, -1, 1))).max()
        dp = np.linalg.norm(WP[-1] - P[0], axis=1).max()
        gap.append((round(float(ang), 2), round(float(dp), 2)))
        k = 1 if ang < 0.5 and dp < 0.5 else 0
        R, P = R[k:].copy(), P[k:].copy()
        if k == 0:
            # the next clip's first frames eased from where the last one ended (its own pose by BLEND_FRAMES)
            qa = m2q(WR[-1]); 
            for i in range(min(BLEND_FRAMES, len(R))):
                w = 1.0 - (i + 1.0) / (BLEND_FRAMES + 1.0)
                qb = m2q(R[i])
                s_ = np.sign(np.sum(qa * qb, axis=1, keepdims=True)); s_[s_ == 0] = 1
                q = (1 - w) * qb + w * qa * s_
                q /= np.linalg.norm(q, axis=1, keepdims=True)
                R[i] = q2m(q)
                P[i] = (1 - w) * P[i] + w * WP[-1]
        WR = np.concatenate([WR, R]); WP = np.concatenate([WP, P])
    return WR, WP, fps, gap


def slashes(rig, G, T, fps, skip_s=0.1, merge_s=0.12):
    """the Masamune's slashes: (start, peak, end) seconds. A slash peaks where the blade's tip (200 cm out) moves fastest
    against the hips while it is out in front (40 cm ahead of the hips or more) and above the ground; it lasts while the
    tip keeps 40 % of that speed. The first skip_s seconds (the wind-up out of his stance) are not slashes."""
    w, h = rig.ix['R_Weapon_a'], rig.ix['C_Hip_a']
    d = np.einsum('fij,j->fi', G[:, w] @ dnt_anim.SOCKET_R, np.array([1.0, 0, 0]))
    tipw = T[:, w] + 200 * d
    tip = tipw - T[:, h]
    sp = np.r_[0.0, np.linalg.norm(np.diff(tip, axis=0), axis=1) * fps / 100.0]
    k = np.exp(-0.5 * (np.arange(-2, 3) / 1.0) ** 2); k /= k.sum()
    sp = np.convolve(np.r_[sp[:2], sp, sp[-2:]], k, mode='valid')
    front = (tip[:, 0] > 40.0) & (tipw[:, 2] > 20.0)
    s0 = int(skip_s * fps)
    if len(sp) <= s0 + 2:
        return [], round(float(sp.max()), 1)
    thr = max(15.0, 0.3 * sp[s0:].max())
    fast = sp > thr
    fast[:s0] = False
    segs, f = [], 0
    while f < len(sp):
        if fast[f]:
            g = f
            while g + 1 < len(sp) and fast[g + 1]:
                g += 1
            if segs and f - segs[-1][1] <= 0.06 * fps:
                segs[-1] = (segs[-1][0], g)
            else:
                segs.append((f, g))
            f = g + 1
        else:
            f += 1
    out = []
    for a, b in segs:
        lo, hi = max(0, a - 2), min(len(sp) - 1, b + 2)
        if not front[lo:hi + 1].any():
            continue
        peak = sp[a:b + 1].max()
        cand = [f for f in range(lo, hi + 1) if sp[f] >= 0.5 * peak and front[f]] or \
               [f for f in range(lo, hi + 1) if front[f]]
        hit = max(cand, key=lambda f: tip[f, 0])
        if out and hit - out[-1][1] * fps < merge_s * fps:
            continue
        out.append((round(a / fps, 3), round(hit / fps, 3), round(b / fps, 3)))
    return out, round(float(sp.max()), 1)


class JoinedMotion:
    """a motion stand-in for Rig.retarget: frames from world transforms already joined"""

    def __init__(self, WR, WP, fps):
        self.WR, self.WP, self.fps = WR, WP, fps
        self.frames = len(WR)
        self.length = self.frames - 1


class Retarget(dnt_anim.Rig):
    def retarget_joined(self, jm, travel, travel_limit):
        skel = self.skel
        world = skel.world
        skel.world = lambda mot: (mot.WR, mot.WP)
        try:
            return self.retarget(jm, travel=travel, travel_limit=travel_limit)
        finally:
            skel.world = world


def main(root, model, base, out):
    keys = os.path.join(out, 'keys')
    os.makedirs(keys, exist_ok=True)
    skel = dnt_anim.DntSkeleton(base)
    rig = Retarget(model, skel)
    skip = rig.game_skip()
    info = {}
    for name, (parts, loop, limit) in CLIPS.items():
        WR, WP, fps, gap = joined(root, skel, parts)
        jm = JoinedMotion(WR, WP, fps)
        LQ, LT, G, T, rep = rig.retarget_joined(jm, not loop, limit)
        n = write_cacanim(os.path.join(keys, name + '.cacanim'), rig.names, LQ, LT, fps, loop, skip)
        cuts, peak = slashes(rig, G, T, fps, skip_s=SKIP.get(name, 0.1))
        hip = T[:, rig.ix['C_Hip_a']]
        v = np.r_[0.0, np.linalg.norm(np.diff(hip[:, :2], axis=0), axis=1) * fps / 100.0]
        info[name] = dict(frames=len(LQ), fps=fps, seconds=round((len(LQ) - 1) / fps, 3), loop=loop, tracks=n, joins=gap,
                          slashes=cuts, tip_peak_ms=peak, root_travel_cm=rep['root_travel_cm'], hips_cm=rep['hip_height_cm'],
                          hip_speed=v.tolist())
        print('%-18s %4d frames %2.0f fps %3d tracks travel %-16s joins %s slashes %s' % (
            name, len(LQ), fps, n, rep['root_travel_cm'], gap, [c[1] for c in cuts]), flush=True)
    # the limit's split: where 700A's dash starts (the hips past 3 m/s after its first second)
    v = np.array(info['DNT_700A']['hip_speed'])
    f0 = int(1.0 * info['DNT_700A']['fps'])
    start = f0 + int(np.argmax(v[f0:] > 3.0))
    split = round(max(0.0, (start - 4) / info['DNT_700A']['fps']), 3)
    moves, plan_keys = [], {}
    for name, (anim, t0, t1, speed, notifies, use) in MOVES.items():
        t0 = split if t0 == 'split' else t0
        t1 = split if t1 == 'split' else t1
        cuts = info[anim]['slashes']
        if use is not None:
            cuts = [cuts[k] for k in use]
        inside = [c for c in cuts if c[1] >= t0 - 1e-6 and (t1 <= 0 or c[1] <= t1 + 1e-6)]
        blows = [c[1] for c in inside] or BLOWS.get(anim, [])
        rel = lambda t: round(max(0.0, (t - t0) / speed), 4)
        m = {'set': SET, 'name': name, 'animation': '%s/%s' % (ANIM_FOLDER, anim), 'notifies_from': notifies or (SEPH + name),
             'hits': [{'time': rel(b)} for b in blows], 'source': anim}
        if t0 > 0 or t1 > 0:
            m['clip'] = [t0, t1]
        if abs(speed - 1.0) > 1e-6:
            m['speed'] = speed
        extras = []
        for a, p, b in inside:
            a2, b2 = max(a, t0), (b if t1 <= 0 else min(b, t1))
            extras.append({'kind': 'effect', 'time': rel(a2), 'duration': round(max(0.12, (b2 - a2) / speed + 0.08), 3),
                           'effect': TRAIL, 'socket': 'C_TrailA_b', 'on': 'Weapon1'})
            extras.append({'kind': 'sound', 'time': rel(p), 'bank': SE, 'cue': 'EB0021_sword_swishM', 'attach': 'C_Hip_a'})
        if extras:
            m['extras'] = extras
        moves.append(m)
        plan_keys[name] = '/Game/RebirthSkelCompat/Built/SephirothForms/%s/%s.%s' % (SET, name, name)
    plan = {'set': SET, 'moves': moves, 'keys': {SET: plan_keys}, 'anim_folder': ANIM_FOLDER, 'limit_split': split}
    json.dump(plan, open(os.path.join(out, 'plan.json'), 'w'), indent=1)
    for v in info.values():
        v.pop('hip_speed')
    json.dump(info, open(os.path.join(out, 'clips.json'), 'w'), indent=1)
    print('limit split at %.3f s' % split)
    for m in moves:
        print('%-22s %-16s clip %-16s hits %s extras %d' % (m['name'], m['source'], m.get('clip', '-'),
                                                           [h['time'] for h in m['hits']], len(m.get('extras', []))))


if __name__ == '__main__':
    main(*sys.argv[1:5])
