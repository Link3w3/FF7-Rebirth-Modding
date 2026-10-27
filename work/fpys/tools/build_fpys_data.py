"""FullyPlayableYoungSephirothDataAssets_P: the Fully Playable Sephiroth's data assets (the installed
FullyPlayableSephirothDataAssets_P, every chunk as it is) for Young Sephiroth in Cloud's slot, a container of its own:
  * Cloud's 9 character packs (CharaSpec_PC0000_*: the Cloud rows the playable Sephiroth spawns from) name his own
    blueprint PC0010_13_Young_Sephiroth (make_bps.py: Sephiroth's player blueprint wearing PC0010_13) instead of
    Sephiroth's: its class, default object and every subobject the pack names. Their entries keep Sephiroth's names
    (the rows' ContentsModel stays PC0010_00_Sephiroth_Standard), so nothing else of the table changes;
  * Cloud's 8 weapon packs (CharaSpec_WE0000_00, _11 - _17: the Masamune in FPS) name the Nameless blueprint
    WE1021_49_Nameless (the Masamune's weapon blueprint wearing WE1021_49); the Masamune's effect pack stays;
  * the two blueprints are added (their store entries the retail ones', the mesh package swapped).
Only the changed packs, the header and the blueprints are written, after the old .ucas (<out>/<NAME>.ucas.tail is what
to append to a copy of it); the .utoc is the new container's (its own id). Sephiroth's own packages are untouched, so
cutscene and boss Sephiroth stay as they are.
    build_fpys_data.py <out dir (new)> <base .utoc> <blueprints dir (make_bps.py)>"""
import hashlib, os, shutil, struct, sys
sys.path[:0] = ['/work/evilboss1016/data', '/work/iostore', '/work/cs', '/work/weap1012/tools',
                '/work/evil1013/tools', '/work/swap1012/tools', '/work/vincentfix']
from zen import Zen
from iostore import Toc
import iostore_write as W
import gameids
import hdr
import make_bp
import build_evilcloud_data as BED

OLD_NAME = 'FullyPlayableSephirothDataAssets_P'
NAME = 'FullyPlayableYoungSephirothDataAssets_P'
MOUNT = '../../../End/Content/'
NULL = 0xFFFFFFFFFFFFFFFF
PKG, OBJ = gameids.load()
objhash = gameids.objhash
RETAIL_HEADER = '/work/retailhdr/pakchunk4_header.bin'
RETAIL = '/work/seph1012/'
PACK = 'DataAsset/Game/CharaSpec/CharaSpec_%s.uasset'
CHAR_BP = ('/Game/BluePrint/Character/Player/', 'PC0010_00_Sephiroth_Standard', 'PC0010_13_Young_Sephiroth',
           ('/Game/Character/Player/PC0010_00_Sephiroth_Standard/Model/PC0010_00', '/Game/Character/Player/PC0010_13_Young_Sephiroth/Model/PC0010_13'))
WEAPON_BP = ('/Game/BluePrint/Character/Weapon/', 'WE1021_00_SephirothIllusion_Masamune', 'WE1021_49_Nameless',
             ('/Game/Character/Weapon/WE1021_00_SephirothIllusion_Masamune/Model/WE1021_00', '/Game/Character/Weapon/WE1021_49_Nameless/Model/WE1021_49'))
CHAR_PACKS = ['PC0000_00_Cloud_Standard', 'PC0000_04_Cloud_ZackCostume', 'PC0000_08_Cloud_SoldierNoHelmet', 'PC0000_09_Cloud_CostaClothing',
              'PC0000_10_Cloud_CostaClothing2', 'PC0000_12_Cloud_ZackCostumeDirty', 'PC0000_18_Cloud_ZackCostumeAge21',
              'PC0000_19_Cloud_ZackCostumeDirtyAge21', 'PC0000_23_Cloud_ZackCostumeWet']
WEAPON_PACKS = ['WE0000_00_Cloud_BusterSword'] + ['WE0000_%d_Cloud_END2Weapon%d' % (10 + k, k) for k in range(1, 7)] + ['WE0000_17_Cloud_Umbrella']


def imp(path):
    return (2 << 62) | objhash(path)


def bp_exports(data, pkg):
    z = Zen(data)
    return {e['global_import'] & ~(3 << 62): make_bp.export_path(z, i, pkg) for i, e in enumerate(z.exports) if e['global_import'] != NULL}


