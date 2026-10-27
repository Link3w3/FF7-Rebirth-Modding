"""The Galian Beast form's data (Create a Character System 3.7.5), in the two containers of Vincent's that hold tables:

FullyPlayableVincentAssets_P (the installed one: the gun shop's, utoc b0b4a3bf; every other package byte for byte):
  * BattleDamageSource (its table, the gun rows in it as they are), new rows PC0011_GB_*:
      - the beast's blows in his moves (galian_moves.json "damage": Square's combo, the dash and air attacks, Punisher
        mode's, synergy): each Cloud's row of that move (power x2, its reaction, stagger and ATB build-up) struck from
        where the beast's blow lands (its claws, feet, tail or body: the shape of the boss's row of that blow, and its
        hit effect),
      - the beast's commands and limit breaks: copies of the boss's rows (the Shinra Manor's field table: they are not in
        the resident one) made a player's: no enemy-attack flags (Flag0 bits 30, 31: a row with them hurts nothing a
        player owns), a player's stagger build-up and power, a limit break's flags (Cloud's), the rows they name renamed
        with them; the grab of the boss's lunge (a sync with the player it pounces on) a plain blow,
  * BattleAbility (the game's resident table, checked by its hash, added): the beast's commands (5), the abilities in place
    of the ones his weapons give (PC0000_AtkBurst01..10) and its two limit breaks, PC0011_GB_*: the boss's ability rows
    made a player's as Bizarro Sephiroth's are (Cloud's Infinity's End's player fields; the limit breaks Cross-Slash's
    row), each playing the boss's animation (or a chain of them, or a copy: galian_moves.json) and striking with its
    rows (ReplaceDamageSourceID: every damage notify of what it plays, "?" and "?_<suffix>", is checked to have its row),
  * CharaSpec: Cloud's six rows (Vincent, the prologue's Cloud too) list the sets Battle07, Battle08 and Facial07 and load
    the beast's effect pack and sound bank.
zzVincentGunShop_P (the installed one: it holds the resident text): the help texts and the new names.
    build_galian_data.py <out dir (new)>"""
import contextlib, hashlib, io, json, os, re, sys
sys.path[:0] = ['/work/sephatb/tools', '/work/iostore', '/work/cs', '/work/tools',
                '/work/evil1013/tools', '/work/swap1012/tools', '/work/vincentfix',
                '/work/weap1012/tools', '/work/shooter1016/tools', '/work/prologue1016/tools',
                '/work/sephforms/tools', '/work/dirgegun1017/tools']
import build_atb as B
import build_dirge_paks as P
import iostore_write as W
import txtres
from iostore import Toc

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = 'FullyPlayableVincentAssets_P'
SHOP = 'zzVincentGunShop_P'
BASE = '/work/gunshop1017/out1'                # installed (the PC's ~mods\FullyPlayableVincentPaks, 2026-10-17)
BASE_MD5 = {ASSETS: 'b0b4a3bf', SHOP: '3c30ffa6'}         # (utoc md5s as the PC has them)
GAME3 = '/work/seph1013/pakchunk3-WindowsNoEditor.utoc'   # the PC's (md5 4d6164d1...)
GAME_ABILITY = '/work/seph1013/tables/game_BattleAbility.uasset'
FIELD_ABILITY = '/work/galian1016/pkgs/DataObject__Field__2650-NIBLS__BattleAbility.uasset'
FIELD_DAMAGE = '/work/galian1016/pkgs/DataObject__Field__2650-NIBLS__BattleDamageSource.uasset'
PLAN = os.path.join(HERE, 'plan', 'galian_moves.json')
SURVEY = os.path.join(HERE, 'survey', 'survey.json')     # the beast's animations' notifies (the editor survey)
ABILITY = 'DataObject/Resident/BattleAbility.uasset'
DAMAGE = 'DataObject/Resident/BattleDamageSource.uasset'
CHARASPEC = 'DataObject/Resident/CharaSpec.uasset'
TEXT = 'Text/US/Resident_TxtRes.uasset'
E = '/Game/Motion/Enemy/EB2160_VincentValentine/'
SET_ORDER = ['Battle00', 'Battle00_Comp', 'Battle02', 'Battle01']   # Battle07's sources (the first with a name wins)

ROWS = ['PC0000_00_Cloud_Standard', 'PC0000_04_Cloud_ZackCostume', 'PC0000_12_Cloud_ZackCostumeDirty', 'PC0000_18_Cloud_ZackCostumeAge21',
        'PC0000_19_Cloud_ZackCostumeDirtyAge21', 'PC0000_23_Cloud_ZackCostumeWet']
ADD_SETS = ['Battle07', 'Battle08', 'Facial07']
ADD_EFFECTS = ['EB2160_VincentValentine_Effect__Pack']
ADD_SOUNDS = ['SE_EB2160_00_VincentValentine_Standard']

