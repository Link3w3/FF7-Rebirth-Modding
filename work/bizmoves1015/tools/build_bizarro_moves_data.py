"""Bizarro Sephiroth's summon with his own moves, the data side, in FullyPlayableSephirothDataAssets_P:
  * BattleAbility: Alexander's summon abilities play Bizarro Sephiroth's own attacks (his animations, and his damage through
    ReplaceDamageSourceID, the prefix his animations' "?_01" damage ids resolve with), keeping their summon settings
    (ids, ATB, command menu, targets); three more of his attacks are new summon abilities,
  * BattleDamageSource: his damage sources for those attacks (from the final battle's field table, 3120-CAPTL), so they
    hit anywhere,
  * BattleSummonAbilityChoice: the summon's AI also picks the three new attacks,
  * Text/US: the two command abilities are called by his attacks' names.
The animations themselves come from his own animation sets (BizarroSummon.json's battle sources).
    build_bizarro_moves_data.py <base dir> <out dir>"""
import io, contextlib, os, shutil, sys
sys.path[:0] = [os.path.dirname(os.path.abspath(__file__)), '/work/sephatb/tools', '/work/iostore',
                '/work/cs', '/work/tools', '/work/evil1013/tools', '/work/swap1012/tools',
                '/work/vincentfix', '/work/weap1012/tools']
import build_atb as B
from iostore import Toc
from zen import Zen
import iostore_write as W
from hdr import parse_header
import gameids
import txtres

NAME = B.NAME
MOUNT = B.MOUNT
ABILITY = 'DataObject/Resident/BattleAbility.uasset'
DAMAGE = 'DataObject/Resident/BattleDamageSource.uasset'
CHOICE = 'DataObject/Resident/BattleSummonAbilityChoice.uasset'
TEXT = B.TEXT_US
FIELD_ABILITY = '/work/bizmoves1015/raw/3120-CAPTL__BattleAbility.uasset'
FIELD_DAMAGE = '/work/bizmoves1015/raw/3120-CAPTL__BattleDamageSource.uasset'
GAME_CHOICE = '/work/summon1015/pkgs/Resident__BattleSummonAbilityChoice.uasset'

# Alexander's summon ability -> Bizarro Sephiroth's attack it becomes
SWAP = {
    'SU2030_00_AtkCleaveR01': 'EB2210_00_WingSwingR',          # close: right wing swing
    'SU2030_00_AtkCleaveL01': 'EB2210_00_WingSwingL',          # close: left wing swing
    'SU2030_00_AtkHardStrike01': 'EB2210_00_BurstFlare',       # close: Apocalyptic Fire
    'SU2030_00_AtkMagicalShockNew': 'EB2210_00_ShadowFlare',   # far: Swarm
    'SU2030_00_AtkShockWaveR01': 'EB2210_00_EyeLaserR',        # far: Lacryma Deus
    'SU2030_00_AtkShockWaveL01': 'EB2210_00_EyeLaserL',        # far: Lacryma Deus
    'SU2030_00_AtkShockWaveB01': 'EB2210_00_WindBlow',         # far: Maelstrom
    'SU2030_00_AtkLaserMissileNew': 'EB2210_00_Hattou',        # command, 1 ATB: Octaslash
    'SU2030_00_AtkGiantbeam': 'EB2210_00_HeartlessAngel',      # command, 2 ATB: Heartless Angel
}
# new summon abilities: id -> (his attack, the Alexander ability whose summon settings it takes, the choice row it copies)
NEW = {
    'SU2030_00_BizZanshin': ('EB2210_00_Zanshin1', 'SU2030_00_AtkHardStrike01', 'SU2030_00_AbilityChoice_03'),
    'SU2030_00_BizWingFeeler': ('EB2210_00_FeelerWingSmash', 'SU2030_00_AtkHardStrike01', 'SU2030_00_AbilityChoice_03'),
    'SU2030_00_BizStigma': ('EB2210_00_Stigma', 'SU2030_00_AtkShockWaveB01', 'SU2030_00_AbilityChoice_07'),
}
NEW_CHOICE = {'SU2030_00_BizZanshin': 'SU2030_00_AbilityChoice_08', 'SU2030_00_BizWingFeeler': 'SU2030_00_AbilityChoice_09',
              'SU2030_00_BizStigma': 'SU2030_00_AbilityChoice_10'}