def graph_entries(d):
    z = Zen(d)
    o = z.graph_off
    n = struct.unpack_from('<i', d, o)[0]
    o += 4
    out = []
    for _ in range(n):
        pid, na = struct.unpack_from('<Qi', d, o)
        out.append((pid, bytes(d[o + 8:o + 12 + 8 * na])))
        o += 12 + 8 * na
    assert o == z.graph_off + z.graph_size
    return out


def swap_pack(data, row, bp, old_objs, new_objs):
    """The pack's imports of the old blueprint's objects -> the same objects of the new one; its graph likewise."""
    folder, old, new, _ = bp
    old_pkg, new_pkg = folder + old, folder + new
    z = Zen(data)
    table = {}
    for v in z.imports:
        if v == NULL:
            continue
        path = old_objs.get(v & ~(3 << 62))
        if not path:
            continue
        assert path.startswith(old_pkg + '.'), path
        to = new_pkg + '.' + path[len(old_pkg) + 1:].replace(old, new)
        assert imp(to) & ~(3 << 62) in new_objs, (row, 'not in the new blueprint', to)
        table[v] = imp(to)
    assert table, (row, 'names nothing of ' + old)
    d = bytearray(data)
    for i, v in enumerate(z.imports):
        if v in table:
            struct.pack_into('<Q', d, z.imp_off + 8 * i, table[v])
    left = [old_objs[v & ~(3 << 62)] for v in Zen(bytes(d)).imports if v != NULL and (v & ~(3 << 62)) in old_objs]
    assert not left, (row, left)
    old_pid, new_pid = W.package_id(old_pkg), W.package_id(new_pkg)
    g = graph_entries(bytes(d))
    assert sum(1 for pid, _ in g if pid == old_pid) == 1, (row, 'the graph does not name ' + old)
    g = sorted([(new_pid if pid == old_pid else pid, rest) for pid, rest in g], key=lambda x: x[0])
    gb = bytearray(struct.pack('<i', len(g)))
    for pid, rest in g:
        gb += struct.pack('<Q', pid) + rest
    assert len(gb) == z.graph_size
    d[z.graph_off:z.graph_off + z.graph_size] = gb
    out = bytes(d)
    assert out[z.header_end:] == data[z.header_end:] and len(out) == len(data)
    return out, len(table)


