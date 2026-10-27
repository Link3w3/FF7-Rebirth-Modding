"""Your playable Sephiroth's Safer form (animation pack Battle06): his moves made of Safer Sephiroth's 20 animations
(PC0010_999, imported), for Create a Character System's Build Moves (editor 1.12.1).
  * every name the player's moves ask for (his own Battle00 moves, his limits, synergy, spells, items and summons) is
    built from one of Safer's animations: an attack from one of his five skills (the part around its blow, faster),
    with his own move's gameplay notifies (combo, cancel and dodge windows, damage) lined up on Safer's blows; the
    damage of his blows on hits named PC0010_SF_* (build_safer_data.py: struck from Safer's wing, hand or body),
  * reactions are Safer's damage animations, spells his casting (start, loop, end), dodges, guards and the like pieces
    of his idle (he floats), his death his own,
  * his walks, runs, strafes, their starts, stops and turns: his idle leaning into the root motion of Sephiroth's flying
    locomotion (editor 1.12 "lean"), the loops as long as his idle,
  * every move is built (none plays Safer's animations as they are): the SAFER form turns his model to face the game's
    way and brings it down (its Model Turn and Model Lift), which only built moves carry.
    make_safer_moves.py <out json> (needs forms36/analysis/seph_lengths.json)"""
import json, os, sys

LENGTHS = json.load(open('/work/forms36/analysis/seph_lengths.json'))
SET = 'Battle06'
SF = '/Game/Motion/Player/PC0010_999_Safer_Sephiroth/Battle00/anim_mo572_%s_Rebirth_BindingRepair'
SEPH = '/Game/Motion/Player/PC0010_Sephiroth/Battle00/'
SEPH01 = '/Game/Motion/Player/PC0010_Sephiroth/Battle01/'
CLOUD = '/Game/Motion/Player/PC0000_Cloud/Battle00/'   # (his summoning moves are Cloud's: his own sets have none)
FLY = '/Game/RebirthSkelCompat/Imported/SephirothFlight/FLY_'
# Safer's animations (seconds) and where their blows land
S2, S3, S4, S5, S6 = SF % 'skill_002', SF % 'skill_003', SF % 'skill_004', SF % 'skill_005', SF % 'skill_006'
# 5.90 s (lunge 4.05) / 5.57 s (2.70) / 4.10 s (2.75) / 3.60 s (wing slash 1.65) / 3.70 s (a slow cast, 0.9)
ST1, ST2, ST3, STOP = SF % 'status_001_01', SF % 'status_001_02_lp', SF % 'status_001_03', SF % 'status_stop_001_lp'
# 1.80 s / 3.00 s (loop) / 1.07 s (release 0.4) / a held pose
IDLE = SF % 'idle_001_02_lp'                            # 8.0 s
DMG_F1, DMG_F2 = SF % 'damage_f_001', SF % 'damage_f_002'   # 1.97 / 2.17 s
DMG_L, DMG_R = SF % 'damage_l_001', SF % 'damage_r_001'     # 1.97 s
DIE, DIE_LOOP = SF % 'die_001_01', SF % 'die_001_02_lp'     # 3.13 s / a held pose
ENTER = SF % 'cutscene_boss_enter_01'                   # 8.0 s: he comes down from the sky
LEAN = 18.0                                             # degrees at a run (his idle leaning into Sephiroth's flying locomotion)
SECONDS = {DMG_F1: 1.9667, DMG_F2: 2.1667, DMG_L: 1.9667, DMG_R: 1.9667, IDLE: 8.0}


def path(p):
    return p if '.' in p.rsplit('/', 1)[-1] else p + '.' + p.rsplit('/', 1)[-1]


