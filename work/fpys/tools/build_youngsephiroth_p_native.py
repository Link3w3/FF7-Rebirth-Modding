"""YoungSephiroth_P with Rebirth's own materials: Young Sephiroth's model PC0010_13 and the Nameless WE1021_49 wear the
game-native material instances made for them (their textures in Rebirth's layout under the retail RMI_Surface_*
instances: PC0010_13_Body (RMI_Surface_Standard_Coverage_Wide), _Head (RMI_Surface_Skin_Wide_Detail), _Hair
(RMI_Surface_Hair_Wide, his hair and his hair tips), _Eye (RMI_Surface_Standard_Wide); WE1021_49_Body
(RMI_Surface_Standard_Wide)) instead of the Unity toon conversions of YoungSephirothMaterials_P (mat_ch049_001_* and
WE1021_49_Mat00). The eyelash, eye shadow and wing materials were the game's kind already and stay.
Everything else is the base container's, byte for byte (the KineDriver fix included). In the two meshes only the
material imports change, and their graph entries (his hair and hair tips share one now) and header entries. The
material instances come from the End project's cook (zen1: the BasePropertyOverrides put in the game's layout,
micfix), their textures from its cook too (tex1: zentex, streamed mips' bulk headers as the game's zen loader reads
them). Every import is checked to be here or the game's: nothing comes from YoungSephirothMaterials_P any more.
    build_youngsephiroth_p_native.py <base YoungSephiroth_P.utoc> <zen1 YS13Zen.utoc> <tex1 dir> <out dir (new)>"""
import gzip, hashlib, os, shutil, struct, sys
import inspect, numpy  # before the tool folders join the path (evil1013/tools has its own inspect.py)
sys.path[:0] = ['/work/fpys/tools', '/work/iostore', '/work/cs', '/work/swap1012/tools',
                '/work/weap1012/tools', '/work/vincentfix', '/work/evil1013/tools',
                '/work/custmat', '/work/custmat/taken', '/work/aval1016/tools',
                '/work/safer1015/tools']
from iostore import Toc
from zen import Zen
from hdr import parse_header
import iostore_write as W
import gameids
import zentex
import pack
import micfix
import build_youngsephiroth_p as YSB

NAME = 'YoungSephiroth_P'
MOUNT = '../../../End/Content/'
U = '/Game/Character/Player/PC0010_10_Young_Sephiroth_Outfit_Transformed/Material/Unity/'
YM = '/Game/Character/Player/PC0010_13_Young_Sephiroth/Material/'
NM = '/Game/Character/Weapon/WE1021_49_Nameless/Material/'
SWAPS = {
    '/Game/Character/Player/PC0010_13_Young_Sephiroth/Model/PC0010_13': {
        U + 'mat_ch049_001_body': YM + 'PC0010_13_Body', U + 'mat_ch049_001_head': YM + 'PC0010_13_Head',
        U + 'mat_ch049_001_hair': YM + 'PC0010_13_Hair', U + 'mat_ch049_001_hair_tp': YM + 'PC0010_13_Hair',
        U + 'mat_ch049_001_eye': YM + 'PC0010_13_Eye'},
    '/Game/Character/Weapon/WE1021_49_Nameless/Model/WE1021_49': {NM + 'WE1021_49_Mat00': NM + 'WE1021_49_Body'},
}
NEW_MIS = [YM + 'PC0010_13_Body', YM + 'PC0010_13_Head', YM + 'PC0010_13_Hair', YM + 'PC0010_13_Eye', NM + 'WE1021_49_Body']
NULL = 0xFFFFFFFFFFFFFFFF


def imp(path):
    return (2 << 62) | gameids.objhash(path)


def leaf(p):
    return p.rsplit('/', 1)[1]


def graph(d):
    z = Zen(d)
    o = z.graph_off
    n = struct.unpack_from('<i', d, o)[0]
    o += 4
    out = []
    for _ in range(n):
        pid, na = struct.unpack_from('<Qi', d, o)
        out.append((pid, [tuple(struct.unpack_from('<ii', d, o + 12 + 8 * k)) for k in range(na)]))
        o += 12 + 8 * na
    assert o == z.graph_off + z.graph_size
    return out


