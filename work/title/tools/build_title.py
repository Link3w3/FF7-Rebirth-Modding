"""Sephiroth title screen: the Buster Sword planted on the title screen becomes the Masamune (by default the bloody
one, WE1021_01 "MasamuneBrood"), and the title music (Prelude) becomes One-Winged Angel - Reborn. One small IoStore
container for ~mods with three of the title's own packages (pakchunk7), each patched in place:
  * Layout/0005-TITLB_Layout_010_Terrain_Strip.umap: the sword actor (WE0000_00_2, name and tag kept) shows the
    Masamune instead of WE0000_00 (the Buster Sword): its SkeletalMesh import, the package in the export bundle graph
    and in the header entry. Same place and angle (the swords have the grip at the origin and the blade along +X, so
    the same length of blade shows above the ground; WE1021_00 and WE1021_01 share one skeleton, 216.8 cm to the tip).
  * 0005-TITLB_BGM.umap: the asset actor that keeps the title's music loaded holds the new music's bank instead of
    bgm_prelude (import, graph, header entry).
  * DataObject/Field/0005-TITLB/Action: act005_BGMTitle (PlayBGM) plays the new BGMList row instead of bgm_prelude.
  * Layout/0005-TITLB_Layout_010_Effect.umap: Sephiroth's black feathers fall over the title. The effect actor that
    showed the title's green motes (FX_0005-TITLB_Ptc_01_01, at the sword's foot; the game shows it as the title
    starts) plays a looping black-feather system of the last chapter's cutscenes instead (import, graph, header
    entry). The smoke actor stays as it is.
Nothing else of the game is touched; the base game's packages stay as they are (removing the files undoes it).

    build_title.py <out dir> [BGMList row = bgm_Foree2_012_08] [sword: brood (default) | clean]
                   [feathers: 8510_01 (default) | 8510_02 | 8510_03 | 8312_02 | 1241_02 | none]

bgm_Foree2_012_08 is Section8 of the final battle's bank: the music the game starts after EV_FOREE_8710 ("Cloud layer:
the last battle with Sephiroth"), right after Section7 (82.5 s, the cutscene's "Let's End This - Together"); 21.6 s of
intro, then a 164.3 s loop (the soundtrack's 5:53 "One-Winged Angel - Reborn" is the intro and the loop twice)."""
import hashlib, os, shutil, struct, sys
sys.path[:0] = ['/work/iostore', '/work/cs', '/work/swap1012/tools',
                '/work/weap1012/tools', '/work/sephatb/tools']
from iostore import Toc
from zen import Zen
import iostore_write as W
from hdr import parse_header
from gameids import objhash
from build_atb import Table

NAME = 'SephirothTitleScreen_P'
MOUNT = '../../../End/Content/'
PKGS = '/work/title/pkgs/'
HEADER = PKGS + 'pakchunk7_header'                 # pakchunk7's container header (the retail entries)
BGMLIST = PKGS + 'DataObject__Resident__BGMList.uasset'
ALLPATHS = '/work/title/allpaths.tsv'
PAK_STUB = '/work/hang1012/out/FullyPlayableVincentAssets_P.pak'
PRELUDE = 'bgm_prelude'
SWORD_OLD = '/Game/Character/Weapon/WE0000_00_Cloud_BusterSword/Model/WE0000_00'
SWORDS = {
    'brood': '/Game/Character/Weapon/WE1021_01_SephirothIllusion_MasamuneBrood/Model/WE1021_01',   # the bloody Masamune
    'clean': '/Game/Character/Weapon/WE1021_00_SephirothIllusion_Masamune/Model/WE1021_00',
}
EFFECT = 'Level/Game/Field/0005-TITLB/Layout/0005-TITLB_Layout_010_Effect.umap'
MOTES = '/Game/Effect/Field/0005-TITLB/Particle/FX_0005-TITLB_Ptc_01'    # the title's green motes (actor 0, component 5)
# looping black-feather systems (m_bIsLoopingFromData): GPU sims; 8510's fall through a 30 x 30 m box from 15 m up
FEATHERS = {
    '8510_01': '/Game/Effect/Cut/8800-FOREE/EV_FOREE_8510/Particle/FX_EV_FOREE_8510_BlackFeather_01',
    '8510_02': '/Game/Effect/Cut/8800-FOREE/EV_FOREE_8510/Particle/FX_EV_FOREE_8510_BlackFeather_02',
    '8510_03': '/Game/Effect/Cut/8800-FOREE/EV_FOREE_8510/Particle/FX_EV_FOREE_8510_BlackFeather_03',
    '8312_02': '/Game/Effect/Cut/8800-FOREE/EV_FOREE_8312/Particle/FX_EV_FOREE_8312_BlackFeather_02',
    '1241_02': '/Game/Effect/Cut/8600-COSME/EV_COSME_1241/Particle/FX_EV_COSME_1241_BlackFeather_02',
}
TERRAIN = 'Level/Game/Field/0005-TITLB/Layout/0005-TITLB_Layout_010_Terrain_Strip.umap'
BGM_MAP = 'Level/Game/Field/0005-TITLB/0005-TITLB_BGM.umap'
ACTION = 'DataObject/Field/0005-TITLB/Action.uasset'
SIZE_MASK = (1 << 60) - 1                           # header entry size: low bits; the top 4 bits are the export alignment shift


