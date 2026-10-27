"""His CharaSpec rows with Cloud's own field sets back where the game has them (Emotion00 in slot 3, Neutral20 in slot 8:
vanilla Cloud), the forms' battle sets in the slots left: Battle02 7 (a slot the game takes), Battle03 9 and Battle04 5
(Create a Character System 3.5 makes any set of the pack switchable). Everything else of the container as it is.
    build_rows.py <base dir> <out dir>"""
import os, shutil, sys, io, contextlib
sys.path[:0] = ['/work/sephatb/tools', '/work/iostore', '/work/cs', '/work/tools',
                '/work/evil1013/tools', '/work/swap1012/tools', '/work/vincentfix',
                '/work/weap1012/tools']
import build_atb as B
from iostore import Toc
import iostore_write as W
from hdr import parse_header

NAME = B.NAME
MOUNT = B.MOUNT
ROWS = ['PC0000_00_Cloud_Standard', 'PC0000_08_Cloud_SoldierNoHelmet', 'PC0000_09_Cloud_CostaClothing', 'PC0000_10_Cloud_CostaClothing2',
        'PC0000_04_Cloud_ZackCostume', 'PC0000_12_Cloud_ZackCostumeDirty', 'PC0000_18_Cloud_ZackCostumeAge21',
        'PC0000_19_Cloud_ZackCostumeDirtyAge21', 'PC0000_23_Cloud_ZackCostumeWet']
BEFORE = ['Battle00', 'Neutral00', 'Neutral20', None, 'Facial00', 'Battle04', 'Battle01', 'Battle02', 'Battle03', None, 'Battle00_Comp']
AFTER = ['Battle00', 'Neutral00', None, 'Emotion00', 'Facial00', 'Battle04', 'Battle01', 'Battle02', 'Neutral20', 'Battle03', 'Battle00_Comp']


def quiet(f, *a):
    with contextlib.redirect_stdout(io.StringIO()):
        return f(*a)


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
                            load_order=e['load_order'], imports=e['imports']))
    paths = [c['path'] for c in chunks[1:]]
    k = paths.index(B.CHARASPEC_TABLE) + 1
    cs = quiet(B.Table, chunks[k]['data'])
    for name in ROWS:
        row = cs.row(name)
        sets = cs.get(row, 'AnimationSetList_Array')
        if sets != BEFORE:
            raise SystemExit('%s: unexpected sets %s' % (name, sets))
        cs.set(row, 'AnimationSetList_Array', AFTER)
        print('%s: %s' % (name, AFTER))
    data = cs.encode()
    chunks[k]['data'] = data
    entries[k - 1]['size'] = len(data)
    cid2 = W.container_id_from_name(NAME)
    assert cid2 == cid
    chunks[0] = dict(id64=cid2, type=10, data=W.container_header(cid2, entries), path=None)
    os.makedirs(out_dir, exist_ok=True)
    outb = os.path.join(out_dir, NAME)
    W.write_container(outb, NAME, chunks, mount=MOUNT)
    shutil.copy(base_path + '.pak', outb + '.pak')
    # read back: every chunk as written; the rows as wanted, every other row and table unchanged
    back = Toc(outb + '.utoc')
    for i, c in enumerate(chunks):
        assert back.read(i) == c['data'] and back.chunk_id64(i) == c['id64'] and back.chunk_type(i) == c['type']
    cs0 = quiet(B.Table, base.read([i for i in range(base.entries) if base.files.get(i) == MOUNT + B.CHARASPEC_TABLE][0]))
    cs1 = quiet(B.Table, back.read(k))
    assert cs1.keys == cs0.keys
    fi = cs1.fi['AnimationSetList_Array']
    for key in cs0.at:
        r0, r1 = cs0.row(key), cs1.row(key)
        if key in ROWS:
            assert cs1.get(r1, 'AnimationSetList_Array') == AFTER
            assert [v for j, v in enumerate(r1) if j != fi] == [v for j, v in enumerate(r0) if j != fi], key
        else:
            assert r1 == r0, key
    print('container: %s (%d chunks), rows read back' % (outb, len(chunks)))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