COMBO_POWER = 2.0                     # the beast's blows in his moves: Cloud's power x2
ENEMY_FLAGS = (1 << 30) | (1 << 31)   # Flag0 of an enemy's attack (the game's ally copies of enemy rows drop them)
LIMIT_FLAG, LIMIT_HOLD = 1 << 11, 1 << 5   # Flag0 of Cloud's limit breaks' rows (all; all but the last blow)
PLAYER_BP = (1.0, 2.0)                # a player's stagger build-up (BPAttack, coefficient)
LIMIT_BP, LIMIT_LAST_BP = (0.0, 1.0), (50.0, 1.0)   # Ascension's, Finishing Touch's
HEAVY_FEEL, LIGHT_FEEL = ('hitslow06', 'FFB_Effect3'), ('hitslow61', 'FFB_Effect0')   # (HitSlowID, rumble: Infinity's End's, the combo's)
SHAPE = ['CreateBasePos', 'CreatePartName', 'TargetBase', 'TargetName', 'CollisionType', 'CollisionParameter_Array', 'CreatePartOffsetX',
         'CreatePartOffsetY', 'CreatePartOffsetZ', 'CreatePartOffsetPitch', 'CreatePartOffsetYaw', 'CreatePartOffsetRoll', 'TargetOffsetX',
         'TargetOffsetY', 'TargetOffsetZ', 'CreatePartOffsetDirectionType', 'TargetOffsetDirectionType']
HIT_EFFECT = ['HitEffectResourceName_Array', 'HitEffectResourceCategory_Array', 'HitEffectAttachCharacter_Array', 'HitEffectAttachHitLocation_Array']
# shapes of the beast's own for blows the boss's rows strike from a chaos arm (Attach_Weapon_*02: its phase 2 limbs)
CUSTOM = {
    '+LHand': dict(base='EB2160_00_ClawRaise_Pursuit_Finish', CreatePartName='L_Hand_a', CollisionParameter_Array=[200.0]),
    '+RClaw': dict(base='EB2160_00_ClawRaise', CreatePartName='R_Hand_a', TargetName='R_Forearm_a', CollisionParameter_Array=[120.0]),
    '+Roar': dict(base='EB2160_00_Roar', CollisionParameter_Array=[450.0]),
}
# the boss's lunge grabs the player it pounces on (a sync action of the boss and Cloud's party): a player's is a blow
GRAB = {'HitReactionParamID_Array': [], 'HitReactionType_Array': [3], 'HitTarget3': 1}
LUNGE = dict(GRAB, HitReactionParam_Array=[400.0, 350.0], AerialHitReactionParam_Array=[400.0, 300.0],   # (Skyward Slash's knock-back)
             BPAttack=2.0, BPAttackDamageCoefficient=9.0)                                              # (Focused Thrust's stagger)
POUNCE = dict(GRAB, HitReactionParam_Array=[100.0, 100.0], AerialHitReactionParam_Array=[100.0, 100.0])  # (the mauling's: it stays put)
TWICE = {'HitGroupName': None}        # one row struck by two blows of a chain (a hit group lets it hit a foe once)


def ability(key, base, name, help, atb, anim, kind, rows):
    """A beast's ability: `base` the boss's ability row it is made from, `anim` what it plays (a Battle07 name), `rows`
    {the boss's damage row: (suffix of its row: key + suffix, power (None: the boss's), overrides)}."""
    return dict(key=key, base=base, name=name, help=help, atb=atb, anim=anim, kind=kind,
                rows={old: (key + v[0], v[1], v[2] if len(v) > 2 else {}) for old, v in rows.items()})


