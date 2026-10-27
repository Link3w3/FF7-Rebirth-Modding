"""The Fully Playable (Young) Sephiroth forms update (Create a Character System 3.12) in a data container (FPYS's or FPS's),
the old container's blocks as they are, the changed and new chunks after them:
  * the moves of the moves container (RebirthSkelCompat/Built/SephirothForms/<set>/<name>, built by run_ys_forms.cmd):
    a move the container has already (WINGED's, made again with the transformed Sephiroth's feelers) takes its place,
    the others are added (YOUNG SEPHIROTH's Battle07, the casts built for your abilities); each laid out the way the game
    reads its own animations (align_moves.realign, checked against the game's reader);
  * CharaSpec (with --battle07): Cloud's 9 rows (his) list Battle07.
    build_ysforms_data.py <base .utoc> <moves .utoc> <out dir (new)> [--battle07] [--sets Battle02,Battle00,...]"""
import contextlib, hashlib, io, os, shutil, sys
sys.path[:0] = ['/work/sephatb/tools', '/work/iostore', '/work/cs', '/work/tools',
                '/work/evil1013/tools', '/work/swap1012/tools', '/work/vincentfix',
                '/work/weap1012/tools', '/work/evilboss1016/data', '/work/sephforms/tools']
import build_atb as B
from iostore import Toc
import iostore_write as W
import hdr
import build_evilcloud_data as BED
import align_moves as A

MOUNT = '../../../End/Content/'
CHARASPEC = 'DataObject/Resident/CharaSpec.uasset'
MOVES = 'RebirthSkelCompat/Built/SephirothForms/'
ROWS = ['PC0000_00_Cloud_Standard', 'PC0000_08_Cloud_SoldierNoHelmet', 'PC0000_09_Cloud_CostaClothing', 'PC0000_10_Cloud_CostaClothing2',
        'PC0000_04_Cloud_ZackCostume', 'PC0000_12_Cloud_ZackCostumeDirty', 'PC0000_18_Cloud_ZackCostumeAge21',
        'PC0000_19_Cloud_ZackCostumeDirtyAge21', 'PC0000_23_Cloud_ZackCostumeWet']


def quiet(f, *a):
    with contextlib.redirect_stdout(io.StringIO()):
        return f(*a)


def moves_from(utoc, sets):
    """The built moves of the moves container in `sets`: (chunk, store entry), each laid out like the game's animations."""
    src = Toc(utoc)
    heads = [i for i in range(src.entries) if src.chunk_type(i) == 10]
    assert len(heads) == 1
    _, store = hdr.parse_header(src.read(heads[0]))
    out, left = [], []
    for i in range(src.entries):
        if src.chunk_type(i) == 10:
            continue
        path = src.files.get(i, '')
        assert path.startswith(MOUNT), path
        rel = path[len(MOUNT):]
        if not rel.startswith(MOVES) or rel[len(MOVES):].split('/', 1)[0] not in sets:
            left.append(rel)
            continue
        assert src.chunk_type(i) == 2, (rel, src.chunk_type(i))
        pid = src.chunk_id64(i)
        se = store[pid]
        data = A.realign(src.read(i))
        A.verify(data, rel)
        out.append((dict(id64=pid, type=2, data=data, path=rel),
                    dict(id=pid, size=len(data) | (A.SHIFT << 60), export_count=se['export_count'], export_bundle_count=se['export_bundle_count'],
                         load_order=se['load_order'], imports=list(se['imports']))))
    return out, left


