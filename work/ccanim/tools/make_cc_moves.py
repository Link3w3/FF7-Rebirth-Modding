"""The CRISIS CORE form's moves (pack Battle10): Crisis Core Reunion Sephiroth's own battle animations (retargeted onto
Rebirth Sephiroth's skeleton with their travel as root motion: /Game/Motion/Player/PC0010_16_CrisisCore_Sephiroth/CCRoot)
built with Create a Character System's Build Moves into Sephiroth's moves, each with the gameplay notifies of Sephiroth's
move of that name (combo, cancel and dodge windows, damage on the Masamune), the damage lined up on Crisis Core's blows
(the middle of each of its sword trails), and Rebirth's sword trail and swing sound on every Crisis Core slash (extras).

  combo (Square)  1 attack1: the downward cut and the sweep        2 attack2: the quick cut and the lunging cut
                  3 attack2: the rising cut and the leaping cut    4 attack3: the iaido dash (a drawn cut through)
  hold Square     attack6: out of the low stance, the rising thrust
  Triangle 9      attack5: the leap and the Masamune driven into the ground
  limit           sp1: Crisis Core's Octaslash in two halves (approach and four cuts, then the last three and the finish)
  spells          mag1 start / loop / release
  idle, damage    idle1, dmg1;  victory: his laugh (field clip gnm_laugh)
Everything else (locomotion, guards, dodges, reactions, abilities) stays Sephiroth's own (Battle00 as Battle10).
    make_cc_moves.py <out plan.json>"""
import json
import sys

SET = 'Battle10'
CC = '/Game/Motion/Player/PC0010_16_CrisisCore_Sephiroth/CCRoot/CC_%s'
SEPH = '/Game/Motion/Player/PC0010_Sephiroth/Battle00/'
TR00 = '/Game/Motion/Player/PC0010_Sephiroth_Transform/Battle00/'
BUILD = '/Game/RebirthSkelCompat/Built/SephirothForms'
SE = '/Game/Sound/SE/Character/Player/SE_PC0010_00_Sephiroth_Standard.SE_PC0010_00_Sephiroth_Standard'
TRAIL = '/Game/Effect/Character/Player/PC0010_Sephiroth/Particle/FX_PC0010_Weapon_Trail_01.FX_PC0010_Weapon_Trail_01'

# Crisis Core's sword trail windows per clip (FairAnimNotifyStateTrail: start, end), seconds into the clip
TRAILS = {
    'btm_attack1': [(0.13, 0.30), (0.34, 0.51)],
    'btm_attack2': [(0.28, 0.37), (0.71, 0.86), (1.08, 1.24), (1.76, 1.86)],
    'btm_attack3': [(2.24, 2.37)],
    'btm_attack5': [(0.90, 1.10)],          # (no trail in Crisis Core: the plunge, from its motion)
    'btm_attack6': [(0.62, 0.84)],          # (no trail: the thrust, from its motion)
    'btm_sp1': [(1.57, 1.70), (3.66, 3.80), (3.94, 4.07), (4.43, 4.51), (7.13, 7.34), (8.22, 8.36), (8.42, 8.83)],
}

