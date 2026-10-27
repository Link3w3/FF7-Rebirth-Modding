"""Your playable Sephiroth's transformed abilities as ATB commands, per form, plus Octaslash Prime and Meteor as limits 2
and 3, merged into FullyPlayableSephirothDataAssets_P:
  * the installed container as it is (every package byte for byte, their header entries), except
  * BattlePlayerParameter: pt_Cloud's limits are Octaslash, Octaslash Prime (flying) and Meteor (commands stay; skel compat
    switches both per form),
  * plus the game's Resident BattleAbility with player versions of the transformed Sephiroth's abilities (PC0010_T_*)
    and the two limits, the game's Resident BattleDamageSource with the Meteor (PC0010_Meteor_01 falls, _02 bursts),
    and the US Resident text with their names and help.
    build_atb.py <out dir>"""
import json, os, random, shutil, struct, sys
sys.path[:0] = ['/work/iostore', '/work/cs', '/work/vincentfix', '/work/weap1012/tools',
                '/work/swap1012/tools', '/work/evil1013/tools', '/work/tools']
from iostore import Toc
from zen import Zen
import iostore_write as W
import charaspec_patch as cp
from hdr import parse_header
from build_merge import with_names, graph_entries
import txtres

NAME = 'FullyPlayableSephirothDataAssets_P'
BASE = '/work/evil1013/out1/' + NAME
MOUNT = '../../../End/Content/'
GAME_ABILITY = '/work/seph1013/tables/game_BattleAbility.uasset'
GAME_DAMAGE = '/work/seph1013/tables/game_BattleDamageSource.uasset'
GAME_TEXT_US = '/work/text1013/pkgs/Text__US__Resident_TxtRes.uasset'
PLAYER_TABLE = 'DataObject/Resident/BattlePlayerParameter.uasset'
CHARASPEC_TABLE = 'DataObject/Resident/CharaSpec.uasset'
# His CharaSpec rows ask for these sets too: a character only takes the sets its row's AnimationSetList names from its pack,
# so EndBattleAPI SetPrimaryAnimPack finds Battle02 / Battle03 (RebirthSkelCompat builds them into the pack) only when the
# row lists them. They go into free (None) slots; the slots the row's pack indices name stay as they are.
FORM_ROWS = ['PC0000_00_Cloud_Standard', 'PC0000_08_Cloud_SoldierNoHelmet', 'PC0000_09_Cloud_CostaClothing', 'PC0000_10_Cloud_CostaClothing2']
FORM_SETS = ['Battle02', 'Battle03']
# The transformed abilities' damage sources name their effects (category 10: the attacker's effect packs, which his row's
# ContentsEffect_Array names and RebirthSkelCompat's "pack_assets" puts into his CharaSpec pack) and spawn props (CharaSpecID:
# a character's row lists those in SharedCharaSpecList_Array, as Cait Sith's lists his tub): Ground/Bind Feeler's feeler
# bullet and the Meteor.
FORM_EFFECTS = ['PC0010_10_Sephiroth_Transform_Effect__Pack']
FORM_SHARED = ['EN9000_22_Feeler_BlackBulletEnd2', 'FA0260_01_SephirothMeteor_Battle']
ABILITY_TABLE = 'DataObject/Resident/BattleAbility.uasset'
DAMAGE_TABLE = 'DataObject/Resident/BattleDamageSource.uasset'
TEXT_US = 'Text/US/Resident_TxtRes.uasset'