# attacks: name -> (animation, clip start, clip end (0: its end), speed, blows (seconds into it),
#                   damage of each blow (PC0010_SF_* rows; None: his move's own), notifies from (None: his own of that name))
OCTA = [3.95, 4.0, 4.05, 4.1, 4.15, 4.2, 4.3, 4.45]
ATTACKS = {
    # Square: his wing slash, the left hand twice, the lunge (the air ones the same)
    'B_NAttack01_0': (S5, 1.0, 2.4, 1.4, [1.65], ['PC0010_SF_NAtk_1_01'], None),
    'B_NAttack02_0': (S4, 2.1, 3.6, 1.2, [2.75], ['PC0010_SF_NAtk_2_01'], None),
    'B_NAttack03_0': (S3, 2.1, 3.5, 1.3, [2.70], ['PC0010_SF_NAtk_3_01'], None),
    'B_NAttack04_0': (S2, 3.3, 5.6, 1.0, [4.05], ['PC0010_SF_NAtk_4_01'], None),
    'B_NAttackJ01_0': (S5, 1.1, 2.3, 1.4, [1.65], ['PC0010_SF_JAtk_1_01'], None),
    'B_NAttackJ02_0': (S4, 2.2, 3.4, 1.2, [2.75], ['PC0010_SF_JAtk_2_01'], None),
    'B_NAttackJ03_0': (S3, 2.2, 3.3, 1.3, [2.70], ['PC0010_SF_JAtk_3_01'], None),
    'B_NAttack20_0': (S5, 1.1, 2.5, 1.4, [1.65], ['PC0010_SF_ChainChange01_01'], None),
    # his ranged attack: a burst around him from his slow cast
    'B_NPAttack01': (S6, 0.0, 2.0, 1.2, [0.9], ['PC0010_SF_NPAtk_1_01'], None),
    'B_NPAttackJ01': (S6, 0.0, 2.0, 1.2, [0.9], ['PC0010_SF_NPAtk_1_01'], None),
    # his unique moves
    'B_SAttack01_0': (S2, 2.8, 5.2, 1.0, [4.05], ['PC0010_SF_Satk_1_01'], None),
    'B_SAttack02_0': (S5, 1.1, 2.6, 1.3, [1.65], ['PC0010_SF_Satk_2_01'], None),
    'B_SAttack05_0': (S6, 0.0, 2.5, 1.2, [0.9], None, None),                 # (his counter: a burst around him already)
    'B_SAttack05_0_Comp': (S6, 0.0, 2.5, 1.2, [0.9], None, SEPH + 'B_SAttack05_0'),
    'B_SAttack06_0': (S5, 0.9, 2.9, 1.25, [1.55, 1.65], None, None),
    'B_SAttack07_0': (S4, 2.0, 3.9, 1.2, [2.67, 2.78], None, None),
    'B_SAttack08_0': (S2, 3.6, 4.2, 1.2, [3.9, 4.05], ['PC0010_SF_SAtk_9_01', 'PC0010_SF_SAtk_9_02'], None),
    'B_SAttack08_1': (ST2, 0.0, 0.0, 1.0, [], None, None),
    'B_SAttack08_2': (S3, 2.4, 4.0, 1.1, [2.70], ['PC0010_SF_SAtk_9_03'], None),
    'B_SAttack09_0': (S6, 0.0, 3.2, 1.2, [0.9], None, None),
    'B_SAttack10_0': (S3, 2.2, 4.2, 1.2, [2.6, 2.7, 2.78], ['PC0010_SF_Satk_8_01', 'PC0010_SF_Satk_8_02', 'PC0010_SF_Satk_8_03'], None),
    # his commands (their damage lands on the target)
    'B_AtkBurst01_0': (S4, 1.5, 3.5, 1.2, [2.75], None, None),
    'B_AtkBurst01_1': (S4, 2.5, 4.1, 0.9, [2.75], None, None),
    'B_AtkBurstA01_0': (S4, 1.5, 3.5, 1.2, [2.75], None, None),
    'B_AtkBurstA01_1': (S4, 2.5, 4.1, 0.9, [2.75], None, None),
    'B_AtkBurst02_0': (S2, 1.5, 5.4, 1.2, [4.05], None, None),
    'B_AtkBurst02_1': (S3, 2.2, 5.0, 1.04, [2.70], None, None),
    # limits: Octaslash's eight blows on the target in his lunge, Heartless Angel his descent and his cast, Meteor his cast
    'B_AtkLimit01_0': (S2, 0.0, 0.0, 0.885, OCTA, ['PC0010_SF_Limit_1_%02d' % n for n in range(1, 9)], None),
    'B_AtkLimit01_1': (S5, 0.0, 0.0, 0.84, [1.65], ['PC0010_SF_Satk_6_01'], None),
    'B_AtkLimit02_0': (S2, 0.0, 0.0, 1.0, [4.05], None, SEPH + 'B_AtkLimit01_1'),
    'B_AtkLimit03_0': (S6, 0.0, 0.0, 1.0, [1.0], None, SEPH + 'B_MagAttack01_2'),
    'B_AtkTenshi01_0': (ENTER, 0.0, 4.0, 1.0, [], None, SEPH01 + 'B_AtkTenshi01_0'),
    'B_AtkTenshi01_1': (S6, 0.0, 0.0, 1.0, [0.9], None, SEPH01 + 'B_AtkTenshi01_1'),
    # synergy and parries
    'B_ChainTatakau_A01_0': (S5, 0.0, 1.0, 1.0, [], None, None),
    'B_ChainTatakau_A01_1': (S5, 1.0, 1.9, 1.0, [], None, None),
    'B_ChainTatakau_A01_2': (S5, 1.3, 2.4, 1.0, [1.65], None, None),
    'B_ChainTatakau_A02_0': (S4, 2.2, 3.5, 1.2, [2.67, 2.78], None, None),
    'B_ChainTatakau_A03_0': (S3, 2.0, 4.1, 1.2, [2.6, 2.75], None, None),
    'B_ChainCharge_B01_0': (S6, 0.0, 3.0, 1.2, [0.9], None, None),
    'B_ChainCounter_B02_0': (S2, 3.0, 5.8, 1.0, [4.0, 4.1], None, None),
    'B_BurstChain_00_10_01_0': (S2, 0.0, 0.0, 0.75, [], None, None),
    # spells, healing, items, summons: his casting (start, loop, release)
    'B_MagAttack01_0': (ST1, 0.0, 0.0, 1.0, [], None, None),
    'B_MagAttack01_1': (ST2, 0.0, 0.0, 1.0, [], None, None),
    'B_MagAttack01_2': (ST3, 0.0, 0.0, 1.0, [0.4], None, None),
    'B_MagCure01_0': (ST1, 0.0, 0.0, 1.0, [], None, None),
    'B_MagCure01_1': (ST2, 0.0, 0.0, 1.0, [], None, None),
    'B_MagCure01_2': (ST3, 0.0, 0.0, 1.0, [0.4], None, None),
    'B_Item01': (ST3, 0.0, 0.0, 1.0, [0.4], None, None),
    'B_ItemCure01': (ST3, 0.0, 0.0, 1.0, [0.4], None, None),
    'B_MagSummon01_0': (ST1, 0.0, 0.0, 1.0, [], None, CLOUD + 'B_MagSummon01_0'),
    'B_MagSummon01_1': (ST2, 0.0, 0.0, 1.0, [], None, CLOUD + 'B_MagSummon01_1'),
    'B_MagSummon01_2': (ST3, 0.0, 0.0, 1.0, [], None, CLOUD + 'B_MagSummon01_2'),
    'B_MagSummon01_3': (ST3, 0.3, 0.0, 1.0, [], None, CLOUD + 'B_MagSummon01_3'),
    'B_MagSummon01_4': (ST3, 0.5, 0.0, 1.0, [], None, CLOUD + 'B_MagSummon01_4'),
}
for side, anim, first in (('L', S4, 'PC0010_SF_PAtk_1_01'), ('R', S5, 'PC0010_SF_PAtk_2_01')):
    blow = 2.75 if anim == S4 else 1.65
    for n in range(1, 5):
        ATTACKS['B_ParryAttack%s%02d' % (side, n)] = (anim, blow - 0.7, blow + 0.7, 1.4, [blow], [first] if n == 1 else None, None)

