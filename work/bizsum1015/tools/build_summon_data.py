"""Bizarro Sephiroth as a summon in Alexander's place, the data side, in FullyPlayableSephirothDataAssets_P:
  * CharaSpec table, row SU2030_00_Alexander_Standard (the summon's character): his model (ContentsModel
    EB2210_00_BizarroSephiroth_Standard), his effect packs and sounds added to Alexander's (his own and the transformed
    Sephiroth's, as his own row has them); Alexander's AI, animation sets and everything else kept,
  * the row's pack CharaSpec_SU2030_00_Alexander_Standard (the game's, changed): it spawns Bizarro Sephiroth's blueprint
    instead of Alexander's and also loads his effect packs and sounds,
  * Text/US: the summon is called Bizarro Sephiroth (materia, summon command, its name in battle).
Everything else of the container as it is.
    build_summon_data.py <base dir> <out dir>"""
import os, shutil, struct, sys, io, contextlib
sys.path[:0] = [os.path.dirname(os.path.abspath(__file__)), '/work/sephatb/tools', '/work/iostore',
                '/work/cs', '/work/tools', '/work/evil1013/tools', '/work/swap1012/tools',
                '/work/vincentfix', '/work/weap1012/tools', '/work/gunmoves',
                '/work/neutral20/tools', '/work/hang1012/tools']
import build_atb as B
from iostore import Toc
from zen import Zen
import iostore_write as W
from hdr import parse_header
import gameids
import txtres
import drop_pack_asset as D

NAME = B.NAME
MOUNT = B.MOUNT
NULL = 0xFFFFFFFFFFFFFFFF
ROW = 'SU2030_00_Alexander_Standard'
PACK_PATH = 'DataAsset/Game/CharaSpec/CharaSpec_%s.uasset' % ROW
GAME_PACK = '/work/summon1015/pkgs/CharaSpec_%s.uasset' % ROW
OLD_BP = '/Game/BluePrint/Character/Summon/SU2030_00_Alexander_Standard'
NEW_BP = '/Game/BluePrint/Character/Enemy/EB2210_00_BizarroSephiroth_Standard'
MODEL = 'EB2210_00_BizarroSephiroth_Standard'
# what his pack loads besides the blueprint (his own row's effect packs and sounds)
EXTRA = ['/Game/Effect/Character/Enemy/EB2210_BizarroSephiroth/Build/EB2210_BizarroSephiroth_Effect__Pack.EB2210_BizarroSephiroth_Effect__Pack',
         '/Game/Effect/Character/Player/PC0010_10_Sephiroth_Transform/Build/PC0010_10_Sephiroth_Transform_Effect__Pack.PC0010_10_Sephiroth_Transform_Effect__Pack',
         '/Game/Sound/SE/Character/Enemy/SE_EB2210_00_BizarroSephiroth_Standard.SE_EB2210_00_BizarroSephiroth_Standard',
         '/Game/Sound/SE/Character/Player/SE_PC0010_00_Sephiroth_Standard.SE_PC0010_00_Sephiroth_Standard']
EFFECTS = ['SU2030_Alexander_Effect__Pack', 'EB2210_BizarroSephiroth_Effect__Pack', 'PC0010_10_Sephiroth_Transform_Effect__Pack']
SOUNDS = ['SE_SU2030_00_Alexander_Standard', 'SE_EB2210_00_BizarroSephiroth_Standard', 'SE_PC0010_00_Sephiroth_Standard']
SUMMON = 'Bizarro Sephiroth'
TEXTS = {   # key -> (the game's text, the new one)
    'Item_M_SUM_103': ('Alexander Materia', SUMMON + ' Materia'),
    'Item_M_SUM_103_help': ('Allows you to summon Alexander.', 'Allows you to summon %s.' % SUMMON),
    'M_SMN_103_atk001': ('Alexander', SUMMON),
    'M_SMN_103_atk001_help': ('Summon Alexander. Costs 2 ATB.', 'Summon %s. Costs 2 ATB.' % SUMMON),
    'en_Alexander_Standard': ('Alexander', SUMMON),
}
HELP2 = 'Item_M_SUM_103_help_2'   # "<color=cyan>Alexander</color>\r\nRole: ..." : the name in it