# new ability -> (boss ability it is made from, its name text key or None to keep the boss's, ATB cost, help text,
#                 overrides)
ABILITIES = {
    # winged (Battle02)
    'PC0010_T_ShadowFlare': ('PC0010_10_ShadowFlare', '$bt_BossSephiroth_ShadowFlare', 1, 'Fire a seeking orb of darkness that bursts on an enemy.', {}),
    'PC0010_T_GroundFeeler': ('PC0010_10_GroundFeeler', None, 1, 'Drive feelers up through the ground beneath an enemy.', {}),
    'PC0010_T_BindFeeler': ('PC0010_10_BindFeeler', None, 1, 'Ensnare an enemy in grasping feelers.', {}),
    'PC0010_T_HardCombo': ('PC0010_10_HeatAttack_1', None, 1, 'Unleash a relentless flurry of sword strikes.', {}),
    'PC0010_T_BindAttackNear': ('PC0010_10_BindAttack01B', None, 1, 'Strike a nearby enemy with a binding blow.', {}),
    'PC0010_T_BindAttackFar': ('PC0010_10_BindAttack02B', None, 1, 'Send a binding wave of energy at a distant enemy.', {}),
    'PC0010_T_Firaga': ('PC0010_10_Fire3', None, 1, 'Engulf an enemy in searing flames.', {}),
    'PC0010_T_Blizzaga': ('PC0010_10_Blizzard3', None, 1, 'Encase an enemy in jagged ice.', {}),
    'PC0010_T_Thundaga': ('PC0010_10_Thunder3', None, 1, 'Strike an enemy with crackling lightning.', {}),
    'PC0010_T_Aeroga': ('PC0010_10_Wind3', None, 1, 'Batter an enemy with violent winds.', {}),
    # flying (Battle03)
    'PC0010_T_HeartlessAngel': ('PC0010_10_Tenshi', None, 2, 'Bring every enemy around you to the brink of death.',
                                {'CameraSequenceID': None, 'ReplaceDamageSourceID': 'PC0010_T_HeartlessAngel'}),
    'PC0010_T_FeelerTornado': ('PC0010_10_FeelerTornado', None, 1, 'Whip up a whirlwind of feelers around an enemy.', {}),
    'PC0010_T_WarpStab': ('PC0010_10_Stab', None, 1, 'Vanish and reappear to run an enemy through.', {}),
    'PC0010_T_FeelerLaser': ('PC0010_10_FeelerLaserLoopL', '$bt_BossSephiroth_FeelerLazer', 2, 'Sweep the field with beams fired from your feelers.',
                             {'AnimationString_Array': ['B_AtkFeelerLaser01_0', 'B_AtkFeelerLaserL01_1', 'B_AtkFeelerLaser01_2'],
                              'AnimationParameter_Array': [0.0, 4.0], 'ReplaceDamageSourceID': 'PC0010_10_FeelerLaser'}),
    'PC0010_T_LastAttack': ('PC0010_10_LastAttack', None, 2, 'Rain down a storm of beams from on high.', {}),
}
# limits: new limit -> (made from, name key, help text, overrides)
LIMITS = {
    'PC0010_Limit002': ('PC0010_Limit001', '$PC0010_SAtk_6', 'Take to the skies and cut an enemy down with blinding speed.',
                        {'AnimationString_Array': ['B_AtkLimit02_0'], 'CameraSequenceID': None, 'ReplaceDamageSourceID': 'PC0010_Limit_1'}),
    'PC0010_Limit003': ('PC0010_Limit001', '$PC0010_Limit003', 'Call down a meteor the size of a world upon your foes.',
                        {'AnimationString_Array': ['B_AtkLimit03_0'], 'CameraSequenceID': None, 'ReplaceDamageSourceID': 'PC0010_Meteor', 'Range': 3000.0,
                         'ResourceID_Array': ['Fire01'], 'ResourceName_Array': ['BattleAbilityResource_Fire01']}),
}
TEXTS = {'$PC0010_Limit003': 'Meteor'}
LIMIT_LIST = ['PC0010_Limit001', 'PC0010_Limit002', 'PC0010_Limit003']   # (3.3 rows; the new mod uses Cloud's, below)

