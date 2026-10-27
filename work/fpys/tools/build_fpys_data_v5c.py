"""FullyPlayableYoungSephirothDataAssets_P v5c: v5b (the Masamune's blueprints of SephirothSwordFX_P, its Masamune
wearing the Nameless: the weapon of Cloud's packs, as FPS names it) with the forms' Masamune: SephirothSwordFX_P's
WE1021_10_SephirothIllusion_MasamuneCutScale blueprint wears the Masamune's own model WE1021_00 in place of its 10%
longer cutscene one (WE1021_10; only its mesh import and that graph entry change), so the forms that fight with it
(Young Sephiroth's winged, flying and KH2 forms: Create a Character System's "weapon") show the real Masamune with the
sword trail. (WE1021_01, the bloodied Masamune of the cutscenes, and WE1021_02, which takes the Masamune blueprint's
model, now the Nameless, stay as they are.)
    build_fpys_data_v5c.py <out dir (new)> <FPS base .utoc> <SephirothSwordFX_P.utoc>"""
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

SEPH_BP = '/Game/BluePrint/Character/Player/PC0010_00_Sephiroth_Standard'
SEPH_SRC = '/work/seph1012/Game__BluePrint__Character__Player__PC0010_00_Sephiroth_Standard.uasset'
OLD_MESH = ('/Game/Character/Player/PC0010_00_Sephiroth_Standard/Model/PC0010_00', 'PC0010_00')
NEW_MESH = ('/Game/Character/Player/PC0010_13_Young_Sephiroth/Model/PC0010_13', 'PC0010_13')
DROP = ['/Game/Character/Player/PC0010_00_Sephiroth_Standard/Model/PC0010_00']
MASAMUNE_BP = '/Game/BluePrint/Character/Weapon/WE1021_00_SephirothIllusion_Masamune'
MASAMUNE_MESH = ('/Game/Character/Weapon/WE1021_00_SephirothIllusion_Masamune/Model/WE1021_00', 'WE1021_00')
NAMELESS_MESH = ('/Game/Character/Weapon/WE1021_49_Nameless/Model/WE1021_49', 'WE1021_49')
CUTSCALE_BP = '/Game/BluePrint/Character/Weapon/WE1021_10_SephirothIllusion_MasamuneCutScale'
CUTSCALE_MESH = ('/Game/Character/Weapon/WE1021_10_SephirothIllusion_MasamuneCutScale/Model/WE1021_10', 'WE1021_10')


def bundle_count(z):
    """The export bundles a package's data has (its bundle headers, until every export's two entries are covered)."""
    total, seen, p, n = 2 * len(z.exports), 0, z.eb_off, 0
    while seen < total:
        first, count = struct.unpack_from('<II', z.d, p)
        p += 8
        seen += count
        n += 1
    return n


def in_place(src, old_mesh, new_mesh, pkg):
    """The retail blueprint with only its mesh import and that graph entry changed."""
    z = Zen(src)
    old, new = MB.imp(old_mesh[0] + '.' + old_mesh[1]), MB.imp(new_mesh[0] + '.' + new_mesh[1])
    hits = [i for i, v in enumerate(z.imports) if v == old]
    assert len(hits) == 1, hits
    d = bytearray(src)
    struct.pack_into('<Q', d, z.imp_off + 8 * hits[0], new)
    old_pid, new_pid = W.package_id(old_mesh[0]), W.package_id(new_mesh[0])
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
    assert c.mapped(c.name_mapped) == pkg and [e['name'] for e in c.exports] == [e['name'] for e in z.exports]
    assert out[c.header_end:] == src[z.header_end:] and len(out) == len(src)
    assert new in c.imports and old not in c.imports
    return out, old_pid, new_pid