GB = 'PC0011_GB_'
ABILITIES = [
    # --- the command menu (5)
    ability(GB + 'BestialFlare', 'EB2160_00_BeastFlare', '$bt_Vincent_BeastFlare', 'Hurl a ball of chaotic flame that bursts on impact.', 1,
            'B_AtkBeastFlare01', 'command', {'EB2160_00_BeastFlare': ('', None), 'EB2160_00_BeastFlare_Explosion': ('_Explosion', 650)}),
    ability(GB + 'PrimalRoar', 'EB2160_00_Roar', '$bt_Vincent_Roar', 'Let out a deafening roar that blasts back every foe nearby.', 1,
            'B_AtkRoar01', 'command', {'EB2160_00_Roar': ('', 400)}),
    ability(GB + 'SkullCrusher', 'EB2160_00_JumpStump', '$bt_Vincent_JumpStump', 'Leap onto a foe and crush it underfoot, then stomp it again and again.', 1,
            'B_GB_SkullCrusher01', 'command',
            {'EB2160_00_JumpStump': ('', 300), 'EB2160_00_JumpStump_Pursuit_00': ('_00', 120), 'EB2160_00_JumpStump_Pursuit_01': ('_01', 80),
             'EB2160_00_JumpStump_Pursuit_02': ('_02', 80), 'EB2160_00_JumpStump_Pursuit_03': ('_03', 110)}),
    ability(GB + 'HoppingSweep', 'EB2160_00_CleaveKick', '$bt_Vincent_CleaveKick', 'Hop in with a cleaving kick, then sweep with tail and claw.', 1,
            'B_GB_HoppingSweep01', 'command',
            {'EB2160_00_CleaveKick': ('', 280), 'EB2160_00_CleaveKick_Pursuit_Tail': ('_Tail', 200), 'EB2160_00_CleaveKick_Pursuit_RFoot': ('_RFoot', 200)}),
    ability(GB + 'SomersaultKick', 'EB2160_00_SummerSalt', '$bt_Vincent_SummerSalt', 'Flip into a rising kick, then pounce on the foe.', 1,
            'B_GB_SomersaultKick01', 'command',
            {'EB2160_00_SummerSalt': ('', 300), 'EB2160_00_SummerSalt_Pursuit_Body': ('_Body', 130), 'EB2160_00_SummerSalt_Pursuit_R': ('_R', 130),
             'EB2160_00_SummerSalt_Pursuit_L': ('_L', 130)}),
    # --- in place of the abilities his weapons give (weapon_abilities below)
    ability(GB + 'FollowUp', 'EB2160_00_JumpStumpChaos_Pursuit_Finish', '$bt_Vincent_Pursuit', 'Spring high and slam a foe into the ground.', 1,
            'B_GB_FollowUp01', 'weapon', {'EB2160_00_JumpStumpChaos_Pursuit_Finish': ('', 650)}),
    ability(GB + 'SavageLunge', 'EB2160_00_BerserkDance', '$PC0011_GB_SavageLunge', 'Lunge at a foe with a savage claw. Greatly increases the stagger gauge.', 1,
            'B_GB_AtkBerserkDance01', 'weapon', {'EB2160_00_BerserkDance': ('', 400, LUNGE)}),
    ability(GB + 'SkywardSlash', 'EB2160_00_ClawRaise', '$bt_Vincent_ClawRaise', 'Rake upward with a claw, rush in, and finish with the other claw.', 1,
            'B_GB_SkywardSlash01', 'weapon',
            {'EB2160_00_ClawRaise': ('', 300), 'EB2160_00_ClawRaise_Pursuit_Rush': ('_Rush', 60), 'EB2160_00_ClawRaise_Pursuit_Finish': ('_Finish', 400)}),
    ability(GB + 'GlaiveCrash', 'EB2160_00_ChaosGlaive_Pursuit', '$PC0011_GB_GlaiveCrash', 'Leap up and crash down in a burst of chaos that engulfs foes all around.', 2,
            'B_AtkChaosGlaive02', 'weapon', {'EB2160_00_ChaosGlaive_Pursuit': ('', 1000)}),
    ability(GB + 'PrimalFury', 'EB2160_00_RoarChaos_Pursuit', '$PC0011_GB_PrimalFury', 'Unleash a roar of chaos that strikes everything around again and again.', 1,
            'B_AtkRoar02', 'weapon', {'EB2160_00_RoarChaos_Pursuit': ('', 100)}),
    ability(GB + 'ChaosSweep', 'EB2160_00_CleaveKickChaos_Pursuit_Finish', '$PC0011_GB_ChaosSweep', 'Sweep a foe away with a claw wreathed in chaos.', 1,
            'B_AtkCleaveKick02_1', 'weapon', {'EB2160_00_CleaveKickChaos_Pursuit_Finish': ('', 600, {'CreatePartName': 'L_Hand_a'})}),
    ability(GB + 'ChaosAssault', 'EB2160_00_ChaosRush', '$bt_Vincent_ChaosRush', 'Rush through a foe in a blur, then crash down on it.', 1,
            'B_GB_ChaosAssault01', 'weapon', {'EB2160_00_ChaosRush': ('', 330, TWICE)}),
    ability(GB + 'ChaosStomp', 'EB2160_00_JumpStumpChaos_Pursuit', '$PC0011_GB_ChaosStomp', 'Stomp the ground again and again, battering every foe in front of you.', 1,
            'B_GB_ChaosStomp01', 'weapon', {'EB2160_00_JumpStumpChaos_Pursuit': ('', 100)}),
    ability(GB + 'ChaosGlaives', 'EB2160_00_ChaosGlaive', '$bt_Vincent_ChaosGrave', 'Call down blades of chaos on every foe around you.', 2,
            'B_AtkChaosGlaive01', 'weapon', {'EB2160_00_ChaosGlaive': ('', 950)}),
    ability(GB + 'ChaosClaw', 'EB2160_00_ClawRaiseChaos_Pursuit_Finish', '$PC0011_GB_ChaosClaw', 'Rake a foe twice with a claw of chaos.', 1,
            'B_GB_ChaosClaw01', 'weapon',
            {'EB2160_00_ClawRaiseChaos_Pursuit_Finish': ('', 380, dict(TWICE, CreatePartName='L_Hand_a', CollisionParameter_Array=[200.0]))}),
    # --- limit breaks
    ability(GB + 'SavageBeast', None, '$bt_Vincent_BerserkDance', 'Pounce on a foe and rend it in a frenzy of claws, fangs and tail.', 0,
            'B_GB_SavageBeast01', 'limit',
            dict({'EB2160_00_BerserkDance': ('', 300, POUNCE), 'EB2160_00_BerserkDance_Pursuit_Finish': ('_Finish', 800)},
                 **{'EB2160_00_BerserkDance_Pursuit_%02d' % k: ('_%02d' % k, 130) for k in range(9)})),
    ability(GB + 'ChaoticImpulse', None, '$bt_Vincent_PillarCleave', 'Roar with chaos, rain blades of it on every foe around you, then crash down among them.', 0,
            'B_GB_ChaoticImpulse01', 'limit', {'EB2160_00_ChaosGlaive': ('', 800)}),
]
BY_KEY = {a['key']: a for a in ABILITIES}
LAST = {GB + 'SavageBeast_Finish', GB + 'ChaoticImpulse'}   # the limit breaks' last blows (all of Chaotic Impulse's: one row)
NEW_NAMES = {'$PC0011_GB_SavageLunge': 'Savage Lunge', '$PC0011_GB_PrimalFury': 'Primal Fury', '$PC0011_GB_GlaiveCrash': 'Glaive Crash',
             '$PC0011_GB_ChaosSweep': 'Chaos Sweep', '$PC0011_GB_ChaosStomp': 'Chaos Stomp', '$PC0011_GB_ChaosClaw': 'Chaos Claw'}
