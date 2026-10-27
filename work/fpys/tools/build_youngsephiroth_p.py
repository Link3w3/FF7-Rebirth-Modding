"""YoungSephiroth_P: Young Sephiroth's model and the Nameless, for the Fully Playable Young Sephiroth:
  * PC0010_13 (his mesh with Sephiroth's wing at 80%: material slot PC0010_10_Wing), PC0010_13_Skeleton, his Bonamik
    PC0010_13_BNM, the wing's Bonamik PC0010_13_Wing_BNM and the wing's KineDriver PC0010_13_KDI;
  * his two game-native material instances (eyelash, eye shadow: the BasePropertyOverrides in the game's layout, micfix)
    and their 4 textures (zentex: streamed mips' bulk headers as the game's zen loader reads them);
  * WE1021_49 (the Nameless, in centimetres, its string on phy_string_01..03), its skeleton and its Bonamik WE1021_49_BNM.
His and the Nameless's Unity materials are YoungSephirothMaterials_P's; the wing's material and the rest the game's. The
blueprints that wear the meshes are FullyPlayableYoungSephirothDataAssets_P's (they import the meshes by path: checked).
A root bone at a scale other than 1 is flattened into the geometry (flatroot; none expected). Load order: each package
after the ones here it imports.
    build_youngsephiroth_p.py <zen dir: YS13Zen2.utoc + tex/> <YoungSephirothMaterials_P.utoc> <out dir (new)>"""
import gzip, hashlib, os, shutil, sys
import inspect, numpy  # before the tool folders join the path (evil1013/tools has its own inspect.py)
sys.path[:0] = ['/work/iostore', '/work/cs', '/work/swap1012/tools', '/work/weap1012/tools',
                '/work/vincentfix', '/work/evil1013/tools', '/work/custmat',
                '/work/custmat/taken', '/work/aval1016/tools', '/work/safer1015/tools']
from iostore import Toc
from zen import Zen
from hdr import parse_header
import iostore_write as W
import gameids
import zentex
import pack
import micfix
import flatroot

NAME = 'YoungSephiroth_P'
MOUNT = '../../../End/Content/'
YS = '/Game/Character/Player/PC0010_13_Young_Sephiroth/'
NM = '/Game/Character/Weapon/WE1021_49_Nameless/'
MESHES = {YS + 'Model/PC0010_13': 'PC0010_13', NM + 'Model/WE1021_49': 'WE1021_49'}
SKELETONS = {YS + 'Model/PC0010_13_Skeleton': 'PC0010_13_Skeleton', NM + 'Model/WE1021_49_Skeleton': 'WE1021_49_Skeleton'}
GAME_FILES = '/work/gamelist/gamefiles.txt.gz'


def imp(path):
    return (2 << 62) | gameids.objhash(path)


def ids_of_files(files):
    out = set()
    for p in files:
        if not p.endswith(('.uasset', '.umap')) or not p.startswith('../../../'):
            continue
        top, sub = p[len('../../../'):].split('/', 1)
        if sub.startswith('Content/'):
            mount = '/Game/' if top == 'End' else '/' + top + '/'
            out.add(W.package_id(mount + sub[len('Content/'):].rsplit('.', 1)[0]))
        elif '/Content/' in sub:
            plugin = sub.split('/Content/')[0].split('/')[-1]
            out.add(W.package_id('/' + plugin + '/' + sub.split('/Content/', 1)[1].rsplit('.', 1)[0]))
    return out


