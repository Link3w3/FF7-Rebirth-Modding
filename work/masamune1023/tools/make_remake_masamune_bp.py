"""The Remake Masamune's weapon blueprint for Rebirth: the game's own Masamune blueprint
(/Game/BluePrint/Character/Weapon/WE1021_00_SephirothIllusion_Masamune: AEndWeaponSkeletalMeshActor, SkeletalMeshComponent0
wearing /Game/Character/Weapon/WE1021_00_SephirothIllusion_Masamune/Model/WE1021_00) copied to Remake's own path and name,
/Game/GameContents/BluePrint/Character/Weapon/WE1021_00_SephirothIllusion_Masamune (the class keeps its name,
WE1021_00_SephirothIllusion_Masamune_C), wearing the imported Remake model at
/Game/GameContents/Character/Weapon/WE1021_00_SephirothIllusion_Masamune/Model/WE1021_00. Every other byte is the game's.
    make_remake_masamune_bp.py <out dir>   -> the package (.uasset) and its store entry (store_entry.json)"""
import json, os, struct, sys
sys.path[:0] = ['/work/iostore', '/work/cs', '/work/weap1012/tools', '/work/fpys/tools',
                '/work/evilboss1016/data', '/work/swap1012/tools']
from zen import Zen
import zenrename
import iostore_write as W
import gameids
import hdr

NULL = 0xFFFFFFFFFFFFFFFF
SRC_FILE = '/work/seph1012/Game__BluePrint__Character__Weapon__WE1021_00_SephirothIllusion_Masamune.uasset'
RETAIL_HEADER = '/work/retailhdr/pakchunk4_header.bin'
SRC_PKG = '/Game/BluePrint/Character/Weapon/WE1021_00_SephirothIllusion_Masamune'
NEW_PKG = '/Game/GameContents/BluePrint/Character/Weapon/WE1021_00_SephirothIllusion_Masamune'
OLD_MESH_PKG = '/Game/Character/Weapon/WE1021_00_SephirothIllusion_Masamune/Model/WE1021_00'
NEW_MESH_PKG = '/Game/GameContents/Character/Weapon/WE1021_00_SephirothIllusion_Masamune/Model/WE1021_00'
MESH = 'WE1021_00'


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


def make():
    src = open(SRC_FILE, 'rb').read()
    z = Zen(src)
    _, retail = hdr.parse_header(open(RETAIL_HEADER, 'rb').read())
    src_pid = W.package_id(SRC_PKG)
    re = retail[src_pid]
    assert re['size'] == len(src), (re['size'], len(src))
    assert re['export_count'] == len(z.exports) and re['export_bundle_count'] == bundle_count(z)
    for i, e in enumerate(z.exports):
        if e['global_import'] != NULL:
            assert imp(export_path(z, i, SRC_PKG)) == e['global_import'], e['name']
    renames = {SRC_PKG: NEW_PKG, OLD_MESH_PKG: NEW_MESH_PKG}
    for old in renames:
        assert old in z.names, old
    gis = {i: imp(export_path(z, i, NEW_PKG)) for i, e in enumerate(z.exports) if e['global_import'] != NULL}
    d = bytearray(zenrename.rebuild(src, renames, gis))
    nz = Zen(bytes(d))
    old_mesh, new_mesh = imp(OLD_MESH_PKG + '.' + MESH), imp(NEW_MESH_PKG + '.' + MESH)
    hits = [i for i, v in enumerate(nz.imports) if v == old_mesh]
    assert len(hits) == 1, hits
    struct.pack_into('<Q', d, nz.imp_off + 8 * hits[0], new_mesh)
    old_pid, new_pid = W.package_id(OLD_MESH_PKG), W.package_id(NEW_MESH_PKG)
    g = graph(bytes(d))
    assert sum(1 for pid, _ in g if pid == old_pid) == 1
    g = sorted([(new_pid if pid == old_pid else pid, arcs) for pid, arcs in g], key=lambda x: x[0])
    gb = bytearray(struct.pack('<i', len(g)))
    for pid, arcs in g:
        gb += struct.pack('<Qi', pid, len(arcs) // 2) + struct.pack('<%di' % len(arcs), *arcs)
    assert len(gb) == nz.graph_size
    d[nz.graph_off:nz.graph_off + nz.graph_size] = gb
    out = bytes(d)
    c = Zen(out)
    assert c.mapped(c.name_mapped) == NEW_PKG and c.mapped(c.srcname_mapped) == NEW_PKG
    assert [e['name'] for e in c.exports] == [e['name'] for e in z.exports]
    assert out[c.header_end:] == src[z.header_end:], 'export data changed'
    for i, e in enumerate(c.exports):
        if e['global_import'] != NULL:
            assert e['global_import'] == imp(export_path(c, i, NEW_PKG))
    assert new_mesh in c.imports and old_mesh not in c.imports
    assert SRC_PKG not in c.names and OLD_MESH_PKG not in c.names
    assert old_pid in re['imports']
    entry = dict(package=NEW_PKG, size=len(out), export_count=len(c.exports), export_bundle_count=bundle_count(c),
                 load_order=re['load_order'], imports=['%016x' % (new_pid if x == old_pid else x) for x in re['imports']])
    return out, entry, c


def main(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    data, entry, c = make()
    rel = NEW_PKG[len('/Game/'):] + '.uasset'
    path = os.path.join(out_dir, 'Content', rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'wb').write(data)
    entry['file'] = 'Content/' + rel
    entry['bulk'] = []
    json.dump(entry, open(os.path.join(out_dir, 'store_entry.json'), 'w'), indent=1)
    print(json.dumps(entry, indent=1))
    print('names:', c.names)
    print('exports:', [(e['name'], hex(e['global_import'])) for e in c.exports])


if __name__ == '__main__':
    main(sys.argv[1])