def swap_materials(data, pkg, swaps):
    """The mesh's imports of the old materials -> the new ones; its graph entries likewise (merged where two old ones
    become one new one); the package header's graph size follows. Every other byte stays."""
    z = Zen(data)
    d = bytearray(data)
    done = []
    for old, new in swaps.items():
        h_old, h_new = imp(old + '.' + leaf(old)), imp(new + '.' + leaf(new))
        hits = [k for k, v in enumerate(z.imports) if v == h_old]
        assert len(hits) == 1, (pkg, old, hits)
        struct.pack_into('<Q', d, z.imp_off + 8 * hits[0], h_new)
        done.append((leaf(old), leaf(new), hits[0]))
    pid_map = {W.package_id(o): W.package_id(n) for o, n in swaps.items()}
    g_old = graph(data)
    assert all(sum(1 for p, _ in g_old if p == o) == 1 for o in pid_map), 'a material package missing from the graph'
    g_new, at = [], {}
    for p, arcs in g_old:
        p2 = pid_map.get(p, p)
        if p2 in at:
            for a in arcs:
                if a not in g_new[at[p2]][1]:
                    g_new[at[p2]][1].append(a)
        else:
            at[p2] = len(g_new)
            g_new.append((p2, list(arcs)))
    gb = bytearray(struct.pack('<i', len(g_new)))
    for p, arcs in g_new:
        gb += struct.pack('<Qi', p, len(arcs))
        for a in arcs:
            gb += struct.pack('<ii', *a)
    d[z.graph_off:z.graph_off + z.graph_size] = gb
    struct.pack_into('<i', d, 56, len(gb))   # FPackageSummary.GraphDataSize
    out = bytes(d)
    c = Zen(out)
    assert c.graph_off == z.graph_off and c.graph_size == len(gb)
    assert out[c.header_end:] == data[z.header_end:], 'export data changed'
    assert [e['name'] for e in c.exports] == [e['name'] for e in z.exports] and c.names == z.names
    for old, new in swaps.items():
        assert imp(new + '.' + leaf(new)) in c.imports and imp(old + '.' + leaf(old)) not in c.imports
    assert graph(out) == g_new
    return out, done, pid_map, len(g_old) - len(g_new)