def main(out, base_utoc, bp_dir):
    assert not os.path.exists(out), out + ' exists (use a new folder)'
    base_ucas = base_utoc[:-len('.utoc')] + '.ucas'
    old = Toc(base_utoc)
    assert [i for i in range(old.entries) if old.chunk_type(i) == 10] == [0]
    for i in range(old.entries):
        assert hashlib.sha1(old.read(i)).digest() == old.b[old.metas_off + 33 * i:old.metas_off + 33 * i + 20], i
    old_cid, store = hdr.parse_header(old.read(0))
    assert old_cid == W.container_id_from_name(OLD_NAME)
    order = [old.chunk_id64(i) for i in range(old.entries) if old.chunk_type(i) == 2]
    assert len(order) == len(store) and set(order) == set(store)
    entries = [dict(id=p, size=store[p]['size'], export_count=store[p]['export_count'], export_bundle_count=store[p]['export_bundle_count'],
                    load_order=store[p]['load_order'], imports=list(store[p]['imports'])) for p in order]
    assert W.container_header(old_cid, entries) == old.read(0), 'the header does not write back as it is'
    entry_of = {e['id']: e for e in entries}
    by_path = {old.files[i][len(MOUNT):]: i for i in old.files}
    _, retail = hdr.parse_header(open(RETAIL_HEADER, 'rb').read())
    changes, additions, report = {}, [], []
    for bp, packs, src_file in ((CHAR_BP, CHAR_PACKS, RETAIL + 'Game__BluePrint__Character__Player__PC0010_00_Sephiroth_Standard.uasset'),
                                (WEAPON_BP, WEAPON_PACKS, RETAIL + 'Game__BluePrint__Character__Weapon__WE1021_00_SephirothIllusion_Masamune.uasset')):
        folder, old_bp, new_bp, (old_mesh, new_mesh) = bp
        old_data = open(src_file, 'rb').read()
        new_file = os.path.join(bp_dir, (folder + new_bp)[len('/Game/'):].replace('/', '__') + '.uasset')
        new_data = open(new_file, 'rb').read()
        old_objs, new_objs = bp_exports(old_data, folder + old_bp), bp_exports(new_data, folder + new_bp)
        for h, p in new_objs.items():
            OBJ.setdefault(h, p)
        # the blueprint itself
        old_pid, new_pid = W.package_id(folder + old_bp), W.package_id(folder + new_bp)
        assert new_pid not in PKG and new_pid not in entry_of, new_bp
        re = retail[old_pid]
        assert re['size'] == len(old_data)
        mesh_old, mesh_new = W.package_id(old_mesh), W.package_id(new_mesh)
        assert mesh_old in re['imports']
        z = Zen(new_data)
        additions.append(dict(id64=new_pid, type=2, data=new_data, path=(folder + new_bp)[len('/Game/'):] + '.uasset'))
        entries.append(dict(id=new_pid, size=len(new_data), export_count=len(z.exports), export_bundle_count=re['export_bundle_count'],
                            load_order=re['load_order'], imports=[mesh_new if x == mesh_old else x for x in re['imports']]))
        assert len(z.exports) == re['export_count']
        report.append('%s: %s\'s blueprint wearing %s (%d bytes, %d exports)' % (folder + new_bp, old_bp, new_mesh, len(new_data), len(z.exports)))
        # the packs that name the old blueprint
        for row in packs:
            i = by_path[PACK % row]
            before = old.read(i)
            new, n = swap_pack(before, row, bp, old_objs, new_objs)
            e = entry_of[old.chunk_id64(i)]
            assert old_pid in e['imports'], (row, 'its header entry does not list ' + old_bp)
            e['imports'] = [new_pid if x == old_pid else x for x in e['imports']]
            if e['size']:
                e['size'] = len(new)      # (most entries of this container carry 0, as the game takes them)
            changes[i] = new
            report.append('  CharaSpec_%s: %d imports of %s -> %s' % (row, n, old_bp, new_bp))
    # every package the changed ones import: here or in the game
    here = {e['id'] for e in entries}
    unknown = []
    for i in list(changes) + []:
        e = entry_of[old.chunk_id64(i)]
        unknown += ['%016x' % x for x in e['imports'] if x not in here and x not in PKG]
    for a in additions:
        e = [x for x in entries if x['id'] == a['id64']][0]
        unknown += ['%016x' % x for x in e['imports'] if x not in here and x not in PKG and x not in (W.package_id(CHAR_BP[3][1]), W.package_id(WEAPON_BP[3][1]))]
    assert not unknown, unknown
    # the container: its own id
    cid = W.container_id_from_name(NAME)
    changes[0] = W.container_header(cid, entries)
    os.makedirs(out)
    path = os.path.join(out, NAME)
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
    # read back
    new = Toc(path + '.utoc')
    assert new.container_id == cid and new.entries == old.entries + len(additions)
    assert new.chunk_id64(0) == cid and new.chunk_type(0) == 10
    for i in range(new.entries):
        data = new.read(i)
        if i < old.entries:
            assert new.files.get(i) == old.files.get(i), i
            assert data == (changes[i] if i in changes else old.read(i)), i
            if i:
                assert new.chunk_ids[i] == old.chunk_ids[i], i
        else:
            c = additions[i - old.entries]
            assert data == c['data'] and new.chunk_id64(i) == c['id64'] and new.chunk_type(i) == c['type'] and new.files.get(i) == MOUNT + c['path']
        assert hashlib.sha1(data).digest() == new.b[new.metas_off + 33 * i:new.metas_off + 33 * i + 20], i
    cid2, store2 = hdr.parse_header(new.read(0))
    assert cid2 == cid and len(store2) == len(store) + len(additions)
    for e in entries:
        b = store2[e['id']]
        for k in ('size', 'export_count', 'export_bundle_count', 'load_order', 'imports'):
            assert b[k] == e[k], k
    report.append('%s: %d chunks (%d before; %d packs and the header changed, %d blueprints added); read back as written; '
                  'the .ucas is the old one plus %d bytes' % (NAME, new.entries, old.entries, len(changes) - 1, len(additions),
                                                             os.path.getsize(path + '.ucas.tail')))
    open(os.path.join(out, 'changes.txt'), 'w').write('\n'.join(report) + '\n')
    print('\n'.join(report))
    for f in sorted(os.listdir(out)):
        p = os.path.join(out, f)
        print('  %-48s %10d %s' % (f, os.path.getsize(p), hashlib.md5(open(p, 'rb').read()).hexdigest()))


if __name__ == '__main__':
    main(*sys.argv[1:])