# The new mod: his moves on Cloud's own ability IDs, which carry Cloud's progression in your save (limit levels: the Folio
# and the story flag of level 3; weapon abilities: each weapon's proficiency). More player abilities first (same fields as
# ABILITIES; their UniqueIds come after the 3.3 rows', which keep theirs): the flying form's Octaslash Prime and the abilities
# Cloud's weapons give in the winged and flying forms (RebirthSkelCompat 3.4 "weapon_abilities").
NEW_ABILITIES = {
    'PC0010_T_OctaslashPrime': ('PC0010_SAtk_6', None, 2, 'Unleash eight lightning-fast strikes on an enemy.', {}),
    'PC0010_W2_ZanshinRising': ('PC0010_SAtk_3', None, 1, 'Slash upward and carry an enemy into the air.', {}),
    'PC0010_W3_DoubleBlizzaga': ('PC0010_10_DoubleBlizzard3', None, 2, 'Encase an enemy in jagged ice, twice over.', {}),
    'PC0010_W3_DoubleFiraga': ('PC0010_10_DoubleFire3', None, 2, 'Engulf an enemy in searing flames, twice over.', {}),
    'PC0010_W3_DoubleThundaga': ('PC0010_10_DoubleThunder3', None, 2, 'Strike an enemy with crackling lightning, twice over.', {}),
    'PC0010_W3_DoubleAeroga': ('PC0010_10_DoubleWind3', None, 2, 'Batter an enemy with violent winds, twice over.', {}),
    'PC0010_W3_InfernalGate': ('PC0010_SAtk_4', None, 1, 'Strike with a blow that throws open the gates of hell.', {}),
    'PC0010_W3_SwordDance': ('PC0010_SAtk_2', None, 1, 'Spin into a dance of sweeping cuts.', {}),
}
# Cloud's row -> (his move it plays, name key or None for the move's, ATB or None for Cloud's, help text, overrides). The row
# keeps Cloud's identity (CLOUD_KEEP: UniqueId, menu order, kind, player fields); everything else is the move's. Limits: level 1
# Octaslash, 2 Heartless Angel, 3 Meteor. Weapon abilities (normal form; RebirthSkelCompat switches them in the other forms).
CLOUD_ROWS = {
    'PC0000_Limit001': ('PC0010_Limit001', None, None, 'Cut down every foe before you with eight blinding slashes.', {}),
    'PC0000_Limit002': ('PC0010_T_HeartlessAngel', None, None, 'Bring every enemy around you to the brink of death.', {}),
    'PC0000_Limit003': ('PC0010_Limit003', None, None, 'Call down a meteor the size of a world upon your foes.', {}),
    'PC0000_AtkBurst02': ('PC0010_SAtk_1', None, 1, 'Lunge forward and run an enemy through.', {}),                       # Focused Thrust: Pierce
    'PC0000_AtkBurst08': ('PC0010_SAtk_4', None, 1, 'Strike with a blow that throws open the gates of hell.', {}),        # Firebolt Blade: Infernal Gate
    'PC0000_AtkBurst07': ('PC0010_SAtk_7', None, 1, 'Dart past an enemy, cutting as you go.', {}),                        # Disorder: Shift Slash
    'PC0000_AtkBurst09': ('PC0010_SAtk_2', None, 1, 'Spin into a dance of sweeping cuts.', {}),                           # Prime Mode: Sword Dance
    'PC0000_AtkBurst04': ('PC0010_SAtk_6', None, 2, 'Unleash eight lightning-fast strikes on an enemy.', {}),             # Infinity's End: Octaslash Prime
    'PC0000_AtkBurst05': ('PC0010_SAtk_8', None, 1, 'Drive your blade into the earth and loose its fury on your foes.', {}),  # Blade Burst: Telluric Fury
    'PC0000_AtkBurst06': ('PC0010_SAtk_5', None, 1, 'Strike back at an enemy the moment it attacks.', {}),                # Counterstance: Retaliation
    'PC0000_AtkBurst10': ('PC0010_SAtk_9', None, 1, 'Bring your blade crashing down on an enemy from the sky.', {}),      # Aerial Onslaught: Skyshatter
}
CLOUD_KEEP = ('UniqueId', 'SortId', 'CommandType', 'ShowName', 'MP', 'ReactionInfluenceID', 'Flag0', 'InputBufferTime', 'KeepValue', 'ActionCategory')
CLOUD_LIMITS = ['PC0000_Limit001', 'PC0000_Limit002', 'PC0000_Limit003']
GAME_PLAYER = '/work/seph1013/tables/game_BattlePlayerParameter.uasset'   # Cloud's own limit flags

