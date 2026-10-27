"""FullyPlayableSephirothDataAssets_P without Cloud's Neutral20 set in his packs: the 9 CharaSpec packs of Cloud's rows (the
playable Sephiroth, Zack's SOLDIER outfits included) no longer load /Game/Motion/Player/PC0000_Cloud/Neutral20 themselves;
Create a Character System builds his field sets (Neutral20 and Emotion00 from Cloud's folder) from SephirothForms.json.
Everything else of the container as it is.
    build_n20.py <base dir> <out dir>"""
import os, shutil, sys, io, contextlib
sys.path[:0] = [os.path.dirname(os.path.abspath(__file__)), '/work/sephatb/tools', '/work/iostore',
                '/work/cs', '/work/tools', '/work/evil1013/tools', '/work/swap1012/tools',
                '/work/vincentfix', '/work/weap1012/tools', '/work/gunmoves']
import build_atb as B
from iostore import Toc
from zen import Zen
import iostore_write as W
from hdr import parse_header
import tagged
import drop_pack_asset as D

NAME = B.NAME
MOUNT = B.MOUNT
SET = '/Game/Motion/Player/PC0000_Cloud/Neutral20.Neutral20'
ROWS = ['PC0000_00_Cloud_Standard', 'PC0000_08_Cloud_SoldierNoHelmet', 'PC0000_09_Cloud_CostaClothing', 'PC0000_10_Cloud_CostaClothing2',
        'PC0000_04_Cloud_ZackCostume', 'PC0000_12_Cloud_ZackCostumeDirty', 'PC0000_18_Cloud_ZackCostumeAge21',
        'PC0000_19_Cloud_ZackCostumeDirtyAge21', 'PC0000_23_Cloud_ZackCostumeWet']
PACK = 'DataAsset/Game/CharaSpec/CharaSpec_%s.uasset'


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
    for row in ROWS:
        k = paths.index(PACK % row) + 1
        old = chunks[k]['data']
        new, pid, imp = D.drop(old, SET)
        assert pid in entries[k - 1]['imports'], row
        chunks[k]['data'] = new          # its header entry's size stays as the base has it (0 in this container)
        entries[k - 1]['imports'] = [x for x in entries[k - 1]['imports'] if x != pid]
        z0, z1 = Zen(old), Zen(new)
        p0, p1 = tagged.export_props(z0, 0), tagged.export_props(z1, 0)
        a0, a1 = p0['AssetDataList'][0]['AssetUserData'], p1['AssetDataList'][0]['AssetUserData']
        assert a1 == [x for x in a0 if x != ('obj', -(imp + 1))] and len(a1) == len(a0) - 1, row
        assert {kk: v for kk, v in p0.items() if kk != 'AssetDataList'} == {kk: v for kk, v in p1.items() if kk != 'AssetDataList'}
        assert p0['AssetClassList'] == p1['AssetClassList']
        assert {gp for gp, _ in D.graph_entries(new, z1)} <= set(entries[k - 1]['imports'])
        report.append('%s: Neutral20 out (%d -> %d asset(s), %d -> %d bytes, %d imported packages)' % (
            row, len(a0), len(a1), len(old), len(new), len(entries[k - 1]['imports'])))
    cid2 = W.container_id_from_name(NAME)
    assert cid2 == cid
    chunks[0] = dict(id64=cid2, type=10, data=W.container_header(cid2, entries), path=None)
    os.makedirs(out_dir, exist_ok=True)
    outb = os.path.join(out_dir, NAME)
    W.write_container(outb, NAME, chunks, mount=MOUNT)
    shutil.copy(base_path + '.pak', outb + '.pak')
    # read back: every chunk as written; header entries as wanted; every other package byte for byte as the base
    back = Toc(outb + '.utoc')
    assert back.container_id == cid2 and back.entries == len(chunks)
    for i, c in enumerate(chunks):
        assert back.read(i) == c['data'] and back.chunk_id64(i) == c['id64'] and back.chunk_type(i) == c['type']
        if c['path']:
            assert back.files.get(i) == MOUNT + c['path'], back.files.get(i)
    _, ents = parse_header(back.read(0))
    assert set(ents) == {c['id64'] for c in chunks[1:]}
    changed = {PACK % r for r in ROWS}
    for c, e in zip(chunks[1:], entries):
        got = ents[c['id64']]
        assert (got['size'], got['export_count'], got['export_bundle_count'], got['imports'], got['load_order']) == \
               (e['size'], e['export_count'], e['export_bundle_count'], e['imports'], e['load_order'])
        if c['path'] not in changed:
            j = [k for k, v in base.files.items() if v == MOUNT + c['path']][0]
            assert c['data'] == base.read(j) and base_entries[c['id64']]['imports'] == e['imports'], c['path']
    print('\n'.join(report))
    print('container: %s (%d packages, %d changed)' % (outb, len(chunks) - 1, len(changed)))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
