"""Grip of Fate's feeler for your Sephiroth: the bind it puts on an enemy (special status Sephiroth_BindFeeler) grows the
feeler EN9000_20_Feeler_BlackEnd2 around it, a character the binder must have loaded, as the boss Sephiroth has it in his
row's SharedCharaSpecList_Array (next to the feeler bullet EN9000_22_Feeler_BlackBulletEnd2). His rows (Cloud's swapped
rows and the CloudZack rows) get it in FullyPlayableSephirothDataAssets_P:
    build_feeler.py <out dir>
  * the installed container as it is (every package byte for byte, their header entries), plus
  * CharaSpec table: EN9000_20_Feeler_BlackEnd2 at the end of each of his rows' SharedCharaSpecList_Array."""
import os, shutil, sys
sys.path[:0] = ['/work/sephatb/tools', '/work/iostore', '/work/cs', '/work/tools',
                '/work/evil1013/tools', '/work/swap1012/tools', '/work/vincentfix',
                '/work/weap1012/tools']
import build_atb as B
from iostore import Toc
import iostore_write as W
import gameids
from hdr import parse_header

NAME = B.NAME
BASE = '/work/zack1014/out1/' + NAME          # what is installed (CloudZack build)
RETAIL_TABLE = '/work/cs/raw/retail_CharaSpec.uasset'
MOUNT = B.MOUNT
FEELER = 'EN9000_20_Feeler_BlackEnd2'
BOSS_ROW = 'PC0010_10_Sephiroth_Transform'
ROWS = ['PC0000_00_Cloud_Standard', 'PC0000_08_Cloud_SoldierNoHelmet', 'PC0000_09_Cloud_CostaClothing', 'PC0000_10_Cloud_CostaClothing2',
        'PC0000_04_Cloud_ZackCostume', 'PC0000_12_Cloud_ZackCostumeDirty', 'PC0000_18_Cloud_ZackCostumeAge21',
        'PC0000_19_Cloud_ZackCostumeDirtyAge21', 'PC0000_23_Cloud_ZackCostumeWet']


def main():
    out_dir = sys.argv[1]
    retail = B.Table(open(RETAIL_TABLE, 'rb').read())
    assert FEELER in retail.get(retail.row(BOSS_ROW), 'SharedCharaSpecList_Array'), 'the boss row does not list the feeler'
    pid_feeler = W.package_id('/Game/DataAsset/Game/CharaSpec/CharaSpec_' + FEELER)
    assert pid_feeler in gameids.load()[0], 'the feeler has no CharaSpec pack in the game'
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
    k = paths.index(B.CHARASPEC_TABLE) + 1
    cs = B.Table(chunks[k]['data'])
    report = []
    for name in ROWS:
        row = cs.row(name)
        shared = cs.get(row, 'SharedCharaSpecList_Array')
        assert 'PC0010_00_Sephiroth_Standard' in shared, (name, 'is not one of his rows', shared)
        assert FEELER not in shared, (name, 'already lists the feeler')
        cs.set(row, 'SharedCharaSpecList_Array', shared + [FEELER])
        report.append('%s: %s' % (name, ', '.join(cs.get(row, 'SharedCharaSpecList_Array'))))
    spec_data = cs.encode()
    chunks[k]['data'] = spec_data
    entries[k - 1]['size'] = len(spec_data)

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
    # every other row and every other field reads back as before
    before = B.Table(base.read([i for i in range(base.entries) if base.files.get(i) == MOUNT + B.CHARASPEC_TABLE][0]))
    after = B.Table(back.read(k))
    assert after.keys == before.keys
    for key in before.at:
        for f in before.fields:
            fn = f[0][0]
            want = before.get(before.row(key), fn)
            if key in ROWS and fn == 'SharedCharaSpecList_Array':
                want = want + [FEELER]
            assert after.get(after.row(key), fn) == want, (key, fn)
    print('\n'.join(report))
    print('%d packages, %d bytes of CharaSpec table (was %d)' % (len(chunks) - 1, len(spec_data), len(before.data)))


if __name__ == '__main__':
    main()
