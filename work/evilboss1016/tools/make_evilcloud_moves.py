"""Evil Cloud's boss moves: in the boss Sephiroth fights (the final battle's PC0010_10_Sephiroth_Transform and the VR
battle's PC0010_20_Sephiroth_VRHard, both playing PC0010_Sephiroth_Transform's sets) Evil Cloud moves like Cloud and
keeps everything else of the boss's: every name the boss's abilities, AI and reactions play is built from one of Cloud's
animations with the boss's own gameplay notifies (damage, AI messages, cancel windows, super armor, warps, phase
changes), so its AI, HP, phases, timing and damage stay the boss's:
  * attacks: the part of Cloud's move around his blows, its speed chosen so the blows land where the boss's hits are
    (hits "boss": the boss's own hit times, the boss's notifies keep their times; a list: where Cloud's blows are, the
    boss's hits are moved there),
  * the boss's big moves are Cloud's: Octaslash -> Cross-Slash, the last phase's Octaslash -> Ascension, Octaslash Prime
    -> Infinity's End, Skewer -> Braver, Hell's Gate -> Focused Thrust, Zanshin -> Disorder and an elemental impulse,
    Blade Dance -> his dash strike, double slash and Mad Dash, Whisper Whirlwind -> Finishing Touch, Heartless Angel
    -> Ascension, Wicked Augment -> Prime Mode; the feeler lasers and Tempus Finis (the boss's sword hidden) -> his
    summoning, held; the spells -> his casts,
  * reactions with gameplay notifies (phase changes, AI messages) are Cloud's reactions with the boss's notifies; the
    others, his walks, runs, turns, idle and deaths are Cloud's as they are.
Built on Cloud's own skeleton (PC0000_00_Skeleton: his animations are copied exactly; the family plays them on Evil
Cloud's body with its own build).
    make_evilcloud_moves.py <survey.json> <out plan json> <out report txt>"""
import json, sys

T = '/Game/Motion/Player/PC0010_Sephiroth_Transform/'
C = '/Game/Motion/Player/PC0000_Cloud/'
CHARACTERS = ['PC0010_10_Sephiroth_Transform', 'PC0010_20_Sephiroth_VRHard']
SKELETON = '/Game/Character/Player/PC0000_00_Cloud_Standard/Model/PC0000_00_Skeleton.PC0000_00_Skeleton'
BUILD_FOLDER = '/Game/RebirthSkelCompat/Built/EvilCloudBoss'
BUILD_CHUNK = 52
DATA_OBJECT = '/Game/RebirthSkelCompat/EvilCloudBoss/DO_EvilCloudBoss'


def B(name, s=0.0, v=1.0, hits='boss', end=None, note=''):
    """A built move from Cloud's `name`: its clip from `s` (source seconds) at speed `v`; `end` (source seconds) when not
    the boss's length; hits 'boss' (the boss's own times), 'none', a list of times in the move, or ('blows', [source
    seconds of Cloud's blows]) for times where his blows land."""
    return dict(cloud=name, s=s, v=v, hits=hits, end=end, note=note)


def FULL(name, v=1.0, hits='none', note=''):
    """A loop: the whole of Cloud's `name` at speed `v` (its own length / v)."""
    return dict(cloud=name, s=0.0, v=v, hits=hits, end='full', note=note)


