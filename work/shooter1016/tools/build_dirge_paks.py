"""The shooter's paks, from the End project's packaging (Saved/StagedBuilds/WindowsNoEditor/End/Content/Paks), every
animation package laid out the way the game reads its own (align_moves: PKG_Cooked, 16-byte exports at aligned cooked
offsets, alignment shift 4 in the container header; the editor's packaging leaves them so that the game reads past an
export), each in a container of its own name (its id from that name, so no other mod's renamed pakchunk clashes):
  FullyPlayableVincentAssets_P: the installed one, with the Dirge of Cerberus melee moves of pakchunk46 in place of its
      moves of those names and the two new ones added; everything else in it (the CharaSpec table, the packs) as it was,
      its moves laid out like the game's too,
  VincentDirgeMotions_P: pakchunk53 (Vincent's Dirge of Cerberus motions, /Game/RebirthSkelCompat/Dirge/Vincent),
  VincentChaos_P: pakchunk54 (Chaos's model and his motions, /Game/RebirthSkelCompat/Dirge/Chaos).
Every chunk is read back and checked (data, id, path, header entry, the game's reading of every animation export).

    build_dirge_paks.py <out dir (new)> <src dir>
"""
import hashlib, os, shutil, sys
sys.path[:0] = ['/work/iostore', '/work/cs', '/work/swap1012/tools', '/work/sephforms/tools']
from iostore import Toc
from zen import Zen
import iostore_write as W
import hdr
import align_moves as A

MOUNT = '../../../End/Content/'
MELEE = 'RebirthSkelCompat/Built/Vincent/'


def verify(d, label):
    """align_moves.verify, with the package's own export read as the animation (align_moves knows the game's animations by
    their names, B_ N_ F_: the Dirge motions are named p000_ / p007_)."""
    z = Zen(d)
    main = label.rsplit('/', 1)[-1].split('.')[0]
    for ex in z.exports:
        if ex['name'] == main and not ex['name'].startswith(('B_', 'N_', 'F_')):
            ex['name'] = 'B_' + ex['name']
    assert z.flags & A.PKG_COOKED and z.flags & A.PKG_ALIGNED_EXPORTS, label
    assert z.header_end % A.ALIGN == 0, label
    spans = A.export_spans(d, z)
    pos = z.header_end
    blocks = 0
    for idx, s, e in spans:
        assert pos == s, (label, 'export %d starts at %d, the game reads it from %d' % (idx, s, pos))
        ex = z.exports[idx]
        assert ex['serial_offset'] % A.ALIGN == 0 and ex['serial_size'] % A.ALIGN == 0, (label, idx)
        used, block = A.game_consumes(z, d, idx, s, e)
        cooked = ex['serial_offset'] + used
        pos = s + (A.align_up(cooked) - ex['serial_offset'])
        if block is not None:
            assert block % A.ALIGN == 0, (label, 'ACL block not 16-aligned in memory', block)
            blocks += 1
    assert pos == len(d), (label, pos, len(d))
    assert blocks >= 1, (label, 'no ACL block read')
    return blocks


def read(utoc):
    t = Toc(utoc)
    heads = [i for i in range(t.entries) if t.chunk_type(i) == 10]
    assert len(heads) == 1, utoc
    _, store = hdr.parse_header(t.read(heads[0]))
    chunks = []
    for i in range(t.entries):
        kind = t.chunk_type(i)
        if kind == 10:
            continue
        raw = t.chunk_ids[i]
        assert raw[8:11] == b'\0\0\0', ('a chunk index this writer does not keep', utoc, t.files.get(i), raw.hex())
        path = t.files.get(i)
        assert path is None or path.startswith(MOUNT), path
        chunks.append(dict(id64=t.chunk_id64(i), type=kind, data=t.read(i), path=path[len(MOUNT):] if path else None))
    packages = sum(1 for c in chunks if c['type'] == 2)
    assert packages == len(store), (utoc, packages, len(store))
    return chunks, store


def entry(c, se):
    return dict(id=c['id64'], size=se['size'], export_count=se['export_count'], export_bundle_count=se['export_bundle_count'],
                load_order=se['load_order'], imports=list(se['imports']))


def lay_out(chunks, entries):
    """Every animation package laid out like the game's; returns how many, and their ACL blocks."""
    by = {e['id']: e for e in entries}
    anims = blocks = 0
    for c in chunks:
        if c['type'] != 2:
            continue
        if not (c['path'] or '').startswith('RebirthSkelCompat/'):
            continue   # (the moves and motions; a table of the game's keeps its own layout)
        z = Zen(c['data'])
        assert z.flags & A.PKG_ALIGNED_EXPORTS, ('not an animation package', c['path'])
        e = by[c['id64']]
        if z.flags & A.PKG_COOKED and e['size'] >> 60 == A.SHIFT:
            blocks += verify(c['data'], c['path'])   # (already laid out)
        else:
            assert e['size'] >> 60 == 0, c['path']
            c['data'] = A.realign(c['data'])
            blocks += verify(c['data'], c['path'])
            e['size'] = len(c['data']) | (A.SHIFT << 60)
        anims += 1
    return anims, blocks


