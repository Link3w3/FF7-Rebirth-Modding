"""The Avalanche Sephiroth outfit, an optional pak: <NAME> holds
  * the user's cooked PC0010_11_Skeleton and PC0010_12 (PC0010_12_Avalanche_Sephiroth_Transformed: Sephiroth in the
    Avalanche clothes with the transformed Sephiroth's wing, material slot PC0010_10_Wing) from their pakchunk51, as they
    are (bytes and header entries), and
  * Sephiroth's character blueprint (PC0010_00_Sephiroth_Standard: the one Cloud's rows spawn for the playable Sephiroth)
    with its mesh import pointing at PC0010_12 instead of PC0010_00; every other byte is the retail blueprint's.
Nothing in it is in FullyPlayableSephirothDataAssets_P, so the two never fight over a package: with this pak in, the
blueprint (field, battle, cutscenes, menus) puts the outfit on; without it, the data pak's winged PC0010_00 again.
    build_outfit.py <out dir (new)>"""
import hashlib, os, shutil, struct, sys
sys.path[:0] = ['/work/iostore', '/work/cs', '/work/swap1012/tools', '/work/weap1012/tools',
                '/work/vincentfix', '/work/evil1013/tools']
from iostore import Toc
from zen import Zen
from hdr import parse_header
import iostore_write as W
import gameids

PKG, OBJ = gameids.load()
NULL = 0xFFFFFFFFFFFFFFFF
NAME = 'AvalancheSephirothOutfit_P'
MOUNT = '../../../End/Content/'
SRC = '/work/aval1016/in/pakchunk51-WindowsNoEditor'
SKELETON = '/Game/Character/Player/PC0010_11_Avalanche_Sephiroth_Standard/Model/PC0010_11_Skeleton'
MESH = '/Game/Character/Player/PC0010_12_Avalanche_Sephiroth_Transformed/Model/PC0010_12'
OTHER_MESH = '/Game/Character/Player/PC0010_11_Avalanche_Sephiroth_Standard/Model/PC0010_11'   # (the wingless one: not needed)
BP = '/Game/BluePrint/Character/Player/PC0010_00_Sephiroth_Standard'
BP_FILE = '/work/abp1016/pkgs/BluePrint__Character__Player__PC0010_00_Sephiroth_Standard.uasset'
BP_MD5 = '515bb98dd5a99cdf532d86a80269d795'   # the retail one (pakchunk4)
RETAIL_HEADER = '/work/retailhdr/pakchunk4_header.bin'
OLD_MESH = '/Game/Character/Player/PC0010_00_Sephiroth_Standard/Model/PC0010_00'


def imp(path):
    return (2 << 62) | gameids.objhash(path)


def graph(d):
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


def blueprint(mesh_import, mesh_pid):
    src = open(BP_FILE, 'rb').read()
    assert hashlib.md5(src).hexdigest() == BP_MD5, 'not the retail blueprint'
    z = Zen(src)
    assert z.mapped(z.name_mapped) == BP
    d = bytearray(src)
    old = imp(OLD_MESH + '.PC0010_00')
    hits = [i for i, v in enumerate(z.imports) if v == old]
    assert len(hits) == 1, hits
    struct.pack_into('<Q', d, z.imp_off + 8 * hits[0], mesh_import)
    old_pid = W.package_id(OLD_MESH)
    g = graph(src)
    assert sum(1 for pid, _ in g if pid == old_pid) == 1
    arcs = [rest for pid, rest in g if pid == old_pid][0]
    assert arcs == struct.pack('<i', 1) + struct.pack('<ii', 0, 0), 'the mesh arc is not bundle 0 -> bundle 0'
    g = sorted([(mesh_pid if pid == old_pid else pid, rest) for pid, rest in g], key=lambda x: x[0])
    gb = bytearray(struct.pack('<i', len(g)))
    for pid, rest in g:
        gb += struct.pack('<Q', pid) + rest
    assert len(gb) == z.graph_size
    d[z.graph_off:z.graph_off + z.graph_size] = gb
    out = bytes(d)
    c = Zen(out)
    # only the mesh import and the graph changed
    assert out[c.header_end:] == src[z.header_end:] and len(out) == len(src)
    changed = [i for i in range(len(src)) if out[i] != src[i]]
    assert all(z.imp_off + 8 * hits[0] <= i < z.imp_off + 8 * hits[0] + 8 or z.graph_off <= i < z.graph_off + z.graph_size for i in changed)
    assert c.imports == [mesh_import if i == hits[0] else v for i, v in enumerate(z.imports)]
    assert [e['name'] for e in c.exports] == [e['name'] for e in z.exports]
    return out, old_pid