def quiet(f, *a):
    with contextlib.redirect_stdout(io.StringIO()):
        return f(*a)


def imp(path):
    return (2 << 62) | (gameids.objhash(path) & ~(3 << 62))


def summon_pack(data):
    """The game's Alexander pack, spawning Bizarro Sephiroth and loading his effects and sounds."""
    PKG, OBJ = gameids.load()
    z = Zen(data)
    assert len(z.exports) == 1 and z.names[z.name_mapped & 0x3FFFFFFF] == '/Game/' + PACK_PATH[:-len('.uasset')]
    import resolve                                   # names of imports the game's id list lacks (subobjects), from the package's own names
    cand = resolve.candidates(z)
    name_of = lambda v: (OBJ.get(v & ~(3 << 62)) or cand.get(v & ~(3 << 62))) if v != NULL else None
    imports = list(z.imports)
    unused = [k for k, v in enumerate(imports) if v == NULL]   # the cooker's own free slots
    old_class, old_cdo = imp(OLD_BP + '.SU2030_00_Alexander_Standard_C'), imp(OLD_BP + '.Default__SU2030_00_Alexander_Standard_C')
    k_class, k_cdo = imports.index(old_class), imports.index(old_cdo)
    imports[k_class] = imp(NEW_BP + '.EB2210_00_BizarroSephiroth_Standard_C')
    imports[k_cdo] = imp(NEW_BP + '.Default__EB2210_00_BizarroSephiroth_Standard_C')
    # Alexander's blueprint's components: imported for preloading only (the export does not refer to them); with his
    # blueprint no longer loaded they are left out, as the cooker leaves out imports it does not need
    dropped = []
    for k, v in enumerate(imports):
        n = name_of(v) or ''
        if v != NULL and n.split('.', 1)[0] == OLD_BP:
            imports[k] = NULL
            dropped.append(n.rsplit('.', 1)[1])
    # his effect packs and sounds take free import slots
    assert len(unused) >= len(EXTRA), unused
    slots = unused[:len(EXTRA)]
    for k, path in zip(slots, EXTRA):
        imports[k] = imp(path)
    # export data: AssetDataList[0].AssetUserData gets the new assets (unversioned: header, count, element...)
    e = bytearray(z.export_data(0))
    assert len(e) == 72, len(e)
    hdr, n_data = struct.unpack_from('<Ii', e, 0)
    assert n_data == 1
    sh, fname, fnum, n_assets = struct.unpack_from('<HIIi', e, 8)
    assert z.names[fname].endswith('_Data') and n_assets == 5, (z.names[fname], n_assets)
    at = 22 + 4 * n_assets
    refs = list(struct.unpack_from('<%di' % n_assets, e, 22))
    new_refs = [-(k + 1) for k in slots]
    e[at:at] = struct.pack('<%di' % len(new_refs), *new_refs)
    struct.pack_into('<i', e, 18, n_assets + len(new_refs))
    # graph: his blueprint's package in place of Alexander's, and the new packages (each with an arc from its first bundle)
    g = D.graph_entries(data, z)
    old_pid, new_pid = W.package_id(OLD_BP), W.package_id(NEW_BP)
    assert sum(1 for p, _ in g if p == old_pid) == 1
    entries = {}
    for p, raw in g:
        q = new_pid if p == old_pid else p
        entries[q] = struct.pack('<Q', q) + raw[8:]
    for path in EXTRA:
        q = W.package_id(path.split('.', 1)[0])
        assert q not in entries, path
        entries[q] = struct.pack('<Qiii', q, 1, 0, 0)
    gb = struct.pack('<i', len(entries)) + b''.join(entries[q] for q in sorted(entries))
    # the package: header with the new imports and graph, then the export
    d = bytearray(data[:z.header_end])
    for k, v in enumerate(imports):
        struct.pack_into('<Q', d, z.imp_off + 8 * k, v)
    d[z.graph_off:z.graph_off + z.graph_size] = gb
    vals = list(struct.unpack_from('<10i', data, 24))
    assert vals[7] == z.graph_off and vals[8] == z.graph_size
    struct.pack_into('<i', d, 24 + 4 * 8, len(gb))
    struct.pack_into('<Q', d, z.exp_off + 8, len(e))
    out = bytes(d) + bytes(e)
    # checks: every import is a known game object or null; the export refers to the classes and assets wanted
    z2 = Zen(out)
    assert z2.imports == imports and z2.header_end == z.header_end + len(gb) - z.graph_size
    for v in z2.imports:
        assert v == NULL or (v >> 62) == 1 or name_of(v), '%016x' % v
    e2 = z2.export_data(0)
    n2 = struct.unpack_from('<i', e2, 18)[0]
    r2 = list(struct.unpack_from('<%di' % n2, e2, 22))
    assert r2 == refs + new_refs
    assets = [name_of(z2.imports[-r - 1]) for r in r2]
    classes_at = 22 + 4 * n2
    nc = struct.unpack_from('<i', e2, classes_at + 14)[0]
    classes = [name_of(z2.imports[-r - 1]) for r in struct.unpack_from('<%di' % nc, e2, classes_at + 18)]
    assert e2[classes_at + 18 + 4 * nc:] == b'\0\0\0\0', e2[classes_at + 18 + 4 * nc:].hex()
    pids = sorted(entries)
    return out, pids, dict(dropped=dropped, assets=assets, classes=classes)