def main(out, base_utoc, fx_utoc):
    assert not os.path.exists(out), out + ' exists (use a new folder)'
    base_ucas = base_utoc[:-len('.utoc')] + '.ucas'
    old = Toc(base_utoc)
    assert [i for i in range(old.entries) if old.chunk_type(i) == 10] == [0]
    for i in range(old.entries):
        assert hashlib.sha1(old.read(i)).digest() == old.b[old.metas_off + 33 * i:old.metas_off + 33 * i + 20], i
    old_cid, store = hdr.parse_header(old.read(0))
    assert old_cid == W.container_id_from_name(B.OLD_NAME)
    order = [old.chunk_id64(i) for i in range(old.entries) if old.chunk_type(i) == 2]
    entries = [dict(id=p, size=store[p]['size'], export_count=store[p]['export_count'], export_bundle_count=store[p]['export_bundle_count'],
                    load_order=store[p]['load_order'], imports=list(store[p]['imports'])) for p in order]
    assert W.container_header(old_cid, entries) == old.read(0), 'the header does not write back as it is'
    entry_of = {e['id']: e for e in entries}
    by_path = {old.files[i][len(B.MOUNT):]: i for i in old.files}
    _, retail = hdr.parse_header(open(B.RETAIL_HEADER, 'rb').read())
    changes, additions, report = {}, [], []
    # Sephiroth's own blueprint, in place, wearing his model
    src = open(SEPH_SRC, 'rb').read()
    bp_pid = W.package_id(SEPH_BP)
    assert bp_pid not in store, 'FPS already carries the blueprint'
    re = retail[bp_pid]
    assert re['size'] == len(src)
    data, old_pid, new_pid = in_place(src, OLD_MESH, NEW_MESH, SEPH_BP)
    assert old_pid in re['imports']
    assert len(Zen(data).exports) == re['export_count']
    additions.append(dict(id64=bp_pid, type=2, data=data, path=SEPH_BP[len('/Game/'):] + '.uasset'))
    entries.append(dict(id=bp_pid, size=len(data), export_count=re['export_count'], export_bundle_count=re['export_bundle_count'],
                        load_order=re['load_order'], imports=[new_pid if x == old_pid else x for x in re['imports']]))
    report.append('%s: the game\'s blueprint wearing %s (in place: its mesh import and graph entry; %d bytes)' % (SEPH_BP, NEW_MESH[0], len(data)))
    # SephirothSwordFX_P's four Masamune blueprints; its Masamune, in place, wearing the Nameless
    fx = Toc(fx_utoc)
    fx_heads = [i for i in range(fx.entries) if fx.chunk_type(i) == 10]
    assert len(fx_heads) == 1
    _, fx_store = hdr.parse_header(fx.read(fx_heads[0]))
    m_pid = W.package_id(MASAMUNE_BP)
    fx_pkgs = [i for i in range(fx.entries) if fx.chunk_type(i) == 2]
    assert len(fx_pkgs) == len(fx_store) == 4 and m_pid in fx_store
    for i in fx_pkgs:
        pid = fx.chunk_id64(i)
        path = fx.files[i]
        assert path.startswith(B.MOUNT + 'BluePrint/Character/Weapon/WE1021_') and pid not in store, path
        data = fx.read(i)
        fe = fx_store[pid]
        imports = list(fe['imports'])
        if pid == m_pid:
            data, m_old, m_new = in_place(data, MASAMUNE_MESH, NAMELESS_MESH, MASAMUNE_BP)
            assert imports == [m_old], imports
            imports = [m_new]
            report.append('%s: SephirothSwordFX_P\'s blueprint wearing %s (in place: its mesh import and graph entry; %d bytes)' % (
                MASAMUNE_BP, NAMELESS_MESH[0], len(data)))
        elif pid == W.package_id(CUTSCALE_BP):
            data, c_old, c_new = in_place(data, CUTSCALE_MESH, MASAMUNE_MESH, CUTSCALE_BP)
            assert c_old in imports, imports
            imports = [c_new if x == c_old else x for x in imports]
            report.append('%s: SephirothSwordFX_P\'s blueprint wearing %s, the forms\' Masamune (in place; %d bytes)' % (
                CUTSCALE_BP, MASAMUNE_MESH[0], len(data)))
        else:
            report.append('%s: SephirothSwordFX_P\'s, as it is (%d bytes)' % (path[len(B.MOUNT):-len('.uasset')], len(data)))
        z = Zen(data)
        assert len(z.exports) == fe['export_count'] and bundle_count(z) == fe['export_bundle_count'], path
        additions.append(dict(id64=pid, type=2, data=data, path=path[len(B.MOUNT):]))
        entries.append(dict(id=pid, size=fe['size'], export_count=fe['export_count'], export_bundle_count=fe['export_bundle_count'],
                            load_order=fe['load_order'], imports=imports))
    for row in B.WEAPON_PACKS:
        e = entry_of[old.chunk_id64(by_path[B.PACK % row])]
        assert m_pid in e['imports'], (row, 'its header entry does not list the Masamune blueprint')
    report.append('  Cloud\'s %d weapon packs name the Masamune\'s, as in FPS (unchanged)' % len(B.WEAPON_PACKS))
    # Sephiroth's model out
    drop_ids = {W.package_id(p) for p in DROP}
    assert drop_ids <= set(entry_of), 'FPS has no PC0010_00'
    importers = [e for e in entries if e['id'] not in drop_ids and drop_ids & set(e['imports'])]
    entries = [e for e in entries if e['id'] not in drop_ids]
    report.append('%s left out (%d package(s) here import it: the game\'s or KH2Sephiroth_P\'s then)' % (', '.join(DROP), len(importers)))
    # every package the changed or added ones import: here or in the game
    here = {e['id'] for e in entries}
    unknown = []
    for i in changes:
        unknown += ['%016x' % x for x in entry_of[old.chunk_id64(i)]['imports'] if x not in here and x not in B.PKG]
    for a in additions:
        e = [x for x in entries if x['id'] == a['id64']][0]
        unknown += ['%016x' % x for x in e['imports'] if x not in here and x not in B.PKG and x not in (W.package_id(NEW_MESH[0]), W.package_id(NAMELESS_MESH[0]), W.package_id(MASAMUNE_MESH[0]))]
    assert not unknown, unknown
    cid = W.container_id_from_name(B.NAME)
    changes[0] = W.container_header(cid, entries)
    os.makedirs(out)
    path = os.path.join(out, B.NAME)
    # the container: FPS's chunks (PC0010_00's dropped from the table), the changed packs and the additions after the old .ucas
    drop_chunks = {i for i in range(1, old.entries) if old.chunk_id64(i) in drop_ids}
    BED.append_container(old, base_ucas, changes, additions, path + '.utoc', path + '.ucas.tail')
    toc = Toc(path + '.utoc')
    # rewrite the table without the dropped chunks (their blocks stay in the .ucas, unreferenced)
    b = toc.b
    keep = [i for i in range(toc.entries) if i not in drop_chunks]
    metas_all = b[toc.metas_off:]
    files = {}
    for k, i in enumerate(keep):
        if i in toc.files:
            files[k] = toc.files[i]
    dindex = W.directory_index(B.MOUNT, [(files[k][len(B.MOUNT):], k) for k in sorted(files)])
    head = bytearray(b[:toc.hdrsize])
    struct.pack_into('<I', head, 24, len(keep))
    struct.pack_into('<I', head, 48, len(dindex))
    struct.pack_into('<Q', head, 56, cid)
    out_toc = bytearray(head)
    for i in keep:
        cidb = bytes(toc.chunk_ids[i])
        if i == 0:
            cidb = struct.pack('<QHBB', cid, 0, 0, 10)
        out_toc += cidb
    for i in keep:
        off, ln = toc.offlen[i]
        out_toc += off.to_bytes(5, 'big') + ln.to_bytes(5, 'big')
    for pos, cs, us, m in toc.blocks:
        out_toc += pos.to_bytes(5, 'little') + cs.to_bytes(3, 'little') + us.to_bytes(3, 'little') + bytes([m])
    out_toc += dindex
    for i in keep:
        out_toc += metas_all[33 * i:33 * i + 33]
    open(path + '.utoc', 'wb').write(bytes(out_toc))
    with open(path + '.ucas', 'wb') as f:
        with open(base_ucas, 'rb') as g:
            shutil.copyfileobj(g, f, 1 << 24)
        f.write(open(path + '.ucas.tail', 'rb').read())
    shutil.copy(base_utoc[:-len('.utoc')] + '.pak', path + '.pak')
    # read back
    new = Toc(path + '.utoc')
    assert new.container_id == cid and new.entries == old.entries - len(drop_chunks) + len(additions)
    assert new.chunk_id64(0) == cid and new.chunk_type(0) == 10
    old_keep = [i for i in range(old.entries) if i not in drop_chunks]
    for k in range(new.entries):
        d = new.read(k)
        if k < len(old_keep):
            i = old_keep[k]
            assert new.files.get(k) == old.files.get(i), (k, i)
            assert d == (changes[i] if i in changes else old.read(i)), (k, i)
            if i:
                assert new.chunk_ids[k] == old.chunk_ids[i], k
        else:
            c = additions[k - len(old_keep)]
            assert d == c['data'] and new.chunk_id64(k) == c['id64'] and new.chunk_type(k) == c['type'] and new.files.get(k) == B.MOUNT + c['path']
        assert hashlib.sha1(d).digest() == new.b[new.metas_off + 33 * k:new.metas_off + 33 * k + 20], k
    cid2, store2 = hdr.parse_header(new.read(0))
    assert cid2 == cid and set(store2) == {e['id'] for e in entries}
    for e in entries:
        for key in ('size', 'export_count', 'export_bundle_count', 'load_order', 'imports'):
            assert store2[e['id']][key] == e[key], key
    report.append('%s: %d chunks (%d before; %d packs and the header changed, %d added, %d dropped); read back as written; the .ucas is the '
                  'old one plus %d bytes' % (B.NAME, new.entries, old.entries, len(changes) - 1, len(additions), len(drop_chunks), os.path.getsize(path + '.ucas.tail')))
    open(os.path.join(out, 'changes.txt'), 'w').write('\n'.join(report) + '\n')
    print('\n'.join(report))
    for f in sorted(os.listdir(out)):
        p = os.path.join(out, f)
        print('  %-48s %10d %s' % (f, os.path.getsize(p), hashlib.md5(open(p, 'rb').read()).hexdigest()))


if __name__ == '__main__':
    main(*sys.argv[1:4])
