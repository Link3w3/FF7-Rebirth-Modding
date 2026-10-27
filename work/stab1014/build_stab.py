"""Skewer that reaches and Meteor as an ATB move, in FullyPlayableSephirothDataAssets_P:
    build_stab.py <out dir>
  * the installed container as it is (the Grip of Fate feeler build), plus
  * BattleAbility: Skewer (PC0010_T_WarpStab) makes its own hits (ReplaceDamageSourceID PC0010_T_Stab); a new ATB ability
    PC0010_T_Meteor, the Meteor limit (PC0010_Limit003) as a command (2 ATB),
  * BattleDamageSource: Skewer's hits PC0010_T_Stab_01 / PC0010_T_Stab_Feeler_01 (the boss's stabs, with his normal
    attacks' reach: the capsule from his sword's NAttack1 to NAttack2, radius 150, where the boss's is a 25 cm needle to
    NAttackBoss, a socket he doesn't have) and the throw-off PC0010_T_StabDetach_01 the same way,
  * US Resident text: Meteor's help."""
import os, shutil, sys, io, contextlib
sys.path[:0] = ['/work/sephatb/tools', '/work/iostore', '/work/cs', '/work/tools',
                '/work/evil1013/tools', '/work/swap1012/tools', '/work/vincentfix',
                '/work/weap1012/tools']
import build_atb as B
from iostore import Toc
import iostore_write as W
from hdr import parse_header
import txtres

NAME = B.NAME
BASE = '/work/feeler1014/out1/' + NAME          # what is installed (Grip of Fate feeler)
MOUNT = B.MOUNT
REACH = {'TargetName': 'NAttack2', 'CollisionParameter_Array': [150.0, 0.0, 100.0]}   # his normal attacks' capsule
STABS = {'PC0010_T_Stab_01': 'PC0010_10_Stab_01', 'PC0010_T_Stab_Feeler_01': 'PC0010_10_Stab_Feeler_01',
         'PC0010_T_StabDetach_01': 'PC0010_10_StabDetach_01'}
METEOR_KEY = 'PC0010_T_Meteor'
METEOR_FROM = 'PC0010_Limit003'
METEOR_ATB = 2.0
METEOR_HELP = 'Call down a meteor the size of a world upon your foes.'


def quiet(f, *a):
    with contextlib.redirect_stdout(io.StringIO()):
        return f(*a)


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
    report = []

    def replace(path, data):
        k = paths.index(path) + 1
        chunks[k]['data'] = data
        entries[k - 1]['size'] = len(data)

    # ---- BattleAbility
    k = paths.index(B.ABILITY_TABLE) + 1
    ab = quiet(B.Table, chunks[k]['data'])
    stab = ab.row('PC0010_T_WarpStab')
    assert ab.get(stab, 'ReplaceDamageSourceID') == 'PC0010_10_Stab', ab.get(stab, 'ReplaceDamageSourceID')
    ab.set(stab, 'ReplaceDamageSourceID', 'PC0010_T_Stab')
    report.append('PC0010_T_WarpStab: ReplaceDamageSourceID PC0010_10_Stab -> PC0010_T_Stab')
    assert METEOR_KEY not in ab.at
    limit = ab.row(METEOR_FROM)
    player = ab.row(B.PLAYER_TEMPLATE)
    row = list(limit)
    for field in ('ReactionInfluenceID', 'Flag0', 'InputBufferTime', 'KeepValue', 'ActionCategory'):
        row[ab.fi[field]] = player[ab.fi[field]]
    ab.set(row, 'CommandType', 1)
    ab.set(row, 'ATB', METEOR_ATB)
    ab.set(row, 'MP', 0)
    ab.set(row, 'UsePlace', 0)
    ab.set(row, 'ShowName', 1)
    sort = max(ab.get(ab.row(n), 'SortId') for n in ab.at if n.startswith('PC0010_T_') or n.startswith('PC0010_W'))
    ab.set(row, 'SortId', sort + 1)
    ab.set(row, 'UniqueId', B.unique_ids(ab, 1, 1015)[0])
    help_key = '$%s_help' % METEOR_KEY
    ab.set(row, 'Explanation', help_key)
    ab.add(METEOR_KEY, row)
    report.append('%s from %s: %s, ATB %g, anims %s, damage %s, range %g, sort %d' % (
        METEOR_KEY, METEOR_FROM, ab.get(row, 'Name'), ab.get(row, 'ATB'), ab.get(row, 'AnimationString_Array'),
        ab.get(row, 'ReplaceDamageSourceID'), ab.get(row, 'Range'), ab.get(row, 'SortId')))
    replace(B.ABILITY_TABLE, ab.encode())

    # ---- BattleDamageSource
    k = paths.index(B.DAMAGE_TABLE) + 1
    dm = quiet(B.Table, chunks[k]['data'])
    for key, src in STABS.items():
        assert key not in dm.at, key
        new = list(dm.row(src))
        for field, v in REACH.items():
            dm.set(new, field, v)
        dm.add(key, new)
        report.append('%s from %s: %s' % (key, src, ', '.join('%s=%s' % (f, dm.get(new, f)) for f in
                                                              ('TargetName', 'CreatePartName', 'CollisionType', 'CollisionParameter_Array',
                                                               'HitReactionType_Array', 'HitReactionParamID_Array', 'HitReactionParam_Array',
                                                               'Power', 'CutValue'))))
    replace(B.DAMAGE_TABLE, dm.encode())

    # ---- US text
    k = paths.index(B.TEXT_US) + 1
    text = txtres.add(chunks[k]['data'], [(help_key, METEOR_HELP)])
    tmap = {a: b for a, b, _ in txtres.parse(text)[0]}
    assert tmap[help_key] == METEOR_HELP and ab.get(row, 'Name') in tmap
    replace(B.TEXT_US, text)
    report.append('text %s: %s (name %s: %s)' % (help_key, METEOR_HELP, ab.get(row, 'Name'), tmap[ab.get(row, 'Name')]))

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
    for c, e in zip(chunks[1:], entries):
        got = ents[c['id64']]
        assert (got['size'], got['export_count'], got['export_bundle_count'], got['imports']) == (e['size'], e['export_count'], e['export_bundle_count'], e['imports'])
    # read back: the tables have the rows, everything else as before
    before = {p: base.read([i for i in range(base.entries) if base.files.get(i) == MOUNT + p][0]) for p in (B.ABILITY_TABLE, B.DAMAGE_TABLE)}
    after = {p: back.read(paths.index(p) + 1) for p in (B.ABILITY_TABLE, B.DAMAGE_TABLE)}
    ab0, ab1 = quiet(B.Table, before[B.ABILITY_TABLE]), quiet(B.Table, after[B.ABILITY_TABLE])
    assert ab1.keys == ab0.keys + [B.name_tuple(METEOR_KEY)]
    for key in ab0.at:
        for f in ab0.fields:
            fn = f[0][0]
            want = ab0.get(ab0.row(key), fn)
            if key == 'PC0010_T_WarpStab' and fn == 'ReplaceDamageSourceID':
                want = 'PC0010_T_Stab'
            assert ab1.get(ab1.row(key), fn) == want, (key, fn)
    dm0, dm1 = quiet(B.Table, before[B.DAMAGE_TABLE]), quiet(B.Table, after[B.DAMAGE_TABLE])
    assert dm1.keys == dm0.keys + [B.name_tuple(k) for k in STABS]
    for key in dm0.at:
        assert dm1.row(key) == dm0.row(key), key
    print('\n'.join(report))
    print('%d packages' % (len(chunks) - 1))


if __name__ == '__main__':
    main()