COMMANDS = [a['key'] for a in ABILITIES if a['kind'] == 'command']
LIMITS = [a['key'] for a in ABILITIES if a['kind'] == 'limit']
# Cloud's weapon abilities (Braver, Focused Thrust, Triple Slash, Infinity's End, Blade Burst, Counterstance, Disorder (and
# its Punisher mode row), Firebolt Blade, Prime Mode, Aerial Onslaught) -> the beast's in the form
WEAPONS = {'PC0000_AtkBurst01': GB + 'FollowUp', 'PC0000_AtkBurst02': GB + 'SavageLunge', 'PC0000_AtkBurst03': GB + 'SkywardSlash',
           'PC0000_AtkBurst04': GB + 'GlaiveCrash', 'PC0000_AtkBurst05': GB + 'PrimalFury', 'PC0000_AtkBurst06': GB + 'ChaosSweep',
           'PC0000_AtkBurst07': GB + 'ChaosAssault', 'PC0000_AtkBurst07_Brave': GB + 'ChaosAssault', 'PC0000_AtkBurst08': GB + 'ChaosStomp',
           'PC0000_AtkBurst09': GB + 'ChaosGlaives', 'PC0000_AtkBurst10': GB + 'ChaosClaw'}
PLAYER_TEMPLATE = 'PC0000_AtkBurst04'    # Infinity's End: a player's ATB ability
PLAYER_FIELDS = ('ReactionInfluenceID', 'Flag0', 'InputBufferTime', 'KeepValue', 'ActionCategory')   # (as Bizarro Sephiroth's)
COMMON_OVERRIDES = {'CameraSequenceID': None, 'ReactionCondition_Array': [], 'ReactionConditionParameterValue_Array': [], 'ReactionType_Array': [],
                    'ReactionParameterString_Array': [], 'AnimationParameter_Array': [], 'AnimationSelectType_Array': []}
LIMIT_TEMPLATE = 'PC0000_Limit001'       # Cross-Slash


def quiet(f, *a):
    with contextlib.redirect_stdout(io.StringIO()):
        return f(*a)


def fields(t):
    return [f[0][0] for f in t.fields]


def name_fields(t):
    return [f[0][0] for f in t.fields if f[1] == 11]


def md5_8(path):
    return hashlib.md5(open(path, 'rb').read()).hexdigest()[:8]


def game_table(path, name):
    """A table of the game's, checked against pakchunk3's hash of it."""
    data = open(path, 'rb').read()
    toc = Toc(GAME3)
    i = [k for k, p in toc.files.items() if p.endswith('/' + name)][0]
    assert toc.b[toc.metas_off + 33 * i:toc.metas_off + 33 * i + 20] == hashlib.sha1(data).digest(), ('not the game\'s', name)
    return data


