"""Create a Character System 3.6: your playable Sephiroth's data, in FullyPlayableSephirothDataAssets_P (the installed
container as it is, every other package byte for byte):
  * BattleDamageSource: every one of his moves hits much harder (Power x6, boss-made hits x12, at most 9998, on hits that
    deal plain damage):
      - his own rows (PC0010_*, not the transformed boss's PC0010_10_*) and Bizarro Sephiroth's (EB2210_00_*: his summon and
        his Bizarro form) in place,
      - the transformed boss's rows his winged / flying abilities use are copied as PC0010_P_* (the boss in the story keeps
        his own) and those abilities point at the copies,
      - boss-made hits (no stagger build-up of a player's: BPAttack 0, coefficient 1) get a player's (1, 2),
      - his Bizarro form's hits (PC0010_BZ_*): his moves' damage from where Bizarro's body strikes (his wings, his conjured
        sword, around him) instead of from his sword, which the form hides; Bizarro's own attacks get the rows the final
        battle's field table has and the resident table lacks (Hell's Gate, Unholy Gate, Zanshin Profaned, Atonement),
  * BattleAbility: Bizarro Sephiroth's attacks as his commands (PC0010_BZ_*: 5 commands, 7 more in place of his weapon
    abilities in the form), player versions like his other transformed abilities,
  * Text/US: their help texts (their names are the game's),
  * CharaSpec: his rows load Bizarro's effect pack and sound bank, and list the Bizarro form's set (Battle05).
    build_forms36_data.py <base dir> <out dir>"""
import io, contextlib, json, os, re, shutil, struct, sys
sys.path[:0] = [os.path.dirname(os.path.abspath(__file__)), '/work/sephatb/tools', '/work/iostore',
                '/work/cs', '/work/tools', '/work/evil1013/tools', '/work/swap1012/tools',
                '/work/vincentfix', '/work/weap1012/tools']
import build_atb as B
from iostore import Toc
import iostore_write as W
from hdr import parse_header
import txtres

NAME = B.NAME
MOUNT = B.MOUNT
ABILITY = 'DataObject/Resident/BattleAbility.uasset'
DAMAGE = 'DataObject/Resident/BattleDamageSource.uasset'
CHARASPEC = 'DataObject/Resident/CharaSpec.uasset'
TEXT = B.TEXT_US
FIELD_ABILITY = '/work/bizmoves1015/raw/3120-CAPTL__BattleAbility.uasset'
FIELD_DAMAGE = '/work/bizmoves1015/raw/3120-CAPTL__BattleDamageSource.uasset'

# ---- the damage buff
POWER_FACTOR = 6           # his own (player) hits
BOSS_FACTOR = 12           # boss-made hits (the transformed boss's, Bizarro's): their Power is about half a player's for the
                           # same blow (a boss's attack is far higher), so twice the buff
POWER_CAP = 9998           # (the game's plain-damage rows go up to 5000; 9999 and up are other kinds' "all")
PLAIN = 0                  # PowerType of plain damage (others: fixed amounts, HP to 1, percentages, heals)
BOSS_BP = (0.0, 1.0)       # BPAttack, BPAttackDamageCoefficient of a boss's or summon's hit
PLAYER_BP = (1.0, 2.0)     # a player's: his own and Cloud's hits build the stagger gauge with these


def in_place(key):
    return (key.startswith('PC0010_') and not key.startswith(('PC0010_10_', 'PC0010_20_', 'PC0010_P_', 'PC0010_BZ_'))) or key.startswith('EB2210_00_')


# the transformed boss's damage his own winged / flying abilities use (their ReplaceDamageSourceID), copied
BOSS = 'PC0010_10_'
COPY = 'PC0010_P_'
MY_ABILITIES = re.compile(r'^PC0010_(T|W2|W3)_')

