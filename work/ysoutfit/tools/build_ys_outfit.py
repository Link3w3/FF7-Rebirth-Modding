"""The Young Sephiroth outfit, an optional pak: YoungSephirothOutfit_P holds
  * the user's PC0010_10 (PC0010_10_Young_Sephiroth_Outfit_Transformed: Young Sephiroth's clothes and hair on Sephiroth's
    skeleton with the transformed Sephiroth's wing, material slot PC0010_10_Wing) and its skeleton PC0010_10_Skeleton
    (Sephiroth's bones, same parents, + Young Sephiroth's 103 physics bones), its materials CH049_001_Body / _Hair (the
    game's RMI_Surface families with his textures), their 8 textures and its Bonamik PC0010_10_YS_BNM (v3), cooked by the
    End editor (Cook For Game): the textures converted with zentex (streamed mips' bulk headers as the game's zen loader
    reads them), the rest by retoc, the material instances' BasePropertyOverrides rewritten in the game's layout
    (micfix: the game crashes reading the editor's stock layout), the root bone's x1.4 import scale flattened into the
    mesh's vertices (flatroot: the game holds a player's root at its reference pose);
  * Sephiroth's character blueprint (PC0010_00_Sephiroth_Standard: the one every Cloud row of the Fully Playable
    Sephiroth spawns) with its mesh import pointing at PC0010_10 instead of PC0010_00; every other byte is the retail
    blueprint's (as AvalancheSephirothOutfit_P does).
Everything the packages import is in it or in the game. Load order: each package after the ones here it imports.
    build_ys_outfit.py <in dir: YSOutfitZen.utoc + tex/Texture/*.uasset(.ubulk)> <out dir (new)>"""
import gzip, hashlib, os, shutil, struct, sys
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
import build_outfit as AV
import micfix
import flatroot

NAME = 'YoungSephirothOutfit_P'
MOUNT = '../../../End/Content/'
FOLDER = '/Game/Character/Player/PC0010_10_Young_Sephiroth_Outfit_Transformed/'
MESH = FOLDER + 'Model/PC0010_10'
SKELETON = FOLDER + 'Model/PC0010_10_Skeleton'
BP = AV.BP
GAME_FILES = '/work/gamelist/gamefiles.txt.gz'
NULL = 0xFFFFFFFFFFFFFFFF