# pieces of an animation as long as his own move of that name (his own's notifies, no blow): name -> Safer animation
PIECES = {}
for name in ['B_DmgF01', 'B_DmgB01', 'B_DmgB02', 'B_DmgF02', 'B_DmgReflect01', 'B_DmgGuard02',
             'B_DmgStrikeB01_0', 'B_DmgStrikeB01_1', 'B_DmgStrikeF01_0', 'B_DmgStrikeF01_1']:
    PIECES[name] = DMG_F1
PIECES['B_DmgL01'] = DMG_L
PIECES['B_DmgR01'] = DMG_R
for name in ['B_DmgF03', 'B_DmgB03', 'B_DmgBlowB01', 'B_DmgBlowF01', 'B_DmgUpperB01', 'B_DmgUpperF01', 'B_DmgDownB01', 'B_DmgDownB02',
             'B_DmgDownB03', 'B_DmgDownF01', 'B_DmgDownF02', 'B_DmgDownF03']:
    for k, anim in enumerate((DMG_F2, IDLE, DMG_F1)):
        PIECES['%s_%d' % (name, k)] = anim
for name in ['B_DmgRecoverB01', 'B_DmgRecoverF01']:
    PIECES[name] = IDLE
PIECES.update({'B_DmgBurst01_0': DMG_F2, 'B_DmgBurst01_1': STOP, 'B_DmgBurst01_2': DMG_F1})
for name in ['B_Avoid01_0', 'B_Avoid01_1', 'B_Avoid01_2', 'B_Avoid02_2', 'B_Guard01_0', 'B_Guard01_1', 'B_Guard01_2',
             'B_GuardFace01_0', 'B_GuardFace01_1', 'B_GuardFace01_2', 'B_GuardFace02_0', 'B_GuardFace02_1', 'B_GuardFace02_2',
             'B_GuardTurn01_L180', 'B_GuardTurn01_L90', 'B_GuardTurn01_R180', 'B_GuardTurn01_R90',
             'B_Idle01_0', 'B_Idle01_2', 'B_Fall01_1', 'B_Fall01_2', 'B_StepAB01', 'B_StepB01', 'B_Run01_Up',
             'B_ChainWait01_0', 'B_ChainWait01_1', 'B_ChainWait01_2', 'B_Abnormal01_0', 'B_Abnormal01_2',
             'B_DownAbnormalB01_0', 'B_DownAbnormalF01_0']:
    PIECES[name] = IDLE