# ---- the Bizarro form's hits (Battle05 moves name them on their hits): his move's row, struck from Bizarro's body
GEOMETRY = {
    'WingR': {'CreateBasePos': 0, 'TargetBase': 0, 'CreatePartName': 'R_UpperArm_a', 'TargetName': 'Attack_Claw_EndR', 'CollisionType': 3,
              'CollisionParameter_Array': [150.0, 0.0, 100.0]},
    'WingL': {'CreateBasePos': 0, 'TargetBase': 0, 'CreatePartName': 'L_UpperArm_a', 'TargetName': 'Attack_Claw_EndL', 'CollisionType': 3,
              'CollisionParameter_Array': [150.0, 0.0, 100.0]},
    'Sword': {'CreateBasePos': 0, 'TargetBase': 0, 'CreatePartName': 'Attack_Sword', 'TargetName': 'Attack_SwordEnd', 'CollisionType': 3,
              'CollisionParameter_Array': [150.0, 0.0, 100.0]},
    'Around': {'CreateBasePos': 0, 'TargetBase': 0, 'CreatePartName': 'Trans', 'TargetName': None, 'CollisionType': 2,
               'CollisionParameter_Array': [600.0]},
    # on the target itself, as Bizarro's Octaslash (and his own Octaslash Prime's later hits) land
    'Direct': {'CreateBasePos': 10, 'TargetBase': 10, 'CreatePartName': None, 'TargetName': None, 'CollisionType': 0,
               'CollisionParameter_Array': []},
}
OFFSETS = ['CreatePartOffsetX', 'CreatePartOffsetY', 'CreatePartOffsetZ', 'CreatePartOffsetPitch', 'CreatePartOffsetYaw', 'CreatePartOffsetRoll',
           'TargetOffsetX', 'TargetOffsetY', 'TargetOffsetZ']
BZ_HITS = {
    'PC0010_BZ_NAtk_1_01': ('PC0010_NAtk_1_01', 'WingR'),
    'PC0010_BZ_NAtk_2_01': ('PC0010_NAtk_2_01', 'WingL'),
    'PC0010_BZ_NAtk_3_01': ('PC0010_NAtk_3_01', 'Sword'),
    'PC0010_BZ_NAtk_4_01': ('PC0010_NAtk_4_01', 'Sword'),
    'PC0010_BZ_JAtk_1_01': ('PC0010_JAtk_1_01', 'WingR'),
    'PC0010_BZ_JAtk_2_01': ('PC0010_JAtk_2_01', 'WingL'),
    'PC0010_BZ_JAtk_3_01': ('PC0010_JAtk_3_01', 'Sword'),
    'PC0010_BZ_NPAtk_1_01': ('PC0010_NPAtk_1_04', 'Around'),
    'PC0010_BZ_Satk_1_01': ('PC0010_Satk_1_01', 'Sword'),
    'PC0010_BZ_Satk_2_01': ('PC0010_Satk_2_01', 'WingR'),
    'PC0010_BZ_Satk_6_01': ('PC0010_Satk_6_01', 'Direct'),
    'PC0010_BZ_Satk_8_01': ('PC0010_Satk_8_01', 'Sword'),
    'PC0010_BZ_Satk_8_02': ('PC0010_Satk_8_02', 'Sword'),
    'PC0010_BZ_Satk_8_03': ('PC0010_Satk_8_03', 'Sword'),
    'PC0010_BZ_SAtk_9_01': ('PC0010_SAtk_9_01', 'Sword'),
    'PC0010_BZ_SAtk_9_02': ('PC0010_SAtk_9_02', 'Sword'),
    'PC0010_BZ_SAtk_9_03': ('PC0010_SAtk_9_03', 'Sword'),
    'PC0010_BZ_ChainChange01_01': ('PC0010_ChainChange01_01', 'WingR'),
    'PC0010_BZ_PAtk_1_01': ('PC0010_PAtk_1_01', 'WingL'),
    'PC0010_BZ_PAtk_2_01': ('PC0010_PAtk_2_01', 'WingR'),
}
for n in range(1, 9):
    BZ_HITS['PC0010_BZ_Limit_1_%02d' % n] = ('PC0010_Limit_1_%02d' % n, 'Direct')