# the Meteor: _01 is the meteor itself (the game's FA0260_01 Sephiroth meteor), falling from high above the target; when it
# hits, the burst goes off where it landed. Heartless Angel's two hits (its animations in the forms carry ?_01 and ?_02).
METEOR = {
    'PC0010_T_HeartlessAngel_01': ('PC0010_10_Tenshi_01', {}),
    'PC0010_T_HeartlessAngel_02': ('PC0010_10_Tenshi_01', {}),
    'PC0010_Meteor_01': ('PC0007_AtkBurst10_R_0_03', {   # Cait Sith's tub that drops on an enemy's head
        'CharaSpecID': 'FA0260_01_SephirothMeteor_Battle', 'CreatePartOffsetZ': 6000.0, 'CreateDelayTime': 0.5, 'LifeTime': 8.0,
        'CollisionType': 2, 'CollisionParameter_Array': [1500.0], 'Power': 800, 'Property': 2, 'HitDestroyType': 1, 'HitCount': 1,
        'DisableHitBackground': 0, 'HitReactionType_Array': [10, 10, 10], 'HitReactionParam_Array': [1500.0],
        'BindEffectResourceName': 'FX_Fire03_Bullet_01', 'HitEffectResourceName_Array': ['FX_Fire03_Hit_01'],
        'BindEffectResourceCategory': 0, 'HitEffectResourceCategory_Array': [0],  # Fire01's effects (the limit's resource)
        'ConditionCreateDamageSourceID_Array': ['PC0010_Meteor_Burst'], 'ConditionCreateDamageSourceType_Array': [2]}),
    'PC0010_Meteor_Burst': ('PC0010_10_ShadowFlare_02', {   # the burst of Shadow Flare's orb, at the meteor
        'CollisionParameter_Array': [4000.0], 'Power': 2500, 'Property': 2, 'HitCount': 1, 'HitInterval': 3.0, 'LifeTime': 0.6,
        'HitReactionType_Array': [10, 10, 10], 'HitReactionParam_Array': [2000.0], 'AerialHitReactionParam_Array': [2000.0],
        'BindEffectResourceName': 'FX_Fire03_Hit_01', 'HitEffectResourceName_Array': ['FX_Fire03_Hit_01'], 'CutValue': 70,
        'BindEffectResourceCategory': 0, 'HitEffectResourceCategory_Array': [0],
        'HitCameraShakeDataID': 'shake_01'}),
}
PLAYER_TEMPLATE = 'PC0010_AtkBurst01'   # player fields for the ATB abilities
POD = {1: '?', 2: 'B', 3: 'b', 4: 'H', 5: 'h', 6: 'I', 7: 'i', 8: 'q', 9: 'f'}


def name_tuple(text):
    """FName text -> (base, number) the way UE splits it ("B_AtkMag01_0" -> ("B_AtkMag01", 1); "_01" is not a number)."""
    if text is None:
        return None
    head, sep, tail = text.rpartition('_')
    if sep and tail.isdigit() and (tail == '0' or not tail.startswith('0')) and len(tail) < 10:
        return (head, int(tail) + 1)
    return (text, 0)


def name_text(t):
    if t is None:
        return None
    return t[0] if t[1] == 0 else '%s_%d' % (t[0], t[1] - 1)


def string_bytes(text):
    return None if text is None else (text + '\0').encode('utf-16-le')