def main(base_dir, out_dir):
    base_path = os.path.join(base_dir, NAME)
    base = Toc(base_path + '.utoc')
    head = [i for i in range(base.entries) if base.chunk_type(i) == 10]
    cid, base_entries = parse_header(base.read(head[0]))
    chunks, entries = [None], []
    for i in range(base.entries):
        if base.chunk_type(i) != 2:
            continue
        path = base.files[i].replace(MOUNT, '', 1)
        pid = base.chunk_id64(i)
        e = base_entries[pid]
        chunks.append(dict(id64=pid, type=2, data=base.read(i), path=path))
        entries.append(dict(id=pid, size=e['size'], export_count=e['export_count'], export_bundle_count=e['export_bundle_count'],
                            load_order=e['load_order'], imports=list(e['imports'])))
    paths = [c['path'] for c in chunks[1:]]
    report = []

    # ---- CharaSpec table: the summon's row
    k = paths.index(B.CHARASPEC_TABLE) + 1
    cs = quiet(B.Table, chunks[k]['data'])
    row = cs.row(ROW)
    before = {f[0][0]: cs.get(row, f[0][0]) for f in cs.fields}
    assert before['ContentsModel'] == 'SU2030_00_Alexander_Standard', before['ContentsModel']
    cs.set(row, 'ContentsModel', MODEL)
    cs.set(row, 'ContentsEffect_Array', EFFECTS)
    cs.set(row, 'ContentsSoundSE_Array', SOUNDS)
    table = quiet(cs.encode)
    chunks[k]['data'] = table
    entries[k - 1]['size'] = len(table)
    cs2 = quiet(B.Table, table)
    after = {f[0][0]: cs2.get(cs2.row(ROW), f[0][0]) for f in cs2.fields}
    changed = sorted(f for f in after if after[f] != before[f])
    assert changed == ['ContentsEffect_Array', 'ContentsModel', 'ContentsSoundSE_Array'], changed
    cs0 = quiet(B.Table, base.read([i for i in range(base.entries) if base.files.get(i) == MOUNT + B.CHARASPEC_TABLE][0]))
    assert cs2.keys == cs0.keys
    for key in cs0.at:
        if key != ROW:
            assert [cs2.get(cs2.row(key), f[0][0]) for f in cs2.fields] == [cs0.get(cs0.row(key), f[0][0]) for f in cs0.fields], key
    report.append('CharaSpec %s: %s' % (ROW, '; '.join('%s %s -> %s' % (f, before[f], after[f]) for f in changed)))

    # ---- the summon's pack
    assert PACK_PATH not in paths, 'the pack is already in the container'
    pack, pids, info = summon_pack(open(GAME_PACK, 'rb').read())
    pid = W.package_id('/Game/' + PACK_PATH[:-len('.uasset')])
    chunks.append(dict(id64=pid, type=2, data=pack, path=PACK_PATH))
    zp = Zen(pack)
    entries.append(dict(id=pid, size=len(pack), export_count=len(zp.exports), export_bundle_count=1, load_order=0, imports=pids))
    report.append('pack %s: spawns %s; loads %s; Alexander blueprint imports left out: %s' % (
        PACK_PATH, ', '.join(info['classes']), ', '.join(a.rsplit('.', 1)[1] for a in info['assets']), ', '.join(info['dropped'])))

    # ---- Text/US: the summon's name
    k = paths.index(B.TEXT_US) + 1
    tdata = chunks[k]['data']
    tentries, lang = txtres.parse(tdata)
    have = {key: text for key, text, _ in tentries}
    def key_of(name):
        for cand in (name, '$' + name):
            if cand in have:
                return cand
        raise KeyError(name)
    pairs = []
    for name, (old, new) in TEXTS.items():
        key = key_of(name)
        assert have[key] == old, (key, have[key])
        pairs.append((key, new))
    key = key_of(HELP2)
    assert have[key].startswith('<color=cyan>Alexander</color>'), have[key][:60]
    pairs.append((key, have[key].replace('<color=cyan>Alexander</color>', '<color=cyan>%s</color>' % SUMMON, 1)))
    text = txtres.add(tdata, pairs)
    chunks[k]['data'] = text
    if entries[k - 1]['size']:
        entries[k - 1]['size'] = len(text)
    t2, _ = txtres.parse(text)
    got = {key: text_ for key, text_, _ in t2}
    for key, new in pairs:
        assert got[key] == new, key
    assert len(t2) == len(tentries)
    for key, old in have.items():
        if key not in dict(pairs):
            assert got[key] == old, key
    report.append('Text/US: %s' % '; '.join('%s = %s' % (key, new.split('\r\n')[0]) for key, new in pairs))

    # ---- the container
    cid2 = W.container_id_from_name(NAME)
    assert cid2 == cid
    chunks[0] = dict(id64=cid2, type=10, data=W.container_header(cid2, entries), path=None)
    os.makedirs(out_dir, exist_ok=True)
    outb = os.path.join(out_dir, NAME)
    W.write_container(outb, NAME, chunks, mount=MOUNT)
    shutil.copy(base_path + '.pak', outb + '.pak')
    back = Toc(outb + '.utoc')
    assert back.container_id == cid2 and back.entries == len(chunks)
    for i, c in enumerate(chunks):
        assert back.read(i) == c['data'] and back.chunk_id64(i) == c['id64'] and back.chunk_type(i) == c['type']
        if c['path']:
            assert back.files.get(i) == MOUNT + c['path'], back.files.get(i)
    _, ents = parse_header(back.read(0))
    assert set(ents) == {c['id64'] for c in chunks[1:]}
    PKG, _ = gameids.load()
    here = {c['id64'] for c in chunks[1:]}
    changed = {B.CHARASPEC_TABLE, B.TEXT_US, PACK_PATH}
    for c, e in zip(chunks[1:], entries):
        got = ents[c['id64']]
        assert (got['size'], got['export_count'], got['export_bundle_count'], got['imports'], got['load_order']) == \
               (e['size'], e['export_count'], e['export_bundle_count'], e['imports'], e['load_order'])
        for x in e['imports']:
            assert x in here or x in PKG, (c['path'], '%016x' % x)
        if c['path'] not in changed:
            j = [kk for kk, v in base.files.items() if v == MOUNT + c['path']][0]
            assert c['data'] == base.read(j) and base_entries[c['id64']]['imports'] == e['imports'], c['path']
    print('\n'.join(report))
    print('container: %s (%d packages: %d from the base, 1 new)' % (outb, len(chunks) - 1, base.entries - 1))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