# ---- Bizarro's attacks as his commands: new ability -> (the final battle's ability, ATB, help, overrides)
BZ_ABILITIES = {
    'PC0010_BZ_Octaslash': ('EB2210_00_Hattou', 2, 'Cut down an enemy with a flurry of lightning-fast slashes.', {}),
    'PC0010_BZ_Zanshin': ('EB2210_00_Zanshin1', 1, 'Loose twin blades of light that cut through enemies.', {}),
    'PC0010_BZ_HellsGate': ('EB2210_00_GokumonA1', 2, 'Conjure a great blade and throw open the gates of hell beneath an enemy.',
                            {'AnimationString_Array': ['B_AtkHellsGate01']}),
    'PC0010_BZ_Swarm': ('EB2210_00_ShadowFlare', 1, 'Unleash a swarm of dark orbs that hound an enemy.', {}),
    'PC0010_BZ_HeartlessAngel': ('EB2210_00_HeartlessAngel', 2, "Bring every enemy's HP to the brink of death.", {}),
    # in place of his weapon abilities in the form
    'PC0010_BZ_ZanshinProfaned': ('EB2210_00_Zanshin2', 1, 'Hurl a wave of profane light at an enemy.', {}),
    'PC0010_BZ_UnholyGate': ('EB2210_00_GokumonB1', 2, 'Hurl a conjured blade that erupts in hellfire around an enemy.',
                             {'AnimationString_Array': ['B_AtkUnholyGate01']}),
    'PC0010_BZ_ApocalypticFire': ('EB2210_00_BurstFlare', 2, 'Erupt in a blast of flame that engulfs everything around you.', {}),
    'PC0010_BZ_Profane': ('EB2210_00_Stigma', 1, 'Burn enemies with a beam fired from your core.', {}),
    'PC0010_BZ_WhisperVortex': ('EB2210_00_FeelerWingSmash', 2, 'Whip up tornadoes of feelers that tear through enemies.', {}),
    'PC0010_BZ_Atonement': ('EB2210_00_WingSmashR', 2, 'Bring a wing crashing down on every foe nearby.', {}),
    'PC0010_BZ_LacrymaDeus': ('EB2210_00_EyeLaserR', 1, 'Fire searing beams from your eyes at an enemy.', {}),
}
COMMON_OVERRIDES = {'CameraSequenceID': None,   # (the final battle's cameras)
                    'ReactionCondition_Array': [], 'ReactionConditionParameterValue_Array': [], 'ReactionType_Array': [],
                    'ReactionParameterString_Array': []}   # (the boss's follow-ups: Hell's Gate's strike is part of its move)
PLAYER_TEMPLATE = 'PC0010_AtkBurst01'
PLAYER_FIELDS = ('ReactionInfluenceID', 'Flag0', 'InputBufferTime', 'KeepValue', 'ActionCategory')
# damage rows of the final battle's field table his Bizarro attacks need that the resident table lacks (row -> overrides)
FIELD_ROWS = {
    'EB2210_00_GokumonA1_01': {}, 'EB2210_00_GokumonA1_02': {}, 'EB2210_00_GokumonA1_03': {}, 'EB2210_00_GokumonA1_04': {},
    'EB2210_00_GokumonB1_01': {}, 'EB2210_00_GokumonB1_02': {}, 'EB2210_00_GokumonB1_03': {}, 'EB2210_00_GokumonB1_04': {},
    'EB2210_00_GokumonB1_05': {}, 'EB2210_00_GokumonDanger': {},
    'EB2210_00_Zanshin2_01': {},
    # Atonement: the boss's slam reaches 50 m (the whole arena); his reaches 15 m
    'EB2210_00_WingSmashR_01': {'CollisionParameter_Array': [1500.0, 0.5, 10.0]},
    'EB2210_00_WingSmashL_01': {'CollisionParameter_Array': [1500.0, 0.5, 10.0]},
}

# ---- CharaSpec: his rows (Cloud's slot rows that are him)
ROWS = ['PC0000_00_Cloud_Standard', 'PC0000_08_Cloud_SoldierNoHelmet', 'PC0000_09_Cloud_CostaClothing', 'PC0000_10_Cloud_CostaClothing2',
        'PC0000_04_Cloud_ZackCostume', 'PC0000_12_Cloud_ZackCostumeDirty', 'PC0000_18_Cloud_ZackCostumeAge21',
        'PC0000_19_Cloud_ZackCostumeDirtyAge21', 'PC0000_23_Cloud_ZackCostumeWet']
ADD_EFFECTS = ['EB2210_BizarroSephiroth_Effect__Pack']
ADD_SOUNDS = ['SE_EB2210_00_BizarroSephiroth_Standard']
ADD_SETS = ['Battle05']


def quiet(f, *a):
    with contextlib.redirect_stdout(io.StringIO()):
        return f(*a)


def fields(t):
    return [f[0][0] for f in t.fields]


def rows_of(t, prefix):
    p = prefix.lower()
    return [k for k in t.at if k.lower() == p or k.lower().startswith(p + '_')]