class Table:
    def __init__(self, data):
        self.data = data
        self.z, self.e, self.m, self.d = cp.decode(data)
        self.keys = [k[0] for k in self.d.keys]
        self.rows = [list(r) for r in self.d.rows]
        self.fields = self.d.fields
        self.fi = {f[0][0]: i for i, f in enumerate(self.fields)}
        self.code = {f[0][0]: f[1] for f in self.fields}
        self.at = {name_text(k): i for i, k in enumerate(self.keys)}
        assert cp.encode(data, self.z, self.e, self.m, self.keys, self.fields, self.rows) == data, 'table does not round-trip'

    def row(self, key):
        return self.rows[self.at[key]]

    def value(self, field, v):
        """A plain value (str / float / int / list) -> the table's stored form for the field."""
        code = self.code[field]
        isarr = field.endswith('_Array')
        def one(x):
            if code == 11:
                return name_tuple(x) if isinstance(x, str) else x
            if code == 10:
                return string_bytes(x) if isinstance(x, str) or x is None else x
            return struct.pack('<' + POD[code], x)
        if isarr:
            return [one(x) for x in v]
        return one(v)

    def set(self, row, field, v):
        row[self.fi[field]] = self.value(field, v)

    def get(self, row, field):
        v = row[self.fi[field]]
        code = self.code[field]
        def one(x):
            if code == 11:
                return name_text(x)
            if code == 10:
                return None if x is None else x.decode('utf-16-le').rstrip('\0')
            return struct.unpack('<' + POD[code], x)[0]
        return [one(x) for x in v] if field.endswith('_Array') else one(v)

    def add(self, key, row):
        assert key not in self.at, key
        self.at[key] = len(self.rows)
        self.keys.append(name_tuple(key))
        self.rows.append(row)

    def names(self):
        out = set()
        for k in self.keys:
            out.add(k[0])
        for r in self.rows:
            for (fname, code, isarr), v in zip(self.fields, r):
                if code != 11:
                    continue
                for x in (v if isarr else [v]):
                    if x is not None:
                        out.add(x[0])
        return out

    def encode(self):
        missing = sorted(n for n in self.names() if n not in self.z.names)
        data = with_names(self.data, missing) if missing else self.data
        z, e, m, d = cp.decode(data)
        out = cp.encode(data, z, e, m, self.keys, self.fields, self.rows)
        z2, e2, m2, d2 = cp.decode(out)
        assert [k[0] for k in d2.keys] == self.keys
        for a, b in zip(self.rows, d2.rows):
            assert list(b) == a
        return out


def unique_ids(table, count, seed):
    used = {table.get(r, 'UniqueId') for r in table.rows}
    rng = random.Random(seed)
    out = []
    while len(out) < count:
        v = rng.randrange(100000, 1999999)
        if v not in used:
            used.add(v)
            out.append(v)
    return out


