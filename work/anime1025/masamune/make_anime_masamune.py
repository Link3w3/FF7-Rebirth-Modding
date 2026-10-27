"""Anime Sephiroth's Masamune for Rebirth: the game's own playable Masamune (the cut-scale one every Sephiroth skin
fights with) copied to paths of its own and pointed at the toon material.

  mesh: /Game/Character/Weapon/WE1021_10_SephirothIllusion_MasamuneCutScale/Model/WE1021_10 (pakchunk10) copied to
        .../WE1021_10_SephirothIllusion_MasamuneCutScale/Anime/WE1021_10, its material slot's import
        (.../Material/WE1021_10_Body) pointed at the toon material instance
        /Game/Character/Weapon/WE1021_00_SephirothIllusion_Masamune/Anime/WE1021_00_Body_Toon (a game material made by
        Game Materials: RebirthGameMaterials_P); its bulk data (.ubulk) as it is
  blueprint: /Game/BluePrint/Character/Weapon/WE1021_10_SephirothIllusion_MasamuneCutScale copied to
        /Game/BluePrint/Character/Weapon/Anime/WE1021_10_SephirothIllusion_MasamuneCutScale (the class keeps its name,
        WE1021_10_SephirothIllusion_MasamuneCutScale_C, and its parent, the game's WE1021_00 Masamune), its mesh's
        import pointed at the copy above
Every other byte is the game's (the export data unchanged). Writes <out>/Content/... and <out>/store_entries.json (the
skin.json "packages" entries).
    make_anime_masamune.py <out dir>"""
import json, os, struct, sys
sys.path[:0] = ['/work/iostore', '/work/cs', '/work/weap1012/tools', '/work/fpys/tools',
                '/work/evilboss1016/data', '/work/swap1012/tools']
from zen import Zen
import zenrename
import iostore_write as W
import gameids
import hdr

NULL = 0xFFFFFFFFFFFFFFFF
PKGS = '/work/anime1025/gx10/pkgs/'
SRC_MESH = PKGS + 'Character__Weapon__WE1021_10_SephirothIllusion_MasamuneCutScale__Model__WE1021_10.uasset'
SRC_BULK = PKGS + 'Character__Weapon__WE1021_10_SephirothIllusion_MasamuneCutScale__Model__WE1021_10.ubulk'
SRC_BP = PKGS + 'BluePrint__Character__Weapon__WE1021_10_SephirothIllusion_MasamuneCutScale.uasset'
RETAIL_HEADER = '/work/retailhdr/pakchunk10_header.bin'

MESH_OLD = '/Game/Character/Weapon/WE1021_10_SephirothIllusion_MasamuneCutScale/Model/WE1021_10'
MESH_NEW = '/Game/Character/Weapon/WE1021_10_SephirothIllusion_MasamuneCutScale/Anime/WE1021_10'
MESH_NAME_OLD = '/Game/Character/Weapon/WE1021_10_SephirothIllusion_MasamuneCutScale/Model/WE1021'   # (number 11: _10)
MESH_NAME_NEW = '/Game/Character/Weapon/WE1021_10_SephirothIllusion_MasamuneCutScale/Anime/WE1021'
MESH_OBJ = 'WE1021_10'
MAT_OLD = '/Game/Character/Weapon/WE1021_10_SephirothIllusion_MasamuneCutScale/Material/WE1021_10_Body'
MAT_NEW = '/Game/Character/Weapon/WE1021_00_SephirothIllusion_Masamune/Anime/WE1021_00_Body_Toon'
BP_OLD = '/Game/BluePrint/Character/Weapon/WE1021_10_SephirothIllusion_MasamuneCutScale'
BP_NEW = '/Game/BluePrint/Character/Weapon/Anime/WE1021_10_SephirothIllusion_MasamuneCutScale'


def imp(path):
    return (2 << 62) | gameids.objhash(path)


def export_path(z, i, pkg):
    chain = []
    while True:
        e = z.exports[i]
        chain.append(e['name'])
        if e['outer'] == NULL:
            break
        i = e['outer']
    chain.reverse()
    path = pkg + '.' + chain[0]
    if len(chain) > 1:
        path += ':' + chain[1]
    for sub in chain[2:]:
        path += '.' + sub
    return path


def graph(d):
    z = Zen(d)
    o = z.graph_off
    n = struct.unpack_from('<i', d, o)[0]
    o += 4
    out = []
    for _ in range(n):
        pid, na = struct.unpack_from('<Qi', d, o)
        out.append((pid, list(struct.unpack_from('<%di' % (2 * na), d, o + 12)) if na else []))
        o += 12 + 8 * na
    assert o == z.graph_off + z.graph_size
    return out


def bundle_count(z):
    total, seen, p, n = 2 * len(z.exports), 0, z.eb_off, 0
    while seen < total:
        first, count = struct.unpack_from('<II', z.d, p)
        p += 8
        seen += count
        n += 1
    return n


