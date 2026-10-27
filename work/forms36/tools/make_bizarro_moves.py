"""Your playable Sephiroth's Bizarro form (animation pack Battle05): his moves made of Bizarro Sephiroth's animations, for
Create a Character System's Build Moves (editor 1.11: clips and speed).
  * Battle05's sets are Bizarro's own (his Battle00, Battle01 and their composites), so his attacks keep their names
    (the PC0010_BZ_* commands play them as the boss does),
  * every name the player's moves ask for (his 150 of the winged form, and his guards, synergy and status animations)
    is built from a Bizarro animation: an attack from one of Bizarro's (the part around its blow, faster), with his own
    move's gameplay notifies (combo, cancel and dodge windows, damage) lined up on Bizarro's blows; the damage of his
    blows on hits named PC0010_BZ_* (built by build_forms36_data.py: struck from Bizarro's wings, sword or body);
    reactions, dodges, guards and his walks and runs are pieces of Bizarro's idle (he floats) as long as his own,
  * a few play Bizarro's animations as they are (his loops, his death).
    make_bizarro_moves.py <out json> (needs ../analysis/seph_lengths.json)"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
LENGTHS = json.load(open(os.path.join(HERE, '..', 'analysis', 'seph_lengths.json')))
SET = 'Battle05'
B00 = '/Game/Motion/Enemy/EB2210_BizarroSephiroth/Battle00/'
B01 = '/Game/Motion/Enemy/EB2210_BizarroSephiroth/Battle01/'
B00C = '/Game/Motion/Enemy/EB2210_BizarroSephiroth/Battle00_Comp/'
SEPH = '/Game/Motion/Player/PC0010_Sephiroth/Battle00/'
SEPH01 = '/Game/Motion/Player/PC0010_Sephiroth/Battle01/'
SOURCES = [B00[:-1] + '.Battle00', '/Game/Motion/Enemy/EB2210_BizarroSephiroth/Battle00_Comp.Battle00_Comp',
           B01[:-1] + '.Battle01', '/Game/Motion/Enemy/EB2210_BizarroSephiroth/Battle01_Comp.Battle01_Comp']
# Bizarro's animations stored as ACL Quat_128 (whole quaternions): Build Moves cannot sample them (the editor's ACL plugin
# stops on them; editor 1.10.3 refuses them), so no move is made from one (checked on the PC's project, 2026-10-15)
QUAT_128 = {B00 + n for n in ('B_AtkEnergyChargeR01_2', 'B_AtkMagA01_0', 'B_AtkMagA01_2', 'B_AtkMagA02_2', 'B_AtkMagB01_2',
                              'B_P2FASyncAction01')} | {B01 + n for n in ('B_AtkMagC01_1', 'B_AtkStigma01_0')}
CLOUD = '/Game/Motion/Player/PC0000_Cloud/Battle00/'   # (his summoning moves are Cloud's: his own sets have none)
IDLE = B00 + 'B_Idle01_1'      # 4.0 s
IDLE2 = B00 + 'B_Idle02_1'


def path(p):
    return p if '.' in p.rsplit('/', 1)[-1] else p + '.' + p.rsplit('/', 1)[-1]


# attacks: name -> (Bizarro animation, clip start, clip end (0: its end), speed, Bizarro's blows (seconds into it),
#                   damage of each blow (PC0010_BZ_* rows; None: his move's own), notifies from (None: his own of that name))
WR, WL = B01 + 'B_AtkWingSwingR01', B01 + 'B_AtkWingSwingL01'   # 5.333 s, blow 1.923
Z0, Z1 = B00 + 'B_AtkZanShin01_0', B00 + 'B_AtkZanShin01_1'      # 5.067 s, blows 1.928 2.724 / 3.1 s, blow 1.229
G0, G1 = B00 + 'B_AtkGokumon01_0', B00 + 'B_AtkGokumon01_1'      # 3.0 s / 3.167 s, blow 0.504
WB = B00 + 'B_AtkWindBlow01'                                      # 5.5 s, blow 1.628
SR = B00 + 'B_AtkWingSmashR01'                                    # 10 s, blow 2.621
O0, O1, O2 = B00 + 'B_AtkOmniSlash01_0', B00 + 'B_AtkOmniSlash01_1', B00 + 'B_AtkOmniSlash01_2'
OMNI = [0.815, 1.13, 1.384, 1.522, 1.741, 2.083, 2.355, 3.178]  # Octaslash's eight blows
ATTACKS = {
    # Square: right wing, left wing, his conjured sword, Hell's Gate's strike (the air ones the same)
    'B_NAttack01_0': (WR, 1.0, 3.0, 1.5, [1.923], ['PC0010_BZ_NAtk_1_01'], None),
    'B_NAttack02_0': (WL, 1.0, 3.0, 1.5, [1.923], ['PC0010_BZ_NAtk_2_01'], None),
    'B_NAttack03_0': (Z1, 0.4, 2.4, 1.4, [1.229], ['PC0010_BZ_NAtk_3_01'], None),
    'B_NAttack04_0': (G1, 0.0, 2.2, 1.2, [0.504], ['PC0010_BZ_NAtk_4_01'], None),
    'B_NAttackJ01_0': (WR, 1.0, 3.0, 1.5, [1.923], ['PC0010_BZ_JAtk_1_01'], None),
    'B_NAttackJ02_0': (WL, 1.0, 3.0, 1.5, [1.923], ['PC0010_BZ_JAtk_2_01'], None),
    'B_NAttackJ03_0': (Z1, 0.4, 2.4, 1.4, [1.229], ['PC0010_BZ_JAtk_3_01'], None),
    'B_NAttack20_0': (WR, 1.0, 3.0, 1.5, [1.923], ['PC0010_BZ_ChainChange01_01'], None),
    # his ranged attack: Maelstrom's burst around him
    'B_NPAttack01': (WB, 0.8, 3.0, 1.2, [1.628], ['PC0010_BZ_NPAtk_1_01'], None),
    'B_NPAttackJ01': (WB, 0.8, 3.0, 1.2, [1.628], ['PC0010_BZ_NPAtk_1_01'], None),
    # his unique moves
    'B_SAttack01_0': (Z0, 0.8, 3.4, 1.3, [1.928, 2.724], ['PC0010_BZ_Satk_1_01', 'PC0010_BZ_Satk_1_01'], None),
    'B_SAttack02_0': (SR, 1.6, 3.6, 1.3, [2.621], ['PC0010_BZ_Satk_2_01'], None),
    'B_SAttack05_0': (WB, 0.8, 3.0, 1.2, [1.628], None, None),              # (his counter: a burst around him already)
    'B_SAttack05_0_Comp': (WB, 0.8, 3.0, 1.2, [1.628], None, SEPH + 'B_SAttack05_0'),
    'B_SAttack06_0': (WR, 1.0, 3.0, 1.5, [1.75, 1.923], None, None),        # (Shift Slash: bursts around him)
    'B_SAttack07_0': (WL, 1.0, 3.0, 1.5, [1.75, 1.923], None, None),
    'B_SAttack08_0': (O0, 0.0, 1.0, 1.0, [0.3, 0.6], ['PC0010_BZ_SAtk_9_01', 'PC0010_BZ_SAtk_9_02'], None),
    'B_SAttack08_1': (O1, 0.0, 0.0, 1.0, [], None, None),
    'B_SAttack08_2': (G1, 0.0, 1.43, 1.0, [0.504], ['PC0010_BZ_SAtk_9_03'], None),
    'B_SAttack09_0': (WB, 0.8, 3.6, 1.2, [1.628], None, None),
    'B_SAttack10_0': (O2, 0.7, 2.4, 1.0, [0.815, 1.13, 1.384], ['PC0010_BZ_Satk_8_01', 'PC0010_BZ_Satk_8_02', 'PC0010_BZ_Satk_8_03'], None),
    # his normal form's commands (not his commands in this form; here for anything that plays them)
    'B_AtkBurst01_0': (Z0, 0.8, 2.4, 1.2, [1.928], None, None),
    'B_AtkBurst01_1': (Z0, 2.3, 4.2, 1.2, [2.724], None, None),
    'B_AtkBurstA01_0': (Z0, 0.8, 2.4, 1.2, [1.928], None, None),
    'B_AtkBurstA01_1': (Z0, 2.3, 4.2, 1.2, [2.724], None, None),
    'B_AtkBurst02_0': (G0, 0.0, 0.0, 1.0, [2.6], None, None),
    'B_AtkBurst02_1': (G1, 0.0, 2.7, 1.0, [0.504], None, None),
    # limits: Octaslash is Bizarro's (its eight blows on the target, like his), Heartless Angel his angel, Meteor his
    # summoning cast
    'B_AtkLimit01_0': (O2, 0.0, 0.0, 1.0, OMNI, ['PC0010_BZ_Limit_1_%02d' % n for n in range(1, 9)], None),
    'B_AtkLimit01_1': (O2, 0.5, 4.5, 1.0, [0.815], ['PC0010_BZ_Satk_6_01'], None),
    'B_AtkLimit03_0': (B01 + 'B_AtkMagC01_2', 0.0, 0.0, 1.0, [1.0], None, SEPH + 'B_MagAttack01_2'),
    'B_AtkTenshi01_0': (B00 + 'B_AtkAngel01_0', 0.0, 0.0, 1.0, [], None, SEPH01 + 'B_AtkTenshi01_0'),
    'B_AtkTenshi01_1': (B00 + 'B_AtkAngel01_2', 0.0, 0.0, 1.0, [0.71], None, SEPH01 + 'B_AtkTenshi01_1'),
    # synergy and parries
    'B_ChainTatakau_A01_0': (WR, 0.0, 1.0, 1.0, [], None, None),
    'B_ChainTatakau_A01_1': (WR, 1.0, 1.9, 1.0, [], None, None),
    'B_ChainTatakau_A01_2': (WR, 1.6, 3.2, 1.0, [1.923], None, None),
    'B_ChainTatakau_A02_0': (WL, 1.0, 3.0, 1.5, [1.75, 1.923], None, None),
    'B_ChainTatakau_A03_0': (Z0, 0.8, 3.4, 1.3, [1.928, 2.724], None, None),
    'B_ChainCharge_B01_0': (WB, 0.6, 3.4, 1.1, [1.628], None, None),
    'B_ChainCounter_B02_0': (Z0, 0.8, 3.4, 1.0, [1.928, 2.724], None, None),
    'B_BurstChain_00_10_01_0': (O2, 0.0, 0.0, 0.8, [], None, None),
    # spells, healing, items, summons: Bizarro's spellcasting and healing
    'B_MagAttack01_0': (B00 + 'B_AtkMagA01_1', 0.0, 1.0, 1.0, [], None, None),   # (B_AtkMagA01_0 is Quat_128: its loop's start)
    'B_MagAttack01_1': (B00 + 'B_AtkMagA01_1', 0.0, 0.0, 1.0, [], None, None),
    'B_MagAttack01_2': (B00 + 'B_AtkMagA01_4', 0.0, 0.0, 1.0, [0.4], None, None),
    'B_MagCure01_0': (B00 + 'B_AtkWingHeal01_0', 0.0, 1.0, 1.0, [], None, None),
    'B_MagCure01_1': (B00 + 'B_AtkWingHeal01_1', 0.0, 0.0, 1.0, [], None, None),
    'B_MagCure01_2': (B00 + 'B_AtkWingHeal01_2', 0.0, 0.0, 1.0, [0.5], None, None),
    'B_Item01': (B00 + 'B_AtkMagA01_1', 0.0, 1.0, 1.0, [0.42], None, None),
    'B_ItemCure01': (B00 + 'B_AtkMagA01_1', 0.0, 1.0, 1.0, [0.42], None, None),
    'B_MagSummon01_0': (B01 + 'B_AtkMagC01_0', 0.0, 0.0, 1.0, [], None, CLOUD + 'B_MagSummon01_0'),
    'B_MagSummon01_1': (B00 + 'B_AtkMagA01_1', 0.0, 0.0, 1.0, [], None, CLOUD + 'B_MagSummon01_1'),   # (B_AtkMagC01_1 is Quat_128)
    'B_MagSummon01_2': (B01 + 'B_AtkMagC01_2', 0.0, 0.0, 1.0, [], None, CLOUD + 'B_MagSummon01_2'),
    'B_MagSummon01_3': (B01 + 'B_AtkMagC01_2', 1.0, 0.0, 1.0, [], None, CLOUD + 'B_MagSummon01_3'),
    'B_MagSummon01_4': (B01 + 'B_AtkMagC01_2', 1.5, 0.0, 1.0, [], None, CLOUD + 'B_MagSummon01_4'),
}
for side, anim in (('L', WL), ('R', WR)):
    for n in range(1, 5):
        ATTACKS['B_ParryAttack%s%02d' % (side, n)] = (anim, 1.4, 3.0, 1.6, [1.923], None, None)

# pieces of an animation as long as his own move of that name (his own's notifies, no blow): name -> Bizarro animation
SMALL_HIT = B00 + 'B_DmgF01'     # 1.333 s
BIG_HIT = [B00 + 'B_DmgF03_0', B00 + 'B_DmgF03_1', B00 + 'B_DmgF03_2']   # 2 / 4 / 2 s
PIECES = {}
for name in ['B_DmgF01', 'B_DmgB01', 'B_DmgB02', 'B_DmgL01', 'B_DmgR01', 'B_DmgF02', 'B_DmgReflect01', 'B_DmgGuard02',
             'B_DmgStrikeB01_0', 'B_DmgStrikeB01_1', 'B_DmgStrikeF01_0', 'B_DmgStrikeF01_1']:
    PIECES[name] = SMALL_HIT
for name in ['B_DmgF03', 'B_DmgB03', 'B_DmgBlowB01', 'B_DmgBlowF01', 'B_DmgUpperB01', 'B_DmgUpperF01', 'B_DmgDownB01', 'B_DmgDownB02',
             'B_DmgDownB03', 'B_DmgDownF01', 'B_DmgDownF02', 'B_DmgDownF03']:
    for k in range(3):
        PIECES['%s_%d' % (name, k)] = BIG_HIT[k]
for name in ['B_DmgRecoverB01', 'B_DmgRecoverF01']:
    PIECES[name] = BIG_HIT[2]
for k in range(3):
    PIECES['B_DmgBurst01_%d' % k] = B00 + 'B_DmgBurst01_%d' % k
for name in ['B_Avoid01_0', 'B_Avoid01_1', 'B_Avoid01_2', 'B_Avoid02_2', 'B_Guard01_0', 'B_Guard01_1', 'B_Guard01_2',
             'B_GuardFace01_0', 'B_GuardFace01_1', 'B_GuardFace01_2', 'B_GuardFace02_0', 'B_GuardFace02_1', 'B_GuardFace02_2',
             'B_GuardTurn01_L180', 'B_GuardTurn01_L90', 'B_GuardTurn01_R180', 'B_GuardTurn01_R90',
             'B_Idle01_0', 'B_Idle01_2', 'B_Fall01_1', 'B_Fall01_2', 'B_StepAB01', 'B_StepB01', 'B_Run01_Up',
             'B_ChainWait01_0', 'B_ChainWait01_1', 'B_ChainWait01_2', 'B_Abnormal01_0', 'B_Abnormal01_1', 'B_Abnormal01_2',
             'B_DownAbnormalB01_0', 'B_DownAbnormalF01_0']:
    PIECES[name] = IDLE
for name in LENGTHS:
    if name.startswith(('B_Walk', 'B_Run', 'B_Turn', 'B_StrafingWalk')) and not name.endswith('_1') and name not in ('B_Walk01_1',):
        PIECES.setdefault(name, IDLE)
# as they are (his loops, his death, his win): name -> Bizarro animation
AS_IS = {name: IDLE for name in LENGTHS if name.startswith(('B_Walk', 'B_Run', 'B_StrafingWalk')) and name.endswith('_1')}
AS_IS.update({'B_Idle01_1_EnemyBook': IDLE, 'B_Win01': IDLE2, 'B_Die01_0': B00 + 'B_Die01_0', 'B_Die01_1': B00 + 'B_DmgPhase1Down01_1',
              'B_Die01_2': B00 + 'B_DmgPhase1Down01_2', 'B_DownDieB01': B00 + 'B_DmgDownCore01_0', 'B_DownDieF01': B00 + 'B_DmgDownCore01_0'})
for name in ('B_Run01_1_L180', 'B_Run01_1_R180'):   # (turns while running: pieces)
    AS_IS.pop(name, None)
    PIECES[name] = IDLE
# chains played one after another in game (Hell's Gate and Unholy Gate: the boss plays them as two abilities)
CHAINS = {
    'B_AtkHellsGate01': [B00C + 'B_AtkGokumonShort', G1],
    'B_AtkUnholyGate01': [B00C + 'B_AtkGokumonLong', G1],
    'B_AtkLimit02_0': [O0, O2],
}


def main(out):
    moves = []
    seen = set()

    def add(m):
        assert m['name'] not in seen, m['name']
        assert not (m['build'] and m['animation'].rsplit('.', 1)[0] in QUAT_128), (m['name'], 'is made from a Quat_128 animation')
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
    for name, anim in sorted(PIECES.items()):
        if name in seen:
            continue
        length = LENGTHS.get(name)
        if not length:
            continue   # (not one of his: B_DmgDownB01 has no _1)
        add({'name': name, 'animation': path(anim), 'build': True, 'notifies_from': path(SEPH + name), 'hits': [], 'clip': [0.0, round(length, 4)]})
    for name, anim in sorted(AS_IS.items()):
        if name in seen:
            continue
        add({'name': name, 'animation': path(anim), 'build': False})
    for name, chain in CHAINS.items():
        add({'name': name, 'animation': path(chain[0]), 'then': [path(p) for p in chain[1:]], 'build': False})
    plan = {'set': SET, 'sources': [{'path': p, 'as_': SET} for p in SOURCES], 'moves': moves,
            'built': sum(1 for m in moves if m['build']), 'as_is': sum(1 for m in moves if not m['build'])}
    json.dump(plan, open(out, 'w'), indent=1)
    print('%d moves (%d built, %d as they are) -> %s' % (len(moves), plan['built'], plan['as_is'], out))


if __name__ == '__main__':
    main(sys.argv[1])
