"""SoraOverCloud_P: Cloud's blueprints with Sora's models, at their own paths (so every CharaSpec pack, row and cutscene
ID table that names them stays as the game has it):
  * BluePrint/Character/Player/PC0000_00_Cloud_Standard: its SkeletalMesh import -> Sora's mesh
    (/Game/Character/Player/PC0000_00_Sora_KH2/Model/PC0000_00_S); the wet one (PC0000_22) is a child of it;
  * BluePrint/Character/Weapon/WE0000_* (the Buster Sword and Cloud's 12 other weapons): their mesh import -> the
    Kingdom Key (/Game/Character/Weapon/WE0000_00_Kingdom_Key/Model/WE0000_00).
  * BluePrint/Character/Player/PC0000_04 ... PC0000_25 (Cloud's other outfits, VARIANTS): the Cloud model each one's
    CharacterMesh0 names -> Sora's mesh, and the models of the cutscene blood overlays (PC0000_13/14/15/25: an
    EndSyncPoseSkeletalMeshComponent posed from the body by bone names, on Cloud's skeleton) dropped (None); the outfits
    that name no model (PC0000_16, 21, 22, 24) have the player's CharacterMesh0 (Sora's) and stay the game's.
Each package is the retail one with only that import's global index and its graph entry's package id changed (the
graph sorted again by package id, as the cooker writes it); the header entries are the retail ones with that package in
their imported packages instead. The player's blueprint also drops the game's human facial control rig (DROP: its
import null, so its FacialControlRig is None; SORA_FCR=1 puts Sora's PC0000_00_S_FCR, in SoraFace_P, in its place
instead: see SWAPS). Read back chunk by chunk.

    build_sora_bps.py <out dir>
"""
import hashlib
import os
import struct
import sys

sys.path[:0] = ['/work/iostore', '/work/cs', '/work/weap1012/tools',
                '/work/swap1012/tools']
from iostore import Toc                      # noqa: E402
from zen import Zen                          # noqa: E402
import iostore_write as W                    # noqa: E402
import hdr                                   # noqa: E402
import gameids                               # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
NAME = 'SoraOverCloud_P'
MOUNT = '../../../End/Content/'
NULL = 0xFFFFFFFFFFFFFFFF
HEADERS = {'pakchunk4': '/work/retailhdr/pakchunk4_header.bin',
           'pakchunk10': '/work/retailhdr/pakchunk10_header.bin'}
SORA_ASSETS = os.path.join(HERE, 'out_assets_r3', 'SoraAssets_P.utoc')
SORA_FACE = '/work/soraface/out_face3/SoraFace_P.utoc'
SORA_MESH = '/Game/Character/Player/PC0000_00_Sora_KH2/Model/PC0000_00_S'
KEYBLADE = '/Game/Character/Weapon/WE0000_00_Kingdom_Key/Model/WE0000_00'
PLAYER = ['PC0000_00_Cloud_Standard']
WEAPONS = ['WE0000_00_Cloud_BusterSword', 'WE0000_01_Cloud_IronBlade', 'WE0000_02_Cloud_HardBreaker',
           'WE0000_03_Cloud_MythrilSaber', 'WE0000_04_Cloud_TwoPair', 'WE0000_05_Cloud_NailBat',
           'WE0000_11_Cloud_END2Weapon1', 'WE0000_12_Cloud_END2Weapon2', 'WE0000_13_Cloud_END2Weapon3',
           'WE0000_14_Cloud_END2Weapon4', 'WE0000_15_Cloud_END2Weapon5', 'WE0000_16_Cloud_END2Weapon6',
           'WE0000_17_Cloud_Umbrella']



def model(folder):
    """the model package of a character folder: /Game/Character/Player/PC0000_04_Cloud_ZackCostume/Model/PC0000_04"""
    return '/Game/Character/Player/%s/Model/%s' % (folder, folder[:9])