def copy_package(src, src_pkg, new_pkg, name_renames, import_redirects, retail):
    """src (zen bytes) of src_pkg copied as new_pkg: name map entries renamed, the exports' global ids made for new_pkg,
    each import object path in import_redirects (old object path -> new object path) pointed at the new one, the graph's
    imported packages (and the store entry's) renamed to match, and every graph arc made to wait for its imported
    package's last export bundle (-1: whatever layout the package the game loads has). Returns (bytes, store entry, Zen)."""
    z = Zen(src)
    src_pid = W.package_id(src_pkg)
    re_ = retail[src_pid]
    assert re_['size'] == len(src), (re_['size'], len(src))
    assert re_['export_count'] == len(z.exports) and re_['export_bundle_count'] == bundle_count(z)
    for i, e in enumerate(z.exports):
        if e['global_import'] != NULL:
            assert imp(export_path(z, i, src_pkg)) == e['global_import'], e['name']
    for old in name_renames:
        assert old in z.names, old
    gis = {i: imp(export_path(z, i, new_pkg)) for i, e in enumerate(z.exports) if e['global_import'] != NULL}
    d = bytearray(zenrename.rebuild(src, name_renames, gis))
    nz = Zen(bytes(d))
    pid_map = {}
    for old_obj, new_obj in import_redirects.items():
        o, n = imp(old_obj), imp(new_obj)
        hits = [i for i, v in enumerate(nz.imports) if v == o]
        assert len(hits) == 1, (old_obj, hits)
        struct.pack_into('<Q', d, nz.imp_off + 8 * hits[0], n)
        pid_map[W.package_id(old_obj.split('.', 1)[0])] = W.package_id(new_obj.split('.', 1)[0])
    g = graph(bytes(d))
    for old_pid in pid_map:
        assert sum(1 for pid, _ in g if pid == old_pid) == 1, hex(old_pid)
        assert old_pid in re_['imports'], hex(old_pid)
    g = sorted([(pid_map.get(pid, pid), arcs) for pid, arcs in g], key=lambda x: x[0])
    # every arc from an imported package made to wait for that package's LAST export bundle (FromExportBundleIndex -1,
    # MAX_uint32: the loader takes the imported package's ExportBundleCount - 1, as for a DLC's arcs to the base game). The
    # game's arcs name bundles of the game's own layout (the retail WE1021_00 Masamune blueprint: one bundle, so "0 -> 0");
    # a mod can replace an imported package with another layout (FullyPlayableYoungSephirothDataAssets_P's WE1021_00: 12
    # bundles, its class created in bundle 0 but serialized in bundle 6), and then "0 -> 0" lets this package's class be
    # serialized against a parent class not yet serialized ("Can't find ClassConstructor for class ...WE1021_00_..._C",
    # 2026-10-25). The last bundle done means all of that package's exports are made and serialized, whatever its layout.
    g = [(pid, [(-1 if k % 2 == 0 else a) for k, a in enumerate(arcs)]) for pid, arcs in g]
    gb = bytearray(struct.pack('<i', len(g)))
    for pid, arcs in g:
        gb += struct.pack('<Qi', pid, len(arcs) // 2) + struct.pack('<%di' % len(arcs), *arcs)
    assert len(gb) == nz.graph_size
    d[nz.graph_off:nz.graph_off + nz.graph_size] = gb
    out = bytes(d)
    assert all(arcs[k] == -1 for _, arcs in graph(out) for k in range(0, len(arcs), 2)), 'an arc names a fixed bundle'
    c = Zen(out)
    assert c.mapped(c.name_mapped) == new_pkg and c.mapped(c.srcname_mapped) == new_pkg, (c.mapped(c.name_mapped), new_pkg)
    assert [e['name'] for e in c.exports] == [e['name'] for e in z.exports]
    assert out[c.header_end:] == src[z.header_end:], 'export data changed'
    for i, e in enumerate(c.exports):
        if e['global_import'] != NULL:
            assert e['global_import'] == imp(export_path(c, i, new_pkg))
    for old_obj, new_obj in import_redirects.items():
        assert imp(new_obj) in c.imports and imp(old_obj) not in c.imports
    entry = dict(package=new_pkg, size=len(out), export_count=len(c.exports), export_bundle_count=bundle_count(c),
                 load_order=re_['load_order'], imports=['%016x' % pid_map.get(x, x) for x in re_['imports']])
    return out, entry, c


def main(out_dir):
    _, retail = hdr.parse_header(open(RETAIL_HEADER, 'rb').read())
    mesh, mesh_entry, mz = copy_package(open(SRC_MESH, 'rb').read(), MESH_OLD, MESH_NEW,
                                        {MESH_NAME_OLD: MESH_NAME_NEW, MAT_OLD: MAT_NEW},
                                        {MAT_OLD + '.WE1021_10_Body': MAT_NEW + '.WE1021_00_Body_Toon'}, retail)
    bp, bp_entry, bz = copy_package(open(SRC_BP, 'rb').read(), BP_OLD, BP_NEW,
                                    {BP_OLD: BP_NEW, MESH_NAME_OLD: MESH_NAME_NEW},
                                    {MESH_OLD + '.' + MESH_OBJ: MESH_NEW + '.' + MESH_OBJ}, retail)
    entries = []
    for pkg, data, entry, bulk in ((MESH_NEW, mesh, mesh_entry, SRC_BULK), (BP_NEW, bp, bp_entry, None)):
        rel = 'Content/' + pkg[len('/Game/'):] + '.uasset'
        path = os.path.join(out_dir, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, 'wb').write(data)
        entry = dict(package=entry['package'], file=rel, size=entry['size'], export_count=entry['export_count'],
                     export_bundle_count=entry['export_bundle_count'], load_order=entry['load_order'],
                     imports=entry['imports'], bulk=[])
        if bulk:
            brel = rel[:-len('.uasset')] + '.ubulk'
            open(os.path.join(out_dir, brel), 'wb').write(open(bulk, 'rb').read())
            entry['bulk'] = [dict(file=brel, type=3)]
        entries.append(entry)
    json.dump(entries, open(os.path.join(out_dir, 'store_entries.json'), 'w'), indent=1)
    print(json.dumps(entries, indent=1))
    print('mesh names (first 6):', mz.names[:6])
    print('bp names (first 4):', bz.names[:4])


if __name__ == '__main__':
    main(sys.argv[1])