# the boss's names -> how Evil Cloud's move is made (Cloud's Battle00 unless 'B01/' leads the name)
MOVES = {
    # his Square combo: Cloud's 1st, 2nd, 3rd and his finisher
    'B_NAttack01_0': B('B_NAttack01_0', s=0.156, note='combo 1'),
    'B_NAttack02_0': B('B_NAttack02_0', note='combo 2'),
    'B_NAttack03_0': B('B_NAttack03_0', s=0.4045, v=1.15, note='combo 3'),
    'B_NAttack04_0': B('B_NAttack05_0', s=0.211, v=0.9, note="combo 4: Cloud's finisher"),
    # air combo, its air dash first
    'B_Avoid01_0': B('B_NAttackJ05_0', v=1.4, hits='none', end='full', note='air dash start'),
    'B_Avoid01_1': FULL('B_NAttackJ05_1', note='air dash'),
    'B_NAttackJ01_0': B('B_NAttackJ01_0', s=0.123, v=0.9, note='air 1'),
    'B_NAttackJ02_0': B('B_NAttackJ02_0', s=0.202, v=0.85, note='air 2'),
    'B_NAttackJ03_0': B('B_NAttackJ03_0', s=0.08, note='air 3'),
    # strong attacks
    'B_SAttack01_0': B('B01/B_SAttack01_1', s=0.24, note='a charged slash (Punisher)'),
    'B_SAttack02_0': B('B_WAttack01_0', v=0.944, note='his lunging slash'),
    'B_SAttack06_0': B('B_AtkBurst06_2', v=0.88, hits=('blows', [0.13, 0.36]), note="Counterstance's counter"),
    'B_SAttack08_0': B('B01/B_SAttackJ01_0', v=1.2, hits=[0.1, 0.425], end='full', note='jump attack: up'),
    'B_SAttack08_1': FULL('B01/B_SAttackJ01_1', hits=[0.0], note='jump attack: down (loop)'),
    'B_SAttack08_2': B('B01/B_SAttackJ01_2', s=0.05, note='jump attack: landing'),
    'B_SAttack10_0': B('B_WAttack02_0', s=0.11, hits=('blows', [0.29, 0.55, 0.62]), note='a three-hit lunge'),
    # Shadowy Chains
    'B_SAttack05_0': B('B01/B_SAttack06_2', s=0.18, hits=[0.0, 1.1], note='Shadowy Chains near'),
    'B_SAttack05_0_Comp': B('B01/B_SAttack06_2', s=0.18, hits=[0.0, 1.1], note='Shadowy Chains near'),
    'B_AtkZekkuu01_0': B('B_ChainCounter_A01_2', v=0.9655, hits=('blows', [0.0, 0.56]), note='Shadowy Chains far: the throw'),
    'B_AtkZekkuu01_0_Comp': B('B_ChainCounter_A01_2', v=0.9655, hits=('blows', [0.0, 0.56]), note='Shadowy Chains far: the throw'),
    'B_AtkZekkuu01_1': FULL('B_AtkBurst06_1', v=1.333, note='Shadowy Chains far: hold (Counterstance)'),
    'B_AtkZekkuu01_2': B('B_AtkBurst06_3', v=1.155, hits='none', end='full', note='Shadowy Chains far: end'),
    # spells (Shadow Flare, the -aga spells, Grip of Fate, Errant Whisper, The End Is Nigh, the elemental magic): his casts
    'B_AtkMag01_0': B('B_MagAttack02_0', v=0.835, hits='none', end='full', note='cast: start'),
    'B_AtkMag01_0_Comp': B('B_MagAttack02_0', v=0.835, hits='none', end='full', note='cast: start'),
    'B_AtkMag01_1': FULL('B_MagAttack02_1', note='cast: hold'),
    'B_AtkMag01_1_Comp': FULL('B_MagAttack02_1', note='cast: hold'),
    'B_AtkMag01_2': B('B_MagAttack02_2', v=0.8, note='cast: release'),
    'B_AtkMag01_2_Comp': FULL('B_MagAttack02_1', note='the pull: hold'),
    'B_AtkMag01_2_Comp1': B('B_MagAttack02_2', v=0.667, note='the pull'),
    'B_AtkMag01_2_CompMagic': B('B_MagAttack02_1', v=1.0605, note='a double cast'),
    'B_AtkMag01_3': B('B_MagAttack02_2', hits='none', note='cast: the call'),
    'B_AtkMag01_4': B('B_MagAttack02_1', note='cast: the barrage (loop)'),
    'B_AtkMag01_4_Fire_Comp': FULL('B_MagAttack02_1', note='Infernal Flare: hold'),
    'B_AtkMag01_4_Ice_Comp': FULL('B_MagAttack02_1', v=0.75, note='Great Tribulation: hold'),
    'B_AtkMag01_4_Lightning_Comp': FULL('B_MagAttack02_1', note='Keraunos: hold'),
    'B_AtkMag01_4_Wind_Comp': B('B_MagAttack02_1', note='Rapture'),
    'B_AtkMag01_5': B('B_MagAttack02_2', s=0.266, hits='none', note='cast: end'),
    # Zanshin: Disorder's two slashes; the second, an elemental impulse
    'B_AtkBurst01_0': B('B_AtkBurst07_0', s=0.47, note='Zanshin 1: Disorder'),
    'B_AtkBurst01_1': B('B_EleBurst01_0', note='Zanshin 2: an elemental impulse'),
    # Hell's Gate: Focused Thrust, then a mode-switch slash
    'B_AtkBurst02_0': B('B_AtkBurst02_0', note="Hell's Gate: Focused Thrust"),
    'B_AtkBurst02_1': B('B01/B_Change_03_0', v=0.963, note="Hell's Gate 2: a mode-switch slash"),
    # Octaslash: Counterstance as he readies, his dash, Cross-Slash; the last phase's, Ascension; Octaslash Prime,
    # Infinity's End; the game over, his victory pose
    'B_AtkLimit01_0': B('B_AtkBurst06_0', v=1.066, hits='none', end='full', note='Octaslash: ready (Counterstance)'),
    'B_AtkLimit01_1': FULL('B_AtkBurst06_1', note='Octaslash: ready, held'),
    'B_AtkLimit01_1_Comp': FULL('B_AtkBurst06_1', note='Octaslash: ready, held'),
    'B_AtkLimit01_1_Comp2': FULL('B_AtkBurst06_1', note='Octaslash: ready, held'),
    'B_AtkLimit01_2': B('B_NAttack01_1_0', v=0.89, hits='none', end='full', note='Octaslash: the dash'),
    'B_AtkLimit01_3': FULL('B_NAttack01_1_1', note='Octaslash: the dash (loop)'),
    'B_AtkLimit01_4': B('B_AtkLimit01_0', s=1.0, end='full', hits=[0.5, 0.6, 0.7, 0.99, 1.09, 1.19, 1.86, 1.96],
                        note="Octaslash: Cross-Slash (his eight hits on its three slashes)"),
    'B_AtkLimit01_3_Comp': B('B_AtkLimit02_0', s=1.85, hits=('blows', [2.41, 2.73, 3.11, 3.39, 3.82, 4.62, 5.37]),
                             note="the last phase's Octaslash: Ascension"),
    'B_AtkLimit01_5': B('B_AtkBurst04_0', s=1.69, end='full', note="Octaslash Prime: Infinity's End"),
    'B_AtkLimit01_5_Comp': B('B_AtkBurst04_0', s=1.69, end='full', note="Octaslash Prime: Infinity's End"),
    'B_AtkLimit01_6': B('B_Win01', hits='none', note='the game over: his victory pose'),
    # Skewer: Braver
    'B_AtkStab01': B('B_AtkBurst01_0', s=0.01, end='full', note='Skewer: Braver'),
    # Blade Dance: his dash, the dash strike, a double slash, Mad Dash
    'B_ChainTatakau_A01_0': B('B_NAttack01_1_0', v=0.8, hits='none', end='full', note='Blade Dance: the dash'),
    'B_ChainTatakau_A01_1': FULL('B_NAttack01_1_1', note='Blade Dance: the dash (loop)'),
    'B_ChainTatakau_A01_2': B('B_NAttack01_1_2', s=0.04, note='Blade Dance 1: his dash strike'),
    'B_ChainTatakau_A02_0': B('B_NAttack07_0', s=0.166, v=1.3, note='Blade Dance 2: a double slash'),
    'B_ChainTatakau_A03_0': B('B_ChainTatakau_B01_0', s=0.513, v=1.514, hits=('blows', [0.74, 1.83]), note='Blade Dance 3: Mad Dash'),
    # the warp to the middle: a dodge as he vanishes
    'B_Warp01_0': B('B_Avoid02', v=1.05, hits='none', end='full', note='the warp: a dodge'),
    'B_Idle01_1_Comp': B('B_Idle01_1', hits='none', note='after the warp'),
    # the feelers and wings: the feeler lasers and Tempus Finis hide his sword, so his summoning, held while they last
    'B_AtkFeelerLaser01_0': B('B_MagSummon01_0', v=1.273, hits='none', end='full', note='the feeler lasers: his summoning'),
    'B_AtkFeelerLaserL01_1': FULL('B_MagSummon01_1', v=0.2222, hits='boss', note='the feeler lasers: held 9 s'),
    'B_AtkFeelerLaserR01_1': FULL('B_MagSummon01_1', v=0.2222, hits='boss', note='the feeler lasers: held 9 s'),
    'B_AtkFeelerLaser01_2': B('B_MagSummon01_2', hits='none', note='the feeler lasers: end'),
    'B_AtkFeelerTornado01_0': B('B_AtkLimit03_0', s=0.87, note='Whisper Whirlwind: Finishing Touch'),
    'B_AtkFeelerTornado01_1': FULL('B_AtkBurst06_1', note='Whisper Whirlwind: in the storm (Counterstance)'),
    'B_AtkFeelerTornado01_2': B('B_AtkLimit03_0', s=7.0, hits='none', note="Whisper Whirlwind: Finishing Touch's last slashes"),
    'B_AtkFinalAttack01_0': B('B_MagSummon01_0', v=0.946, hits='none', end='full', note='Tempus Finis: his summoning'),
    'B_AtkFinalAttack01_1': FULL('B_MagSummon01_1', v=0.13333, hits='boss', note='Tempus Finis: held 15 s'),
    'B_AtkFinalAttack01_2': B('B_MagSummon01_2', hits='none', note='Tempus Finis: end'),
    'B_AtkTenshi01_0': B('B_AtkLimit02_0', v=0.615, end=0.41, hits='none', note='Heartless Angel: Ascension begins'),
    'B_AtkTenshi01_1': B('B_AtkLimit02_0', s=0.41, note='Heartless Angel: Ascension'),
    'B_SetFeeler01': B('B_AtkBurst09_0', v=1.078, hits='none', end='full', note='Wicked Augment: Prime Mode'),
    # reactions with the boss's gameplay notifies (phase changes, AI messages): Cloud's, as long as his own
    'B_DmgB01': FULL('B_DmgB01'), 'B_DmgF01': FULL('B_DmgF01'), 'B_DmgL01': FULL('B_DmgL01'), 'B_DmgR01': FULL('B_DmgR01'),
    'B_DmgB03_0': FULL('B_DmgB03_0'), 'B_DmgB03_1': FULL('B_DmgB03_1'), 'B_DmgB03_2': FULL('B_DmgB03_2'),
    'B_DmgF03_0': FULL('B_DmgF03_0'),
    'B_DmgBlowB01_0': FULL('B_DmgBlowB01_0'), 'B_DmgBlowF01_0': FULL('B_DmgBlowF01_0'),
    'B_DmgReflect01': FULL('B_DmgReflect01'), 'B_DmgStrikeB01_0': FULL('B_DmgStrikeB01_0'),
    'B_DmgUpperB01_0': FULL('B_DmgUpperB01_0'), 'B_DmgUpperB01_1': FULL('B_DmgUpperB01_1'),
    'B_DmgUpperF01_0': FULL('B_DmgUpperF01_0'), 'B_DmgUpperF01_1': FULL('B_DmgUpperF01_1'),
    'B_Fall01_1': FULL('B_Fall01_1'), 'B_Fall01_2': FULL('B_Fall01_2'),
    # lying down (Cloud has no loop of it: his fall's last pose, held)
    'B_DmgDownB01_1': B('B_DmgDownB01_0', s=0.9, v=0.0333, hits='none', end=0.933, note='lying down: his last pose held'),
    'B_DmgDownF01_1': B('B_DmgDownF01_0', s=0.9, v=0.0333, hits='none', end=0.933, note='lying down: his last pose held'),
    # staggered (Cloud has no stagger: his status ailment's start, loop and end)
    'B_DmgBurst01_0': FULL('B_Abnormal01_0', note='staggered'), 'B_DmgBurst01_1': FULL('B_Abnormal01_1', note='staggered (loop)'),
    'B_DmgBurst01_2': FULL('B_Abnormal01_2', note='staggered: end'),
    'B_DownBurstB01_0': FULL('B_DmgDownB01_0', note='down while staggered'), 'B_DownBurstF01_0': FULL('B_DmgDownF01_0', note='down while staggered'),
    # dodges and steps
    'B_Avoid01_2': B('B_AvoidJ10_2', v=1.2, hits='none', end='full', note='air dash end'),
    'B_Avoid02_2': B('B_Avoid02', s=0.25, hits=[0.0], note='a dodge with a hit'),
    'B_StepB01': FULL('B_Avoid02', v=0.764, note='a step back'),
    'B_StepB01_Comp': FULL('B_Avoid02', v=0.848, note='a step back'), 'B_StepB01_Comp2': FULL('B_Avoid02', v=0.848, note='a step back'),
    'B_StepB01_CompMagic': FULL('B_MagAttack02_1', v=0.8816, hits='boss', note='a step back and a cast'),
    # in the air (the winged phases): Cloud's falls, staggers and getting up
    'B_DmgBurstA01_0': FULL('B_Abnormal01_0', note='staggered in the air'), 'B_DmgBurstA01_1': FULL('B_Abnormal01_1', note='staggered in the air (loop)'),
    'B_DmgBurstA01_2': FULL('B_Abnormal01_2', note='staggered in the air: end'),
    'B_DmgDown01_1': FULL('B_DmgDownB01_0', note='knocked down'), 'B_DmgDown01_2': FULL('B_DmgDownB01_2', note='getting up'),
    'B_DmgDownSword01_0': FULL('B_DmgRecoverF01', note='knocked down (sword)'), 'B_DmgDownWing01_0': FULL('B_DmgRecoverB01', note='knocked down (wing)'),
    'B_DmgFall01_0': FULL('B_Fall01_1', v=0.857, note='hit in the air'), 'B_DmgFall01_1': FULL('B_Fall01_1', v=0.75, note='falling'),
    'B_DmgFall01_2': B('B_Fall01_2', hits='none', note='landing'),
    'B_DmgFallDownWing01_0': FULL('B_DmgRecoverB01', note='fallen (wing)'),
}