def main(src, mats_utoc, out):
    assert not os.path.exists(out), out + ' exists (use a new folder)'
    game = ids_of_files(line.rstrip('\n').split('\t')[-1] for line in gzip.open(GAME_FILES, 'rt'))
    mt = Toc(mats_utoc)
    mats = ids_of_files(f for f in (mt.files.get(i) for i in range(mt.entries)) if f)
    t = Toc(os.path.join(src, 'YS13Zen2.utoc'))
    heads = [i for i in range(t.entries) if t.chunk_type(i) == 10]
    assert len(heads) == 1
    _, store = parse_header(t.read(heads[0]))
    chunks, entries, names = [None], [], {}
    for i in range(t.entries):
        kind = t.chunk_type(i)
        if kind == 10:
            continue
        assert kind == 2, ('a chunk this builder does not expect', t.files.get(i), kind)
        data = t.read(i)
        data, notes = micfix.fix_package(data)
        for n in notes:
            print('  material fix: %s %s -> %s, kept %s, left out %s' % (n['export'], n['size'][0], n['size'][1], n['kept'], n['dropped']))
        z = Zen(data)
        pkg = z.mapped(z.name_mapped)
        assert pkg.startswith(YS) or pkg.startswith(NM), pkg
        if pkg in MESHES or pkg in SKELETONS:
            nm = MESHES.get(pkg) or SKELETONS[pkg]
            ex = [e for e in z.exports if e['name'] == nm]
            assert ex, (pkg, [e['name'] for e in z.exports])
            # the root's reference scale
            k = z.exports.index(ex[0])
            start, size = z.bundle_positions()[k]
            body = data[start:start + size]
            p, n = flatroot._find_refskel(z.names, body)
            assert p is not None, ('no reference skeleton in', nm)
            _, rot, tr, sc = flatroot._root(body, p, n)
            if abs(sc[0] - 1.0) > 1e-4:
                data, rep = flatroot.flatten_package(data, nm, 'mesh' if pkg in MESHES else 'skeleton')
                print('  root flattened: %s %s scale %.6f -> 1' % (nm, rep['root_name'], rep['root_scale']))
                z = Zen(data)
            else:
                print('  %s: %d bones, root at scale %.4f (left as it is)' % (nm, n, sc[0]))
        pid = W.package_id(pkg)
        assert t.chunk_id64(i) == pid and pid not in game, pkg
        se = store[pid]
        chunks.append(dict(id64=pid, type=2, data=data, path=pkg[len('/Game/'):] + '.uasset'))
        entries.append(dict(id=pid, size=se['size'], export_count=se['export_count'], export_bundle_count=se['export_bundle_count'],
                            load_order=0, imports=list(se['imports'])))
        names[pid] = pkg
    assert set(MESHES) | set(SKELETONS) <= set(names.values()), sorted(names.values())
    # the meshes' exports: the blueprints import them by path
    for pkg, nm in MESHES.items():
        z = Zen([c for c in chunks[1:] if c['id64'] == W.package_id(pkg)][0]['data'])
        g = [e['global_import'] for e in z.exports if e['name'] == nm][0]
        assert g == imp(pkg + '.' + nm), (pkg, hex(g))
    # the textures
    for dp, dn, fn in os.walk(os.path.join(src, 'tex')):
        for f in sorted(fn):
            if not f.endswith('.uasset'):
                continue
            ua = open(os.path.join(dp, f), 'rb').read()
            ubp = os.path.join(dp, f[:-7] + '.ubulk')
            ub = open(ubp, 'rb').read() if os.path.exists(ubp) else b''
            data, bulk, rep = zentex.convert(ua, ub)
            z = Zen(data)
            pkg = z.mapped(z.name_mapped)
            assert pkg.startswith(YS + 'Texture/'), pkg
            pid = W.package_id(pkg)
            assert pid not in game
            chunks.append(dict(id64=pid, type=2, data=data, path=pkg[len('/Game/'):] + '.uasset'))
            if bulk:
                chunks.append(dict(id64=pid, type=3, data=bulk, path=pkg[len('/Game/'):] + '.ubulk'))
            imports = [g for g, arcs in zentex.matcore.graph_packages(data)]
            entries.append(dict(id=pid, size=len(data), export_count=len(z.exports), export_bundle_count=pack._bundle_count(z),
                                load_order=0, imports=imports))
            names[pid] = pkg
    ours = {e['id']: e for e in entries}
    order = {}

    def lo(pid, stack=()):
        if pid in order:
            return order[pid]
        assert pid not in stack, 'import cycle'
        deps = [lo(i, stack + (pid,)) for i in ours[pid]['imports'] if i in ours]
        order[pid] = 1 + max(deps or [0])
        return order[pid]
    for e in entries:
        e['load_order'] = 1000 + lo(e['id'])
    here = set(ours)
    unknown = sorted({'%016x (imported by %s)' % (i, names[e['id']]) for e in entries for i in e['imports'] if i not in here and i not in game and i not in mats})
    assert not unknown, unknown
    from_mats = sorted({names[e['id']].rsplit('/', 1)[1] for e in entries for i in e['imports'] if i in mats})
    cid = W.container_id_from_name(NAME)
    chunks[0] = dict(id64=cid, type=10, data=W.container_header(cid, entries), path=None)
    os.makedirs(out)
    base = os.path.join(out, NAME)
    W.write_container(base, NAME, chunks, mount=MOUNT)
    shutil.copy(os.path.join(src, 'YS13Zen2.pak'), base + '.pak')
    back = Toc(base + '.utoc')
    assert back.container_id == cid and back.entries == len(chunks)
    for i, c in enumerate(chunks):
        assert back.read(i) == c['data'] and back.chunk_id64(i) == c['id64'] and back.chunk_type(i) == c['type']
        if c['path']:
            assert back.files.get(i) == MOUNT + c['path'], back.files.get(i)
    cid2, ents = parse_header(back.read(0))
    assert cid2 == cid and set(ents) == here
    for e in entries:
        b = ents[e['id']]
        for k in ('size', 'export_count', 'export_bundle_count', 'load_order', 'imports'):
            assert b[k] == e[k], (k, names[e['id']])
    print('%s: %d packages (%s), %d bulk chunks; every import here, in the game or in YoungSephirothMaterials_P (imported from it by %s)' % (
        NAME, len(entries), ', '.join(sorted(n.rsplit('/', 1)[1] for n in names.values())), sum(1 for c in chunks[1:] if c['type'] == 3),
        ', '.join(from_mats)))
    for f in sorted(os.listdir(out)):
        p = os.path.join(out, f)
        print('  %-30s %9d %s' % (f, os.path.getsize(p), hashlib.md5(open(p, 'rb').read()).hexdigest()))


if __name__ == '__main__':
    main(*sys.argv[1:4])