def buff(t, key, row, report):
    """Plain damage (0 < Power < 9999): Power x6, or x12 and a player's stagger build-up on a boss-made hit."""
    changed = []
    power, kind = t.get(row, 'Power'), t.get(row, 'PowerType')
    if kind == PLAIN and 0 < power < 9999:
        boss = (t.get(row, 'BPAttack'), t.get(row, 'BPAttackDamageCoefficient')) == BOSS_BP
        new = min(power * (BOSS_FACTOR if boss else POWER_FACTOR), POWER_CAP)
        if new != power:
            t.set(row, 'Power', new)
            changed.append('Power %d -> %d' % (power, new))
        if boss:
            t.set(row, 'BPAttack', PLAYER_BP[0])
            t.set(row, 'BPAttackDamageCoefficient', PLAYER_BP[1])
            changed.append('boss-made: x%d, stagger like a player\'s' % BOSS_FACTOR)
    if changed:
        report.append('  %-34s %s' % (key, ', '.join(changed)))
    return bool(changed)


def name_fields(t):
    return [f[0][0] for f in t.fields if f[1] == 11]


def main(base_dir, out_dir):
    base_path = os.path.join(base_dir, NAME)
    base = Toc(base_path + '.utoc')
    head = [i for i in range(base.entries) if base.chunk_type(i) == 10]
    cid, base_entries = parse_header(base.read(head[0]))
    chunks, entries = [None], []
    for i in range(base.entries):
        if base.chunk_type(i) != 2:
            continue
        path = base.files[i].replace(MOUNT, '', 1)
        pid = base.chunk_id64(i)
        e = base_entries[pid]
        chunks.append(dict(id64=pid, type=2, data=base.read(i), path=path))
        entries.append(dict(id=pid, size=e['size'], export_count=e['export_count'], export_bundle_count=e['export_bundle_count'],
                            load_order=e['load_order'], imports=list(e['imports'])))
    paths = [c['path'] for c in chunks[1:]]
    report = []
    changed = set()

    def put(path, data):
        k = paths.index(path) + 1
        chunks[k]['data'] = data
        if entries[k - 1]['size']:
            entries[k - 1]['size'] = len(data)
        changed.add(path)

    def table(path):
        return quiet(B.Table, chunks[paths.index(path) + 1]['data'])

    ab = table(ABILITY)
    ds = table(DAMAGE)
    fab = quiet(B.Table, open(FIELD_ABILITY, 'rb').read())
    fds = quiet(B.Table, open(FIELD_DAMAGE, 'rb').read())
    assert fields(ab) == fields(fab) and fields(ds) == fields(fds), 'the field tables have other fields'
    ab0 = {k: list(ab.row(k)) for k in ab.at}
    ds0 = {k: list(ds.row(k)) for k in ds.at}
    names11 = name_fields(ds)

    # ---- 1. his and Bizarro's rows, in place
    report.append('Damage, in place (his own x%d, boss-made x%d, at most %d):' % (POWER_FACTOR, BOSS_FACTOR, POWER_CAP))
    count = 0
    for key in list(ds.at):
        if in_place(key):
            count += buff(ds, key, ds.row(key), report)
    report.append('  %d rows' % count)

    # ---- 2. the transformed boss's rows his own abilities use: copies (PC0010_P_*), buffed
    prefixes = {}
    for key in ab.at:
        if not MY_ABILITIES.match(key):
            continue
        p = ab.get(ab.row(key), 'ReplaceDamageSourceID')
        if p and p.startswith(BOSS) and rows_of(ds, p):
            prefixes.setdefault(p, []).append(key)
    todo = []
    for p in sorted(prefixes):
        todo += rows_of(ds, p)
    copies = {}
    while todo:   # with every boss row they name (bullets they create, hits they make)
        key = todo.pop(0)
        if key in copies:
            continue
        copies[key] = COPY + key[len(BOSS):]
        for f in names11:
            v = ds.get(ds.row(key), f)
            for x in (v if isinstance(v, list) else [v]):
                if x and x.startswith(BOSS) and x in ds.at and x not in copies:
                    todo.append(x)
    report.append('Damage, the transformed boss\'s rows his abilities use, copied as %s* (%d rows):' % (COPY, len(copies)))
    for old, new in copies.items():
        assert new not in ds.at, new
        row = list(ds.row(old))
        for f in names11:
            v = ds.get(row, f)
            if isinstance(v, list):
                if any(x in copies for x in v):
                    ds.set(row, f, [copies.get(x, x) for x in v])
            elif v in copies:
                ds.set(row, f, copies[v])
        ds.add(new, row)
        buff(ds, new, ds.row(new), report)
    for p, users in sorted(prefixes.items()):
        for key in users:
            ab.set(ab.row(key), 'ReplaceDamageSourceID', COPY + p[len(BOSS):])
        report.append('  %s -> %s%s: %s' % (p, COPY, p[len(BOSS):], ', '.join(users)))

    # ---- 3. the field table's rows his Bizarro attacks need
    report.append('Damage, the final battle\'s rows his Bizarro attacks need (%d):' % len(FIELD_ROWS))
    for key, over in FIELD_ROWS.items():
        assert key in fds.at and key not in ds.at, key
        row = list(fds.row(key))
        for f, v in over.items():
            ds.set(row, f, v)
        ds.add(key, row)
        buff(ds, key, ds.row(key), report)
    for key in FIELD_ROWS:   # what they name is there
        r = ds.row(key)
        for f in ('HitDamageSourceID_Array', 'ConditionCreateDamageSourceID_Array'):
            for v in ds.get(r, f) or []:
                assert v in ds.at, (key, f, v)

    # ---- 4. the Bizarro form's hits: his moves' rows struck from Bizarro's body
    report.append('Damage, the Bizarro form\'s hits (%d):' % len(BZ_HITS))
    for key, (src, shape) in BZ_HITS.items():
        assert key not in ds.at and src in ds.at, (key, src)
        row = list(ds.row(src))   # (already buffed)
        for f, v in GEOMETRY[shape].items():
            ds.set(row, f, v)
        for f in OFFSETS:
            ds.set(row, f, 0.0)
        ds.add(key, row)
        report.append('  %-28s %s from %s, power %d' % (key, shape, src, ds.get(row, 'Power')))

    # ---- 5. Bizarro's attacks as his commands
    player = ab.row(PLAYER_TEMPLATE)
    ids = iter(B.unique_ids(ab, len(BZ_ABILITIES), 1016))
    sort = 1 + max(ab.get(ab.row(k), 'SortId') for k in ab.at if MY_ABILITIES.match(k))
    help_texts = {}
    report.append('Abilities (%d):' % len(BZ_ABILITIES))
    for key, (src, atb, help_text, over) in BZ_ABILITIES.items():
        assert key not in ab.at, key
        boss = fab.row(src)
        row = list(boss)
        for f in PLAYER_FIELDS:
            row[ab.fi[f]] = player[ab.fi[f]]
        ab.set(row, 'CommandType', 1)
        ab.set(row, 'ATB', float(atb))
        ab.set(row, 'MP', 0)
        ab.set(row, 'Range', 1500.0)
        ab.set(row, 'UsePlace', 0)
        ab.set(row, 'ShowName', 1)
        ab.set(row, 'SortId', sort)
        ab.set(row, 'UniqueId', next(ids))
        sort += 1
        if not fab.get(boss, 'ReplaceDamageSourceID'):
            ab.set(row, 'ReplaceDamageSourceID', src)
        help_key = '$%s_help' % key
        ab.set(row, 'Explanation', help_key)
        help_texts[help_key] = help_text
        for f, v in list(COMMON_OVERRIDES.items()) + list(over.items()):
            ab.set(row, f, v)
        ab.add(key, row)
        damage = ab.get(row, 'ReplaceDamageSourceID')
        hits = rows_of(ds, damage)
        assert hits, (key, 'no damage rows for', damage)
        report.append('  %-26s from %-26s %-38s ATB %d  anims %s  damage %s (%d rows)' % (key, src, ab.get(row, 'Name'), atb,
                                                                                          ab.get(row, 'AnimationString_Array'), damage, len(hits)))
    data = quiet(ab.encode)
    put(ABILITY, data)
    data_ds = quiet(ds.encode)
    put(DAMAGE, data_ds)

    # ---- 6. Text/US: the help texts (names are the game's: $bt_BizarroSephiroth_*)
    k_tx = paths.index(TEXT) + 1
    tdata = chunks[k_tx]['data']
    tentries, _ = txtres.parse(tdata)
    have = {key: text for key, text, _ in tentries}
    for key in BZ_ABILITIES:
        name = ab.get(ab.row(key), 'Name')
        assert name in have, (key, 'name text missing', name)
    for key in help_texts:
        assert key not in have, key
    text = txtres.add(tdata, sorted(help_texts.items()))
    put(TEXT, text)
    t2 = {key: t for key, t, _ in txtres.parse(text)[0]}
    assert all(t2[k] == v for k, v in help_texts.items()) and len(t2) == len(have) + len(help_texts)
    report.append('Text/US: %d help texts' % len(help_texts))

    # ---- 7. CharaSpec: his rows load Bizarro's effects and sounds, and list Battle05
    cs = table(CHARASPEC)
    cs0 = {k: list(cs.row(k)) for k in cs.at}
    report.append('CharaSpec:')
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
            free = [i for i, v in enumerate(sets) if v is None and i not in used and i >= 7] or [i for i, v in enumerate(sets) if v is None and i not in used]
            if free:
                sets[free[0]] = want
            else:
                sets.append(want)
        cs.set(row, 'AnimationSetList_Array', sets)
        report.append('  %s: effects %s; sounds %s; sets %s' % (name, cs.get(row, 'ContentsEffect_Array'), cs.get(row, 'ContentsSoundSE_Array'), sets))
    put(CHARASPEC, quiet(cs.encode))

    # ---- read back: every other row as it was
    ab2 = quiet(B.Table, chunks[paths.index(ABILITY) + 1]['data'])
    for key, r0 in ab0.items():
        r2 = ab2.row(key)
        if key in [u for us in prefixes.values() for u in us]:
            diff = [f for f in fields(ab2) if r2[ab2.fi[f]] != r0[ab2.fi[f]]]
            assert diff == ['ReplaceDamageSourceID'], (key, diff)
        else:
            assert r2 == r0, key
    assert all(k in ab2.at for k in BZ_ABILITIES) and len(ab2.keys) == len(ab0) + len(BZ_ABILITIES)
    uids = [ab2.get(ab2.row(k), 'UniqueId') for k in ab2.at]
    assert len(uids) == len(set(uids)), 'unique ids repeat'
    ds2 = quiet(B.Table, chunks[paths.index(DAMAGE) + 1]['data'])
    allowed = {'Power', 'BPAttack', 'BPAttackDamageCoefficient'}
    for key, r0 in ds0.items():
        r2 = ds2.row(key)
        diff = {f for f in fields(ds2) if r2[ds2.fi[f]] != r0[ds2.fi[f]]}
        if in_place(key):
            assert diff <= allowed, (key, diff)
        else:
            assert not diff, (key, diff)
    added = set(copies.values()) | set(FIELD_ROWS) | set(BZ_HITS)
    assert set(ds2.at) == set(ds0) | added and len(ds2.keys) == len(ds0) + len(added)
    for key in added:
        r = ds2.row(key)
        for f in ('HitDamageSourceID_Array', 'ConditionCreateDamageSourceID_Array'):
            for v in ds2.get(r, f) or []:
                assert v in ds2.at, (key, f, v)
    cs2 = quiet(B.Table, chunks[paths.index(CHARASPEC) + 1]['data'])
    for key, r0 in cs0.items():
        if key not in ROWS:
            assert cs2.row(key) == r0, key

    # ---- the container
    cid2 = W.container_id_from_name(NAME)
    assert cid2 == cid
    chunks[0] = dict(id64=cid2, type=10, data=W.container_header(cid2, entries), path=None)
    os.makedirs(out_dir, exist_ok=True)
    outb = os.path.join(out_dir, NAME)
    W.write_container(outb, NAME, chunks, mount=MOUNT)
    shutil.copy(base_path + '.pak', outb + '.pak')
    back = Toc(outb + '.utoc')
    assert back.container_id == cid2 and back.entries == len(chunks)
    for i, c in enumerate(chunks):
        assert back.read(i) == c['data'] and back.chunk_id64(i) == c['id64'] and back.chunk_type(i) == c['type']
        if c['path']:
            assert back.files.get(i) == MOUNT + c['path'], back.files.get(i)
    _, ents = parse_header(back.read(0))
    assert set(ents) == {c['id64'] for c in chunks[1:]}
    for c, e in zip(chunks[1:], entries):
        got = ents[c['id64']]
        assert (got['size'], got['export_count'], got['export_bundle_count'], got['imports'], got['load_order']) == \
               (e['size'], e['export_count'], e['export_bundle_count'], e['imports'], e['load_order'])
        if c['path'] not in changed:
            j = [kk for kk, v in base.files.items() if v == MOUNT + c['path']][0]
            assert c['data'] == base.read(j), c['path']
    report.append('container: %s (%d packages; changed: %s)' % (outb, len(chunks) - 1, ', '.join(sorted(changed))))
    print('\n'.join(report))
    json.dump({'bz_hits': {k: v[1] for k, v in BZ_HITS.items()}, 'abilities': {k: v[0] for k, v in BZ_ABILITIES.items()},
               'copies': copies}, open(os.path.join(out_dir, 'forms36_data.json'), 'w'), indent=1)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
