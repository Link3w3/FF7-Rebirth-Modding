"""Sephiroth in prologue Cloud's place too: Cloud in Zack's SOLDIER outfit ("CloudZack": PC0000_04_Cloud_ZackCostume and its
dirty, age-21, dirty age-21 and wet versions) gets the same swap as Cloud's other rows in FullyPlayableSephirothDataAssets_P.
    build_zack.py <out dir>
  * the installed container as it is (every package byte for byte, their header entries), plus
  * CharaSpec table: each ZackCostume row becomes the swapped PC0000_00_Cloud_Standard row (Sephiroth's model, voice, sounds,
    effects, AI, his sets and forms) with its own CharaID; its NoBattle / Reserve rows point at itself, as the swap does,
  * a CharaSpec pack per row: the swapped PC0000_00_Cloud_Standard pack (it spawns Sephiroth) under the row's name."""
import os, shutil, struct, sys
sys.path[:0] = ['/work/sephatb/tools', '/work/iostore', '/work/cs', '/work/tools',
                '/work/evil1013/tools', '/work/swap1012/tools', '/work/vincentfix',
                '/work/weap1012/tools']
import build_atb as B
from iostore import Toc
from zen import Zen
import iostore_write as W
import zenrename
import gameids
from hdr import parse_header

NAME = B.NAME
BASE = '/work/sephatb/out4/' + NAME
RETAIL_TABLE = '/work/cs/raw/retail_CharaSpec.uasset'
MOUNT = B.MOUNT
PACKS = 'DataAsset/Game/CharaSpec/'
SOURCE_ROW = 'PC0000_00_Cloud_Standard'
ZACK_ROWS = ['PC0000_04_Cloud_ZackCostume', 'PC0000_12_Cloud_ZackCostumeDirty', 'PC0000_18_Cloud_ZackCostumeAge21',
             'PC0000_19_Cloud_ZackCostumeDirtyAge21', 'PC0000_23_Cloud_ZackCostumeWet']
OWN_FIELDS = ('CharaID',)                                  # each row keeps its own
SELF_FIELDS = ('NoBattleCharaSpec', 'ReserveCharaSpec')   # point at the row itself (when the game's row has one)


def pack_for(row, source_data):
    old_pkg, new_pkg = '/Game/' + PACKS + 'CharaSpec_' + SOURCE_ROW, '/Game/' + PACKS + 'CharaSpec_' + row
    old_obj, new_obj = 'CharaSpec_' + SOURCE_ROW, 'CharaSpec_' + row
    z = Zen(source_data)
    assert z.names[z.name_mapped & 0x3FFFFFFF] == old_pkg, 'the source pack is not named ' + old_pkg
    assert len(z.exports) == 1 and z.exports[0]['name'] == old_obj
    hashed = (2 << 62) | gameids.objhash(new_pkg + '.' + new_obj)
    data = zenrename.rebuild(source_data, {old_pkg: new_pkg, old_obj: new_obj}, export_global_imports={0: hashed})
    z2 = Zen(data)
    assert z2.names[z2.name_mapped & 0x3FFFFFFF] == new_pkg and z2.exports[0]['name'] == new_obj
    assert z2.exports[0]['global_import'] == hashed
    assert z2.imports == z.imports and data[z2.header_end:] == source_data[z.header_end:]
    assert not [n for n in z2.names if SOURCE_ROW in n], [n for n in z2.names if SOURCE_ROW in n]
    return data


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

    # ---- CharaSpec table: the ZackCostume rows take the swapped standard row
    retail = B.Table(open(RETAIL_TABLE, 'rb').read())
    k = paths.index(B.CHARASPEC_TABLE) + 1
    cs = B.Table(chunks[k]['data'])
    source = cs.row(SOURCE_ROW)
    report = []
    for name in ZACK_ROWS:
        row = cs.row(name)
        assert row == retail.row(name), name + ' is already changed in the container'
        new = list(source)
        for f in OWN_FIELDS:
            new[cs.fi[f]] = row[cs.fi[f]]
        for f in SELF_FIELDS:
            if retail.get(retail.row(name), f) is not None:
                new[cs.fi[f]] = cs.value(f, name)
            else:
                new[cs.fi[f]] = row[cs.fi[f]]
        row[:] = new
        changed = [f[0][0] for f in cs.fields if cs.get(row, f[0][0]) != retail.get(retail.row(name), f[0][0])]
        report.append('%s: %s' % (name, ', '.join(changed)))
    spec_data = cs.encode()
    chunks[k]['data'] = spec_data
    entries[k - 1]['size'] = len(spec_data)

    # ---- packs: the swapped standard pack under each row's name, with the same dependencies
    src_path = PACKS + 'CharaSpec_' + SOURCE_ROW + '.uasset'
    src = paths.index(src_path) + 1
    for name in ZACK_ROWS:
        path = PACKS + 'CharaSpec_' + name + '.uasset'
        assert path not in paths, ('already in the container', path)
        data = pack_for(name, chunks[src]['data'])
        pid = W.package_id('/Game/' + path[:-len('.uasset')])
        assert pid in gameids.load()[0], ('not a game package', path)
        chunks.append(dict(id64=pid, type=2, data=data, path=path))
        e = dict(entries[src - 1])
        e.update(id=pid, size=len(data))
        entries.append(e)
        report.append('pack %s (%d bytes, %d imports in its header entry)' % (path, len(data), len(e['imports'])))

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
    # the rows read back as the standard row
    cs2 = B.Table(back.read(chunks.index(chunks[k])))
    for name in ZACK_ROWS:
        for f in cs2.fields:
            fn = f[0][0]
            want = cs2.get(cs2.row(SOURCE_ROW), fn)
            if fn in OWN_FIELDS:
                want = retail.get(retail.row(name), fn)
            if fn in SELF_FIELDS:
                want = name if retail.get(retail.row(name), fn) is not None else None
            assert cs2.get(cs2.row(name), fn) == want, (name, fn)
    print('\n'.join(report))
    print('%d packages (%d from %s + %d packs)' % (len(chunks) - 1, base.entries - 1, BASE, len(ZACK_ROWS)))


if __name__ == '__main__':
    main()