def obj(path):
    """FPackageObjectIndex of a package's main object (/Game/X/Y -> /Game/X/Y.Y)."""
    return (2 << 62) | objhash(path + '.' + path.rsplit('/', 1)[1])


def pid(path):
    return W.package_id(path)


def game_path(rel):
    return '/Game/' + rel.rsplit('.', 1)[0]


def read_pkg(rel):
    return open(PKGS + rel.replace('/', '__'), 'rb').read()


def swap_import(d, old, new):
    z = Zen(d)
    hits = [k for k, v in enumerate(z.imports) if v == old]
    assert len(hits) == 1, ('import', hex(old), hits)
    assert new not in z.imports
    b = bytearray(d)
    struct.pack_into('<Q', b, z.imp_off + 8 * hits[0], new)
    return bytes(b), hits[0]


def swap_graph(d, old, new):
    """The export bundle graph with one imported package replaced (same arcs), kept in id order as the cooker writes it."""
    z = Zen(d)
    o = z.graph_off
    n = struct.unpack_from('<i', d, o)[0]
    p = o + 4
    ents = []
    for _ in range(n):
        g, na = struct.unpack_from('<Qi', d, p)
        ents.append([g, na, d[p + 12:p + 12 + 8 * na]])
        p += 12 + 8 * na
    assert p <= o + z.graph_size and not any(d[p:o + z.graph_size]), 'graph does not parse'
    assert [e[0] for e in ents] == sorted(e[0] for e in ents), 'graph not in id order'
    hits = [e for e in ents if e[0] == old]
    assert len(hits) == 1 and not any(e[0] == new for e in ents), ('graph', hex(old))
    hits[0][0] = new
    ents.sort(key=lambda e: e[0])
    g = struct.pack('<i', n) + b''.join(struct.pack('<Qi', a, na) + arcs for a, na, arcs in ents)
    b = bytearray(d)
    b[o:o + len(g)] = g
    return bytes(b)


def entry_like(old, data, imports=None):
    """The retail header entry for a package, for the patched data (its alignment shift and load order kept)."""
    z = Zen(data)
    assert len(z.exports) == old['export_count']
    return dict(id=old['id'], size=(old['size'] & ~SIZE_MASK) | len(data), export_count=old['export_count'],
                export_bundle_count=old['export_bundle_count'], load_order=old['load_order'],
                imports=list(old['imports'] if imports is None else imports))


def swapped(ids, old, new):
    assert ids.count(old) == 1 and new not in ids, (hex(old), [hex(i) for i in ids])
    return [new if i == old else i for i in ids]


