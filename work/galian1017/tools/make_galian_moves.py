"""Vincent's Galian Beast form: his moves made of the Galian Beast's own animations (the boss EB2160 of the Shinra Manor),
for Create a Character System's Build Moves (editor 1.12.4), in two animation packs of his CharaSpec rows:

  Battle07  the GALIAN form's pack: every name Cloud's kit plays (Vincent is in Cloud's slot: his combo, dodges, guards,
            reactions, synergy, magic, items, summons, limit breaks, walks and runs, and Punisher mode's attacks too), each
            built from one of the beast's animations,
  Battle08  the same with Punisher mode's own idle, guard, walks and turns (game mod 3.7.5 "sets": the form gives Battle08
            for Battle01 and Battle07 for Battle00 while the beast is out),
and the beast's own sets (EB2160 Battle00, Battle00_Comp, Battle02, Battle01) under both, for the commands, which play the
boss's animations by their names as the boss does (BattleAbility PC0011_GB_*, build_galian_data.py), and chains of them
(a command made of two or three of the boss's moves in a row).

How a move is made:
  * attacks: the part of the beast's attack around its blow (a clip, a speed), with Cloud's move's gameplay notifies
    (combo and cancel windows, dodge and guard cancels) lined up on the beast's blows; each blow's damage a PC0011_GB_*
    row (Cloud's row of that move, struck from the beast's claw, foot or tail as the boss's row of that blow is:
    build_galian_data.py reads them from this plan's "damage"),
  * reactions, dodges, guards, casts and the rest: a piece of the beast's matching animation as long as Cloud's move
    (Cloud's notifies, so the game's timing stays his),
  * walks, runs, turns: the beast's own walk, run or turn (Base: its whole body) with the root of Cloud's animation of
    that name (Bone Map Trans=Trans: the game moves a player by its walks' and runs' root motion), as Vincent's Dirge of
    Cerberus walk and run are made,
  * the beast does not talk: the editor script takes the voice lines of Cloud's moves out of the built moves; the
    beast's own growls, footsteps and effects stay (Keep Source Effects).
    make_galian_moves.py <out plan json> <out report txt>"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BEAST = json.load(open(os.path.join(ROOT, 'beast_anims.json')))        # survey: length, hits of each beast animation
ROOT_TRAVEL = json.load(open(os.path.join(ROOT, 'beast_root.json')))   # the beast's root travel and turn in each animation (measure/)
CLOUD = json.load(open(os.path.join(ROOT, 'cloud_moves.json')))        # Cloud's Battle00/Battle01 moves: length, hits
LOCO = json.load(open('/work/galian1016/cloud_loco.json'))  # Cloud's walks and runs: root travel

SET, PSET = 'Battle07', 'Battle08'
E = '/Game/Motion/Enemy/EB2160_VincentValentine/'
C0 = '/Game/Motion/Player/PC0000_Cloud/Battle00/'
C1 = '/Game/Motion/Player/PC0000_Cloud/Battle01/'
BUILT = '/Game/RebirthSkelCompat/Built/VincentGalian'
SKELETON = '/Game/Character/Enemy/EB2160_00_VincentValentine_Standard/Model/EB2160_00_Skeleton.EB2160_00_Skeleton'
SOURCES = [E + 'Battle00.Battle00', E + 'Battle00_Comp.Battle00_Comp', E + 'Battle02.Battle02', E + 'Battle01.Battle01']
FACIAL = (E + 'Facial00.Facial00', 'Facial07')
GB = 'PC0011_GB_'
PUNISHER_ONLY = ('B_SAttack', 'B_SSAttack', 'B_Change_', 'B_CounterAttack', 'B_Connect', 'B_ChainRangeAtk_A04', 'B_ChainRangeAtk_A06',
                 'B_DmgGuard01_Add')


def path(p):
    return p if '.' in p.rsplit('/', 1)[-1] else p + '.' + p.rsplit('/', 1)[-1]


def beast(key):
    assert key in BEAST, ('the beast has no', key)
    return BEAST[key]


def cloud_source(set_name, name):
    """Cloud's move of that name whose notifies a move takes: Battle01's in Battle08 (or a name only Battle01 has)."""
    in0, in1 = ('Battle00/' + name) in CLOUD, ('Battle01/' + name) in CLOUD
    if in1 and (set_name == PSET or not in0):
        return C1 + name, CLOUD['Battle01/' + name]
    if in0:
        return C0 + name, CLOUD['Battle00/' + name]
    return None, None


# ---------------------------------------------------------------------------------------------------------------------
# The beast's attacks and where each of their blows strikes from: the boss's damage row whose shape a blow's row takes
# (build_galian_data.py; '+name' rows are shapes of its own)
CR1, CR20, CR21 = 'Battle00/B_AtkClawRaise01', 'Battle00/B_AtkClawRaise02_0', 'Battle00/B_AtkClawRaise02_1'
CK1, CK20 = 'Battle00/B_AtkCleaveKick01', 'Battle00/B_AtkCleaveKick02_0'
SS1, SS20 = 'Battle00/B_AtkSummerSalt01', 'Battle00/B_AtkSummerSalt02_0'
JS1, JS20, JS21 = 'Battle00/B_AtkJumpStump01', 'Battle00/B_AtkJumpStump02_0', 'Battle00/B_AtkJumpStump02_1'
BD1, BD22, BD23 = 'Battle00/B_AtkBerserkDance01', 'Battle00/B_AtkBerserkDance02_2', 'Battle00/B_AtkBerserkDance02_3'
BD24 = 'Battle01/B_AtkBerserkDance02_4'
BF, ROAR, ROAR2 = 'Battle00/B_AtkBeastFlare01', 'Battle00/B_AtkRoar01', 'Battle01/B_AtkRoar02'
CNT = 'Battle00/B_Counter_ClawRaise01'
CG1, CG2 = 'Battle01/B_AtkChaosGlaive01', 'Battle01/B_AtkChaosGlaive02'
CR21B, CK21B, SS21B, JS21B = 'Battle01/B_AtkClawRaise02_1', 'Battle01/B_AtkCleaveKick02_1', 'Battle01/B_AtkSummerSalt02_1', 'Battle01/B_AtkJumpStump02_1'
FM0, FM1, FM2 = 'Battle00/B_FastMove01_0', 'Battle00/B_FastMove01_1', 'Battle00/B_FastMove01_2'
IDLE, IDLE2 = 'Battle00/B_Idle01_1', 'Battle00/B_Idle02_1'
G0, G1, G2 = 'Battle00/B_Guard01_0', 'Battle00/B_Guard01_1', 'Battle00/B_Guard01_2'
STB, STL, STR = 'Battle00/B_StepB01', 'Battle00/B_StepL01', 'Battle00/B_StepR01'
JB0, JB1, JB2 = 'Battle00/B_JumpB01_0', 'Battle00/B_JumpB01_1', 'Battle00/B_JumpB01_2'
DF1, DB1, DL1, DR1 = 'Battle00/B_DmgF01', 'Battle00/B_DmgB01', 'Battle00/B_DmgL01', 'Battle00/B_DmgR01'
DF3 = ['Battle00/B_DmgF03_0', 'Battle00/B_DmgF03_1', 'Battle00/B_DmgF03_2']
DB3 = ['Battle00/B_DmgB03_0', 'Battle00/B_DmgB03_1', 'Battle00/B_DmgB03_2']
BURST = ['Battle00/B_DmgBurst01_0', 'Battle00/B_DmgBurst01_1', 'Battle00/B_DmgBurst01_2']
ABN = ['Battle00/B_Abnormal01_0', 'Battle00/B_Abnormal01_1', 'Battle00/B_Abnormal01_2']
PARTS = {
    CR1: ['EB2160_00_ClawRaise'], CNT: ['EB2160_00_ClawRaise'], CR21: ['EB2160_00_ClawRaise_Pursuit_Finish'],
    CR20: ['EB2160_00_ClawRaise_Pursuit_Rush'], CK1: ['EB2160_00_CleaveKick'],
    CK20: ['EB2160_00_CleaveKick_Pursuit_Tail', 'EB2160_00_CleaveKick_Pursuit_RFoot'], SS1: ['EB2160_00_SummerSalt'],
    SS20: ['EB2160_00_SummerSalt_Pursuit_Body', 'EB2160_00_SummerSalt_Pursuit_R', 'EB2160_00_SummerSalt_Pursuit_L'],
    JS1: ['EB2160_00_JumpStump'], JS20: ['EB2160_00_JumpStump_Pursuit_%02d' % k for k in range(4)],
    JS21: ['EB2160_00_JumpStump_Pursuit_Finish'], BD22: ['EB2160_00_BerserkDance_Pursuit_%02d' % k for k in range(9)],
    BD24: ['EB2160_00_BerserkDance_Pursuit_06'], CK21B: ['+LHand'], CR21B: ['+RClaw'],
    SS21B: ['EB2160_00_SummerSalt_Pursuit_Body', 'EB2160_00_SummerSalt_Pursuit_R'], JS21B: ['EB2160_00_JumpStumpChaos_Pursuit_Finish'],
    ROAR2: ['+Roar'], CG1: ['EB2160_00_ChaosGlaive'],
}


def A(anim, s=0.0, e=0.0, v=1.0, blows=None, at=None, damage=None, cloud=None, note=''):
    """An attack: the beast's `anim` from `s` to `e` (0: its end) at speed `v`; its blows at `blows` (seconds of the
    beast's animation; None: its own) or `at` (seconds of the move); `damage`: the PC0011_GB_ prefix of their rows (one
    row per blow: <prefix>_01, _02, ...; None: Cloud's own) copied from Cloud's rows `cloud` (a prefix: PC0000_...)."""
    return dict(anim=anim, s=s, e=e, v=v, blows=blows, at=at, damage=damage, cloud=cloud, note=note)


ATTACKS = {
    # --- Square: right claw, left claw, hopping kick, somersault kick, skull crusher (Cloud's 5-hit combo)
    'B_NAttack01_0': A(CR1, 0.40, 2.00, 1.3, damage='NAtk_1', cloud='PC0000_NAtk_1', note='combo 1: Skyward Slash\'s claw'),
    'B_NAttack02_0': A(CR21, 0.15, 0.0, 1.1, damage='NAtk_2', cloud='PC0000_NAtk_2', note='combo 2: the left claw'),
    'B_NAttack03_0': A(CK1, 0.50, 2.50, 1.0, damage='NAtk_3', cloud='PC0000_NAtk_3', note='combo 3: Hopping Sweep\'s kick'),
    'B_NAttack04_0': A(CK20, 0.20, 2.1667, 1.0, damage='NAtk_4', cloud='PC0000_NAtk_4', note='combo 4: the tail sweep (the somersault flips 7 m back)'),
    'B_NAttack05_0': A(JS1, 0.45, 0.0, 1.05, damage='NAtk_5', cloud='PC0000_NAtk_5', note='combo 5: Skull Crusher\'s stomp'),
    'B_NAttack01_1_2': A(CR1, 0.65, 2.20, 1.0, damage='NLAtk_1', cloud='PC0000_NLAtk_1', note='the lunge from afar: the strike'),
    'B_NAttack01_1': A(CR1, 0.30, 2.10, 1.0, damage='NAtk_1', cloud='PC0000_NAtk_1', note='(another first attack)'),
    # dash attacks, held Square, the switch-in attack
    'B_WAttack01_0': A(CR1, 0.56, 1.66, 1.0, [0.73, 0.77], damage='NDAtk_1', cloud='PC0000_NDAtk_1', note='dash attack: a claw'),
    'B_WAttack02_0': A(BD22, 0.39, 2.30, 1.5, [0.69, 1.22, 1.64, 2.17], damage='NDAtk_2', cloud='PC0000_NDAtk_2',
                       note='dash attack 2: four of Savage Beast\'s blows'),
    'B_NAttack06_0': A(CK20, 0.20, 0.0, 1.0, [0.58, 0.65], damage='NDAtk_3', cloud='PC0000_NDAtk_3', note='a tail and foot sweep'),
    'B_NAttack07_0': A(CR20, 0.0, 1.60, 1.0, [0.27, 0.62], damage='NPAtk_1', cloud='PC0000_NPAtk_1', note='held Square: the tail rush'),
    'B_NAttack20_0': A(CR1, 0.50, 1.70, 1.0, [0.73, 1.03], damage='ChainChange01', cloud='PC0000_ChainChange01', note='the switch-in attack'),
    # in the air
    'B_NAttackJ01_0': A(BD24, 0.26, 0.0, 1.0, damage='JAtk_1', cloud='PC0000_JAtk_1', note='air 1'),
    'B_NAttackJ02_0': A(CR21, 0.10, 0.0, 1.2, damage='JAtk_2', cloud='PC0000_JAtk_2', note='air 2'),
    'B_NAttackJ03_0': A(SS20, 0.30, 0.0, 1.0, [0.69], damage='JAtk_3', cloud='PC0000_JAtk_3', note='air 3: the somersault'),
    'B_NAttackJ04_0': A(JS20, 0.30, 1.75, 1.0, [0.6157, 1.0185], damage='JNDAtk_1', cloud='PC0000_NDAtk_3', note='air dash attack: the stomps (the finish leaps 15 m back)'),
    'B_NAttackJ05_2': A(JS20, 0.58, 2.00, 1.3, [0.62, 1.02, 1.21], damage='JNPAtk_1', cloud='PC0000_JNPAtk_1', note='air held Square: three stomps'),
    # synergy attacks and counters
    'B_ChainTatakau_B01_0': A(BD22, 0.30, 3.40, 1.0, [0.69, 1.22, 2.17], damage='ChainTatakau1', cloud='PC0000_ChainTatakau1_AI_1', note='synergy attack'),
    'B_ChainTatakauJ_B01_0': A(BD22, 0.30, 3.40, 1.0, [0.69, 1.22, 2.17], damage='ChainTatakau1', cloud='PC0000_ChainTatakau1_AI_1', note='synergy attack (air)'),
    'B_ChainCounter_A01_2': A(CR20, 0.0, 2.233, 1.05, [0.33, 0.9, 1.1], damage='ChainCounter1', cloud='PC0000_ChainCounter1_UC', note='Combo Counter'),
    'B_ChainCounter_A02_2': A(CK20, 0.0, 0.0, 0.85, [0.58, 0.60, 0.62], damage='ChainCounter2', cloud='PC0000_ChainCounter2_UC', note='Counterfire'),
    'B_ChainCharge_A01_2': A(CK1, 0.75, 2.767, 0.9, damage='ChainCharge1', cloud='PC0000_ChainCharge1_UC', note='Power Cleave 1'),
    'B_ChainCharge_A02_2': A(JS1, 0.50, 2.667, 0.85, damage='ChainCharge2', cloud='PC0000_ChainCharge2_UC', note='Power Cleave 2'),
    # magic, items, materia commands: the beast's casts (Bestial Flare's breath, its roar); their damage the spell's own
    'B_MagAttack01_2': A(BF, 0.75, 2.85, 1.0, [1.10], note='spell: release'),
    'B_MagAttack02_2': A(BF, 0.95, 2.287, 1.0, [1.10], note='spell (long): release'),
    'B_MagCure01_2': A(ROAR, 1.24, 3.14, 1.0, [1.60], note='healing: release'),
    'B_Item01': A(IDLE2, 0.0, 1.60, 1.0, at=[0.73], note='item'),
    'B_ItemCure01': A(IDLE2, 0.0, 1.60, 1.0, at=[0.83], note='healing item'),
    'B_Ability01_2': A(ROAR, 1.30, 2.633, 1.0, [1.60], note='materia command (heal)'),
    'B_Ability02_2': A(ROAR, 1.50, 2.833, 1.0, [1.60], note='materia command'),
    'B_Ability03_2': A(CR1, 0.73, 2.163, 1.0, [0.73], note='materia command: Steal'),
    'B_Ability04_2': A(CR1, 0.72, 2.50, 0.97, [0.73, 1.10], note='materia command: Assess'),
    'B_Ability05_2_1': A(CR21, 0.37, 0.637, 1.0, [0.37], note='materia command'),
    'B_Ability05_2_2': A(CR21, 0.35, 1.267, 0.466, [0.36], note='materia command: end'),
    'B_Ability06_1': A(CR1, 0.53, 1.30, 1.0, [0.73], note='materia command'),
    'B_CompAbility01_1': A(CR1, 0.73, 1.73, 1.0, at=[0.0, 0.0, 0.0, 0.33, 0.67], note='materia command (combined)'),
    'B_EleBurst01_0': A(CR1, 0.20, 2.233, 1.0, [0.73], note='elemental strike'),
    'B_EleBurstJ01_0': A(CR1, 0.20, 1.967, 1.0, [0.73], note='elemental strike (air)'),
    'B_CompEleBurst01_0': A(CR1, 0.73, 2.50, 0.87, [0.73], note='elemental strike (combined)'),
    'B_CompEleBurstJ01_0': A(CR1, 0.73, 2.50, 1.0, [0.73], note='elemental strike (combined, air)'),
    # Cloud's ATB abilities and limit breaks (the form's are the beast's: these for anything else that plays them)
    'B_AtkBurst01_0': A(JS1, 0.0, 2.667, 0.825, [1.16], note='Braver'),
    'B_AtkBurst02_0': A(CK1, 0.50, 2.767, 0.92, [1.03, 1.40], note='Focused Thrust'),
    'B_AtkBurst03_0_2': A(CR21, 0.27, 0.60, 1.0, [0.37], note='Triple Slash 1'),
    'B_AtkBurst03_1_2': A(CR1, 0.72, 0.95, 1.0, [0.73], note='Triple Slash 2'),
    'B_AtkBurst03_2_2': A(JS1, 1.15, 2.667, 0.95, [1.16], note='Triple Slash 3'),
    'B_AtkBurst04_0': A(CG1, 0.0, 5.60, 1.0, [2.64], note='Infinity\'s End'),
    'B_AtkBurst05_0': A(BD22, 0.30, 4.93, 1.0, [1.37, 2.44, 2.50, 2.50, 2.50, 2.50, 2.50], note='Blade Burst'),
    'B_AtkBurst06_2': A(CNT, 0.10, 2.50, 1.0, [0.70, 0.83, 1.06], note='Counterstance: the counter'),
    'B_AtkBurst06_3': A(CNT, 0.36, 2.10, 1.0, [0.70], note='Counterstance: the counter (2)'),
    'B_AtkBurst07_0': A(CR20, 0.0, 2.233, 0.87, [0.33, 0.70], note='Disorder'),
    'B_AtkBurst07_1': A(CK20, 0.07, 2.137, 1.0, [0.58, 0.93], note='Disorder (2)'),
    'B_AtkBurst08_0': A(BF, 1.00, 2.067, 1.0, [1.10], note='Firebolt Blade 1'),
    'B_AtkBurst08_2': A(BF, 1.07, 3.00, 1.0, [1.10, 1.24, 1.51, 2.30], note='Firebolt Blade 2'),
    'B_AtkBurst09_0': A(ROAR, 0.0, 3.833, 1.186, [1.60, 2.60], note='Prime Mode'),
    'B_AtkBurst10_0': A(JS20, 0.0, 3.20, 1.067, [0.62, 1.02, 1.21, 1.49, 3.10], note='Aerial Onslaught'),
    'B_AtkBurst10_2': A(JS20, 1.30, 3.20, 1.0, [1.493], note='Aerial Onslaught: the landing'),
    'B_AtkBurstJ01_0': A(JS1, 0.0, 1.40, 1.0, [1.16], note='Braver (air)'),
    'B_AtkBurstJ01_2': A(JS1, 1.14, 2.667, 0.75, [1.16], note='Braver (air): the landing'),
    'B_AtkBurstJ06_2': A(CNT, 0.70, 2.27, 1.0, [0.70, 0.83, 1.06], note='Counterstance (air): the counter'),
    'B_AtkBurstJ06_3': A(CNT, 0.36, 2.10, 1.0, [0.70], note='Counterstance (air): the counter (2)'),
    'B_AtkBurstJ07_1': A(CK20, 0.07, 2.137, 1.0, [0.58, 0.93], note='Disorder (air)'),
    'B_AtkLimit01_0': A(BD22, 0.0, 5.10, 1.0, at=[1.60, 2.09, 2.91], note='Cross-Slash'),
    'B_AtkLimit02_0': A(BD22, 0.0, 5.50, 0.645, at=[2.41, 2.73, 3.10, 3.39, 3.82, 4.62, 5.01, 5.37], note='Ascension'),
    'B_AtkLimit03_0': A(CG1, 0.0, 5.667, 0.552, at=[3.20, 3.79, 3.90, 4.09, 4.42, 4.70, 7.17, 7.40], note='Finishing Touch'),
    'B_BurstChain_Vision01': A(ROAR, 0.0, 3.833, 0.885, at=[0.47, 2.74], note='United Refocus'),
    'B_Vision01_0': A(ROAR, 0.0, 3.833, 0.927, at=[0.0], note='a vision'),
    # Punisher mode (Cloud's Battle01 names: Battle07 has them for every way the game may look them up)
    'B_SAttack01_0': A(CK21B, 0.86, 2.70, 1.0, [1.50], damage='SAtk_1', cloud='PC0000_SAtk_1', note='Punisher: a chaos kick'),
    'B_SAttack01_1': A(CK21B, 0.22, 2.62, 1.0, [1.50], damage='SAtk_1', cloud='PC0000_SAtk_1', note='Punisher: the charged kick'),
    'B_SAttack02_0': A(CR21B, 0.0, 0.70, 0.70, [0.52], damage='SAtk_2', cloud='PC0000_SAtk_2', note='Punisher combo 1: the chaos claw'),
    'B_SAttack02_1': A(CR21, 0.33, 0.93, 1.0, [0.37, 0.64], damage='SAtk_2b', cloud='PC0000_SAtk_2', note='Punisher combo 2'),
    'B_SAttack02_2_0': A(JS20, 0.45, 1.60, 0.75, [0.6157, 1.0185], damage='SAtk_2c', cloud='PC0000_SAtk_2', note='Punisher combo 3: the stomps'),
    'B_SAttack02_2_1': A(JS20, 0.45, 1.60, 0.73, [0.6157, 1.0185], damage='SAtk_2c', cloud='PC0000_SAtk_2', note='Punisher combo 3 (2): the stomps'),
    'B_SAttack03_0': A(JS21B, 0.67, 3.233, 1.0, [1.43], damage='SAtk_3', cloud='PC0000_AAASAtk_1', note='Punisher: the chaos stomp'),
    'B_SAttack04_0': A(ROAR2, 0.51, 3.31, 1.0, [1.34], damage='SPAtk_1', cloud='PC0000_SPAtk_1', note='Punisher: the chaos roar'),
    'B_SAttack05_0': A(CNT, 0.33, 2.50, 1.0, [0.70, 1.16], damage='AAASAtk_1', cloud='PC0000_AAASAtk_1', note='Punisher: Berserk counter'),
    'B_SAttack06_0': A(CR21B, 0.0, 0.70, 0.42, [0.24], damage='AAASPAtk_1', cloud='PC0000_AAASPAtk_1', note='Punisher: held Square 1'),
    'B_SAttack06_1': A(CK21B, 1.0, 2.767, 1.0, [1.50], damage='AAASPAtk_2', cloud='PC0000_AAASPAtk_2', note='Punisher: held Square 2'),
    'B_SAttack06_2': A(JS21B, 0.15, 2.717, 1.0, [1.43], damage='AAASPAtk_3', cloud='PC0000_AAASPAtk_3', note='Punisher: held Square 3'),
    'B_SAttackJ01_0': A(JS1, 0.65, 1.25, 1.0, [1.16], damage='JChange_ON', cloud='PC0000_JChange_ON', note='Punisher in the air: the dive'),
    'B_SAttackJ01_2': A(JS1, 1.12, 2.667, 0.83, [1.16], damage='JChange_ON', cloud='PC0000_JChange_ON', note='Punisher in the air: the landing'),
    'B_SSAttack01_0': A(CK21B, 0.28, 2.81, 1.0, [1.50], note='Punisher: a charged attack'),
    'B_SSAttack01_1': A(CK21B, 0.52, 2.82, 1.0, [1.50], note='Punisher: a charged attack (2)'),
    'B_CounterAttack01': A(CNT, 0.63, 2.50, 0.6375, [0.70, 0.80], damage='CounterAtk_1', cloud='PC0000_CounterAtk_1', note='Punisher: the counter on a guard'),
    'B_Change_02_0': A(CR1, 0.43, 1.86, 1.0, [0.73], damage='Change_OFF', cloud='PC0000_Change_OFF', note='out of Punisher: a claw'),
    'B_Change_03_0': A(CR1, 0.47, 2.50, 1.0, [0.73], damage='Change_OFF', cloud='PC0000_Change_OFF', note='out of Punisher (after an attack)'),
    'B_Change_F04_0': A(CR1, 0.46, 1.73, 1.0, [0.73], damage='Change_OFF', cloud='PC0000_Change_OFF', note='out of Punisher: forward'),
    'B_Change_B04_0': A(CR1, 0.46, 1.73, 1.0, [0.73], damage='Change_OFF', cloud='PC0000_Change_OFF', note='out of Punisher: back'),
    'B_Change_L04_0': A(CR1, 0.46, 1.70, 1.0, [0.73], damage='Change_OFF', cloud='PC0000_Change_OFF', note='out of Punisher: left'),
    'B_Change_R04_0': A(CR1, 0.46, 1.70, 1.0, [0.73], damage='Change_OFF', cloud='PC0000_Change_OFF', note='out of Punisher: right'),
}
# the ranged synergy attacks (Bullet Batter, Howling Smash): two hits at once, Bestial Flare's breath; the synergy's own damage
for n, ln in (('A01', 1.133), ('A02', 1.233), ('A03', 1.433), ('A05', 1.367), ('A04', 0.8), ('A06', 1.2)):
    ATTACKS['B_ChainRangeAtk_%s_2' % n] = A(BF, 1.08, 1.08 + ln, 1.0, [1.10, 1.10], note='ranged synergy: the shot')
for n, ln in (('A01', 1.133), ('A02', 1.233), ('A03', 1.233)):
    ATTACKS['B_ChainRangeAtkJ_%s_2' % n] = A(BF, 1.08, 1.08 + ln, 1.0, [1.10, 1.10], note='ranged synergy (air): the shot')
# synergy abilities with a partner: the beast's flurries, as long as Cloud's, the hits where his land
BURST_CHAINS = {
    'B_BurstChain_00_01_01_0': BD22, 'B_BurstChain_00_02_01_0': BD22, 'B_BurstChain_00_02_02_0': JS20, 'B_BurstChain_00_03_01_0': BD22,
    'B_BurstChain_00_04_01_0': CG1, 'B_BurstChain_00_04_02_0': JS20, 'B_BurstChain_00_05_01_0': BD22, 'B_BurstChain_00_05_02_0': CG1,
    'B_BurstChain_00_07_01_0': BD22, 'B_BurstChain_00_07_02_0': ROAR, 'B_BurstChain_00_09_01_0': BD22, 'B_BurstChain_00_09_02_0': BD22,
    'B_BurstChain_00_10_01_0': CG1,
}
# Punisher mode's own versions of names Battle07 has as Operator mode's (Battle08 only)
PUNISHER_ATTACKS = {
    'B_DmgJGuard01': A(CNT, 0.0, 2.50, 0.765, [0.70, 0.75, 1.20, 1.38, 1.51], damage='JGuardCounter', cloud='PC0000_AAASAtk_1',
                       note='Punisher: the counter as he guards'),
}

# ---------------------------------------------------------------------------------------------------------------------
# Pieces: Cloud's name -> (beast animation, start): as long as Cloud's move, Cloud's notifies at their own times
PIECES = {
    'B_DmgF01': (DF1, 0.0), 'B_DmgStrikeF01_1': (DF1, 0.0), 'B_DmgReflect01': (DF1, 0.0), 'B_DmgB01': (DB1, 0.0), 'B_DmgStrikeB01_1': (DB1, 0.0),
    'B_DmgL01': (DL1, 0.0), 'B_DmgR01': (DR1, 0.0), 'B_DmgF02': (DF3[0], 0.0), 'B_DmgB02': (DB3[0], 0.0), 'B_DmgStrikeF01_0': (DF1, 0.0),
    'B_DmgStrikeB01_0': (DB1, 0.0), 'B_Dmg01_Add': (DF1, 0.0),
    'B_DmgF03_0': (DF3[0], 0.0), 'B_DmgF03_1': (DF3[1], 0.0), 'B_DmgF03_2': (DF3[2], 0.0),
    'B_DmgB03_0': (DB3[0], 0.0), 'B_DmgB03_1': (DB3[1], 0.0), 'B_DmgB03_2': (DB3[2], 0.0),
    'B_DmgBlowF01_0': (DB3[0], 0.0), 'B_DmgBlowF01_1': (DB3[1], 0.0), 'B_DmgBlowB01_0': (DF3[0], 0.0), 'B_DmgBlowB01_1': (DF3[1], 0.0),
    'B_DmgUpperF01_0': (DB3[0], 0.0), 'B_DmgUpperF01_1': (DB3[1], 0.0), 'B_DmgUpperB01_0': (DF3[0], 0.0), 'B_DmgUpperB01_1': (DF3[1], 0.0),
    'B_DmgDownF01_0': (DF3[1], 0.0), 'B_DmgDownF01_2': (DF3[2], 0.0), 'B_DmgDownF02_0': (DF3[1], 0.6), 'B_DmgDownF02_2': (DF3[2], 0.0),
    'B_DmgDownF03_0': (DF3[1], 1.2), 'B_DmgDownB01_0': (DB3[1], 0.0), 'B_DmgDownB01_2': (DB3[2], 0.0), 'B_DmgDownB02_0': (DB3[1], 0.6),
    'B_DmgDownB02_2': (DB3[2], 0.0), 'B_DmgDownB03_0': (DB3[1], 1.2), 'B_DmgRecoverF01': (DF3[2], 0.0), 'B_DmgRecoverB01': (DB3[2], 0.0),
    'B_DownAbnormalF01_0': (DF3[1], 0.3), 'B_DownAbnormalB01_0': (DB3[1], 0.3), 'B_DownDieF01': (DF3[1], 0.0), 'B_DownDieB01': (DB3[1], 0.0),
    'B_Die01_0': (DF3[0], 0.0), 'B_Die01_1': (DF3[1], 0.0), 'B_Die01_2': (DF3[1], 1.0),
    'B_Abnormal01_0': (ABN[0], 0.0), 'B_Abnormal01_1': (ABN[1], 0.0), 'B_Abnormal01_2': (ABN[2], 0.0),
    'B_DmgCatch01_0': (BURST[0], 0.0), 'B_DmgCatch01_1': (BURST[1], 0.0), 'B_DmgCatch01_2': (BURST[2], 0.0),
    'B_DmgCatch02_0': (BURST[0], 0.0), 'B_DmgCatch02_1': (BURST[1], 0.0), 'B_DmgCatch02_2': (BURST[2], 0.0),
    'B_DmgCatch03_0': (BURST[0], 0.0), 'B_DmgCatch03_1': (BURST[1], 0.0), 'B_DmgCatch03_2': (BURST[2], 0.0),
    'B_Fall01_1': (JB1, 0.0), 'B_Fall01_2': (JB2, 0.0), 'B_Fall01_3': (JB2, 0.3),
    'B_Guard01_0': (G0, 0.0), 'B_Guard01_1': (G1, 0.0), 'B_Guard01_2': (G2, 0.0),
    'B_GuardFace01_0': (G0, 0.0), 'B_GuardFace01_1': (G1, 0.0), 'B_GuardFace01_2': (G2, 0.0),
    'B_GuardFace02_0': (G0, 0.0), 'B_GuardFace02_1': (G1, 0.3), 'B_GuardFace02_2': (G2, 0.0),
    'B_DmgGuard02': (G1, 0.2), 'B_DmgGuard03': (G1, 0.0), 'B_DmgJGuard01': (G2, 0.0),
    'B_Avoid01': (STR, 0.0), 'B_Avoid02': (STB, 0.0), 'B_AvoidJ01': (JB1, 0.0),
    'B_AvoidJ10_0': (JB0, 0.0), 'B_AvoidJ10_1': (JB1, 0.0), 'B_AvoidJ10_2': (JB2, 0.0),
    'B_AvoidStpB01': (STB, 0.0), 'B_AvoidStpF01': (FM2, 0.0), 'B_AvoidStpL01': (STL, 0.0), 'B_AvoidStpR01': (STR, 0.0),
    'B_ChainDodge_B01_0': (STB, 0.0), 'B_ChainGuard_B01_0': (G0, 0.0), 'B_ChainGuard_B01_1': (G1, 0.0), 'B_ChainGuard_B01_2': (G2, 0.0),
    'B_ChainSPGuard_B01_0': (G0, 0.0), 'B_ChainSPGuard_B01_1': (G1, 0.0), 'B_ChainSPGuard_B01_2': (G2, 0.0), 'B_ChainSPGuard_B01_3': (G2, 0.0),
    'B_ChainJump_A02_0': (JB0, 0.0), 'B_ChainJump_B01_0': (JB0, 0.0), 'B_ChainSupport_B02_0': (FM2, 0.0),
    'B_ChainWait01_0': (IDLE2, 0.0), 'B_ChainWait01_1': (IDLE2, 0.5), 'B_ChainWait01_2': (IDLE2, 3.0),
    'B_ChainCharge_A01_0': (CK1, 0.0), 'B_ChainCharge_A01_1': (IDLE2, 0.0), 'B_ChainCharge_A02_0': (JS1, 0.0), 'B_ChainCharge_A02_1': (IDLE2, 0.0),
    'B_ChainCounter_A01_0': (G0, 0.0), 'B_ChainCounter_A01_1': (G1, 0.0), 'B_ChainCounter_A01_3': (G2, 0.0),
    'B_NAttack01_1_0': (FM0, 0.0), 'B_NAttack01_1_1': (FM1, 0.0), 'B_NAttackJ05_0': (FM0, 0.0), 'B_NAttackJ05_1': (FM1, 0.0),
    'B_NAttack07_1': (CR20, 1.0), 'B_NAttack07_2': (CR20, 1.0), 'B_AAttack01_0': (FM0, 0.0), 'B_AAttack01_1': (FM1, 0.0),
    'B_MagAttack01_0': (BF, 0.0), 'B_MagAttack01_1': (BF, 0.43), 'B_MagAttack02_0': (BF, 0.0), 'B_MagAttack02_1': (BF, 0.43),
    'B_MagCure01_0': (ROAR, 0.0), 'B_MagCure01_1': (ROAR, 0.27),
    'B_MagSummon01_0': (ROAR, 0.0), 'B_MagSummon01_1': (IDLE2, 0.0), 'B_MagSummon01_2': (ROAR, 0.5), 'B_MagSummon01_3': (IDLE2, 0.0),
    'B_MagSummon01_4': (IDLE2, 0.0),
    'B_Ability01_0': (ROAR, 0.0), 'B_Ability01_1': (ROAR, 0.6), 'B_Ability02_0': (ROAR, 0.0), 'B_Ability02_1': (ROAR, 0.5),
    'B_Ability03_0': (CR1, 0.0), 'B_Ability03_1': (IDLE2, 0.0), 'B_Ability04_0': (CR1, 0.0), 'B_Ability04_1': (CR1, 0.27),
    'B_Ability05_0': (CR21, 0.0), 'B_Ability05_2_0': (CR21, 0.0), 'B_Ability06_0': (CR1, 0.0), 'B_Ability06_2': (CR1, 1.3),
    'B_AtkBurst03_0_0': (CR21, 0.0), 'B_AtkBurst03_0_1': (CR21, 0.13), 'B_AtkBurst03_1_0': (CR1, 0.39), 'B_AtkBurst03_1_1': (CR1, 0.62),
    'B_AtkBurst03_2_0': (JS1, 0.83), 'B_AtkBurst03_2_1': (JS1, 1.0), 'B_AtkBurst06_0': (G0, 0.0), 'B_AtkBurst06_1': (G1, 0.0),
    'B_AtkBurst08_1': (BF, 1.07), 'B_AtkBurst10_1': (JS20, 1.60), 'B_AtkBurstJ01_1': (JS1, 1.15), 'B_AtkBurstJ06_0': (G0, 0.0),
    'B_AtkBurstJ06_1': (G1, 0.0),
    'B_ChainRangeAtk_A01_0': (BF, 0.43), 'B_ChainRangeAtk_A02_0': (BF, 0.43), 'B_ChainRangeAtk_A03_0': (BF, 0.0),
    'B_ChainRangeAtk_A05_0': (BF, 0.43), 'B_ChainRangeAtk_A11_0': (BF, 0.43), 'B_ChainRangeAtk_A12_0': (BF, 0.43),
    'B_ChainRangeAtk_A13_0': (BF, 0.0), 'B_ChainRangeAtkJ_A01_0': (BF, 0.43), 'B_ChainRangeAtkJ_A02_0': (BF, 0.43),
    'B_ChainRangeAtkJ_A03_0': (BF, 0.0), 'B_ChainRangeAtk_A04_0': (BF, 0.43), 'B_ChainRangeAtk_A06_0': (BF, 0.3),
    'B_Jump01_0': (JB0, 0.0), 'PC0000_00_B_AreaJump01_2': (JB2, 0.0),
    'B_Win01': (ROAR, 0.0), 'B_Idle01_0': (IDLE, 0.0), 'B_Idle01_2': (IDLE, 3.0),
    'PC0000_00_B_AtkBlowAwayA01': (DB3[0], 0.0), 'PC0000_00_B_AtkBlowAwayA02_3': (DB3[2], 0.0), 'PC0000_00_B_AtkBlowAwayB01': (DB3[0], 0.0),
    'PC0000_00_B_AtkBlowAwayB02_0': (DB3[0], 0.0), 'PC0000_00_B_AtkBlowAwayB02_1': (DB3[1], 0.0), 'PC0000_00_B_AtkBlowAwayB02_2': (DB3[2], 0.0),
    'PC0000_00_B_AtkBlowAwayD01_0': (DF3[0], 0.0), 'PC0000_00_B_AtkBlowAwayD01_1': (DF3[1], 0.0), 'PC0000_00_B_AtkBlowAwayD01_2': (DF3[2], 0.0),
    # Punisher mode's (Battle01 names Battle00 lacks)
    'B_Change_01_0': (ROAR2, 0.0), 'B_Change_F04_1': (FM1, 0.0), 'B_Change_F04_2': (FM2, 0.0), 'B_Change_B04_1': (FM1, 0.0),
    'B_Change_B04_2': (STB, 0.0), 'B_Change_L04_2': (STL, 0.0), 'B_Change_R04_1': (FM1, 0.0), 'B_Change_R04_2': (STR, 0.0),
    'B_Connect01': (IDLE2, 0.0), 'B_SAttack05_1': (G1, 0.0), 'B_SAttack05_2': (CNT, 0.0), 'B_SAttack05_3': (CNT, 0.0),
    'B_SAttackJ01_1': (JS1, 1.16), 'B_DmgGuard01_Add': (G1, 0.0),
}
# Punisher mode's own pieces (Battle08 only: Cloud's Battle01 versions of names Battle07 has as Operator mode's)
PUNISHER_PIECES = {'B_Guard01_0': (G0, 0.0), 'B_Guard01_1': (G1, 0.0), 'B_Guard01_2': (G2, 0.0), 'B_Dmg01_Add': (DF1, 0.0),
                   'B_Idle01_2': (IDLE2, 3.0)}

# ---------------------------------------------------------------------------------------------------------------------
# Locomotion: Cloud's name -> (the beast's animation under it (Base), its forward version, Cloud's animation for the root
# (None: the name's own)). The editor script measures how far each Base turns its root and takes the forward one when
# it does not turn as Cloud's does (so the body does not turn twice), and the beast's facing for Source Turn.
W0, W1, W2 = 'Battle00/B_Walk01_0', 'Battle00/B_Walk01_1', 'Battle00/B_Walk01_2r'
R0, R1, R2 = 'Battle00/B_Run01_0', 'Battle00/B_Run01_1', 'Battle00/B_Run01_2r'
LOCOMOTION = {
    'B_Run01_0': (R0, R0, 'B_Run01_0_L0'), 'B_Run01_0_L0': (R0, R0, None), 'B_Run01_0_L90': ('Battle00/B_Run01_0_L90', R0, None),
    'B_Run01_0_L180': ('Battle00/B_Run01_0_L180', R0, None), 'B_Run01_0_R90': ('Battle00/B_Run01_0_R90', R0, None),
    'B_Run01_0_R180': ('Battle00/B_Run01_0_R180', R0, None), 'B_Run01_1': (R1, R1, None), 'B_Run01_1_L180': ('Battle00/B_Run01_0_L180', R1, None),
    'B_Run01_1_R180': ('Battle00/B_Run01_0_R180', R1, None), 'B_Run01_Up': (R1, R1, None), 'B_Run01_2': (R2, R2, None),
    'B_Run01_2l': (R2, R2, None), 'B_Run01_2r': (R2, R2, None),
    'B_Walk01_0': (W0, W0, 'B_Walk01_0_L0'), 'B_Walk01_0_L0': (W0, W0, None), 'B_Walk01_0_L90': ('Battle00/B_Walk01_0_L90', W0, None),
    'B_Walk01_0_L180': ('Battle00/B_Walk01_0_L180', W0, None), 'B_Walk01_0_R90': ('Battle00/B_Walk01_0_R90', W0, None),
    'B_Walk01_0_R180': ('Battle00/B_Walk01_0_R180', W0, None), 'B_Walk01_1': (W1, W1, None), 'B_Walk01_2l': (W2, W2, None),
    'B_Walk01_2r': (W2, W2, None),
    'B_WalkF01_0': (W0, W0, None), 'B_WalkF01_1': (W1, W1, None), 'B_WalkF01_2l': (W2, W2, None), 'B_WalkF01_2r': (W2, W2, None),
    'B_WalkB01_0': (W0, W0, None), 'B_WalkB01_1': (W1, W1, None), 'B_WalkB01_2l': (W2, W2, None), 'B_WalkB01_2r': (W2, W2, None),
    'B_WalkBL01_1': (W1, W1, None), 'B_WalkBR01_1': (W1, W1, None), 'B_WalkFL01_1': (W1, W1, None), 'B_WalkFR01_1': (W1, W1, None),
    'B_WalkL01_0': (W0, W0, None), 'B_WalkL01_0l': (W0, W0, None), 'B_WalkL01_1': (W1, W1, None), 'B_WalkL01_2l': (W2, W2, None),
    'B_WalkL01_2r': (W2, W2, None), 'B_WalkR01_0': (W0, W0, None), 'B_WalkR01_1': (W1, W1, None), 'B_WalkR01_2l': (W2, W2, None),
    'B_WalkR01_2r': (W2, W2, None),
    'B_Turn01_L90': ('Battle00/B_Turn01_L90', IDLE, None), 'B_Turn01_L180': ('Battle00/B_Turn01_L180', IDLE, None),
    'B_Turn01_R90': ('Battle00/B_Turn01_R90', IDLE, None), 'B_Turn01_R180': ('Battle00/B_Turn01_R180', IDLE, None),
}
# the strafes (the beast has none): its walk on Cloud's root; every other name the beast's own as it is
STRAFES = ('B_WalkB', 'B_WalkL', 'B_WalkR', 'B_WalkFL', 'B_WalkFR')
# ... and the run's stops (the beast's slides 6.5 m; Cloud's 33 cm) and its run up a slope (Cloud's stays put)
ROOT_LOCOMOTION = {'B_Run01_Up', 'B_Run01_2', 'B_Run01_2l', 'B_Run01_2r'}
# pieces made of the beast's dodges, steps and dashes: its body on Cloud's root (the beast's go 6 to 12 m)
ROOT_PIECES = {STB, STL, STR, FM0, FM1, FM2, JB0, JB1, JB2}
# Punisher mode walks (slower: the root of Cloud's Battle01 walks) and turns: Battle08 only
PUNISHER_LOCOMOTION = {n: LOCOMOTION[n] for n in LOCOMOTION if n.startswith(('B_Walk', 'B_Turn')) and ('Battle01/' + n) in CLOUD}
# the beast's own as they are: its idle (its Punisher stance its other idle)
AS_IS = {(SET, 'B_Idle01_1'): E + 'Battle00/B_Idle01_1', (PSET, 'B_Idle01_1'): E + 'Battle00/B_Idle02_1'}
# commands that play one of the boss's Battle01 (chaos phase) moves whose name Battle00's shadows in Battle07 (first wins):
# under a name of their own
ALIASES = {'B_GB_FollowUp01': JS21B, 'B_GB_ChaosStomp01': 'Battle01/B_AtkJumpStump02_0'}
for _name, _anim in ALIASES.items():
    AS_IS[(SET, _name)] = AS_IS[(PSET, _name)] = E + _anim
# blend spaces: Vincent's own (his strafes and his turn in place) made for the beast's skeleton, sampling the built moves
# (make_galian_blendspaces.py, after the build)
BLEND_SPACES = ['B_StrafingWalk01_0', 'B_StrafingWalk01_1', 'B_StrafingWalk01_2l', 'B_StrafingWalk01_2r', 'B_Turn01']

# ---------------------------------------------------------------------------------------------------------------------
# The boss's attacks the commands play whose trails and smoke check the boss's ability (m_BranchConditionType AbilityID: a
# PC0011_GB_* ability is not it): copies of them as they are (their own notifies, blows and effects; the editor script
# takes the check off)
COPIES = {'B_GB_AtkClawRaise01': CR1, 'B_GB_AtkClawRaise02_0': CR20, 'B_GB_AtkClawRaise02_1': CR21, 'B_GB_AtkCleaveKick01': CK1,
          'B_GB_AtkCleaveKick02_0': CK20, 'B_GB_AtkSummerSalt01': SS1, 'B_GB_AtkSummerSalt02_0': SS20, 'B_GB_AtkJumpStump01': JS1,
          'B_GB_AtkBerserkDance01': BD1, 'B_GB_AtkBerserkDance02_2': BD22}
COPY = {anim: name for name, anim in COPIES.items()}
# The beast's commands made of two or three of the boss's moves in a row (the mod chains them in game: an AnimComposite;
# the copies above in place of the boss's)
CHAINS = {
    'B_GB_SkullCrusher01': [JS1, JS20],
    'B_GB_HoppingSweep01': [CK1, CK20],
    'B_GB_SomersaultKick01': [SS1, SS20],
    'B_GB_SkywardSlash01': [CR1, CR20, CR21],
    'B_GB_ChaosAssault01': [FM0, 'Battle00/B_FastMove02_1', JS1],
    'B_GB_ChaosClaw01': [CR21B, 'Battle01/B_AtkClawRaise02_2', 'Battle01/B_AtkClawRaise02_3'],
    'B_GB_SavageBeast01': [BD1, BD22, BD23],
    'B_GB_ChaoticImpulse01': [ROAR2, CG1, CG2],
}


def chain_part(p):
    return '%s/%s/%s.%s' % (BUILT, SET, COPY[p], COPY[p]) if p in COPY else path(E + p)


def main(out, report_path):
    moves, lines, problems, damage = [], [], [], {}
    seen = set()

    def add(m, line):
        key = (m['set'], m['name'])
        assert key not in seen, key
        seen.add(key)
        moves.append(m)
        lines.append(line)

    def attack(set_name, name, spec):
        notifies, c = cloud_source(set_name, name)
        if c is None:
            problems.append('%s/%s: Cloud has no move of that name' % (set_name, name))
            return
        b = beast(spec['anim'])
        e = spec['e'] or b['length']
        assert 0 <= spec['s'] < e <= b['length'] + 1e-3, (name, spec['s'], e, b['length'])
        length = (e - spec['s']) / spec['v']
        if spec['at'] is not None:
            times, blows = [round(t, 4) for t in spec['at']], None
        else:
            blows = spec['blows'] if spec['blows'] is not None else b['hits']
            times = [round(max(0.0, (t - spec['s']) / spec['v']), 4) for t in blows]
        hits = []
        parts = PARTS.get(spec['anim'], [])
        for k, t in enumerate(times):
            h = {'time': t}
            if spec['damage']:
                row = '%s%s_%02d' % (GB, spec['damage'], k + 1)
                part = parts[min(k, len(parts) - 1)] if parts else None
                if part is None:
                    problems.append('%s/%s: no shape for the blows of %s' % (set_name, name, spec['anim']))
                h['damage'] = row
                known = damage.get(row)
                entry = {'cloud': spec['cloud'], 'index': k + 1, 'part': part, 'anim': spec['anim']}
                if known and (known['cloud'], known['part']) != (entry['cloud'], entry['part']):
                    problems.append('%s: made two ways (%s, %s)' % (row, known, entry))
                damage[row] = entry
            hits.append(h)
        if any(t > length + 1e-3 for t in times):
            problems.append('%s/%s: a blow after the move\'s end (%s, %.3f s)' % (set_name, name, times, length))
        m = {'name': name, 'set': set_name, 'animation': path(E + spec['anim']), 'build': True, 'notifies_from': path(notifies), 'hits': hits,
             'clip': [round(spec['s'], 4), round(e, 4)], 'speed': round(spec['v'], 4), 'kind': 'attack'}
        add(m, '%-9s %-26s %-38s %5.2f-%5.2f x%.3f = %5.2f s (Cloud %5.2f) blows %-26s Cloud %-26s %s' % (
            set_name, name, spec['anim'], spec['s'], e, spec['v'], length, c['length'], ','.join('%.2f' % t for t in times),
            ','.join('%.2f' % t for t in c['hits']), spec['note']))

    def piece(set_name, name, anim, start):
        notifies, c = cloud_source(set_name, name)
        if c is None:
            problems.append('%s/%s: Cloud has no move of that name' % (set_name, name))
            return
        b = beast(anim)
        if anim in ROOT_PIECES:
            # a dodge, step or dash: the beast's body (Base) moving with Cloud's root (his distance and timing); the
            # beast's own goes 6 to 12 m. A Cloud's move longer than the beast's is played faster to its length (Base
            # loops under a longer move).
            speed = round(max(1.0, c['length'] / b['length']), 4)
            m = {'name': name, 'set': set_name, 'animation': path(notifies), 'build': True, 'notifies_from': path(notifies), 'hits': [],
                 'base': path(E + anim), 'base_loop': False, 'speed': speed, 'kind': 'piece', 'mode': 'root',
                 'expect': {'cloud_length': c['length'], 'length': round(c['length'] / speed, 4), 'beast_travel': ROOT_TRAVEL.get(anim, {}).get('dist')}}
            add(m, '%-9s %-26s %-38s the beast\'s body on Cloud\'s root (%.2f s at x%.2f = %.2f s; the beast\'s own goes %s cm)' % (
                set_name, name, anim, c['length'], speed, c['length'] / speed, ROOT_TRAVEL.get(anim, {}).get('dist')))
            return
        want, avail = c['length'], b['length'] - start
        assert avail > 0.05, (name, anim, start)
        s, e, v = (start, start + want, 1.0) if avail >= want else (start, b['length'], avail / want)
        m = {'name': name, 'set': set_name, 'animation': path(E + anim), 'build': True, 'notifies_from': path(notifies), 'hits': [],
             'clip': [round(s, 4), round(e, 4)], 'speed': round(v, 4), 'kind': 'piece', 'mode': 'asis'}
        add(m, '%-9s %-26s %-38s %5.2f-%5.2f x%.3f = %5.2f s (Cloud %5.2f) piece' % (set_name, name, anim, s, e, v, (e - s) / v, want))

    def locomotion(set_name, name, base, forward, root_name):
        root = root_name or name
        src, c = cloud_source(set_name, root)
        if c is None:
            problems.append('%s/%s: Cloud has no %s' % (set_name, name, root))
            return
        b = beast(base)
        beast(forward)
        travel = LOCO.get(root, {}) if src.startswith(C0) else {}
        own = ROOT_TRAVEL.get(base, {})
        expect = {'cloud_length': c['length'], 'cloud_travel': travel.get('dist'), 'cloud_yaw': travel.get('yaw'),
                  'beast_travel': own.get('dist'), 'beast_yaw': own.get('yaw')}
        if not name.startswith(STRAFES) and name not in ROOT_LOCOMOTION:
            # forward, its starts, turns and stops: the beast's own as it is (its root moves it as the boss moves:
            # its walk as fast as Cloud's, its run twice his)
            m = {'name': name, 'set': set_name, 'animation': path(E + base), 'build': True, 'notifies_from': path(src), 'hits': [],
                 'clip': [0.0, 0.0], 'speed': 1.0, 'kind': 'locomotion', 'mode': 'asis', 'expect': dict(expect, length=b['length'], root_travel=own.get('dist'))}
            add(m, '%-9s %-26s the beast\'s %-30s as it is (%.2f s, %s cm, turns %s; Cloud\'s %s: %.2f s, %s cm, %s)' % (
                set_name, name, base, b['length'], own.get('dist'), own.get('yaw'), src.split('/PC0000_Cloud/')[1].split('.')[0], c['length'],
                travel.get('dist'), travel.get('yaw')))
            return
        # a strafe (it has none of its own) or a run's stop: the beast's walk or run with the root of Cloud's (Bone Map Trans=Trans)
        loop = name.endswith('_1') and not name.endswith(('_L180', '_R180'))
        loops = max(1, round(b['length'] / c['length'])) if loop else 0
        m = {'name': name, 'set': set_name, 'animation': path(src), 'build': True, 'notifies_from': path(src), 'hits': [],
             'base': path(E + base), 'base_forward': path(E + forward), 'base_loop': loop, 'speed': 1.0, 'kind': 'locomotion', 'mode': 'root',
             'expect': dict(expect, length=round(b['length'] if loop else c['length'], 4), root_travel=travel.get('dist'))}
        add(m, '%-9s %-26s base %-30s root %s%s' % (set_name, name, base, src.split('/PC0000_Cloud/')[1],
                                                    ', a loop: %d of Cloud\'s in the beast\'s %.2f s' % (loops, b['length']) if loop else ''))

    # Battle07: Operator mode and everything shared; Punisher mode's own attacks too
    for name, spec in ATTACKS.items():
        attack(SET, name, spec)
    for name, anim in BURST_CHAINS.items():
        _, c = cloud_source(SET, name)
        b = beast(anim)
        v = round(b['length'] / c['length'], 4)
        attack(SET, name, A(anim, 0.0, 0.0, v, at=c['hits'] or None, note='synergy ability (with a partner)'))
    for name, (anim, start) in sorted(PIECES.items()):
        if (SET, name) not in seen:
            piece(SET, name, anim, start)
    for name, (base, forward, root) in LOCOMOTION.items():
        locomotion(SET, name, base, forward, root)
    for (set_name, name), anim in AS_IS.items():
        add({'name': name, 'set': set_name, 'animation': path(anim), 'build': False, 'kind': 'as_is'}, '%-9s %-26s %s as it is' % (set_name, name, anim))
    for name, anim in COPIES.items():
        b = beast(anim)
        add({'name': name, 'set': SET, 'animation': path(E + anim), 'build': True, 'notifies_from': path(E + anim), 'hits': [],
             'clip': [0.0, round(b['length'], 4)], 'speed': 1.0, 'kind': 'copy'},
            '%-9s %-26s %s as it is (a copy: its effects without the boss\'s ability check)' % (SET, name, anim))
    for name, chain in CHAINS.items():
        for set_name in (SET, PSET):
            add({'name': name, 'set': set_name, 'animation': chain_part(chain[0]), 'then': [chain_part(p) for p in chain[1:]], 'build': False,
                 'kind': 'chain'}, '%-9s %-26s chain %s' % (set_name, name, ' + '.join(COPY.get(p, p) for p in chain)))
    # Battle08: Punisher mode's own; every other name Battle07's move as it is
    for name, spec in PUNISHER_ATTACKS.items():
        attack(PSET, name, spec)
    for name, (anim, start) in PUNISHER_PIECES.items():
        piece(PSET, name, anim, start)
    for name, (base, forward, root) in PUNISHER_LOCOMOTION.items():
        locomotion(PSET, name, base, forward, root)
    own8 = {m['name'] for m in moves if m['set'] == PSET}
    for m in list(moves):
        if m['set'] == SET and m['name'] not in own8 and m['kind'] != 'chain':
            animation = '%s/%s/%s.%s' % (BUILT, SET, m['name'], m['name']) if m['build'] else m['animation']
            add({'name': m['name'], 'set': PSET, 'animation': animation, 'build': False, 'kind': 'shared', 'from_set': SET},
                '%-9s %-26s Battle07\'s' % (PSET, m['name']))
    names7 = {m['name'] for m in moves if m['set'] == SET}
    wanted = {k.split('/')[1] for k in CLOUD if 'misiyo' not in k and '_test' not in k}
    missing = sorted(n for n in wanted if n not in names7 and n not in BLEND_SPACES)
    if missing:
        problems.append('Cloud\'s names with no move in Battle07: ' + ', '.join(missing))
    plan = {
        'plan': 'Vincent: the Galian Beast form (Battle07, Battle08) made of the Galian Beast\'s animations',
        'data_object': '/Game/RebirthSkelCompat/VincentGalian/DO_VincentGalian',
        'characters': ['PC0000_00_Cloud_Standard', 'PC0000_04_Cloud_ZackCostume', 'PC0000_12_Cloud_ZackCostumeDirty', 'PC0000_18_Cloud_ZackCostumeAge21',
                       'PC0000_19_Cloud_ZackCostumeDirtyAge21', 'PC0000_23_Cloud_ZackCostumeWet'],
        'character_skeleton': '/Game/Character/Player/PC0011_00_Vincent_Standard/Model/PC0011_00_Skeleton.PC0011_00_Skeleton',
        'beast_skeleton': SKELETON,
        'build_folder': BUILT,
        'build_chunk': 55,             # (pakchunk55: the project's packaging has 0 and 45 to 54)
        'requires_paks': ['VincentGalian_P', 'FullyPlayableVincentAssets_P'],
        'bone_map': 'Trans=Trans',
        'battle': [{'path': p, 'as_': s} for s in (SET, PSET) for p in SOURCES] + [{'path': FACIAL[0], 'as_': FACIAL[1]}],
        'blend_spaces': BLEND_SPACES,
        'moves': moves,
        'damage': damage,
        'built': sum(1 for m in moves if m['build']),
        'describe': sorted({m['animation'] for m in moves if m['build']} | {m['notifies_from'] for m in moves if m['build']} |
                           {m['base'] for m in moves if m.get('base')} | {m['base_forward'] for m in moves if m.get('base_forward')}),
    }
    json.dump(plan, open(out, 'w'), indent=1)
    kinds = {}
    for m in moves:
        kinds[m['kind']] = kinds.get(m['kind'], 0) + 1
    head = '%d moves, %d built: %s; %d damage rows\n' % (len(moves), plan['built'], ', '.join('%s %d' % kv for kv in sorted(kinds.items())), len(damage))
    open(report_path, 'w').write(head + '\n'.join(lines) + '\n\nPROBLEMS:\n' + ('\n'.join(problems) or 'none') + '\n')
    print(head + ('PROBLEMS:\n' + '\n'.join(problems) if problems else 'no problems'))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