def game_package_ids():
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
    game = game_package_ids()
    # 1. retoc's packages (the mesh, its skeleton, materials, Bonamik)
    t = Toc(os.path.join(src, 'YSOutfitZen.utoc'))
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
        # material instances: the editor's BasePropertyOverrides in the game's layout (the game crashes on the editor's)
        data, notes = micfix.fix_package(data)
        for n in notes:
            print('  material fix: %s %s -> %s, kept %s, left out %s' % (n['export'], n['size'][0], n['size'][1], n['kept'], n['dropped']))
        z = Zen(data)
        pkg = z.mapped(z.name_mapped)
        assert pkg.startswith(FOLDER), pkg
        # the root bone's reference scale (Trans x1.4 from the import) moved into the vertices: the game holds a
        # player's root at its reference pose, so a scaled root draws the whole character that much bigger
        if pkg in (MESH, SKELETON):
            data, rep = flatroot.flatten_package(data, pkg.rsplit('/', 1)[1], 'mesh' if pkg == MESH else 'skeleton')
            print('  root flattened: %s %s scale %.6f -> 1%s' % (pkg.rsplit('/', 1)[1], rep['root_name'], rep['root_scale'],
                  (', bounds %s -> %s' % (rep['bounds_before'], rep['bounds_after'])) if 'bounds_after' in rep else ''))
            z = Zen(data)
        pid = W.package_id(pkg)
        assert t.chunk_id64(i) == pid and pid not in game, pkg
        se = store[pid]
        chunks.append(dict(id64=pid, type=2, data=data, path=pkg[len('/Game/'):] + '.uasset'))
        entries.append(dict(id=pid, size=se['size'], export_count=se['export_count'], export_bundle_count=se['export_bundle_count'],
                            load_order=0, imports=list(se['imports'])))
        names[pid] = pkg
    assert {MESH, SKELETON} <= set(names.values()), sorted(names.values())
    # 2. the textures (zentex)
    tex_dir = os.path.join(src, 'tex', 'Texture')
    for fn in sorted(os.listdir(tex_dir)):
        if not fn.endswith('.uasset'):
            continue
        ua = open(os.path.join(tex_dir, fn), 'rb').read()
        ubp = os.path.join(tex_dir, fn[:-7] + '.ubulk')
        ub = open(ubp, 'rb').read() if os.path.exists(ubp) else b''
        data, bulk, rep = zentex.convert(ua, ub)
        z = Zen(data)
        pkg = z.mapped(z.name_mapped)
        assert pkg == FOLDER + 'Texture/' + fn[:-7], pkg
        pid = W.package_id(pkg)
        assert pid not in game
        chunks.append(dict(id64=pid, type=2, data=data, path=pkg[len('/Game/'):] + '.uasset'))
        if bulk:
            chunks.append(dict(id64=pid, type=3, data=bulk, path=pkg[len('/Game/'):] + '.ubulk'))
        imports = [g for g, arcs in zentex.matcore.graph_packages(data)]
        entries.append(dict(id=pid, size=len(data), export_count=len(z.exports), export_bundle_count=pack._bundle_count(z),
                            load_order=0, imports=imports))
        names[pid] = pkg
    # 3. Sephiroth's blueprint wearing the outfit
    mz = Zen([c for c in chunks[1:] if c['id64'] == W.package_id(MESH) and c['type'] == 2][0]['data'])
    mesh_import = [e['global_import'] for e in mz.exports if e['name'] == 'PC0010_10'][0]
    assert mesh_import == AV.imp(MESH + '.PC0010_10'), 'the mesh export index is not its path\'s'
    bp, old_pid = AV.blueprint(mesh_import, W.package_id(MESH))
    _, retail = parse_header(open(AV.RETAIL_HEADER, 'rb').read())
    bp_pid = W.package_id(BP)
    re = retail[bp_pid]
    bp_imports = [W.package_id(MESH) if x == old_pid else x for x in re['imports']]
    # 4. load orders: each package after the packages here it imports; the blueprint keeps the game's
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
    chunks.append(dict(id64=bp_pid, type=2, data=bp, path=BP[len('/Game/'):] + '.uasset'))
    entries.append(dict(id=bp_pid, size=re['size'], export_count=re['export_count'], export_bundle_count=re['export_bundle_count'],
                        load_order=re['load_order'], imports=bp_imports))
    # 5. every package any of them imports: here or the game's
    here = {e['id'] for e in entries}
    unknown = sorted({'%016x (imported by %s)' % (i, names.get(e['id'], BP)) for e in entries for i in e['imports'] if i not in here and i not in game})
    assert not unknown, unknown
    assert W.package_id(SKELETON) in ours[W.package_id(MESH)]['imports']
    # 6. the container
    cid = W.container_id_from_name(NAME)
    chunks[0] = dict(id64=cid, type=10, data=W.container_header(cid, entries), path=None)
    os.makedirs(out)
    base = os.path.join(out, NAME)
    W.write_container(base, NAME, chunks, mount=MOUNT)
    shutil.copy(os.path.join(src, 'YSOutfitZen.pak'), base + '.pak')
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
            assert b[k] == e[k], (k, names.get(e['id'], BP))
    print('%s: %d packages (%s), %d bulk chunks; every import here or in the game' % (
        NAME, len(entries), ', '.join(sorted(n.rsplit('/', 1)[1] for n in names.values())) + ', Sephiroth\'s blueprint',
        sum(1 for c in chunks[1:] if c['type'] == 3)))
    for f in sorted(os.listdir(out)):
        p = os.path.join(out, f)
        print('  %-30s %9d %s' % (f, os.path.getsize(p), hashlib.md5(open(p, 'rb').read()).hexdigest()))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