def write(out, name, chunks, entries, pak_stub):
    cid = W.container_id_from_name(name)
    allc = [dict(id64=cid, type=10, data=W.container_header(cid, entries), path=None)] + chunks
    base = os.path.join(out, name)
    W.write_container(base, name, allc, mount=MOUNT)
    shutil.copy(pak_stub, base + '.pak')
    # read back
    back = Toc(base + '.utoc')
    assert back.entries == len(allc), name
    cid2, ents = hdr.parse_header(back.read(0))
    assert cid2 == cid and len(ents) == len(entries), name
    by = {e['id']: e for e in entries}
    for i in range(1, back.entries):
        c = allc[i]
        data = back.read(i)
        assert data == c['data'] and back.chunk_id64(i) == c['id64'] and back.chunk_type(i) == c['type'], (name, c['path'])
        assert back.files.get(i) == (MOUNT + c['path'] if c['path'] else None), (name, back.files.get(i), c['path'])
        if c['type'] == 2:
            e, b = by[c['id64']], ents[c['id64']]
            assert (b['size'], b['export_count'], b['export_bundle_count'], b['load_order'], list(b['imports'])) == \
                   (e['size'], e['export_count'], e['export_bundle_count'], e['load_order'], e['imports']), (name, c['path'])
            if (c['path'] or '').startswith('RebirthSkelCompat/'):
                assert b['size'] >> 60 == A.SHIFT and verify(data, c['path']) >= 1, (name, c['path'])
    files = {}
    for ext in ('utoc', 'ucas', 'pak'):
        p = base + '.' + ext
        files[ext] = (os.path.getsize(p), hashlib.md5(open(p, 'rb').read()).hexdigest())
    return cid, files


def main(out, src):
    assert not os.path.exists(out), out + ' exists (use a new folder)'
    os.makedirs(out)
    report = []
    # 1. FullyPlayableVincentAssets_P: the installed one with the new melee moves
    old, old_store = read(os.path.join(src, 'FullyPlayableVincentAssets_P.utoc'))
    new, new_store = read(os.path.join(src, 'pakchunk46-WindowsNoEditor.utoc'))
    moves = {(c['id64'], c['type']): c for c in new if c['path'] and c['path'].startswith(MELEE)}
    assert all(c['type'] == 2 for c in moves.values()) and not any(c['type'] != 2 and c['path'] is None for c in new), 'pakchunk46 has bulk data'
    chunks, entries, replaced, kept = [], [], [], []
    taken = set()
    for c in old:
        key = (c['id64'], c['type'])
        if key in moves:
            m = moves[key]
            chunks.append(dict(m))
            entries.append(entry(m, new_store[m['id64']]))
            replaced.append(m['path'][len(MELEE):])
            taken.add(key)
        else:
            chunks.append(dict(c))
            if c['type'] == 2:
                entries.append(entry(c, old_store[c['id64']]))
            kept.append(c['path'])
    added = []
    for key, m in sorted(moves.items(), key=lambda kv: kv[1]['path']):
        if key in taken:
            continue
        chunks.append(dict(m))
        entries.append(entry(m, new_store[m['id64']]))
        added.append(m['path'][len(MELEE):])
    left = sorted(c['path'] for c in new if c['path'] and not c['path'].startswith(MELEE))
    anims, blocks = lay_out(chunks, entries)
    cid, files = write(out, 'FullyPlayableVincentAssets_P', chunks, entries, os.path.join(src, 'FullyPlayableVincentAssets_P.pak'))
    report.append('FullyPlayableVincentAssets_P (%016x): %d packages; the melee moves %s replaced, %s added; kept as they were: %s; '
                  'NOT taken from pakchunk46: %s; %d animations laid out like the game\'s (%d ACL blocks aligned); %s'
                  % (cid, len(entries), ', '.join(replaced), ', '.join(added), ', '.join(k for k in kept if not k.startswith(MELEE)), ', '.join(left),
                     anims, blocks, files))
    # 2. and 3.: the motions
    for chunk, name in ((53, 'VincentDirgeMotions_P'), (54, 'VincentChaos_P')):
        utoc = os.path.join(src, 'pakchunk%d-WindowsNoEditor.utoc' % chunk)
        chunks, store = read(utoc)
        entries = [entry(c, store[c['id64']]) for c in chunks if c['type'] == 2]
        anims, blocks = lay_out(chunks, entries)
        cid, files = write(out, name, chunks, entries, utoc[:-len('.utoc')] + '.pak')
        folders = {}
        for c in chunks:
            if c['path']:
                f = c['path'].rsplit('/', 1)[0]
                folders[f] = folders.get(f, 0) + 1
        report.append('%s (%016x) from pakchunk%d: %d packages + %d bulk chunks (%s); %d animations laid out like the game\'s (%d ACL blocks aligned); %s'
                      % (name, cid, chunk, len(entries), sum(1 for c in chunks if c['type'] != 2), ', '.join('%s %d' % kv for kv in sorted(folders.items())),
                         anims, blocks, files))
    open(os.path.join(out, 'paks_report.txt'), 'w').write('\n'.join(report) + '\n')
    print('\n'.join(report))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