# what of his ability a summon ability takes: the animations and how they play, and the damage prefix
TAKE = ['AddAnimationName_Array', 'AnimationString_Array', 'AddAnimationPlayInterval_Array', 'AnimationParameter_Array',
        'AnimationSelectType_Array', 'AddAnimationIndex_Array', 'AddAnimationPlayCount_Array', 'AddAnimationEndBase_Array',
        'CancelNumber_Array', 'AnimationUpperBodyName', 'ReplaceDamageSourceID', 'ResourceID_Array', 'ResourceName_Array']
TEXTS = {
    'SU2030_00_Atk001': ('Tracking Beam', 'Octaslash'),
    'SU2030_00_Atk001_help': ('Fire myriad lasers at an enemy.', 'Cut down an enemy with a flurry of lightning-fast slashes.'),
    'SU2030_00_Atk002': ('Grand Laser', 'Heartless Angel'),
    'SU2030_00_Atk002_help': ('Fire an enormous beam of light at an enemy.', "Bring every enemy's HP to the brink of death."),
}


def quiet(f, *a):
    with contextlib.redirect_stdout(io.StringIO()):
        return f(*a)


def fields(t):
    return [f[0][0] for f in t.fields]


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

    # ---- BattleAbility
    k_ab = paths.index(ABILITY) + 1
    ab = quiet(B.Table, chunks[k_ab]['data'])
    fab = quiet(B.Table, open(FIELD_ABILITY, 'rb').read())
    assert fields(ab) == fields(fab), 'the field table has other fields'
    before = {key: list(ab.row(key)) for key in SWAP}
    for mine, his in SWAP.items():
        row, src = ab.row(mine), fab.row(his)
        for f in TAKE:
            row[ab.fi[f]] = src[fab.fi[f]]
        report.append('%s plays %s: %s, damage %s' % (mine, his, ab.get(row, 'AnimationString_Array'), ab.get(row, 'ReplaceDamageSourceID')))
    ids = iter(B.unique_ids(ab, len(NEW), 1015))
    for key, (his, template, _) in NEW.items():
        assert key not in ab.at, key
        row = list(before.get(template) or ab.row(template))
        src = fab.row(his)
        for f in TAKE:
            row[ab.fi[f]] = src[fab.fi[f]]
        ab.set(row, 'UniqueId', next(ids))
        ab.add(key, row)
        report.append('%s (new) plays %s: %s' % (key, his, ab.get(row, 'AnimationString_Array')))
    data = quiet(ab.encode)
    chunks[k_ab]['data'] = data
    if entries[k_ab - 1]['size']:
        entries[k_ab - 1]['size'] = len(data)
    # read back: the swapped rows changed only in TAKE, new rows present, every other row as it was
    ab0 = quiet(B.Table, base.read([i for i in range(base.entries) if base.files.get(i) == MOUNT + ABILITY][0]))
    ab2 = quiet(B.Table, data)
    take = {ab2.fi[f] for f in TAKE}
    for key in ab0.at:
        r0, r2 = ab0.row(key), ab2.row(key)
        if key in SWAP:
            assert [v for j, v in enumerate(r2) if j not in take] == [v for j, v in enumerate(r0) if j not in take], key
            src = fab.row(SWAP[key])
            assert all(r2[ab2.fi[f]] == src[fab.fi[f]] for f in TAKE), key
        else:
            assert r2 == r0, key
    assert all(k in ab2.at for k in NEW) and len(ab2.keys) == len(ab0.keys) + len(NEW)
    uids = [ab2.get(ab2.row(k), 'UniqueId') for k in ab2.at]
    assert len(uids) == len(set(uids)), 'unique ids repeat'

    # ---- BattleDamageSource: his damage sources for those attacks
    k_ds = paths.index(DAMAGE) + 1
    ds = quiet(B.Table, chunks[k_ds]['data'])
    fds = quiet(B.Table, open(FIELD_DAMAGE, 'rb').read())
    assert fields(ds) == fields(fds), 'the field table has other fields'
    prefixes = sorted({fab.get(fab.row(h), 'ReplaceDamageSourceID') for h in list(SWAP.values()) + [n[0] for n in NEW.values()]})
    added = []
    for key in fds.at:
        if any(key == p or key.startswith(p + '_') for p in prefixes):
            assert key not in ds.at, ('already a resident damage source', key)
            ds.add(key, list(fds.row(key)))
            added.append(key)
    # everything those rows name of other damage sources is there too
    for key in added:
        r = ds.row(key)
        for f in ('HitDamageSourceID_Array', 'ConditionCreateDamageSourceID_Array'):
            for v in ds.get(r, f) or []:
                assert v in ds.at, (key, f, v)
    data = quiet(ds.encode)
    chunks[k_ds]['data'] = data
    if entries[k_ds - 1]['size']:
        entries[k_ds - 1]['size'] = len(data)
    ds2 = quiet(B.Table, data)
    assert len(ds2.keys) == len(ds.keys) and all(k in ds2.at for k in added)
    report.append('BattleDamageSource: %d of his rows added (%s)' % (len(added), ', '.join(prefixes)))

    # ---- BattleSummonAbilityChoice: the AI picks the new attacks too
    assert CHOICE not in paths
    choice_data = open(GAME_CHOICE, 'rb').read()
    ch = quiet(B.Table, choice_data)
    for key, (_, _, template) in NEW.items():
        row = list(ch.row(template))
        ch.set(row, 'AbilityID', key)
        ch.add(NEW_CHOICE[key], row)
    data = quiet(ch.encode)
    ch2 = quiet(B.Table, data)
    assert [ch2.get(ch2.row(NEW_CHOICE[k]), 'AbilityID') for k in NEW] == list(NEW)
    ch0 = quiet(B.Table, choice_data)
    for key in ch0.at:
        assert ch2.row(key) == ch0.row(key), key
    pid = W.package_id('/Game/' + CHOICE[:-len('.uasset')])
    assert pid in gameids.load()[0], 'not a game package: ' + CHOICE
    z = Zen(choice_data)
    imports = sorted({(v & ~(3 << 62)) for v in []})
    chunks.append(dict(id64=pid, type=2, data=data, path=CHOICE))
    # a data object with no package imports (the table) needs no imported packages
    entries.append(dict(id=pid, size=len(data), export_count=len(Zen(data).exports), export_bundle_count=1, load_order=0, imports=[]))
    report.append('BattleSummonAbilityChoice: %s' % ', '.join('%s -> %s' % (NEW_CHOICE[k], k) for k in NEW))

    # ---- Text/US: the command abilities' names
    k_tx = paths.index(TEXT) + 1
    tdata = chunks[k_tx]['data']
    tentries, _ = txtres.parse(tdata)
    have = {key: text for key, text, _ in tentries}
    pairs = []
    for name, (old, new) in TEXTS.items():
        key = '$' + name if '$' + name in have else name
        assert have[key] == old, (key, have[key])
        pairs.append((key, new))
    text = txtres.add(tdata, pairs)
    chunks[k_tx]['data'] = text
    if entries[k_tx - 1]['size']:
        entries[k_tx - 1]['size'] = len(text)
    t2 = {key: t for key, t, _ in txtres.parse(text)[0]}
    assert all(t2[k] == v for k, v in pairs) and len(t2) == len(have)
    report.append('Text/US: %s' % '; '.join('%s = %s' % kv for kv in pairs))

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
    changed = {ABILITY, DAMAGE, TEXT, CHOICE}
    for c, e in zip(chunks[1:], entries):
        got = ents[c['id64']]
        assert (got['size'], got['export_count'], got['export_bundle_count'], got['imports'], got['load_order']) == \
               (e['size'], e['export_count'], e['export_bundle_count'], e['imports'], e['load_order'])
        if c['path'] not in changed:
            j = [kk for kk, v in base.files.items() if v == MOUNT + c['path']][0]
            assert c['data'] == base.read(j), c['path']
    print('\n'.join(report))
    print('container: %s (%d packages)' % (outb, len(chunks) - 1))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
