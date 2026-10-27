"""FullyPlayableYoungSephirothDataAssets_P v8: v7 with the Classic Sephiroth voice bank in his packs. Cloud's 9 character
packs (the rows he spawns from) list VO_PC0010_15_ClassicSephiroth (ClassicSephirothVoice_P: the JP package, the one
everything imports; the game loads the voice language's in its place) right after the young voice bank in their asset
list, so the game loads it with him and the Customization screen's VOICES page can give it to anyone (the mod never
loads a voice bank itself: 3.6.3). Each pack: one import added, the list's array one longer (its three size fields), the
graph and the header entry name the bank's package. Everything else of v7 is byte for byte; the container keeps its name
and id.
    build_fpys_data_v8.py <out dir (new)> <v7 .utoc>"""
import hashlib, os, shutil, struct, sys
sys.path[:0] = ['/work/fpys/tools', '/work/evilboss1016/data', '/work/iostore', '/work/cs',
                '/work/weap1012/tools', '/work/evil1013/tools', '/work/swap1012/tools', '/work/vincentfix']
from iostore import Toc
import iostore_write as W
import hdr
import build_evilcloud_data as BED
import build_fpys_data as B
import build_fpys_data_v6 as V6

AFTER = '/Game/Sound/Voice/JP/Character/Player/VO_PC0010_13_YoungSephiroth'
CLASSIC = '/Game/Sound/Voice/JP/Character/Player/VO_PC0010_15_ClassicSephiroth'


def main(out, base_utoc):
    assert not os.path.exists(out), out + ' exists (use a new folder)'
    base_ucas = base_utoc[:-len('.utoc')] + '.ucas'
    old = Toc(base_utoc)
    assert [i for i in range(old.entries) if old.chunk_type(i) == 10] == [0]
    cid, store = hdr.parse_header(old.read(0))
    assert cid == W.container_id_from_name(B.NAME)
    order = [old.chunk_id64(i) for i in range(old.entries) if old.chunk_type(i) == 2]
    entries = [dict(id=p, size=store[p]['size'], export_count=store[p]['export_count'], export_bundle_count=store[p]['export_bundle_count'],
                    load_order=store[p]['load_order'], imports=list(store[p]['imports'])) for p in order]
    assert W.container_header(cid, entries) == old.read(0), 'the header does not write back as it is'
    entry_of = {e['id']: e for e in entries}
    by_path = {old.files[i][len(B.MOUNT):]: i for i in old.files}
    old_obj = AFTER + '.' + V6.leaf(AFTER)
    new_obj = CLASSIC + '.' + V6.leaf(CLASSIC)
    changes, report = {}, []
    for row in B.CHAR_PACKS:
        i = by_path[B.PACK % row]
        data = old.read(i)
        new, new_pid, (n0, n1) = V6.add_voice(data, old_obj, new_obj)
        listed = V6.check_pack(new, old_obj, new_obj)
        e = entry_of[old.chunk_id64(i)]
        assert e['size'] in (0, len(data)) and e['export_count'] == 1, (row, e['size'], len(data))
        if e['size']:
            e['size'] = len(new)
        assert new_pid not in e['imports']
        e['imports'] = e['imports'] + [new_pid]
        changes[i] = new
        report.append('CharaSpec_%s: lists %s (its entry %d -> %d objects; %d -> %d bytes; %d objects in its lists)' % (
            row, V6.leaf(CLASSIC), n0, n1, len(data), len(new), listed))
    changes[0] = W.container_header(cid, entries)
    os.makedirs(out)
    path = os.path.join(out, B.NAME)
    BED.append_container(old, base_ucas, changes, [], path + '.utoc', path + '.ucas.tail')
    with open(path + '.ucas', 'wb') as f:
        with open(base_ucas, 'rb') as g:
            shutil.copyfileobj(g, f, 1 << 24)
        f.write(open(path + '.ucas.tail', 'rb').read())
    shutil.copy(base_utoc[:-len('.utoc')] + '.pak', path + '.pak')
    new = Toc(path + '.utoc')
    assert new.container_id == cid and new.entries == old.entries
    same = 0
    for k in range(new.entries):
        d = new.read(k)
        assert hashlib.sha1(d).digest() == new.b[new.metas_off + 33 * k:new.metas_off + 33 * k + 20]
        if k in changes:
            assert d == changes[k]
        else:
            assert d == old.read(k) and new.files.get(k) == old.files.get(k)
            same += 1
    cid2, ents = hdr.parse_header(new.read(0))
    for e in entries:
        b = ents[e['id']]
        for key in ('size', 'export_count', 'export_bundle_count', 'load_order', 'imports'):
            assert b[key] == e[key], key
    report.append('%d chunks byte for byte v7\'s; the header and %d packs changed' % (same, len(changes) - 1))
    for line in report:
        print(line)
    for f in sorted(os.listdir(out)):
        p = os.path.join(out, f)
        print('  %-48s %10d %s' % (f, os.path.getsize(p), hashlib.md5(open(p, 'rb').read()).hexdigest()))


if __name__ == '__main__':
    main(*sys.argv[1:3])
