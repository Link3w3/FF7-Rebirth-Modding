"""Everything of the Fully Playable Sephiroth in one container, FullyPlayableSephirothDataAssets_P: the data container
(abilities, damage sources, CharaSpec ...) with the packages of the mod's other containers added as they are (every
chunk byte for byte, with its header entry: the moves keep their alignment shift):
  SephirothForms_P (every form's built moves), SaferSephiroth_P (Safer's model, Bonamik, materials, textures, his
  AnimBlueprint), BizarroSummon_P (the Bizarro summon's moves), SephirothTransformedBaseModel_P (his model with the
  wings' parts).
A package in two of them is an error (none is expected). Checks: every chunk reads back as it was, every header entry
is the one of its container, every move's ACL data is still 16-aligned.
    merge_fullyplayable.py <out dir (new)> <data.utoc> <other.utoc> ..."""
import os, shutil, sys
sys.path[:0] = ['/work/iostore', '/work/cs', '/work/swap1012/tools', '/work/sephforms/tools',
                '/work/vincentfix', '/work/weap1012/tools', '/work/evil1013/tools']
from iostore import Toc
import iostore_write as W
import hdr
import align_moves as A

NAME = 'FullyPlayableSephirothDataAssets_P'
MOUNT = '../../../End/Content/'


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
    return chunks, store


def main(out, data_utoc, others):
    assert not os.path.exists(out), out + ' exists (use a new folder)'
    os.makedirs(out)
    sources = [data_utoc] + others
    chunks, entries, seen, counts = [None], [], {}, []
    for utoc in sources:
        part, store = read(utoc)
        label = os.path.basename(utoc)[:-len('.utoc')]
        pk = bulk = 0
        for c in part:
            key = (c['id64'], c['type'])
            assert key not in seen, ('%s is in %s and %s' % (c['path'] or '%016x' % c['id64'], seen[key], label))
            seen[key] = label
            chunks.append(c)
            if c['type'] == 2:
                se = store[c['id64']]
                entries.append(dict(id=c['id64'], size=se['size'], export_count=se['export_count'], export_bundle_count=se['export_bundle_count'],
                                    load_order=se['load_order'], imports=list(se['imports'])))
                pk += 1
            else:
                bulk += 1
        assert pk == len(store), ('%s: %d packages, %d header entries' % (label, pk, len(store)))
        counts.append('%s %d packages%s' % (label, pk, (' + %d bulk' % bulk) if bulk else ''))
    cid = W.container_id_from_name(NAME)
    chunks[0] = dict(id64=cid, type=10, data=W.container_header(cid, entries), path=None)
    base = os.path.join(out, NAME)
    W.write_container(base, NAME, chunks, mount=MOUNT)
    shutil.copy(data_utoc[:-len('.utoc')] + '.pak', base + '.pak')
    # read back
    back = Toc(base + '.utoc')
    assert back.entries == len(chunks)
    cid2, ents = hdr.parse_header(back.read(0))
    assert cid2 == cid and len(ents) == len(entries)
    by = {e['id']: e for e in entries}
    aligned = 0
    for i in range(1, back.entries):
        c = chunks[i]
        data = back.read(i)
        assert data == c['data'] and back.chunk_id64(i) == c['id64'] and back.chunk_type(i) == c['type'], c['path']
        if c['path']:
            assert back.files.get(i) == MOUNT + c['path'], (back.files.get(i), c['path'])
        if c['type'] == 2:
            e, b = by[c['id64']], ents[c['id64']]
            assert (b['size'], b['export_count'], b['export_bundle_count'], b['load_order'], list(b['imports'])) == \
                   (e['size'], e['export_count'], e['export_bundle_count'], e['load_order'], e['imports']), c['path']
            if c['path'] and c['path'].startswith('RebirthSkelCompat/Built/'):
                aligned += A.verify(data, c['path'])
    total = sum(len(c['data']) for c in chunks[1:])
    print('%s: %d chunks (%s); %.1f MB; read back as written; %d ACL blocks of the moves 16-aligned'
          % (NAME, len(chunks) - 1, '; '.join(counts), total / 1048576.0, aligned))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