def main():
    out_dir = sys.argv[1]
    row = sys.argv[2] if len(sys.argv) > 2 else 'bgm_Foree2_012_08'
    sword = sys.argv[3] if len(sys.argv) > 3 else 'brood'
    feathers = sys.argv[4] if len(sys.argv) > 4 else '8510_01'
    SWORD_NEW = SWORDS[sword]
    FEATHER = None if feathers == 'none' else FEATHERS[feathers]
    _, retail = parse_header(open(HEADER, 'rb').read())
    game_files = {l.rstrip('\n').split('\t')[3] for l in open(ALLPATHS)}
    assert MOUNT + SWORD_NEW[len('/Game/'):] + '.uasset' in game_files, 'sword not in the game: ' + SWORD_NEW
    assert FEATHER is None or MOUNT + FEATHER[len('/Game/'):] + '.uasset' in game_files, 'feathers not in the game: ' + FEATHER

    # ---- the music: the BGMList row and its bank
    bl = Table(open(BGMLIST, 'rb').read())
    assert row in bl.at, 'no BGMList row ' + row
    bank = bl.get(bl.row(row), 'BGMName')
    section = bl.get(bl.row(row), 'SectionName00')
    bank_path = '/Game/Sound/BGM/' + bank
    assert MOUNT + 'Sound/BGM/%s.uasset' % bank in game_files, 'bank not in the game: ' + bank
    print('music: BGMList row %s -> bank %s, %s' % (row, bank, section or '(the whole piece)'))

    # ---- 1. the sword
    rel = TERRAIN
    d0 = read_pkg(rel)
    old_e = retail[pid(game_path(rel))]
    assert old_e['size'] == len(d0)
    d1, k = swap_import(d0, obj(SWORD_OLD), obj(SWORD_NEW))
    d1 = swap_graph(d1, pid(SWORD_OLD), pid(SWORD_NEW))
    z = Zen(d1)
    comp = [i for i, e in enumerate(z.exports) if e['name'] == 'SkeletalMeshComponent0']
    assert len(comp) == 1
    body = z.export_bytes(comp[0])
    assert struct.pack('<i', -(k + 1)) in body, 'the component does not use the swapped import'
    terrain = (rel, d1, entry_like(old_e, d1, swapped(old_e['imports'], pid(SWORD_OLD), pid(SWORD_NEW))))
    print('sword: import %d WE0000_00 -> %s' % (k, SWORD_NEW.rsplit('/', 1)[1]))

    # ---- 2. the BGM preload
    rel = BGM_MAP
    d0 = read_pkg(rel)
    old_e = retail[pid(game_path(rel))]
    assert old_e['size'] == len(d0)
    pre = '/Game/Sound/BGM/' + PRELUDE
    if bank == PRELUDE:
        d1, imps = d0, old_e['imports']
    else:
        d1, k = swap_import(d0, obj(pre), obj(bank_path))
        d1 = swap_graph(d1, pid(pre), pid(bank_path))
        imps = swapped(old_e['imports'], pid(pre), pid(bank_path))
        print('preload: import %d %s -> %s' % (k, PRELUDE, bank))
    bgm = (rel, d1, entry_like(old_e, d1, imps))

    # ---- 3. the title's PlayBGM action
    rel = ACTION
    d0 = read_pkg(rel)
    old_e = retail[pid(game_path(rel))]
    assert old_e['size'] & SIZE_MASK == len(d0)
    t = Table(d0)
    r = t.row('act005_BGMTitle')
    assert t.get(r, 'StringArgumentList_Array') == [PRELUDE], t.get(r, 'StringArgumentList_Array')
    t.set(r, 'StringArgumentList_Array', [row])
    d1 = t.encode()
    back = Table(d1)
    assert back.get(back.row('act005_BGMTitle'), 'StringArgumentList_Array') == [row]
    for kk, a in zip(t.keys, t.rows):
        if kk != ('act005_BGMTitle', 0):
            assert back.rows[back.at[kk[0] if kk[1] == 0 else '%s_%d' % (kk[0], kk[1] - 1)]] == a
    action = (rel, d1, entry_like(old_e, d1))
    print('action: act005_BGMTitle plays %s (was %s)' % (row, PRELUDE))

    # ---- 4. the feathers: the motes' actor plays the feather system
    packages = [terrain, bgm, action]
    if FEATHER:
        rel = EFFECT
        d0 = read_pkg(rel)
        old_e = retail[pid(game_path(rel))]
        assert old_e['size'] == len(d0)
        d1, k = swap_import(d0, obj(MOTES), obj(FEATHER))
        d1 = swap_graph(d1, pid(MOTES), pid(FEATHER))
        z = Zen(d1)
        assert [e['name'] for e in z.exports[:1]] == ['FX_0005-TITLB_Ptc_01_01'] and z.exports[5]['name'] == 'NiagaraComponent0' and z.exports[5]['outer'] == 0
        assert struct.pack('<i', -(k + 1)) in z.export_bytes(5), 'the motes component does not use the swapped import'
        assert struct.pack('<i', -(k + 1)) not in z.export_bytes(6), 'the smoke component uses the swapped import'
        packages.append((rel, d1, entry_like(old_e, d1, swapped(old_e['imports'], pid(MOTES), pid(FEATHER)))))
        print('feathers: import %d FX_0005-TITLB_Ptc_01 -> %s' % (k, FEATHER.rsplit('/', 1)[1]))

    # ---- the container
    chunks, entries = [None], []
    for rel, data, ent in packages:
        assert ent['id'] == pid(game_path(rel))
        chunks.append(dict(id64=ent['id'], type=2, data=data, path=rel))
        entries.append(ent)
    cid = W.container_id_from_name(NAME)
    chunks[0] = dict(id64=cid, type=10, data=W.container_header(cid, entries), path=None)
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.join(out_dir, NAME)
    W.write_container(base, NAME, chunks, mount=MOUNT)
    shutil.copy(PAK_STUB, base + '.pak')
    back = Toc(base + '.utoc')
    assert back.container_id == cid and back.entries == len(chunks)
    for i, c in enumerate(chunks):
        assert back.read(i) == c['data'] and back.chunk_id64(i) == c['id64'] and back.chunk_type(i) == c['type']
        if c['path']:
            assert back.files.get(i) == MOUNT + c['path'], back.files.get(i)
    _, ents = parse_header(back.read(0))
    for e in entries:
        got = ents[e['id']]
        assert all(got[f] == e[f] for f in ('size', 'export_count', 'export_bundle_count', 'load_order', 'imports')), e['id']
    for f in sorted(os.listdir(out_dir)):
        if f.startswith(NAME):
            p = os.path.join(out_dir, f)
            print('%-36s %9d %s' % (f, os.path.getsize(p), hashlib.md5(open(p, 'rb').read()).hexdigest()))


if __name__ == '__main__':
    main()