# name -> (clip, start, end (0: its end), speed, notifies from (None: Sephiroth's Battle00 move of that name), trails used)
MOVES = {
    'B_NAttack01_0': ('btm_attack1', 0.0, 0.0, 1.0, None, None),
    'B_NAttack02_0': ('btm_attack2', 0.0, 0.98, 1.0, None, [0, 1]),
    'B_NAttack03_0': ('btm_attack2', 0.95, 0.0, 1.0, None, [2, 3]),
    'B_NAttack04_0': ('btm_attack3', 0.70, 0.0, 1.25, None, None),
    'B_NPAttack01': ('btm_attack6', 0.0, 0.0, 1.0, None, None),
    'B_SAttack09_0': ('btm_attack5', 0.0, 0.0, 1.0, None, None),
    'B_AtkLimit01_0': ('btm_sp1', 0.0, 6.90, 1.0, None, [0, 1, 2, 3]),
    'B_AtkLimit01_1': ('btm_sp1', 6.90, 0.0, 1.0, None, [4, 5, 6]),
    'B_MagAttack01_0': ('btm_mag1_s', 0.0, 0.0, 1.0, None, []),
    'B_MagAttack01_1': ('btm_mag1_l', 0.0, 0.0, 1.0, None, []),
    'B_MagAttack01_2': ('btm_mag1_e', 0.0, 0.0, 1.0, None, []),
    'B_AtkMag01_0': ('btm_mag1_s', 0.0, 0.0, 1.0, TR00 + 'B_AtkMag01_0', []),
    'B_AtkMag01_1': ('btm_mag1_l', 0.0, 0.0, 1.0, TR00 + 'B_AtkMag01_1', []),
    'B_AtkMag01_2': ('btm_mag1_e', 0.0, 0.0, 1.0, TR00 + 'B_AtkMag01_2', []),
    'B_Idle01_1': ('btm_idle1', 0.0, 0.0, 1.0, None, []),
    'B_Idle01_1_EnemyBook': ('btm_idle1', 0.0, 0.0, 1.0, SEPH + 'B_Idle01_1', []),
    'B_DmgF01': ('btm_dmg1', 0.0, 0.0, 1.0, None, []),
    'B_Win01': ('gnm_laugh', 0.0, 7.5, 1.0, None, []),
}
# blows of moves without trails of their own (seconds into the clip): the spell's release (Crisis Core's event)
BLOWS = {'btm_mag1_e': [1.14]}


def path(p):
    return p if '.' in p.rsplit('/', 1)[-1] else p + '.' + p.rsplit('/', 1)[-1]


def main(out):
    moves, keys = [], {}
    for name, (clip, t0, t1, speed, notifies, use) in MOVES.items():
        trails = TRAILS.get(clip, [])
        if use is not None:
            trails = [trails[k] for k in use]
        inside = [(a, b) for a, b in trails if a >= t0 - 1e-6 and (t1 <= 0 or b <= t1 + 1e-6)]
        blows = [round((a + b) / 2, 3) for a, b in inside] or BLOWS.get(clip, [])
        rel = lambda t: round(max(0.0, (t - t0) / speed), 4)
        m = {'set': SET, 'name': name, 'animation': CC % clip, 'notifies_from': notifies or (SEPH + name),
             'hits': [{'time': rel(b)} for b in blows], 'source': clip}
        if t0 > 0 or t1 > 0:
            m['clip'] = [t0, t1]
        if abs(speed - 1.0) > 1e-6:
            m['speed'] = speed
        extras = []
        for a, b in inside:
            extras.append({'kind': 'effect', 'time': rel(a), 'duration': round(max(0.12, (b - a) / speed + 0.08), 3),
                           'effect': TRAIL, 'socket': 'C_TrailA_b', 'on': 'Weapon1'})
            extras.append({'kind': 'sound', 'time': rel((a + b) / 2), 'bank': SE, 'cue': 'EB0021_sword_swishM', 'attach': 'C_Hip_a'})
        if extras:
            m['extras'] = extras
        m['notes'] = __doc__.split('\n')[0][:0] + clip
        moves.append(m)
        keys[name] = '%s/%s/%s.%s' % (BUILD, SET, name, name)
    plan = {'set': SET, 'moves': moves, 'keys': {SET: keys}}
    json.dump(plan, open(out, 'w'), indent=1)
    for m in moves:
        print('%-22s %-14s clip %-12s speed %-4s hits %s extras %d' % (m['name'], m['source'], m.get('clip', '-'), m.get('speed', 1),
                                                                      [h['time'] for h in m['hits']], len(m.get('extras', []))))


if __name__ == '__main__':
    main(sys.argv[1])