def main(out):
    assert not os.path.exists(out), out + ' exists (use a new folder)'
    src = Toc(SRC + '.utoc')
    heads = [i for i in range(src.entries) if src.chunk_type(i) == 10]
    assert len(heads) == 1
    _, ents = parse_header(src.read(heads[0]))
    found = {}
    for i in range(src.entries):
        if src.chunk_type(i) != 2:
            continue
        data = src.read(i)
        z = Zen(data)
        pkg = z.mapped(z.name_mapped)
        assert src.chunk_id64(i) == W.package_id(pkg) and src.files[i] == MOUNT + pkg[len('/Game/'):] + '.uasset', (pkg, src.files[i])
        found[pkg] = (data, ents[W.package_id(pkg)])
    assert set(found) == {SKELETON, MESH, OTHER_MESH}, sorted(found)
    skel_pid, mesh_pid = W.package_id(SKELETON), W.package_id(MESH)
    mesh_data, mesh_entry = found[MESH]
    mz = Zen(mesh_data)
    mesh_import = [e['global_import'] for e in mz.exports if e['name'] == 'PC0010_12'][0]
    assert mesh_import == imp(MESH + '.PC0010_12'), 'the mesh export index is not its path\'s'
    assert skel_pid in mesh_entry['imports'] and W.package_id(OTHER_MESH) not in mesh_entry['imports']
    assert mesh_entry['export_bundle_count'] == 1
    # the outfit's packages come from the game or this pak
    here = {skel_pid, mesh_pid}
    for pkg in (SKELETON, MESH):
        for x in found[pkg][1]['imports']:
            assert x in here or x in PKG, (pkg, '%016x' % x)
    # the blueprint and its header entry (the retail entry, the mesh package swapped in its place)
    bp, old_pid = blueprint(mesh_import, mesh_pid)
    _, retail = parse_header(open(RETAIL_HEADER, 'rb').read())
    bp_pid = W.package_id(BP)
    re = retail[bp_pid]
    assert re['size'] == len(bp) and re['export_count'] == len(Zen(bp).exports) and old_pid in re['imports']
    bp_imports = [mesh_pid if x == old_pid else x for x in re['imports']]
    assert {pid for pid, _ in graph(bp)} == set(bp_imports)
    for x in bp_imports:
        assert x in here or x in PKG, ('blueprint', '%016x' % x)
    for v in Zen(bp).imports:
        if v != NULL and (v >> 62) == 2:
            assert v == mesh_import or OBJ.get(v & ~(3 << 62)), ('blueprint import unknown', '%016x' % v)
    # the container
    chunks = [None]
    entries = []
    for pkg in (SKELETON, MESH):
        data, e = found[pkg]
        chunks.append(dict(id64=W.package_id(pkg), type=2, data=data, path=pkg[len('/Game/'):] + '.uasset'))
        entries.append(dict(id=W.package_id(pkg), size=e['size'], export_count=e['export_count'], export_bundle_count=e['export_bundle_count'],
                            load_order=e['load_order'], imports=e['imports']))
    chunks.append(dict(id64=bp_pid, type=2, data=bp, path=BP[len('/Game/'):] + '.uasset'))
    entries.append(dict(id=bp_pid, size=re['size'], export_count=re['export_count'], export_bundle_count=re['export_bundle_count'],
                        load_order=re['load_order'], imports=bp_imports))
    cid = W.container_id_from_name(NAME)
    chunks[0] = dict(id64=cid, type=10, data=W.container_header(cid, entries), path=None)
    os.makedirs(out)
    base = os.path.join(out, NAME)
    W.write_container(base, NAME, chunks, mount=MOUNT)
    shutil.copy(SRC + '.pak', base + '.pak')
    # read back
    back = Toc(base + '.utoc')
    assert back.container_id == cid and back.entries == len(chunks)
    for i, c in enumerate(chunks):
        assert back.read(i) == c['data'] and back.chunk_id64(i) == c['id64'] and back.chunk_type(i) == c['type']
        if c['path']:
            assert back.files.get(i) == MOUNT + c['path'], back.files.get(i)
        assert hashlib.sha1(c['data']).digest() == back.b[back.metas_off + 33 * i:back.metas_off + 33 * i + 20]
    cid2, back_entries = parse_header(back.read(0))
    assert cid2 == cid and set(back_entries) == {c['id64'] for c in chunks[1:]}
    for e in entries:
        b = back_entries[e['id']]
        for k in ('size', 'export_count', 'export_bundle_count', 'load_order', 'imports'):
            assert b[k] == e[k], (k, e['id'])
    for pkg in (SKELETON, MESH):
        assert back_entries[W.package_id(pkg)]['imports'] == found[pkg][1]['imports']
    print('%s: %d packages (the skeleton and PC0010_12 from pakchunk51 as they are; Sephiroth\'s blueprint, its mesh %s -> %s)'
          % (NAME, len(chunks) - 1, OLD_MESH.rsplit('/', 1)[1], MESH.rsplit('/', 1)[1]))
    for f in sorted(os.listdir(out)):
        p = os.path.join(out, f)
        print('  %-36s %9d %s' % (f, os.path.getsize(p), hashlib.md5(open(p, 'rb').read()).hexdigest()))


if __name__ == '__main__':
    main(sys.argv[1])