# Cloud's other outfits (each a child of PC0000_00_Cloud_Standard's blueprint, but PC0000_17, which names Cloud's
# animation blueprint itself). 'swap': the model its CharacterMesh0 names -> Sora's; 'null': the models of its cutscene
# overlays (blood on the cheek, palm or back of the hand: EndSyncPoseSkeletalMeshComponent, Cloud's skeleton, posed from
# the body by bone names, which Sora's body does not have) -> None. Every model a blueprint imports is in one of the two.
# Cloud's animation blueprint names Cloud's lip maps (Sora's, in SoraFace_P): a Cloud model left in an outfit would crash
# the game when he speaks (the lip sync looks up the lip map's bones, Sora's, on Cloud's skeleton).
VARIANTS = {
    'PC0000_04_Cloud_ZackCostume': dict(swap=model('PC0000_04_Cloud_ZackCostume')),
    'PC0000_06_Cloud_Soldier': dict(swap=model('PC0000_06_Cloud_Soldier')),
    'PC0000_07_Cloud_SoldierSenior': dict(swap=model('PC0000_07_Cloud_SoldierSenior')),
    'PC0000_08_Cloud_SoldierNoHelmet': dict(swap=model('PC0000_08_Cloud_SoldierNoHelmet')),
    'PC0000_09_Cloud_CostaClothing': dict(swap=model('PC0000_09_Cloud_CostaClothing')),
    'PC0000_10_Cloud_CostaClothing2': dict(swap=model('PC0000_10_Cloud_CostaClothing2')),
    'PC0000_11_Cloud_Loveless': dict(swap=model('PC0000_11_Cloud_Loveless')),
    'PC0000_12_Cloud_ZackCostumeDirty': dict(swap=model('PC0000_12_Cloud_ZackCostumeDirty')),
    'PC0000_13_Cloud_CutBroodCheek': dict(null=[model('PC0000_13_Cloud_CutBroodCheek')]),
    'PC0000_14_Cloud_CutBroodPalm': dict(swap=model('PC0000_12_Cloud_ZackCostumeDirty'),
                                         null=[model('PC0000_14_Cloud_CutBroodPalm')]),
    'PC0000_15_Cloud_CutBroodBackOfHand': dict(null=[model('PC0000_15_Cloud_CutBroodBackOfHand')]),
    'PC0000_17_Cloud_LovelessNoMask': dict(swap=model('PC0000_17_Cloud_LovelessNoMask')),
    'PC0000_18_Cloud_ZackCostumeAge21': dict(swap=model('PC0000_18_Cloud_ZackCostumeAge21')),
    'PC0000_19_Cloud_ZackCostumeDirtyAge21': dict(swap=model('PC0000_19_Cloud_ZackCostumeDirtyAge21')),
    'PC0000_20_Cloud_LovelessHologram': dict(swap=model('PC0000_11_Cloud_Loveless')),
    'PC0000_23_Cloud_ZackCostumeWet': dict(swap=model('PC0000_04_Cloud_ZackCostume')),
    'PC0000_25_Cloud_CutBroodCheek2': dict(null=[model('PC0000_25_Cloud_CutBroodCheek2')]),
}
if os.environ.get('SORA_VARIANTS') == '0':
    VARIANTS = {}

PKG, OBJ = gameids.load()


def imp(path):
    return (2 << 62) | gameids.objhash(path)


def graph(d, z):
    o = z.graph_off
    n, = struct.unpack_from('<i', d, o); o += 4
    out = []
    for _ in range(n):
        pid, na = struct.unpack_from('<Qi', d, o)
        out.append((pid, d[o + 8:o + 12 + 8 * na])); o += 12 + 8 * na
    assert o == z.graph_off + z.graph_size
    return out


def retail_entries():
    out = {}
    for c, p in HEADERS.items():
        _, ents = hdr.parse_header(open(p, 'rb').read())
        for pid, e in ents.items():
            out[pid] = (c, e)
    return out


def our_entries():
    ents = {}
    for utoc in (SORA_ASSETS, SORA_FACE):
        t = Toc(utoc)
        head = [i for i in range(t.entries) if t.chunk_type(i) == 10][0]
        _, e = hdr.parse_header(t.read(head))
        assert not set(e) & set(ents), utoc
        ents.update(e)
    return ents


