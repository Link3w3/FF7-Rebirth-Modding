"""Young Sephiroth (the YOUNG SEPHIROTH form, animation pack Battle07): his moves for Create a Character System's Build
Moves, built on CH049_001_Skeleton from
  * his own 96 Ever Crisis clips (/Game/Motion/Player/CH049_001/anim_ch049_*): every attack, ability and limit a part of
    one of his skills around its blows (the blade sweeping through what is in front of him, found from his motion), at a
    speed that keeps the blow about where Sephiroth's lands; his casting, items and summons his chants; his idle, run,
    backstep, damage, knockdown, death and victory his own;
  * Sephiroth's own animations retargeted onto him (/Game/Motion/Player/CH049_001/FromSephiroth/YS_*, made by
    retarget_from_seph.py) for what he has no clip of: walks, turning runs, turns, guards, dodges, falls, knock-ups and
    the rest of the reactions;
each with the gameplay notifies of Sephiroth's move of that name (combo, cancel and dodge windows, damage on the
Masamune, trails, sounds), his hits lined up on Young Sephiroth's blows.
    make_ys_moves.py <out json>"""
import json, sys

SET = 'Battle07'
YS = '/Game/Motion/Player/CH049_001/anim_ch049_%s'
FROM = '/Game/Motion/Player/CH049_001/FromSephiroth/YS_%s'
SEPH = '/Game/Motion/Player/PC0010_Sephiroth/Battle00/'
SEPH01 = '/Game/Motion/Player/PC0010_Sephiroth/Battle01/'
SEPHC = '/Game/Motion/Player/PC0010_Sephiroth/Battle00_Comp/'
TR00 = '/Game/Motion/Player/PC0010_Sephiroth_Transform/Battle00/'
TR01 = '/Game/Motion/Player/PC0010_Sephiroth_Transform/Battle01/'
CLOUD = '/Game/Motion/Player/PC0000_Cloud/Battle00/'
LENGTHS = json.load(open('/work/forms36/analysis/seph_lengths.json'))


def path(p):
    return p if '.' in p.rsplit('/', 1)[-1] else p + '.' + p.rsplit('/', 1)[-1]