def make_abilities(ab):
    player = ab.row(PLAYER_TEMPLATE)
    ids = iter(unique_ids(ab, len(ABILITIES) + len(LIMITS), 1013))
    help_texts = {}
    sort = 1100
    report = []
    for key, (src, name, atb, help_text, over) in ABILITIES.items():
        boss = ab.row(src)
        row = list(boss)
        for field in ('ReactionInfluenceID', 'Flag0', 'InputBufferTime', 'KeepValue', 'ActionCategory'):
            row[ab.fi[field]] = player[ab.fi[field]]
        ab.set(row, 'CommandType', 1)
        ab.set(row, 'ATB', float(atb))
        ab.set(row, 'MP', 0)
        ab.set(row, 'Range', 1500.0)
        ab.set(row, 'UsePlace', 0)
        ab.set(row, 'ShowName', 1)
        ab.set(row, 'SortId', sort)
        ab.set(row, 'UniqueId', next(ids))
        sort += 1
        if not ab.get(boss, 'ReplaceDamageSourceID'):
            ab.set(row, 'ReplaceDamageSourceID', src)
        if name:
            ab.set(row, 'Name', name)
        assert ab.get(row, 'Name'), (key, 'no name')
        help_key = '$%s_help' % key
        ab.set(row, 'Explanation', help_key)
        help_texts[help_key] = help_text
        for field, v in over.items():
            ab.set(row, field, v)
        ab.add(key, row)
        report.append('%-26s from %-28s %-40s ATB %d  anims %s  damage %s' % (key, src, ab.get(row, 'Name'), atb, ab.get(row, 'AnimationString_Array'),
                                                                          ab.get(row, 'ReplaceDamageSourceID')))
    new_ids = None
    for key, (src, name, help_text, over) in LIMITS.items():
        row = list(ab.row(src))
        ab.set(row, 'UniqueId', next(ids))
        ab.set(row, 'Name', name)
        help_key = '$%s_help' % key
        ab.set(row, 'Explanation', help_key)
        help_texts[help_key] = help_text
        for field, v in over.items():
            ab.set(row, field, v)
        ab.add(key, row)
        report.append('%-26s from %-28s %-40s limit  anims %s  damage %s' % (key, src, ab.get(row, 'Name'), ab.get(row, 'AnimationString_Array'),
                                                                           ab.get(row, 'ReplaceDamageSourceID')))
    new_ids = iter(unique_ids(ab, len(NEW_ABILITIES), 1014))
    for key, (src, name, atb, help_text, over) in NEW_ABILITIES.items():
        boss = ab.row(src)
        row = list(boss)
        for field in ('ReactionInfluenceID', 'Flag0', 'InputBufferTime', 'KeepValue', 'ActionCategory'):
            row[ab.fi[field]] = player[ab.fi[field]]
        ab.set(row, 'CommandType', 1)
        ab.set(row, 'ATB', float(atb))
        ab.set(row, 'MP', 0)
        ab.set(row, 'Range', 1500.0)
        ab.set(row, 'UsePlace', 0)
        ab.set(row, 'ShowName', 1)
        ab.set(row, 'SortId', sort)
        ab.set(row, 'UniqueId', next(new_ids))
        sort += 1
        if not ab.get(boss, 'ReplaceDamageSourceID'):
            ab.set(row, 'ReplaceDamageSourceID', src)
        if name:
            ab.set(row, 'Name', name)
        assert ab.get(row, 'Name'), (key, 'no name')
        help_key = '$%s_help' % key
        ab.set(row, 'Explanation', help_key)
        help_texts[help_key] = help_text
        for field, v in over.items():
            ab.set(row, field, v)
        ab.add(key, row)
        report.append('%-26s from %-28s %-40s ATB %d  anims %s  damage %s' % (key, src, ab.get(row, 'Name'), atb, ab.get(row, 'AnimationString_Array'),
                                                                          ab.get(row, 'ReplaceDamageSourceID')))
    return help_texts, report


def make_cloud_rows(ab, help_texts):
    """Cloud's limit and weapon ability rows with his moves (after make_abilities: some moves are its rows)."""
    report = []
    for key, (src, name, atb, help_text, over) in CLOUD_ROWS.items():
        cloud = ab.row(key)
        move = ab.row(src)
        row = list(move)
        for field in CLOUD_KEEP:
            row[ab.fi[field]] = cloud[ab.fi[field]]
        if atb is not None:
            ab.set(row, 'ATB', float(atb))
        else:
            row[ab.fi['ATB']] = cloud[ab.fi['ATB']]
        if ab.get(row, 'CommandType') == 1 and not ab.get(row, 'Range'):
            ab.set(row, 'Range', 1500.0)
        if not ab.get(move, 'ReplaceDamageSourceID'):
            ab.set(row, 'ReplaceDamageSourceID', src)
        if name:
            ab.set(row, 'Name', name)
        assert ab.get(row, 'Name'), (key, 'no name')
        help_key = '$%s_seph_help' % key
        ab.set(row, 'Explanation', help_key)
        help_texts[help_key] = help_text
        for field, v in over.items():
            ab.set(row, field, v)
        ab.rows[ab.at[key]] = row
        report.append('%-18s (Cloud %-22s) plays %-24s %-34s type %d ATB %g  anims %s  damage %s' % (
            key, ab.get(cloud, 'Name'), src, ab.get(row, 'Name'), ab.get(row, 'CommandType'), ab.get(row, 'ATB'),
            ab.get(row, 'AnimationString_Array'), ab.get(row, 'ReplaceDamageSourceID')))
    return report