def mesh_swap(data, old_mesh, new_mesh, label):
    """The package with its import of old_mesh (package path) -> new_mesh, the graph listing new_mesh's package."""
    z = Zen(data)
    old_obj = imp(old_mesh + '.' + old_mesh.rsplit('/', 1)[1])
    new_obj = imp(new_mesh + '.' + new_mesh.rsplit('/', 1)[1])
    old_pid, new_pid = W.package_id(old_mesh), W.package_id(new_mesh)
    # every import of the old mesh's package is its mesh object
    of_pkg = [i for i, v in enumerate(z.imports) if v != NULL and (OBJ.get(v & ~(3 << 62)) or '').startswith(old_mesh + '.')]
    hits = [i for i, v in enumerate(z.imports) if v == old_obj]
    assert len(hits) == 1 and of_pkg == hits, (label, hits, of_pkg)
    d = bytearray(data)
    struct.pack_into('<Q', d, z.imp_off + 8 * hits[0], new_obj)
    g = graph(data, z)
    assert sum(1 for pid, _ in g if pid == old_pid) == 1, label
    assert not any(pid == new_pid for pid, _ in g), label
    g = sorted([(new_pid if pid == old_pid else pid, rest) for pid, rest in g], key=lambda x: x[0])
    gb = bytearray(struct.pack('<i', len(g)))
    for pid, rest in g:
        gb += struct.pack('<Q', pid) + rest
    assert len(gb) == z.graph_size
    d[z.graph_off:z.graph_off + z.graph_size] = gb
    out = bytes(d)
    # checks: the same package but for that import and the graph's order
    c = Zen(out)
    assert c.names == z.names and [e['name'] for e in c.exports] == [e['name'] for e in z.exports], label
    assert c.imports == [new_obj if i == hits[0] else v for i, v in enumerate(z.imports)], label
    assert out[c.header_end:] == data[z.header_end:], label
    assert out[:z.imp_off] == data[:z.imp_off] and out[z.exp_off:z.graph_off] == data[z.exp_off:z.graph_off], label
    arcs_old = [rest for pid, rest in graph(data, z) if pid == old_pid]
    arcs_new = [rest for pid, rest in graph(out, c) if pid == new_pid]
    assert arcs_old == arcs_new, label
    return out, old_pid, new_pid, arcs_new[0]


# Packages whose imports a blueprint drops (each import of them becomes null: the property naming it is None):
#   CommonHuman00_FCR  the game's human facial control rig. Whatever rig the player's blueprint names, the game's control
#                      rig (CommonHuman00_Rig, in Cloud's animation blueprint) does its eye, lid and brow work on the bones of
#                      its own hierarchy (Cloud's) that it finds on the mesh by name: on Sora it finds L_eye/R_eye (names
#                      compare without case) but none of his head or face base, and dragged his eyes down to his feet
#                      (2026-10-19, with Sora's own rig in, SORA_FCR=1 below); with the human rig in, a voice crashed the
#                      game and the matching bones (L_eye, R_brow_a, ...) were bent out of shape.
DROP = {'PC0000_00_Cloud_Standard': ['/Game/Character/Common/ControlRig/CommonHuman00_FCR']}
# Imports a blueprint has swapped, as for its mesh (old package -> new package, the import being the package's object):
#   CommonHuman00_FCR -> PC0000_00_S_FCR  the game's human facial control rig names face bones of Cloud's face (its
#                      defaults in the game: L_Eye, L_Ulid_A, C_Forehead, ...); Sora's KH3 face has none of most of them
#                      (a voice crashed the game looking one up while it was in) and the ones that match by name (L_eye,
#                      R_brow_a, ...) were bent out of shape. Sora's rig has the human rig's settings with his face's bones,
#                      and his facial set (SoraFace_P: Facial00) the poses and blend spaces it plays.
SWAPS = {'PC0000_00_Cloud_Standard': [('/Game/Character/Common/ControlRig/CommonHuman00_FCR',
                                       '/Game/Character/Player/PC0000_00_Sora_KH2/Model/PC0000_00_S_FCR')]} \
    if os.environ.get('SORA_FCR') == '1' else {}
if SWAPS:
    DROP = {}


def null_imports(data, package, label):
    """The package with every import of `package` null (the properties naming them load as None). The graph and the
    header entry keep listing the package: it still loads first, unused."""
    z = Zen(data)
    hits = [i for i, v in enumerate(z.imports) if v != NULL and (OBJ.get(v & ~(3 << 62)) or '').startswith(package + '.')]
    assert hits, (label, package)
    d = bytearray(data)
    for i in hits:
        struct.pack_into('<Q', d, z.imp_off + 8 * i, NULL)
    out = bytes(d)
    c = Zen(out)
    assert c.imports == [NULL if i in hits else v for i, v in enumerate(z.imports)], label
    assert out[c.imp_off + 8 * len(z.imports):] == data[z.imp_off + 8 * len(z.imports):] and out[:z.imp_off] == data[:z.imp_off], label
    return out, hits