# name -> (his clip, clip start, clip end (0: its end), speed, blows (seconds into the clip), notifies from (None: Sephiroth's
# Battle00 move of that name))
ATTACKS = {
    # Square: skill_003's three slashes (his Ever Crisis attack), then skill_013's drawn cut into the low stance
    'B_NAttack01_0': ('skill_003', 0.60, 1.30, 1.15, [0.77], None),
    'B_NAttack02_0': ('skill_003', 1.25, 2.05, 1.0, [1.40], None),
    'B_NAttack03_0': ('skill_003', 2.08, 3.00, 1.0, [2.27], None),
    'B_NAttack04_0': ('skill_013', 3.55, 5.70, 1.0, [4.03], None),
    'B_NAttack20_0': ('skill_030', 2.10, 3.10, 1.0, [2.33], None),
    # in the air: skill_007's two cuts, skill_038's rising one
    'B_NAttackJ01_0': ('skill_007', 0.92, 1.55, 1.0, [1.07], None),
    'B_NAttackJ02_0': ('skill_007', 1.48, 2.30, 1.0, [1.60], None),
    'B_NAttackJ03_0': ('skill_038', 2.45, 3.30, 1.0, [2.77], None),
    # his ranged attack (the wave leaves from his sword)
    'B_NPAttack01': ('skill_027', 2.80, 4.30, 1.0, [3.07], None),
    'B_NPAttackJ01': ('skill_023', 2.42, 3.90, 1.0, [2.70], None),
    # Triangle and his other unique moves
    'B_SAttack01_0': ('skill_026', 1.95, 4.30, 1.0, [3.00], None),            # the dash and the cut through
    'B_SAttack02_0': ('skill_009', 0.72, 1.85, 1.0, [0.90], None),            # (Sword Dance too)
    'B_SAttack05_0': ('skill_008', 0.55, 2.62, 1.0, [1.37], None),            # the low stance and the cut out of it
    'B_SAttack05_0_Comp': ('skill_008', 0.55, 2.62, 1.0, [1.37], SEPHC + 'B_SAttack05_0_Comp'),
    'B_SAttack06_0': ('skill_038', 2.25, 3.65, 1.0, [2.50, 2.77], None),
    'B_SAttack07_0': ('skill_007', 0.92, 2.30, 1.2, [1.07, 1.60], None),
    'B_SAttack08_0': ('skill_028', 1.73, 2.45, 1.45, [1.83, 2.40], None),
    'B_SAttack08_1': ('skill_028', 2.85, 3.85, 1.0, [2.93], None),
    'B_SAttack08_2': ('skill_031', 2.55, 3.98, 1.0, [2.60], None),
    'B_SAttack09_0': ('skill_020', 2.10, 4.75, 1.0, [3.13], None),            # the leap and the plunge
    'B_SAttack10_0': ('skill_012', 1.05, 2.75, 1.2, [1.27, 1.77, 2.30], None),   # three cuts, stepping in
    # his commands
    'B_AtkBurst01_0': ('skill_037', 2.30, 3.75, 1.15, [2.53, 3.07], None),
    'B_AtkBurstA01_0': ('skill_037', 2.30, 3.75, 1.15, [2.53, 3.07], None),
    'B_AtkBurst01_1': ('skill_024', 2.50, 4.30, 1.0, [3.00], None),            # (Zanshin Rising)
    'B_AtkBurstA01_1': ('skill_024', 2.50, 4.30, 1.0, [3.00], None),
    'B_AtkBurst02_0': ('skill_014', 3.05, 6.30, 1.0, [4.03], None),            # the sword driven into the ground
    'B_AtkBurst02_1': ('skill_032', 2.95, 5.65, 1.0, [3.23], None),            # (Infernal Gate)
    'B_AtkStab01': ('skill_011', 1.75, 5.15, 1.0, [3.07], TR01 + 'B_AtkStab01'),   # (Warp Stab: the dash and the cut)
    # limits: Octaslash his eight-blow flurry, Octaslash Prime the dive, level 2 the other flurry then the drawn cut,
    # Meteor his sword raised to the sky
    'B_AtkLimit01_0': ('skill_036', 0.0, 0.0, 0.85, [1.10, 2.13, 2.43, 2.53, 2.97, 3.47, 4.27, 4.63], None),
    'B_AtkLimit01_1': ('skill_029', 1.65, 5.90, 1.0, [2.93], None),
    'B_AtkLimit02_0': ('skill_033', 0.0, 0.0, 0.85, [0.70, 1.17, 2.17, 2.47, 2.63, 2.97, 3.67, 4.10], TR01 + 'B_AtkLimit02_0'),
    'B_YSLimit02_1': ('skill_013', 2.80, 0.0, 1.0, [4.03], TR01 + 'B_AtkLimit02_1'),
    'B_AtkLimit03_0': ('skill_015', 1.40, 4.30, 1.0, [1.75], SEPH + 'B_MagAttack01_2'),
    'B_AtkTenshi01_0': ('skill_021', 1.40, 3.40, 1.0, [], SEPH01 + 'B_AtkTenshi01_0'),
    'B_AtkTenshi01_1': ('skill_005', 0.0, 0.0, 0.95, [1.55, 2.74], SEPH01 + 'B_AtkTenshi01_1'),
    # synergy
    'B_ChainTatakau_A01_0': ('run_001_01', 0.0, 0.0, 1.0, [], None),
    'B_ChainTatakau_A01_1': ('run_001_02_lp', 0.0, 0.0, 1.0, [], None),
    'B_ChainTatakau_A01_2': ('skill_031', 0.58, 1.68, 1.0, [0.70], None),
    'B_ChainTatakau_A02_0': ('skill_038', 2.42, 3.60, 1.0, [2.50, 2.77], None),
    'B_ChainTatakau_A03_0': ('skill_032', 2.38, 4.20, 1.0, [2.53, 3.23], None),
    'B_ChainCharge_B01_0': ('skill_016', 2.23, 4.73, 1.0, [3.10], None),
    'B_ChainCounter_B02_0': ('skill_018', 2.80, 5.00, 0.8, [2.87, 3.60], None),
    'B_BurstChain_00_10_01_0': ('skill_035', 0.0, 0.0, 0.757, [0.23, 0.67, 0.97, 1.47, 2.07, 3.00, 3.53, 3.77, 4.80], None),
    # dodge and parry counters
    'B_Avoid01_2': ('skill_009', 0.85, 1.68, 1.0, [0.90], None),
    'B_Avoid02_2': ('skill_038', 2.72, 3.15, 1.0, [2.77], None),
    # spells, healing, items, summons: his chants (start, loop, release)
    'B_MagAttack01_0': ('chant_001_01', 0.0, 0.0, 1.0, [], None),
    'B_MagAttack01_1': ('chant_001_02_lp', 0.0, 0.0, 1.0, [], None),
    'B_MagAttack01_2': ('chant_001_03', 0.0, 0.0, 1.0, [0.36], None),
    'B_MagCure01_0': ('chant_002_01', 0.0, 0.0, 1.0, [], None),
    'B_MagCure01_1': ('chant_002_02_lp', 0.0, 0.0, 1.0, [], None),
    'B_MagCure01_2': ('chant_002_03', 0.0, 0.0, 1.0, [0.30], None),
    'B_AtkMag01_0': ('chant_002_01', 0.0, 0.0, 1.0, [], TR00 + 'B_AtkMag01_0'),
    'B_AtkMag01_1': ('chant_002_02_lp', 0.0, 0.0, 1.0, [], TR00 + 'B_AtkMag01_1'),
    'B_AtkMag01_2': ('chant_002_03', 0.0, 0.0, 1.0, [0.30], TR00 + 'B_AtkMag01_2'),
    'B_Item01': ('5star_001_01', 0.0, 0.0, 1.0, [0.74], None),
    'B_ItemCure01': ('5star_001_01', 0.0, 0.0, 1.0, [0.83], None),
    'B_MagSummon01_0': ('status_001_01', 0.0, 0.0, 0.42, [], CLOUD + 'B_MagSummon01_0'),
    'B_MagSummon01_1': ('status_001_02_lp', 0.0, 0.0, 1.0, [], CLOUD + 'B_MagSummon01_1'),
    'B_MagSummon01_2': ('status_001_03', 0.0, 0.0, 0.36, [], CLOUD + 'B_MagSummon01_2'),
    'B_MagSummon01_3': ('status_001_02_lp', 0.0, 0.0, 1.5, [], CLOUD + 'B_MagSummon01_3'),
    'B_MagSummon01_4': ('status_001_03', 0.20, 0.0, 1.0, [], CLOUD + 'B_MagSummon01_4'),
    # his own idle, run, backstep, reactions, death, victory
    'B_Idle01_0': ('idle_001_01', 0.0, 0.0, 1.0, [], None),
    'B_Idle01_1': ('idle_001_02_lp', 0.0, 0.0, 1.0, [], None),
    'B_Idle01_1_EnemyBook': ('idle_001_02_lp', 0.0, 0.0, 1.0, [], SEPH + 'B_Idle01_1'),
    'B_Run01_0_L0': ('run_001_01', 0.0, 0.0, 1.0, [], None),
    'B_Run01_1': ('run_001_02_lp', 0.0, 0.0, 1.0, [], None),
    'B_Run01_2l': ('run_001_03', 0.0, 0.0, 1.0, [], None),
    'B_Run01_2r': ('run_001_03', 0.0, 0.0, 1.0, [], None),
    'B_StepB01': ('longstep_b_001_01', 0.0, 0.0, 0.73, [], None),
    'B_StepAB01': ('longstep_b_001_01', 0.0, 0.0, 0.73, [], None),
    'B_DmgF01': ('damage_f_001', 0.0, 0.0, 1.0, [], None),
    'B_DmgL01': ('damage_l_001', 0.0, 0.0, 1.0, [], None),
    'B_DmgR01': ('damage_r_001', 0.0, 0.0, 1.0, [], None),
    'B_DmgF02': ('damage_f_002', 0.0, 0.0, 1.0, [], None),
    'B_DmgF03_0': ('damage_f_003_01', 0.0, 0.0, 1.0, [], None),
    'B_DmgF03_1': ('damage_f_003_02_lp', 0.0, 0.0, 1.0, [], None),
    'B_DmgF03_2': ('damage_f_003_03', 0.0, 0.0, 1.0, [], None),
    'B_Die01_0': ('die_001_01', 0.0, 0.0, 1.0, [], None),
    'B_Die01_1': ('die_001_02_lp', 0.0, 0.0, 1.0, [], None),
    'B_Die01_2': ('die_001_03', 0.0, 0.0, 1.0, [], None),
    'B_Win01': ('win_001_01', 0.0, 0.0, 1.0, [], None),
}
for side, (clip, t0, t1, blow) in (('L', ('skill_030', 2.28, 3.60, 2.33)), ('R', ('skill_023', 2.65, 3.98, 2.70))):
    for n in range(1, 5):
        ATTACKS['B_ParryAttack%s%02d' % (side, n)] = (clip, t0, t1, 1.0, [blow], None)