PIECES['B_Abnormal01_1'] = STOP
# whole animations: name -> (Safer animation, his move the notifies come from)
WHOLE = {'B_Idle01_1': (IDLE, SEPH + 'B_Idle01_1'), 'B_Idle01_1_EnemyBook': (IDLE, SEPH + 'B_Idle01_1'), 'B_Win01': (ENTER, SEPH + 'B_Win01'),
         'B_Die01_0': (DIE, SEPH + 'B_Die01_0'), 'B_Die01_1': (DIE_LOOP, SEPH + 'B_Die01_1'), 'B_Die01_2': (DIE_LOOP, SEPH + 'B_Die01_2'),
         'B_DownDieB01': (DIE, SEPH + 'B_DownDieB01'), 'B_DownDieF01': (DIE, SEPH + 'B_DownDieF01')}
# his movement: the flight's root motion, leaning his idle (the loops as long as his idle)
MOVEMENT = sorted(n for n in LENGTHS if n.startswith(('B_Walk', 'B_Run', 'B_Turn')) and n not in ('B_Run01_Up',))
LOOPS = {n for n in MOVEMENT if n.endswith('01_1') and not n.endswith(('_L180', '_R180'))}


def main(out):
    moves = []
    seen = set()

    def add(m):
        assert m['name'] not in seen, m['name']
        seen.add(m['name'])
        m['set'] = SET
        moves.append(m)
    for name, (anim, start, end, speed, blows, damage, notifies) in ATTACKS.items():
        hits = []
        for k, t in enumerate(blows):
            hit = {'time': round(max(0.0, (t - start) / speed), 4)}
            if damage:
                hit['damage'] = damage[k]
            hits.append(hit)
        m = {'name': name, 'animation': path(anim), 'build': True, 'notifies_from': path(notifies or (SEPH + name)), 'hits': hits}
        if start > 0 or end > 0:
            m['clip'] = [start, end]
        if speed != 1.0:
            m['speed'] = speed
        add(m)
    for name in MOVEMENT:
        add({'name': name, 'animation': path(FLY + name), 'build': True, 'notifies_from': path(SEPH + name), 'hits': [],
             'retarget': 'lean', 'base': path(IDLE), 'base_loop': name in LOOPS, 'lean_bone': 'Trans', 'lean': LEAN})
    for name, (anim, notifies) in sorted(WHOLE.items()):
        add({'name': name, 'animation': path(anim), 'build': True, 'notifies_from': path(notifies), 'hits': []})
    for name, anim in sorted(PIECES.items()):
        if name in seen:
            continue
        length = LENGTHS.get(name)
        if not length:
            continue   # (not one of his)
        m = {'name': name, 'animation': path(anim), 'build': True, 'notifies_from': path(SEPH + name), 'hits': []}
        if anim in SECONDS and length > SECONDS[anim]:
            m['speed'] = round(SECONDS[anim] / length, 4)   # (longer than his animation: all of it, a little slower)
        elif anim not in (STOP, DIE_LOOP):
            m['clip'] = [0.0, round(length, 4)]
        add(m)
    plan = {'set': SET, 'sources': [], 'moves': moves, 'built': sum(1 for m in moves if m['build']), 'as_is': 0}
    json.dump(plan, open(out, 'w'), indent=1)
    names = {m['name'] for m in moves}
    missing = sorted(n for n in LENGTHS if n not in names)
    print('%d moves (%d attacks, %d movement, %d whole, %d pieces) -> %s; his names left out: %s' % (
        len(moves), len(ATTACKS), len(MOVEMENT), len(WHOLE), len(moves) - len(ATTACKS) - len(MOVEMENT) - len(WHOLE), out, missing or 'none'))


if __name__ == '__main__':
    main(sys.argv[1])