def main(out_dir):
    retail = retail_entries()
    ours = our_entries()
    chunks, entries, report = [None], [], []
    for name in PLAYER + list(VARIANTS) + WEAPONS:
        folder = 'Weapon' if name in WEAPONS else 'Player'
        pkg = '/Game/BluePrint/Character/%s/%s' % (folder, name)
        pid = W.package_id(pkg)
        data = open(os.path.join(HERE, 'retailbp', name + '.uasset'), 'rb').read()
        chunk_name, e = retail[pid]
        assert e['size'] == len(data) and e['export_count'] == len(Zen(data).exports), name
        models = [PKG[i] for i in e['imports'] if PKG.get(i, '').startswith('/Game/Character/') and '/Model/' in PKG[i]]
        out, swapped, dropped = data, [], []
        if name in VARIANTS:
            plan = VARIANTS[name]
            nulls = plan.get('null', [])
            assert sorted(models) == sorted(([plan['swap']] if 'swap' in plan else []) + nulls), (name, models, plan)
            assert not any('/ControlRig/' in PKG.get(i, '') for i in e['imports']), name
            old_mesh = plan.get('swap')
            new_mesh = SORA_MESH if old_mesh else None
            for package in nulls:
                out, hits = null_imports(out, package, name)
                assert len(hits) == 1, (name, package, hits)
                dropped.append('%s overlay None (import %s)' % (package.rsplit('/', 1)[1], ', '.join(map(str, hits))))
        else:
            meshes = [m for m in models if '/PC0099_' not in m]      # (Cloud's toad transformation keeps its own mesh)
            assert len(meshes) == 1, (name, meshes)
            old_mesh = meshes[0]
            new_mesh = SORA_MESH if name in PLAYER else KEYBLADE
        if old_mesh:
            out, old_pid, new_pid, arcs = mesh_swap(out, old_mesh, new_mesh, name)
            swapped.append((old_pid, new_pid, arcs))
        for old_pkg, new_pkg in SWAPS.get(name, []):
            out, o2, n2, a2 = mesh_swap(out, old_pkg, new_pkg, name)
            swapped.append((o2, n2, a2))
        for package in DROP.get(name, []):
            out, hits = null_imports(out, package, name)
            dropped.append('%s (import %s)' % (package.rsplit('/', 1)[1], ', '.join(map(str, hits))))
        # the arcs name export bundles of each swapped-in package: the new one has as many
        for o2, n2, a2 in swapped:
            na, = struct.unpack_from('<i', a2, 0)
            froms = struct.unpack_from('<%di' % (2 * na), a2, 4)[0::2] if na else ()
            assert all(f < ours[n2]['export_bundle_count'] for f in froms), (name, froms, ours[n2]['export_bundle_count'])
        swap_pids = {o2: n2 for o2, n2, a2 in swapped}
        imports = [swap_pids.get(x, x) for x in e['imports']]
        if list(e['imports']) == sorted(e['imports']):
            imports = sorted(imports)
        assert len(set(imports)) == len(imports)
        z = Zen(out)
        assert {p for p, _ in graph(out, z)} <= set(imports), name
        chunks.append(dict(id64=pid, type=2, data=out, path='BluePrint/Character/%s/%s.uasset' % (folder, name)))
        entries.append(dict(id=pid, size=e['size'], export_count=e['export_count'], export_bundle_count=e['export_bundle_count'],
                            load_order=e['load_order'], imports=imports))
        report.append((name, chunk_name, old_mesh or '(no mesh)', new_mesh or '(parent\'s)', len(out), dropped + ['swap %s -> %s' % (a.rsplit('/', 1)[1], b.rsplit('/', 1)[1]) for a, b in SWAPS.get(name, [])]))
    cid = W.container_id_from_name(NAME)
    chunks[0] = dict(id64=cid, type=10, data=W.container_header(cid, entries), path=None)
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.join(out_dir, NAME)
    W.write_container(base, NAME, chunks, mount=MOUNT)
    open(base + '.pak', 'wb').write(open('/work/soradata/out_assets/SoraAssets_P.pak', 'rb').read())
    back = Toc(base + '.utoc')
    assert back.container_id == cid and back.entries == len(chunks)
    _, ents = hdr.parse_header(back.read(0))
    by = {e['id']: e for e in entries}
    for i in range(1, back.entries):
        c = chunks[i]
        assert back.read(i) == c['data'] and back.chunk_id64(i) == c['id64'] and back.chunk_type(i) == c['type'], c['path']
        assert back.files.get(i) == MOUNT + c['path'], back.files.get(i)
        b, e = ents[c['id64']], by[c['id64']]
        assert (b['size'], b['export_count'], b['export_bundle_count'], b['load_order'], list(b['imports'])) == \
               (e['size'], e['export_count'], e['export_bundle_count'], e['load_order'], e['imports']), c['path']
    for r in report:
        print('%-38s (%s) %s -> %s  %d bytes%s' % (r[0], r[1], r[2].rsplit('/', 1)[-1], r[3], r[4], ('; ' + '; '.join(r[5])) if r[5] else ''))
    for ext in ('utoc', 'ucas', 'pak'):
        p = base + '.' + ext
        print('%-24s %8d %s' % (os.path.basename(p), os.path.getsize(p), hashlib.md5(open(p, 'rb').read()).hexdigest()))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'out_bps'))