def anim_key(path):
    """'/Game/Motion/Enemy/EB2160_VincentValentine/Battle01/B_AtkRoar02.B_AtkRoar02' -> 'Battle01/B_AtkRoar02'"""
    assert path.startswith(E), path
    return path[len(E):].split('.')[0]


def damage_ids():
    """The damage source ids each of the beast's animations names in its notifies ('?' for the ability's own)."""
    out = {}
    for x in json.load(open(SURVEY)):
        if not x['path'].startswith(E) or x['class'] == 'EndAnimSet':
            continue
        ids = []
        for n in x.get('notifies', []):
            if 'BattleDamage' in n['class']:
                st = n.get('settings') or {}
                ids += re.findall(r'"([^"]*)"', st.get('DamageSourceIDs', '"?"')) or ['?']
        out[anim_key(x['path'])] = (x['class'], ids)
    return out


def plays(plan, anim, beast):
    """What a Battle07 name plays: the beast's animations (set/name), through the plan's chains, copies and aliases."""
    moves = {m['name']: m for m in plan['moves'] if m['set'] == 'Battle07'}
    built = plan['build_folder'] + '/Battle07/'
    m = moves.get(anim)
    if m is None:
        for s in SET_ORDER:
            if s + '/' + anim in beast:
                return [s + '/' + anim]
        raise AssertionError((anim, 'is not a name of Battle07'))
    parts = [m['animation']] + m.get('then', [])
    out = []
    for p in parts:
        if p.startswith(built):
            copy = moves[p[len(built):].split('.')[0]]
            assert copy['kind'] == 'copy', p
            p = copy['animation']
        out.append(anim_key(p))
    assert m['kind'] in ('chain', 'as_is', 'copy'), (anim, m['kind'])
    return out


def to_player(ds, row, key, kind, power, over):
    """A copy of a boss's row made a player's (in place); returns what changed, for the report."""
    flags = ds.get(row, 'Flag0')
    new = flags & ~ENEMY_FLAGS
    if kind == 'limit':
        new |= LIMIT_FLAG | (0 if key in LAST else LIMIT_HOLD)
    ds.set(row, 'Flag0', new)
    if power is not None:
        assert ds.get(row, 'PowerType') == 0, (key, 'not plain damage')
        ds.set(row, 'Power', int(power))
    bp = (LIMIT_LAST_BP if key in LAST else LIMIT_BP) if kind == 'limit' else PLAYER_BP
    ds.set(row, 'BPAttack', bp[0])
    ds.set(row, 'BPAttackDamageCoefficient', bp[1])
    # a player's hit stop and controller rumble (the boss's rows have none): Infinity's End's for a big blow, the combo's
    heavy = ds.get(row, 'Power') >= 600 and max(1, ds.get(row, 'HitCount')) == 1
    if not ds.get(row, 'HitSlowID'):
        ds.set(row, 'HitSlowID', HEAVY_FEEL[0] if heavy else LIGHT_FEEL[0])
    if not ds.get(row, 'HitForceFeedbackFileName'):
        ds.set(row, 'HitForceFeedbackFileName', HEAVY_FEEL[1] if heavy else LIGHT_FEEL[1])
    for f, v in over.items():
        ds.set(row, f, v)
    return 'power %4d x%d, Flag0 %d -> %d, BP %s %s, %s %s, reaction %s, shape %s %s %s r%s%s' % (
        ds.get(row, 'Power'), max(1, ds.get(row, 'HitCount')), flags, new, ds.get(row, 'BPAttack'), ds.get(row, 'BPAttackDamageCoefficient'),
        ds.get(row, 'HitSlowID'), ds.get(row, 'HitForceFeedbackFileName'),
        ds.get(row, 'HitReactionType_Array'), ds.get(row, 'CollisionType'), ds.get(row, 'CreatePartName'), ds.get(row, 'TargetName') or '',
        ds.get(row, 'CollisionParameter_Array'), (' (' + ', '.join(sorted(over)) + ')') if over else '')