def make_meteor(dm):
    report = []
    for key, (src, over) in METEOR.items():
        row = list(dm.row(src))
        for field, v in over.items():
            dm.set(row, field, v)
        dm.add(key, row)
        report.append('%s from %s: %s' % (key, src, ', '.join('%s=%s' % (f, dm.get(row, f)) for f in over)))
    return report


def graph_packages(data):
    """Package ids of the export bundle graph (retail packages pad the graph after its count)."""
    z = Zen(data)
    o = z.graph_off
    n = struct.unpack_from('<i', data, o)[0]
    o += 4
    out = []
    for _ in range(n):
        pid, arcs = struct.unpack_from('<Qi', data, o)
        out.append(pid)
        o += 12 + 8 * arcs
    assert o <= z.graph_off + z.graph_size and not any(data[o:z.graph_off + z.graph_size]), 'graph does not parse'
    return out


def store_entry(pid, data):
    """Header entry for a package new to the container: no export alignment shift (like the container's own tables)."""
    z = Zen(data)
    region = z.graph_off - z.eb_off
    bundles = (region - 16 * len(z.exports)) // 8
    return dict(id=pid, size=len(data), export_count=len(z.exports), export_bundle_count=bundles, load_order=0,
                imports=graph_packages(data))


def main():
    out_dir = sys.argv[1]
    base = Toc(BASE + '.utoc')
    head = [i for i in range(base.entries) if base.chunk_type(i) == 10]
    assert len(head) == 1
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
                            load_order=e['load_order'], imports=e['imports']))
    paths = [c['path'] for c in chunks[1:]]
    for p in (ABILITY_TABLE, DAMAGE_TABLE, TEXT_US):
        assert p not in paths, ('already in the container', p)

    # ---- BattleAbility: the game's, plus the new abilities and limits
    ab = Table(open(GAME_ABILITY, 'rb').read())
    help_texts, ab_report = make_abilities(ab)
    ab_report += make_cloud_rows(ab, help_texts)
    ability_data = ab.encode()
    # ---- BattleDamageSource: the game's, plus the Meteor
    dm = Table(open(GAME_DAMAGE, 'rb').read())
    dm_report = make_meteor(dm)
    damage_data = dm.encode()
    # ---- BattlePlayerParameter (the container's): pt_Cloud's limits
    k = paths.index(PLAYER_TABLE) + 1
    pp = Table(chunks[k]['data'])
    cloud = pp.row('pt_Cloud')
    before = (pp.get(cloud, 'CommandAbilityID_Array'), pp.get(cloud, 'LimitAbilityID_Array'))
    game_pp = Table(open(GAME_PLAYER, 'rb').read())
    game_cloud = game_pp.row('pt_Cloud')
    assert game_pp.get(game_cloud, 'LimitAbilityID_Array') == CLOUD_LIMITS, game_pp.get(game_cloud, 'LimitAbilityID_Array')
    pp.set(cloud, 'LimitAbilityID_Array', CLOUD_LIMITS)
    pp.set(cloud, 'LimitAbilityUseableFlag_Array', game_pp.get(game_cloud, 'LimitAbilityUseableFlag_Array'))   # Cloud's unlocks
    pp.set(cloud, 'FirstLimitAbilityUseableFlag_Array', game_pp.get(game_cloud, 'FirstLimitAbilityUseableFlag_Array'))
    player_data = pp.encode()
    chunks[k]['data'] = player_data
    entries[k - 1]['size'] = len(player_data)
    # ---- CharaSpec (the container's): his rows list the form sets
    k = paths.index(CHARASPEC_TABLE) + 1
    cs = Table(chunks[k]['data'])
    spec_report = []
    for name in FORM_ROWS:
        row = cs.row(name)
        sets = cs.get(row, 'AnimationSetList_Array')
        used = {cs.get(row, f) for f in ('GroundAnimationBattlePackIndex', 'GroundAnimationFieldPackIndex', 'FlyAnimationBattlePackIndex',
                                         'FlyAnimationFieldPackIndex')}
        old_sets = list(sets)
        for want in FORM_SETS:
            if want in sets:
                continue
            free = [i for i, v in enumerate(sets) if v is None and i not in used and i >= 7] or \
                   [i for i, v in enumerate(sets) if v is None and i not in used]
            if free:
                sets[free[0]] = want
            else:
                sets.append(want)
        cs.set(row, 'AnimationSetList_Array', sets)
        spec_report.append('%s sets %s -> %s' % (name, old_sets, sets))
        for field, wanted in (('ContentsEffect_Array', FORM_EFFECTS), ('SharedCharaSpecList_Array', FORM_SHARED)):
            values = cs.get(row, field)
            old_values = list(values)
            values += [w for w in wanted if w not in values]
            cs.set(row, field, values)
            spec_report.append('%s %s %s -> %s' % (name, field, old_values, values))
    spec_data = cs.encode()
    chunks[k]['data'] = spec_data
    entries[k - 1]['size'] = len(spec_data)
    # ---- the US resident text: names and help
    texts = dict(TEXTS)
    texts.update(help_texts)
    text_data = txtres.add(open(GAME_TEXT_US, 'rb').read(), sorted(texts.items()))
    tentries, _ = txtres.parse(text_data)
    tmap = {a: b for a, b, _ in tentries}
    for key, value in texts.items():
        assert tmap[key] == value
    for key in [ab.get(ab.row(n), 'Name') for n in list(ABILITIES) + list(LIMITS) + list(NEW_ABILITIES) + list(CLOUD_ROWS)]:
        assert key in tmap, ('name text missing', key)

    for path, data in ((ABILITY_TABLE, ability_data), (DAMAGE_TABLE, damage_data), (TEXT_US, text_data)):
        pid = W.package_id('/Game/' + path[:-len('.uasset')])
        chunks.append(dict(id64=pid, type=2, data=data, path=path))
        entries.append(store_entry(pid, data))

    cid2 = W.container_id_from_name(NAME)
    assert cid2 == cid
    chunks[0] = dict(id64=cid2, type=10, data=W.container_header(cid2, entries), path=None)
    os.makedirs(out_dir, exist_ok=True)
    outb = os.path.join(out_dir, NAME)
    W.write_container(outb, NAME, chunks, mount=MOUNT)
    shutil.copy(BASE + '.pak', outb + '.pak')
    back = Toc(outb + '.utoc')
    assert back.container_id == cid2 and back.entries == len(chunks)
    for i, c in enumerate(chunks):
        assert back.read(i) == c['data'] and back.chunk_id64(i) == c['id64'] and back.chunk_type(i) == c['type']
        if c['path']:
            assert back.files.get(i) == MOUNT + c['path'], back.files.get(i)
    _, ents = parse_header(back.read(0))
    assert set(ents) == {c['id64'] for c in chunks[1:]}
    print('\n'.join(ab_report))
    print('\n'.join(dm_report))
    print('pt_Cloud commands %s, limits %s -> %s (flags %s, first %s)' % (before[0], before[1], CLOUD_LIMITS, pp.get(cloud, 'LimitAbilityUseableFlag_Array'),
                                                                     pp.get(cloud, 'FirstLimitAbilityUseableFlag_Array')))
    print('\n'.join(spec_report))
    print('texts added: %d' % len(texts))
    print('%d packages (%d from the installed %s + BattleAbility, BattleDamageSource, US Resident_TxtRes)' % (len(chunks) - 1, base.entries - 1, NAME))


if __name__ == '__main__':
    main()