# the boss's names played as Cloud's of that name, as they are (no gameplay notifies of the boss's in them)
AS_IS_PREFIXES = ('B_Walk', 'B_Run', 'B_Turn', 'B_StrafingWalk', 'B_Die', 'B_DownDie', 'B_Idle01_1', 'B_Dmg01_Add', 'B_DmgBlowB01_1',
                  'B_DmgBlowF01_1', 'B_DmgDownB01_0', 'B_DmgDownB01_2', 'B_DmgDownB02', 'B_DmgDownB03', 'B_DmgDownF01_0', 'B_DmgDownF01_2',
                  'B_DmgDownF02', 'B_DmgDownF03', 'B_DmgF03_1', 'B_DmgF03_2', 'B_DmgRecover', 'B_DmgStrikeB01_1', 'B_DmgStrikeF01')
# left as the boss's (not played by the boss's abilities, or an additive pose)
LEFT = {'B_AtkMag01_6', 'B_NPAttack01', 'B_DmgBurst01_Add', 'B_AtkLimit02_0', 'B_AtkLimit02_1', 'B_AtkStab02', 'B_NAttackWing02_0',
        'B_NAttackWing04_0', 'B_SAttackWing02_0', 'B_SAttackWing06_0'}


def groups(hits):
    out = []
    for t in sorted(hits):
        if not out or t - out[-1] >= 0.05:
            out.append(t)
    return out


