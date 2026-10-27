"""KH2Sephiroth_P: the user's KH2 Sephiroth model as a package of its own, two ways in one:
  * /Game/Character/Player/PC0010_00_Sephiroth_Standard/Model/PC0010_00: the KH2 model (from PC0010_10KH2.fbx, the
    transformed Sephiroth's bones and wing: slot "Wing") in the place of Sephiroth's own model, everywhere it shows;
  * /Game/Character/Player/PC0010_14_Sephiroth_KH2/Model/PC0010_14: the same model under its own name, the one Young
    Sephiroth's KH2 form turns him into (a form's model: his own model stays his elsewhere);
  * the KH2 material instances (MaterialsKH2: their BasePropertyOverrides in the game's layout, micfix) and textures
    (TexturesKH2: zentex) they use. Everything else they use is the game's (checked against the game's file list).
A root bone at a scale other than 1 is flattened into the geometry (flatroot). Load orders: the model in Sephiroth's
place keeps the game's; the rest go after what they import here.
    build_kh2sephiroth_p.py <zen dir: KH2Zen.utoc + tex/> <out dir (new)>"""
import gzip, hashlib, os, shutil, sys
import inspect, numpy  # before the tool folders join the path
sys.path[:0] = ['/work/iostore', '/work/cs', '/work/swap1012/tools', '/work/weap1012/tools',
                '/work/vincentfix', '/work/evil1013/tools', '/work/custmat',
                '/work/custmat/taken', '/work/aval1016/tools', '/work/safer1015/tools']
from iostore import Toc
from zen import Zen
from hdr import parse_header
import iostore_write as W
import zentex
import pack
import micfix
import flatroot

NAME = 'KH2Sephiroth_P'
MOUNT = '../../../End/Content/'
STD = '/Game/Character/Player/PC0010_00_Sephiroth_Standard/'
COPY = '/Game/Character/Player/PC0010_14_Sephiroth_KH2/'
MESHES = {STD + 'Model/PC0010_00': 'PC0010_00', COPY + 'Model/PC0010_14': 'PC0010_14'}
REPLACES = {STD + 'Model/PC0010_00'}
OWN = (STD + 'MaterialsKH2/', STD + 'TexturesKH2/', COPY)
GAME_FILES = '/work/gamelist/gamefiles.txt.gz'
RETAIL_HEADER = '/work/retailhdr/pakchunk4_header.bin'


def game_ids():
    out = set()
    for line in gzip.open(GAME_FILES, 'rt'):
        p = line.rstrip('\n').split('\t')[-1]
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


def main(src, out):
    assert not os.path.exists(out), out + ' exists (use a new folder)'
    game = game_ids()
    _, retail = parse_header(open(RETAIL_HEADER, 'rb').read())
    t = Toc(os.path.join(src, 'KH2Zen.utoc'))
    heads = [i for i in range(t.entries) if t.chunk_type(i) == 10]
    _, store = parse_header(t.read(heads[0]))
    chunks, entries, names = [None], [], {}
    for i in range(t.entries):
        kind = t.chunk_type(i)
        if kind == 10:
            continue
        assert kind == 2, (t.files.get(i), kind)
        data = t.read(i)
        data, notes = micfix.fix_package(data)
        for n in notes:
            print('  material fix: %s %s -> %s, kept %s, left out %s' % (n['export'], n['size'][0], n['size'][1], n['kept'], n['dropped']))
        z = Zen(data)
        pkg = z.mapped(z.name_mapped)
        assert pkg in MESHES or pkg.startswith(OWN), pkg
        if pkg in MESHES:
            nm = MESHES[pkg]
            k = [j for j, e in enumerate(z.exports) if e['name'] == nm][0]
            start, size = z.bundle_positions()[k]
            body = data[start:start + size]
            p, n = flatroot._find_refskel(z.names, body)
            assert p is not None, nm
            _, rot, tr, sc = flatroot._root(body, p, n)
            if abs(sc[0] - 1.0) > 1e-4:
                data, rep = flatroot.flatten_package(data, nm, 'mesh')
                print('  root flattened: %s %s scale %.6f -> 1' % (nm, rep['root_name'], rep['root_scale']))
                z = Zen(data)
            else:
                print('  %s: %d bones, root at scale %.4f' % (nm, n, sc[0]))
        pid = W.package_id(pkg)
        assert t.chunk_id64(i) == pid
        assert (pid in game) == (pkg in REPLACES), ('in the game' if pid in game else 'not in the game', pkg)
        se = store[pid]
        chunks.append(dict(id64=pid, type=2, data=data, path=pkg[len('/Game/'):] + '.uasset'))
        entries.append(dict(id=pid, size=se['size'], export_count=se['export_count'], export_bundle_count=se['export_bundle_count'],
                            load_order=retail[pid]['load_order'] if pkg in REPLACES else 0, imports=list(se['imports'])))
        names[pid] = pkg
    assert set(MESHES) <= set(names.values())
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
            assert pkg.startswith(OWN), pkg
            pid = W.package_id(pkg)
            assert pid not in game, pkg
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
        if not e['load_order']:
            e['load_order'] = 1000 + lo(e['id'])
    here = set(ours)
    unknown = sorted({'%016x (imported by %s)' % (i, names[e['id']]) for e in entries for i in e['imports'] if i not in here and i not in game})
    assert not unknown, unknown
    cid = W.container_id_from_name(NAME)
    chunks[0] = dict(id64=cid, type=10, data=W.container_header(cid, entries), path=None)
    os.makedirs(out)
    base = os.path.join(out, NAME)
    W.write_container(base, NAME, chunks, mount=MOUNT)
    shutil.copy(os.path.join(src, 'KH2Zen.pak'), base + '.pak')
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
    print('%s: %d packages (%s), %d bulk chunks; every import here or in the game' % (
        NAME, len(entries), ', '.join(sorted(n.rsplit('/', 1)[1] for n in names.values())), sum(1 for c in chunks[1:] if c['type'] == 3)))
    for f in sorted(os.listdir(out)):
        p = os.path.join(out, f)
        print('  %-30s %9d %s' % (f, os.path.getsize(p), hashlib.md5(open(p, 'rb').read()).hexdigest()))


if __name__ == '__main__':
    main(*sys.argv[1:3])
