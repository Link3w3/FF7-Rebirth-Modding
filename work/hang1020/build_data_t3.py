"""Test data pak t3: the Fully Playable Sephiroth's data pak, every chunk as it is, plus Sephiroth's own player blueprint
(/Game/BluePrint/Character/Player/PC0010_00_Sephiroth_Standard, the retail package) changed in place to wear Young
Sephiroth's model PC0010_13 (only its mesh import and that graph entry; its name and everything else the game's), under
FullyPlayableYoungSephirothDataAssets_P's name. Cloud's packs keep naming Sephiroth's blueprint as in FPS, so no new
blueprint name is involved; the weapon packs keep the Masamune.
    build_data_t3.py <out dir (new)> <FPS base .utoc>"""
import hashlib, os, shutil, struct, sys
sys.path[:0] = ['/work/fpys/tools', '/work/evilboss1016/data', '/work/iostore', '/work/cs',
                '/work/weap1012/tools', '/work/evil1013/tools', '/work/swap1012/tools', '/work/vincentfix']
from zen import Zen
from iostore import Toc
import iostore_write as W
import hdr
import build_evilcloud_data as BED
import build_fpys_data as B
import make_bps as MB

BP = '/Game/BluePrint/Character/Player/PC0010_00_Sephiroth_Standard'
SRC = '/work/seph1012/Game__BluePrint__Character__Player__PC0010_00_Sephiroth_Standard.uasset'
OLD_MESH = ('/Game/Character/Player/PC0010_00_Sephiroth_Standard/Model/PC0010_00', 'PC0010_00')
NEW_MESH = ('/Game/Character/Player/PC0010_13_Young_Sephiroth/Model/PC0010_13', 'PC0010_13')


def in_place(src):
    z = Zen(src)
    old, new = MB.imp(OLD_MESH[0] + '.' + OLD_MESH[1]), MB.imp(NEW_MESH[0] + '.' + NEW_MESH[1])
    hits = [i for i, v in enumerate(z.imports) if v == old]
    assert len(hits) == 1, hits
    d = bytearray(src)
    struct.pack_into('<Q', d, z.imp_off + 8 * hits[0], new)
    old_pid, new_pid = W.package_id(OLD_MESH[0]), W.package_id(NEW_MESH[0])
    g = MB.graph(bytes(d))
    assert sum(1 for pid, _ in g if pid == old_pid) == 1
    g = sorted([(new_pid if pid == old_pid else pid, arcs) for pid, arcs in g], key=lambda x: x[0])
    gb = bytearray(struct.pack('<i', len(g)))
    for pid, arcs in g:
        gb += struct.pack('<Qi', pid, len(arcs) // 2) + struct.pack('<%di' % len(arcs), *arcs)
    assert len(gb) == z.graph_size
    d[z.graph_off:z.graph_off + z.graph_size] = gb
    out = bytes(d)
    c = Zen(out)
    assert c.mapped(c.name_mapped) == BP and [e['name'] for e in c.exports] == [e['name'] for e in z.exports]
    assert out[c.header_end:] == src[z.header_end:] and len(out) == len(src)
    return out, old_pid, new_pid


def main(out, base_utoc):
    assert not os.path.exists(out), out
    base_ucas = base_utoc[:-len('.utoc')] + '.ucas'
    old = Toc(base_utoc)
    old_cid, store = hdr.parse_header(old.read(0))
    order = [old.chunk_id64(i) for i in range(old.entries) if old.chunk_type(i) == 2]
    entries = [dict(id=p, size=store[p]['size'], export_count=store[p]['export_count'], export_bundle_count=store[p]['export_bundle_count'],
                    load_order=store[p]['load_order'], imports=list(store[p]['imports'])) for p in order]
    assert W.container_header(old_cid, entries) == old.read(0)
    _, retail = hdr.parse_header(open(B.RETAIL_HEADER, 'rb').read())
    src = open(SRC, 'rb').read()
    bp_pid = W.package_id(BP)
    assert bp_pid not in store, 'FPS already has the blueprint'
    re = retail[bp_pid]
    assert re['size'] == len(src)
    data, old_pid, new_pid = in_place(src)
    assert old_pid in re['imports']
    z = Zen(data)
    assert len(z.exports) == re['export_count']
    entries.append(dict(id=bp_pid, size=len(data), export_count=re['export_count'], export_bundle_count=re['export_bundle_count'],
                        load_order=re['load_order'], imports=[new_pid if x == old_pid else x for x in re['imports']]))
    additions = [dict(id64=bp_pid, type=2, data=data, path=BP[len('/Game/'):] + '.uasset')]
    cid = W.container_id_from_name(B.NAME)
    changes = {0: W.container_header(cid, entries)}
    os.makedirs(out)
    path = os.path.join(out, B.NAME)
    BED.append_container(old, base_ucas, changes, additions, path + '.utoc', path + '.ucas.tail')
    toc = bytearray(open(path + '.utoc', 'rb').read())
    assert struct.unpack_from('<Q', toc, 56)[0] == old_cid
    struct.pack_into('<Q', toc, 56, cid)
    hs = struct.unpack_from('<I', toc, 20)[0]
    assert toc[hs:hs + 12] == struct.pack('<QHBB', old_cid, 0, 0, 10)
    toc[hs:hs + 12] = struct.pack('<QHBB', cid, 0, 0, 10)
    open(path + '.utoc', 'wb').write(bytes(toc))
    with open(path + '.ucas', 'wb') as f:
        with open(base_ucas, 'rb') as g:
            shutil.copyfileobj(g, f, 1 << 24)
        f.write(open(path + '.ucas.tail', 'rb').read())
    shutil.copy(base_utoc[:-len('.utoc')] + '.pak', path + '.pak')
    new = Toc(path + '.utoc')
    assert new.container_id == cid and new.entries == old.entries + 1
    for i in range(new.entries):
        d = new.read(i)
        if i == 0:
            assert d == changes[0]
        elif i < old.entries:
            assert d == old.read(i), i
        else:
            assert d == data and new.chunk_id64(i) == bp_pid
        assert hashlib.sha1(d).digest() == new.b[new.metas_off + 33 * i:new.metas_off + 33 * i + 20], i
    cid2, st2 = hdr.parse_header(new.read(0))
    assert cid2 == cid and st2[bp_pid]['imports'] == entries[-1]['imports']
    print('%s: FPS\'s data + Sephiroth\'s blueprint wearing PC0010_13 (in place, %d bytes); %d chunks; tail %d bytes' % (
        B.NAME, len(data), new.entries, os.path.getsize(path + '.ucas.tail')))


if __name__ == '__main__':
    main(*sys.argv[1:])