def main(base_utoc, zen1_utoc, tex_dir, out):
    assert not os.path.exists(out), out + ' exists (use a new folder)'
    game = YSB.ids_of_files(line.rstrip('\n').split('\t')[-1] for line in gzip.open(YSB.GAME_FILES, 'rt'))
    base = Toc(base_utoc)
    assert [i for i in range(base.entries) if base.chunk_type(i) == 10] == [0]
    cid, store = parse_header(base.read(0))
    assert cid == W.container_id_from_name(NAME)
    chunks, entries, names = [None], {}, {}
    report = []
    for i in range(1, base.entries):
        f = base.files.get(i)
        data = base.read(i)
        pid = base.chunk_id64(i)
        kind = base.chunk_type(i)
        pkg = '/Game/' + f[len(MOUNT):].rsplit('.', 1)[0]
        if kind == 2:
            se = store[pid]
            e = dict(id=pid, size=se['size'], export_count=se['export_count'], export_bundle_count=se['export_bundle_count'],
                     load_order=se['load_order'], imports=list(se['imports']))
            if pkg in SWAPS:
                data, done, pid_map, merged = swap_materials(data, pkg, SWAPS[pkg])
                e['imports'] = list(dict.fromkeys(pid_map.get(x, x) for x in e['imports']))
                if e['size']:
                    e['size'] = len(data)
                report.append('%s: %s (graph entries merged: %d)' % (leaf(pkg), ', '.join('%s -> %s' % (a, b) for a, b, _ in done), merged))
            entries[pid] = e
            names[pid] = pkg
        chunks.append(dict(id64=pid, type=kind, data=data, path=f[len(MOUNT):]))
    # the game-native material instances
    z1 = Toc(zen1_utoc)
    by_pkg = {'/Game/' + z1.files[i][len(MOUNT):].rsplit('.', 1)[0]: i for i in z1.files}
    for pkg in NEW_MIS:
        pid = W.package_id(pkg)
        assert pid not in entries and pid not in game, pkg
        data = z1.read(by_pkg[pkg])
        data, notes = micfix.fix_package(data)
        for n in notes:
            report.append('  material fix %s: %s %s -> %s, kept %s, left out %s' % (leaf(pkg), n['export'], n['size'][0], n['size'][1], n['kept'], n['dropped']))
        z = Zen(data)
        assert z.mapped(z.name_mapped) == pkg
        imports = [g for g, arcs in zentex.matcore.graph_packages(data)]
        chunks.append(dict(id64=pid, type=2, data=data, path=pkg[len('/Game/'):] + '.uasset'))
        entries[pid] = dict(id=pid, size=len(data), export_count=len(z.exports), export_bundle_count=pack._bundle_count(z), load_order=0,
                            imports=imports)
        names[pid] = pkg
        report.append('%s: added (%d bytes, %d imported packages)' % (leaf(pkg), len(data), len(imports)))
    # their textures: every one they import that is not here yet
    wanted = sorted({i for pkg in NEW_MIS for i in entries[W.package_id(pkg)]['imports'] if i not in entries and i not in game})
    found = {}
    for dp, dn, fn in os.walk(tex_dir):
        for f in sorted(fn):
            if not f.endswith('.uasset'):
                continue
            rel = os.path.relpath(os.path.join(dp, f), tex_dir).replace(os.sep, '/')
            pkg = '/Game/' + rel[:-len('.uasset')].lstrip('./')
            if W.package_id(pkg) in wanted:
                found[W.package_id(pkg)] = os.path.join(dp, f)
    missing = [('%016x' % w) for w in wanted if w not in found]
    assert not missing, ('textures the materials need and tex1 does not have', missing)
    for pid in wanted:
        p = found[pid]
        ua = open(p, 'rb').read()
        ubp = p[:-len('.uasset')] + '.ubulk'
        ub = open(ubp, 'rb').read() if os.path.exists(ubp) else b''
        data, bulk, rep = zentex.convert(ua, ub)
        z = Zen(data)
        pkg = z.mapped(z.name_mapped)
        assert W.package_id(pkg) == pid, pkg
        chunks.append(dict(id64=pid, type=2, data=data, path=pkg[len('/Game/'):] + '.uasset'))
        if bulk:
            chunks.append(dict(id64=pid, type=3, data=bulk, path=pkg[len('/Game/'):] + '.ubulk'))
        imports = [g for g, arcs in zentex.matcore.graph_packages(data)]
        entries[pid] = dict(id=pid, size=len(data), export_count=len(z.exports), export_bundle_count=pack._bundle_count(z), load_order=0,
                            imports=imports)
        names[pid] = pkg
    report.append('%d textures added: %s' % (len(wanted), ', '.join(sorted(leaf(names[p]) for p in wanted))))
    # load orders: each package after the ones here it imports (as YoungSephiroth_P's builder)
    order = {}

    def lo(pid, stack=()):
        if pid in order:
            return order[pid]
        assert pid not in stack, 'import cycle'
        deps = [lo(i, stack + (pid,)) for i in entries[pid]['imports'] if i in entries]
        order[pid] = 1 + max(deps or [0])
        return order[pid]
    for e in entries.values():
        e['load_order'] = 1000 + lo(e['id'])
    here = set(entries)
    unknown = sorted({'%016x (imported by %s)' % (i, leaf(names[e['id']])) for e in entries.values() for i in e['imports'] if i not in here and i not in game})
    assert not unknown, unknown
    # nothing names the Unity materials any more
    for c in chunks[1:]:
        if c['type'] == 2:
            zz = Zen(c['data'])
            left = [n for n in zz.names if n.startswith(U) or n == NM + 'WE1021_49_Mat00']
            if left:
                assert c['path'].endswith(('PC0010_13.uasset', 'WE1021_49.uasset')), (c['path'], left)
    ent_list = [entries[c['id64']] for c in chunks[1:] if c['type'] == 2]
    chunks[0] = dict(id64=cid, type=10, data=W.container_header(cid, ent_list), path=None)
    os.makedirs(out)
    basep = os.path.join(out, NAME)
    assert W.write_container(basep, NAME, chunks, mount=MOUNT) == cid
    shutil.copy(base_utoc[:-len('.utoc')] + '.pak', basep + '.pak')
    back = Toc(basep + '.utoc')
    assert back.container_id == cid and back.entries == len(chunks)
    for i, c in enumerate(chunks):
        assert back.read(i) == c['data'] and back.chunk_id64(i) == c['id64'] and back.chunk_type(i) == c['type']
        if c['path']:
            assert back.files.get(i) == MOUNT + c['path'], (back.files.get(i), c['path'])
    cid2, ents = parse_header(back.read(0))
    assert cid2 == cid and set(ents) == here
    for e in ent_list:
        b = ents[e['id']]
        for k in ('size', 'export_count', 'export_bundle_count', 'load_order', 'imports'):
            assert b[k] == e[k], (k, names[e['id']])
    for line in report:
        print(line)
    print('%s: %d packages, %d bulk chunks; every import here or the game\'s (none from YoungSephirothMaterials_P)' % (
        NAME, len(ent_list), sum(1 for c in chunks[1:] if c['type'] == 3)))
    for f in sorted(os.listdir(out)):
        p = os.path.join(out, f)
        print('  %-30s %9d %s' % (f, os.path.getsize(p), hashlib.md5(open(p, 'rb').read()).hexdigest()))


if __name__ == '__main__':
    main(*sys.argv[1:5])