def main(out):
    assert not os.path.exists(out), out + ' exists (use a new folder)'
    for name, want in BASE_MD5.items():
        assert md5_8(os.path.join(BASE, name + '.utoc')) == want, (name, 'is not the installed one')
    plan = json.load(open(PLAN))
    beast = damage_ids()
    chunks, store = P.read(os.path.join(BASE, ASSETS + '.utoc'))
    entries = [P.entry(c, store[c['id64']]) for c in chunks if c['type'] == 2]
    paths = [c['path'] for c in chunks]
    report = []

    def table_at(path):
        return quiet(B.Table, chunks[paths.index(path)]['data'])

    def put(path, data):
        k = paths.index(path)
        chunks[k]['data'] = data
        e = [x for x in entries if x['id'] == chunks[k]['id64']][0]
        assert e['size'] >> 60 == 0, path
        e['size'] = len(data)

    ds = table_at(DAMAGE)
    cs = table_at(CHARASPEC)
    ab = quiet(B.Table, game_table(GAME_ABILITY, ABILITY))
    assert ABILITY not in paths, 'the base has an ability table already'
    fab = quiet(B.Table, open(FIELD_ABILITY, 'rb').read())
    fds = quiet(B.Table, open(FIELD_DAMAGE, 'rb').read())
    assert fields(fds) == fields(ds) and fields(fab) == fields(ab), 'the field tables have other fields'
    ds0 = {k: list(ds.row(k)) for k in ds.at}
    ab0 = {k: list(ab.row(k)) for k in ab.at}
    cs0 = {k: list(cs.row(k)) for k in cs.at}
    names11 = name_fields(ds)

    # ---- 1. the beast's blows in his moves: Cloud's rows struck from the beast's body
    report.append('Damage: the beast\'s blows in his moves (%d), Cloud\'s rows x%.1f from the boss\'s shapes:' % (len(plan['damage']), COMBO_POWER))
    for key, d in sorted(plan['damage'].items()):
        assert key not in ds.at, key
        cloud_rows = sorted(k for k in ds.at if k.startswith(d['cloud'] + '_') and k[len(d['cloud']) + 1:].isdigit() and ds.get(ds.row(k), 'Power') > 0)
        assert cloud_rows, (key, 'Cloud has no rows', d['cloud'])
        src = cloud_rows[min(d['index'], len(cloud_rows)) - 1]
        row = list(ds.row(src))
        part = d['part']
        custom = CUSTOM.get(part)
        shape_row = fds.row(custom['base'] if custom else part)
        for f in SHAPE + HIT_EFFECT:
            row[ds.fi[f]] = shape_row[ds.fi[f]]
        if custom:
            for f, v in custom.items():
                if f != 'base':
                    ds.set(row, f, v)
        ds.set(row, 'Power', int(round(ds.get(row, 'Power') * COMBO_POWER)))
        ds.set(row, 'Flag0', ds.get(row, 'Flag0') & ~ENEMY_FLAGS)
        ds.add(key, row)
        report.append('  %-34s from %-30s power %4d, shape %-28s (%s) %s r%s' % (key, src, ds.get(row, 'Power'), part, ds.get(row, 'CreatePartName'),
                      ds.get(row, 'CollisionType'), ds.get(row, 'CollisionParameter_Array')))

    # ---- 2. the beast's abilities' rows: the boss's, as a player's
    report.append('Damage: the beast\'s abilities\' rows (the boss\'s as a player\'s):')
    made = {}
    for a in ABILITIES:
        mine = {old: new for old, (new, _, _) in a['rows'].items()}
        for old, (new, power, over) in a['rows'].items():
            assert old in fds.at and new not in ds.at and new not in made, (a['key'], old, new)
            row = list(fds.row(old))
            for f in names11:
                if f in over:
                    continue
                v = ds.get(row, f)
                for x in (v if isinstance(v, list) else [v]):
                    assert not (x and x.startswith('EB2160') and x not in mine), (new, f, x, 'names a boss row it does not take along')
                if isinstance(v, list):
                    if any(x in mine for x in v if x):
                        ds.set(row, f, [mine.get(x, x) for x in v])
                elif v in mine:
                    ds.set(row, f, mine[v])
            line = to_player(ds, row, new, a['kind'], power, over)
            ds.add(new, row)
            made[new] = old
            report.append('  %-34s from %-40s %s' % (new, old, line))
    for new in made:   # what they name is there
        r = ds.row(new)
        for f in ('HitDamageSourceID_Array', 'ConditionCreateDamageSourceID_Array'):
            for v in ds.get(r, f) or []:
                assert v in ds.at, (new, f, v)

    # every damage notify of what each ability plays has its row; every row is struck by one
    report.append('Abilities: what they play and the rows their notifies name:')
    struck = set()
    for a in ABILITIES:
        anims = plays(plan, a['anim'], beast)
        need = []
        for k in anims:
            assert k in beast, (a['key'], k, 'not in the survey')
            cls, ids = beast[k]
            if cls == 'AnimComposite':
                raise AssertionError((a['key'], k, 'a composite of the boss\'s: its parts\' notifies are not surveyed'))
            for i in ids:
                assert i.startswith('?'), (a['key'], k, i, 'names a boss row itself (not the ability\'s)')
                need.append(a['key'] + i[1:])
        missing = [n for n in need if n not in ds.at or n not in made]
        assert not missing, (a['key'], 'notifies name rows not made', missing)
        unused = [new for new, _, _ in a['rows'].values() if new not in need and not any(
            new in (ds.get(ds.row(n), 'ConditionCreateDamageSourceID_Array') or []) + (ds.get(ds.row(n), 'HitDamageSourceID_Array') or []) for n in need)]
        assert not unused, (a['key'], 'rows no notify strikes', unused)
        struck |= set(need)
        report.append('  %-26s %-26s plays %s: %d blow(s) %s' % (a['key'], a['anim'], ' + '.join(anims), len(need), ', '.join(sorted(set(need)))))

    # ---- 3. the abilities
    player = ab.row(PLAYER_TEMPLATE)
    limit_t = ab.row(LIMIT_TEMPLATE)
    ids = iter(B.unique_ids(ab, len(ABILITIES), 1017))
    sort = 5100
    help_texts = {}
    report.append('Abilities (%d):' % len(ABILITIES))
    for a in ABILITIES:
        key = a['key']
        assert key not in ab.at, key
        if a['kind'] == 'limit':
            row = list(limit_t)
        else:
            boss = fab.row(a['base'])
            row = list(boss)
            for f in PLAYER_FIELDS:
                row[ab.fi[f]] = player[ab.fi[f]]
            ab.set(row, 'CommandType', 1)
            ab.set(row, 'MP', 0)
            ab.set(row, 'Range', 1500.0)
            ab.set(row, 'UsePlace', 0)
            ab.set(row, 'ShowName', 1)
        for f, v in COMMON_OVERRIDES.items():
            ab.set(row, f, v)
        ab.set(row, 'AnimationString_Array', [a['anim']])
        ab.set(row, 'ReplaceDamageSourceID', key)
        ab.set(row, 'Name', a['name'])
        ab.set(row, 'ATB', float(a['atb']))
        help_key = '$%s_help' % key
        ab.set(row, 'Explanation', help_key)
        help_texts[help_key] = a['help']
        ab.set(row, 'SortId', sort)
        ab.set(row, 'UniqueId', next(ids))
        sort += 1
        ab.add(key, row)
        report.append('  %-26s %-7s %-26s ATB %d CT %d  plays %-24s from %s' % (key, a['kind'], a['name'], a['atb'], ab.get(row, 'CommandType'), a['anim'],
                                                                             a['base'] or LIMIT_TEMPLATE))
    for k in list(WEAPONS) + [PLAYER_TEMPLATE, LIMIT_TEMPLATE]:
        assert k in ab.at, k

    # ---- 4. CharaSpec: Vincent's rows list the beast's sets and load its effects and sounds
    report.append('CharaSpec:')
    boss = cs.row('EB2160_00_VincentValentine_Standard')   # (the beast's own effect pack and sound bank)
    assert all(x in cs.get(boss, 'ContentsEffect_Array') for x in ADD_EFFECTS) and all(x in cs.get(boss, 'ContentsSoundSE_Array') for x in ADD_SOUNDS)
    for name in ROWS:
        row = cs.row(name)
        for f, wanted in (('ContentsEffect_Array', ADD_EFFECTS), ('ContentsSoundSE_Array', ADD_SOUNDS)):
            values = cs.get(row, f)
            values += [w for w in wanted if w not in values]
            cs.set(row, f, values)
        sets = cs.get(row, 'AnimationSetList_Array')
        used = {cs.get(row, f) for f in ('GroundAnimationBattlePackIndex', 'GroundAnimationFieldPackIndex', 'FlyAnimationBattlePackIndex',
                                         'FlyAnimationFieldPackIndex')}
        for want in ADD_SETS:
            if want in sets:
                continue
            free = [i for i, v in enumerate(sets) if v is None and i not in used and i >= 7]   # (not the low empty slots: append)
            if free:
                sets[free[0]] = want
            else:
                sets.append(want)
        cs.set(row, 'AnimationSetList_Array', sets)
        report.append('  %s: sets %s; effects %s; sounds %s' % (name, sets, cs.get(row, 'ContentsEffect_Array'), cs.get(row, 'ContentsSoundSE_Array')))

    # ---- the tables into the container; read back: every other row as it was
    put(DAMAGE, quiet(ds.encode))
    put(CHARASPEC, quiet(cs.encode))
    ab_data = quiet(ab.encode)
    pid = W.package_id('/Game/' + ABILITY[:-len('.uasset')])
    assert pid not in store
    chunks.append(dict(id64=pid, type=2, data=ab_data, path=ABILITY))
    entries.append(B.store_entry(pid, ab_data))
    ds2 = quiet(B.Table, chunks[paths.index(DAMAGE)]['data'])
    for k, r0 in ds0.items():
        assert ds2.row(k) == r0, k
    added = set(plan['damage']) | set(made)
    assert set(ds2.at) == set(ds0) | added and len(ds2.at) == len(ds0) + len(added)
    for k in added:
        assert ds2.row(k) == ds.row(k), k
    ab2 = quiet(B.Table, ab_data)
    for k, r0 in ab0.items():
        assert ab2.row(k) == r0, k
    assert set(ab2.at) == set(ab0) | set(BY_KEY)
    for k in BY_KEY:
        assert ab2.row(k) == ab.row(k), k
    uids = [ab2.get(ab2.row(k), 'UniqueId') for k in ab2.at]
    assert len(uids) == len(set(uids)), 'unique ids repeat'
    cs2 = quiet(B.Table, chunks[paths.index(CHARASPEC)]['data'])
    for k, r0 in cs0.items():
        if k not in ROWS:
            assert cs2.row(k) == r0, k
    for k in ROWS:
        assert all(s in cs2.get(cs2.row(k), 'AnimationSetList_Array') for s in ADD_SETS), k
    os.makedirs(out)
    cid, files = P.write(out, ASSETS, chunks, entries, os.path.join(BASE, ASSETS + '.pak'))
    back = Toc(os.path.join(out, ASSETS + '.utoc'))
    old = Toc(os.path.join(BASE, ASSETS + '.utoc'))
    old_by = {(old.chunk_id64(k), old.chunk_type(k)): k for k in range(old.entries)}
    changed = same = 0
    for k in range(back.entries):
        key = (back.chunk_id64(k), back.chunk_type(k))
        if key[1] == 10:
            continue
        if key in old_by:
            if back.read(k) != old.read(old_by[key]):
                changed += 1
                assert back.files[k].endswith((DAMAGE, CHARASPEC)), back.files[k]
            else:
                same += 1
        else:
            assert key == (pid, 2) and back.files[k].endswith(ABILITY) and back.read(k) == ab_data
    assert changed == 2 and same == len([k for k in range(old.entries) if old.chunk_type(k) != 10]) - 2, (changed, same)
    report.append('container %s: %d packages (the damage and CharaSpec tables changed, the ability table added, %d as they were); %s' % (
        ASSETS, len(entries), same, files))

    # ---- 5. zzVincentGunShop_P: the help texts and the new names in its resident text
    schunks, sstore = P.read(os.path.join(BASE, SHOP + '.utoc'))
    sentries = [P.entry(c, sstore[c['id64']]) for c in schunks if c['type'] == 2]
    spaths = [c['path'] for c in schunks]
    k_tx = spaths.index(TEXT)
    tdata = schunks[k_tx]['data']
    have = {key: text for key, text, _ in txtres.parse(tdata)[0]}
    pairs = dict(help_texts)
    pairs.update(NEW_NAMES)
    for a in ABILITIES:
        assert a['name'] in have or a['name'] in NEW_NAMES, (a['key'], 'name text missing', a['name'])
    assert all(n in [a['name'] for a in ABILITIES] for n in NEW_NAMES)
    for key in pairs:
        assert key not in have, key
    text = txtres.add(tdata, sorted(pairs.items()))
    t2 = {key: t for key, t, _ in txtres.parse(text)[0]}
    assert all(t2[k] == v for k, v in pairs.items()) and len(t2) == len(have) + len(pairs)
    assert all(t2[k] == v for k, v in have.items())
    schunks[k_tx]['data'] = text
    e = [x for x in sentries if x['id'] == schunks[k_tx]['id64']][0]
    assert e['size'] >> 60 == 0
    e['size'] = len(text)
    _, sfiles = P.write(out, SHOP, schunks, sentries, os.path.join(BASE, SHOP + '.pak'))
    sback = Toc(os.path.join(out, SHOP + '.utoc'))
    sold = Toc(os.path.join(BASE, SHOP + '.utoc'))
    sold_by = {(sold.chunk_id64(k), sold.chunk_type(k)): k for k in range(sold.entries)}
    for k in range(sback.entries):
        key = (sback.chunk_id64(k), sback.chunk_type(k))
        if key[1] != 10 and not sback.files[k].endswith(TEXT):
            assert sback.read(k) == sold.read(sold_by[key]), sback.files[k]
    report.append('container %s: the resident text with %d help texts and %d names added; %s' % (SHOP, len(help_texts), len(NEW_NAMES), sfiles))
    for a in ABILITIES:
        report.append('  %-26s %-16s %s' % (a['key'], t2[a['name']], t2['$%s_help' % a['key']]))
    abilities = [{'pack': 'Battle07', 'commands': COMMANDS, 'limits': LIMITS, 'weapon_abilities': WEAPONS}]
    json.dump({'abilities': abilities, 'rows': sorted(added), 'ability_rows': sorted(BY_KEY),
               'names': {a['key']: t2[a['name']] for a in ABILITIES}}, open(os.path.join(out, 'galian_data.json'), 'w'), indent=1)
    open(os.path.join(out, 'galian_data_report.txt'), 'w').write('\n'.join(report) + '\n')
    print('\n'.join(report[-40:]))


if __name__ == '__main__':
    main(sys.argv[1])