ATTACKS['B_ParryAttackL01'] = ('skill_016', 3.05, 4.00, 1.0, [3.10], None)
ATTACKS['B_ParryAttackR01'] = ('skill_027', 3.02, 4.00, 1.0, [3.07], None)
# level 2's second part, chained after B_AtkLimit02_0 in the compat file (as Sephiroth's Battle00 plays the transformed
# Sephiroth's two halves)
CHAINS = {'B_AtkLimit02_0': ['B_YSLimit02_1']}
# the rest of his moves: Sephiroth's own, retargeted onto Young Sephiroth (his name for each)
FROM_SEPH = sorted(n for n in LENGTHS if n not in ATTACKS and not n.endswith('_Add'))


def main(out):
    moves = []
    for name, (clip, t0, t1, speed, blows, notifies) in ATTACKS.items():
        m = {'name': name, 'set': SET, 'animation': path(YS % clip), 'build': True,
             'notifies_from': path(notifies or (SEPH + name)),
             'hits': [{'time': round(max(0.0, (b - t0) / speed), 4)} for b in blows]}
        if t0 > 0 or t1 > 0:
            m['clip'] = [t0, t1]
        if abs(speed - 1.0) > 1e-6:
            m['speed'] = speed
        m['source'] = clip
        moves.append(m)
    for name in FROM_SEPH:
        moves.append({'name': name, 'set': SET, 'animation': path(FROM % name), 'build': True, 'notifies_from': path(SEPH + name),
                      'hits': [], 'retarget': 'as_is', 'source': 'Sephiroth'})
    names = [m['name'] for m in moves]
    assert len(names) == len(set(names))
    missing = sorted(n for n in LENGTHS if n not in names and not n.endswith('_Add'))
    plan = {'set': SET, 'moves': moves, 'chains': CHAINS, 'from_seph': FROM_SEPH,
            'describe': sorted({m['notifies_from'] for m in moves})}
    json.dump(plan, open(out, 'w'), indent=1)
    print('%d moves (%d from his clips, %d of Sephiroth retargeted); Sephiroth\'s names left out: %s' % (
        len(moves), len(ATTACKS), len(FROM_SEPH), missing or 'none'))


if __name__ == '__main__':
    main(sys.argv[1])