def main(base_utoc, moves_utoc, out, battle07, sets):
    assert not os.path.exists(out), out + ' exists (use a new folder)'
    name = os.path.basename(base_utoc)[:-len('.utoc')]
    base_ucas = base_utoc[:-len('.utoc')] + '.ucas'
    old = Toc(base_utoc)
    assert [i for i in range(old.entries) if old.chunk_type(i) == 10] == [0]
    cid, store = hdr.parse_header(old.read(0))
    assert cid == W.container_id_from_name(name), 'the container is not called ' + name
    order = [old.chunk_id64(i) for i in range(old.entries) if old.chunk_type(i) == 2]
    entries = [dict(id=p, size=store[p]['size'], export_count=store[p]['export_count'], export_bundle_count=store[p]['export_bundle_count'],
                    load_order=store[p]['load_order'], imports=list(store[p]['imports'])) for p in order]
    assert W.container_header(cid, entries) == old.read(0), 'the header does not write back as it is'
    entry_of = {e['id']: e for e in entries}
    by_path = {old.files[i][len(MOUNT):]: i for i in old.files}
    changes, additions, report = {}, [], []

    # ---- the moves: replaced or added
    moves, left = moves_from(moves_utoc, sets)
    replaced, added = [], []
    for chunk, entry in moves:
        i = by_path.get(chunk['path'])
        if i is not None:
            assert old.chunk_id64(i) == chunk['id64'] and old.chunk_type(i) == 2, chunk['path']
            changes[i] = chunk['data']
            e = entry_of[chunk['id64']]
            for key in ('size', 'export_count', 'export_bundle_count', 'load_order', 'imports'):
                e[key] = entry[key]
            replaced.append(chunk['path'])
        else:
            assert chunk['id64'] not in entry_of, ('the package id is taken', chunk['path'])
            additions.append(chunk)
            entries.append(entry)
            added.append(chunk['path'])

    def sets_of(paths):
        c = {}
        for p in paths:
            s = p[len(MOVES):].split('/', 1)[0]
            c[s] = c.get(s, 0) + 1
        return ', '.join('%s %d' % kv for kv in sorted(c.items())) or 'none'
    report.append('Moves: %d made again in place (%s), %d added (%s); not taken from the moves container: %s' % (
        len(replaced), sets_of(replaced), len(added), sets_of(added), sets_of([p for p in left if p.startswith(MOVES)]) if left else 'nothing'))

    # ---- CharaSpec: his rows list Battle07
    if battle07:
        cs = quiet(B.Table, old.read(by_path[CHARASPEC]))
        cs0 = {k: list(cs.row(k)) for k in cs.at}
        report.append('CharaSpec:')
        for row_name in ROWS:
            row = cs.row(row_name)
            have = cs.get(row, 'AnimationSetList_Array')
            used = {cs.get(row, f) for f in ('GroundAnimationBattlePackIndex', 'GroundAnimationFieldPackIndex', 'FlyAnimationBattlePackIndex',
                                             'FlyAnimationFieldPackIndex')}
            if 'Battle07' not in have:
                free = [i for i, v in enumerate(have) if v is None and i not in used]
                if free:
                    have[free[0]] = 'Battle07'
                else:
                    have.append('Battle07')
            cs.set(row, 'AnimationSetList_Array', have)
            report.append('  %s: %s' % (row_name, have))
        data = quiet(cs.encode)
        i = by_path[CHARASPEC]
        e = entry_of[old.chunk_id64(i)]
        assert e['size'] >> 60 == 0
        e['size'] = len(data)
        changes[i] = data
        cs2 = quiet(B.Table, data)
        for k, r in cs0.items():
            if k not in ROWS:
                assert cs2.row(k) == r, k
            else:
                assert 'Battle07' in cs2.get(cs2.row(k), 'AnimationSetList_Array'), k
        assert set(cs2.at) == set(cs0)
    changes[0] = W.container_header(cid, entries)

    # ---- the container: the old blocks, then the new
    os.makedirs(out)
    path = os.path.join(out, name)
    BED.append_container(old, base_ucas, changes, additions, path + '.utoc', path + '.ucas.tail')
    with open(path + '.ucas', 'wb') as f:
        with open(base_ucas, 'rb') as g:
            shutil.copyfileobj(g, f, 1 << 24)
        f.write(open(path + '.ucas.tail', 'rb').read())
    shutil.copy(base_utoc[:-len('.utoc')] + '.pak', path + '.pak')
    new = Toc(path + '.utoc')
    assert new.container_id == cid and new.entries == old.entries + len(additions)
    same = 0
    for k in range(new.entries):
        d = new.read(k)
        assert hashlib.sha1(d).digest() == new.b[new.metas_off + 33 * k:new.metas_off + 33 * k + 20], k
        if k < old.entries:
            assert new.files.get(k) == old.files.get(k) and new.chunk_id64(k) == old.chunk_id64(k)
            if k in changes:
                assert d == changes[k]
                if k and old.files.get(k, '').startswith(MOUNT + MOVES):
                    A.verify(d, old.files[k][len(MOUNT):])
            else:
                assert d == old.read(k)
                same += 1
        else:
            c = additions[k - old.entries]
            assert d == c['data'] and new.chunk_id64(k) == c['id64'] and new.files.get(k) == MOUNT + c['path']
            A.verify(d, c['path'])
    cid2, ents = hdr.parse_header(new.read(0))
    assert cid2 == cid and len(ents) == len(entries)
    for e in entries:
        b = ents[e['id']]
        for key in ('size', 'export_count', 'export_bundle_count', 'load_order', 'imports'):
            assert b[key] == e[key], key
    report.append('%s: %d chunks (%d before; %d byte for byte the old ones; %d changed: the moves made again%s and the header; %d added); .ucas +%d bytes' % (
        name, new.entries, old.entries, same, len(changes), ', the CharaSpec table' if battle07 else '', len(additions),
        os.path.getsize(path + '.ucas.tail')))
    open(os.path.join(out, 'report.txt'), 'w').write('\n'.join(report) + '\n')
    print('\n'.join(report))
    for f in sorted(os.listdir(out)):
        p = os.path.join(out, f)
        if f.endswith('.tail'):
            continue
        print('  %-48s %10d %s' % (f, os.path.getsize(p), hashlib.md5(open(p, 'rb').read()).hexdigest()))


if __name__ == '__main__':
    args = sys.argv[1:]
    battle07 = '--battle07' in args
    sets = ['Battle00', 'Battle02', 'Battle07']
    if '--sets' in args:
        sets = args[args.index('--sets') + 1].split(',')
    plain = [a for a in args if not a.startswith('--') and (args.index(a) == 0 or args[args.index(a) - 1] != '--sets')]
    main(plain[0], plain[1], plain[2], battle07, sets)