def main(survey_path, out, report_path):
    survey = json.load(open(survey_path, encoding='utf-8'))
    by = {x['path']: x for x in survey}
    sets = {x['path']: x['animations'] for x in survey if x['class'] == 'EndAnimSet'}
    boss_sets = [(p, p.rsplit('/', 1)[1].split('.')[0]) for p in sets if p.startswith(T)]
    where = {}
    for p, set_name in boss_sets:
        for name, anim in sets[p].items():
            where.setdefault(name, []).append((set_name, anim))
    cloud = {}
    for set_name in ('Battle00', 'Battle01'):
        for name, anim in sets[C + set_name + '.' + set_name].items():
            cloud[set_name + '/' + name] = anim
    used = set(open(survey_path.replace('survey.json', 'boss_anims.txt')).read().split('distinct animation names:')[1].split())

    def cloud_path(name):
        key = name if name.startswith('B01/') else 'B00/' + name
        key = key.replace('B00/', 'Battle00/').replace('B01/', 'Battle01/')
        assert key in cloud, ('Cloud has no', name)
        return cloud[key]

    moves, lines, problems = [], [], []
    for name in sorted(where):
        for set_name, boss_path in where[name]:
            boss = by.get(boss_path, {})
            if name in MOVES:
                m = MOVES[name]
                src_path = cloud_path(m['cloud'])
                src = by[src_path]
                src_len = src['length']
                boss_len = boss.get('length', 0.0)
                rate = boss.get('rate_scale', 1) or 1
                target = boss_len / rate
                s, v = m['s'], m['v']
                if m['end'] == 'full':
                    e = src_len
                elif m['end'] is not None:
                    e = m['end']
                else:
                    e = min(src_len, s + target * v)
                assert 0 <= s < e <= src_len + 1e-4, (name, s, e, src_len)
                length = (e - s) / v
                bh = groups(boss.get('hits', []))
                if m['hits'] == 'boss':
                    hits = [round(t, 4) for t in bh]
                elif m['hits'] == 'none':
                    hits = []
                elif isinstance(m['hits'], tuple):
                    hits = [round((t - s) / v, 4) for t in m['hits'][1]]
                else:
                    hits = [round(t, 4) for t in m['hits']]
                if hits and (max(hits) > length + 1e-3 or min(hits) < 0):
                    problems.append('%s: a hit outside the move (%s, %.3f s)' % (name, hits, length))
                if len(hits) != len(bh) and not (m['hits'] == 'none' and not bh):
                    problems.append('%s: %d hit(s) for the boss\'s %d' % (name, len(hits), len(bh)))
                move = {'name': name, 'set': set_name, 'animation': src_path, 'build': True, 'notifies_from': boss_path, 'hits': hits}
                if s > 0 or e < src_len - 1e-4:
                    move['clip'] = [round(s, 4), round(e, 4)]
                if abs(v - 1.0) > 1e-4:
                    move['speed'] = round(v, 4)
                moves.append(move)
                lines.append('%-26s %-13s %6.3f s  <- %-22s %5.2f-%5.2f x%.3f = %6.3f s  boss hits %-28s move hits %-30s %s' % (
                    name, set_name, target, m['cloud'], s, e, v, length, ','.join('%.2f' % t for t in bh), ','.join('%.2f' % t for t in hits), m['note']))
            elif name in LEFT:
                lines.append('%-26s %-13s left as the boss\'s' % (name, set_name))
            elif name.startswith(AS_IS_PREFIXES):
                key = 'Battle00/' + name
                if key not in cloud:
                    lines.append('%-26s %-13s left as the boss\'s (Cloud has none of that name)' % (name, set_name))
                    continue
                moves.append({'name': name, 'set': set_name, 'animation': cloud[key], 'build': False})
                lines.append('%-26s %-13s Cloud\'s as it is' % (name, set_name))
            else:
                problems.append('%s (%s) is not planned' % (name, set_name))
    missing = sorted(n for n in used if n not in MOVES)
    if missing:
        problems.append('the boss\'s abilities play %s, which no move is made for' % ', '.join(missing))
    for name in MOVES:
        if name not in where:
            problems.append('%s is not one of the boss\'s' % name)
    plan = {
        'data_object': DATA_OBJECT,
        'characters': CHARACTERS,
        'character_skeleton': SKELETON,
        'build_folder': BUILD_FOLDER,
        'build_chunk': BUILD_CHUNK,
        'requires_paks': ['FullyPlayableSephirothDataAssets_P'],
        'battle': [{'path': p, 'as_': n} for p, n in boss_sets],
        'moves': moves,
        'describe': sorted({m['animation'] for m in moves} | {m['notifies_from'] for m in moves if m['build']}),
    }
    json.dump(plan, open(out, 'w'), indent=1)
    built = sum(1 for m in moves if m['build'])
    head = '%d moves for the boss\'s sets (%d built from Cloud\'s with the boss\'s notifies, %d Cloud\'s as they are)\n' % (
        len(moves), built, len(moves) - built)
    open(report_path, 'w', encoding='utf-8').write(head + '\n'.join(lines) + '\n\nPROBLEMS:\n' + ('\n'.join(problems) or 'none') + '\n')
    print(head + ('PROBLEMS:\n' + '\n'.join(problems) if problems else 'no problems'))


if __name__ == '__main__':
    main(*sys.argv[1:4])
