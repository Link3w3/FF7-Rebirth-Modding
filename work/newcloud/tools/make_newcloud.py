"""The new Cloud (Create a Character System): Cloud as a character of his own, the game's own Cloud under new names, so the
Fully Playable (Young) Sephiroth (which turns the game's Cloud into Sephiroth) does not reach him:
  * his AnimBlueprint PC0000_00_Cloud_Standard_CACS_Animation: the AnimBlueprint Maker's copy of Cloud's (Control Rig kept:
    he is on Cloud's own skeleton),
  * his character blueprints: PC0000_00_Cloud_Standard_CACS (Cloud's, with his AnimBlueprint) and the outfits' (04, 08, 09,
    10, 12: Cloud's, their parent his),
  * his CharaSpec packs: each outfit's, its _NoBattle and _Reserve, and their minigame (OA00-19) and voice (SFV00-02) packs,
    named <row>_CACS..., spawning his blueprints,
  * his weapons' CharaSpec packs: the game's own (the Buster Sword, Rebirth's six, the Nail Bat, the umbrella) as _CACS,
  * the game's CharaPopPack and CharaPopAsset tables with rows for all of them (what each pack loads, and its memory).
Every package is the game's own (vanilla, not the Fully Playable Sephiroth's) under its new name: its export data unchanged,
its public exports at the global indices of their new paths, its imports of the renamed objects (the import map and the
export map's class, super and template indices) and its dependencies on the renamed packages (the graph) the new ones.
Written to <out>/pkgs/<content path>.uasset with entries.json (store entries) and report.txt.
    make_newcloud.py <out dir>"""
import hashlib, json, os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, '/work/iostore', '/work/cs', '/work/vincentfix', '/work/charaspecmod',
                '/work/sephatb/tools', '/work/weap1012/tools', '/work/swap1012/tools',
                '/work/evil1013/tools', '/work/tools']
from zen import Zen
import zenrename
import iostore_write as W
import make_cacs_abp_lib as ABP
from build_atb import Table

NULL = 0xFFFFFFFFFFFFFFFF
GX = '/work/owncloud/gx/'
VANILLA = ['bp4', 'bp10', 'van4', 'van10', 'oa4', 'oa10', 'tab3', 'van3']   # (not fpys / fpys2: the Fully Playable Sephiroth's)
SUFFIX = '_CACS'
BP = '/Game/BluePrint/Character/Player/'
CS = '/Game/DataAsset/Game/CharaSpec/'
ANIM_OLD = '/Game/BluePrint/Animation/Player/PC0000_00_Cloud_Standard_Animation'
ANIM_NEW = '/Game/BluePrint/Animation/Player/PC0000_00_Cloud_Standard' + SUFFIX + '_Animation'
SKELETON = '/Game/Character/Player/PC0000_00_Cloud_Standard/Model/PC0000_00_Skeleton'
BASE = 'PC0000_00_Cloud_Standard'
OUTFITS = ['PC0000_00_Cloud_Standard', 'PC0000_04_Cloud_ZackCostume', 'PC0000_08_Cloud_SoldierNoHelmet', 'PC0000_09_Cloud_CostaClothing',
           'PC0000_10_Cloud_CostaClothing2', 'PC0000_12_Cloud_ZackCostumeDirty']
WEAPONS = ['WE0000_00_Cloud_BusterSword', 'WE0000_05_Cloud_NailBat', 'WE0000_11_Cloud_END2Weapon1', 'WE0000_12_Cloud_END2Weapon2',
           'WE0000_13_Cloud_END2Weapon3', 'WE0000_14_Cloud_END2Weapon4', 'WE0000_15_Cloud_END2Weapon5', 'WE0000_16_Cloud_END2Weapon6',
           'WE0000_17_Cloud_Umbrella']
VARIANTS = [''] + ['OA%02d' % k for k in range(20)] + ['SFV%02d' % k for k in range(3)]
KINDS = ['', '_NoBattle', '_Reserve']
EXPORT_REFS = (('outer', 24), ('cls', 32), ('super', 40), ('template', 48))   # FExportMapEntry fields holding object indices


def new_row(row):
    """PC0000_00_Cloud_Standard_NoBattleOA00 -> PC0000_00_Cloud_Standard_CACS_NoBattleOA00 (the suffix after the outfit's name)."""
    for o in OUTFITS + WEAPONS:
        if row == o or row.startswith(o + '_') or (row.startswith(o) and row[len(o):len(o) + 2] in ('OA', 'SF')):
            return o + SUFFIX + row[len(o):]
    raise KeyError(row)


def find_pkg(rel):
    """A vanilla game package extracted under owncloud/gx/<block>/pkgs (rel: DataAsset/Game/CharaSpec/X.uasset). The same
    package in two blocks must be the same bytes."""
    name = rel.replace('/', '__')
    found = []
    for d in VANILLA:
        p = os.path.join(GX, d, 'pkgs', name)
        if os.path.exists(p):
            found.append(open(p, 'rb').read())
    if not found:
        raise FileNotFoundError(rel)
    assert all(f == found[0] for f in found), ('different copies of', rel)
    return found[0]


imp = ABP.imp


def graph_parse(d):
    """The export bundle graph: [(package id, arcs)] and the bytes after it (retail packages pad the graph)."""
    z = Zen(d)
    o = z.graph_off
    n = struct.unpack_from('<i', d, o)[0]
    o += 4
    out = []
    for _ in range(n):
        pid, na = struct.unpack_from('<Qi', d, o)
        out.append((pid, list(struct.unpack_from('<%di' % (2 * na), d, o + 12)) if na else []))
        o += 12 + 8 * na
    end = z.graph_off + z.graph_size
    assert o <= end and not any(d[o:end]), 'graph does not parse'
    return out, d[o:end]


def graph_bytes(g, pad):
    return ABP.graph_bytes(g) + pad


def store_entry(pkg, data):
    z = Zen(data)
    return dict(id=W.package_id(pkg), size=len(data), export_count=len(z.exports),
                export_bundle_count=(z.graph_off - z.eb_off - 16 * len(z.exports)) // 8, load_order=0,
                imports=[pid for pid, _ in graph_parse(data)[0]])


def old_refs(data, gi_map, pid_map):
    """What in a package still names a renamed object or package (imports, export map indices, graph)."""
    z = Zen(data)
    left = ['import %d' % i for i, v in enumerate(z.imports) if v in gi_map]
    for i, e in enumerate(z.exports):
        for field, _ in EXPORT_REFS:
            if e[field] in gi_map:
                left.append('export %s %s' % (e['name'], field))
    left += ['graph %x' % pid for pid, _ in graph_parse(data)[0] if pid in pid_map]
    return left


def rename(src, old_pkg, new_pkg, names, gi_map, pid_map, need=()):
    """The package under new_pkg: `names` renamed (old_pkg's too), its public exports' global indices those of their new
    paths, its imports of renamed packages' objects (gi_map: old global index -> new) in the import map and in the export
    map (class, super, template, outer) and its dependencies on renamed packages (pid_map) the new ones.
    Returns (data, store entry, {old global index -> new} of this package's public exports, references made new)."""
    z = Zen(src)
    assert z.mapped(z.name_mapped) == old_pkg, (z.mapped(z.name_mapped), old_pkg)
    renames = {old_pkg: new_pkg}
    for old, new in names.items():
        if old in z.names:
            renames[old] = new
        else:
            assert old not in need, (old_pkg, 'has no name', old)
    for i, e in enumerate(z.exports):
        if e['global_import'] != NULL:
            assert imp(ABP.export_path(z.exports, i, old_pkg)) == e['global_import'], (old_pkg, e['name'])
    after = [renames.get(n, n) for n in z.names]
    dup = sorted({n for n in after if after.count(n) > 1})
    assert not dup, (old_pkg, 'names clash', dup)
    renamed = [dict(e, name=renames.get(e['name'], e['name'])) for e in z.exports]
    gis = {i: imp(ABP.export_path(renamed, i, new_pkg)) for i, e in enumerate(z.exports) if e['global_import'] != NULL}
    mine = {z.exports[i]['global_import']: gis[i] for i in gis}
    d = bytearray(zenrename.rebuild(src, renames, gis))
    nz = Zen(bytes(d))
    hits = 0
    for i, v in enumerate(nz.imports):
        if v in gi_map:
            struct.pack_into('<Q', d, nz.imp_off + 8 * i, gi_map[v])
            hits += 1
    for i, e in enumerate(nz.exports):
        for field, at in EXPORT_REFS:
            if e[field] in gi_map:
                struct.pack_into('<Q', d, nz.exp_off + 72 * i + at, gi_map[e[field]])
                hits += 1
    g, pad = graph_parse(bytes(d))
    hits += sum(1 for pid, _ in g if pid in pid_map)
    g = sorted([(pid_map.get(pid, pid), arcs) for pid, arcs in g], key=lambda x: x[0])
    gb = graph_bytes(g, pad)
    assert len(gb) == nz.graph_size
    d[nz.graph_off:nz.graph_off + nz.graph_size] = gb
    out = bytes(d)
    c = Zen(out)
    assert c.mapped(c.name_mapped) == new_pkg and c.mapped(c.srcname_mapped) == new_pkg
    assert [e['name'] for e in c.exports] == [renames.get(e['name'], e['name']) for e in z.exports]
    assert out[c.header_end:] == src[z.header_end:], 'export data changed'
    assert c.cooked_header_size == z.cooked_header_size
    for i, e in enumerate(c.exports):
        if e['global_import'] != NULL:
            assert e['global_import'] == imp(ABP.export_path(c.exports, i, new_pkg))
    left = old_refs(out, gi_map, pid_map)
    assert not left, (new_pkg, 'still names renamed objects', left)
    return out, store_entry(new_pkg, out), mine, hits


def pop_key(path):
    """/Game/BluePrint/Character/Player/X -> BluePrint_Character_Player_X (how CharaPopPack and CharaPopAsset name assets)."""
    return path[len('/Game/'):].replace('/', '_')


def main(out):
    os.makedirs(os.path.join(out, 'pkgs'), exist_ok=False)
    made, entries, report = {}, [], []
    gi_map, pid_map = {}, {}

    def keep(pkg, data, entry, note):
        rel = pkg[len('/Game/'):] + '.uasset'
        path = os.path.join(out, 'pkgs', rel.replace('/', '__'))
        assert not os.path.exists(path), path
        open(path, 'wb').write(data)
        made[pkg] = rel
        entries.append(dict(entry, path=rel, md5=hashlib.md5(data).hexdigest()))
        report.append('%-84s %8d bytes  %s' % (pkg, len(data), note))

    def renamed_pkg(old, new):
        pid_map[W.package_id(old)] = W.package_id(new)

    # 1. the AnimBlueprint (the AnimBlueprint Maker's copy, on Cloud's skeleton, its Control Rig kept)
    src = find_pkg('BluePrint/Animation/Player/PC0000_00_Cloud_Standard_Animation.uasset')
    data, entry, t, notes = ABP.make(src, ANIM_NEW, SKELETON, 'PC0000_00_Skeleton', 'keep')
    z0, z1 = Zen(src), Zen(data)
    for i, e in enumerate(z0.exports):
        if e['global_import'] != NULL:
            gi_map[e['global_import']] = z1.exports[i]['global_import']
    renamed_pkg(ANIM_OLD, ANIM_NEW)
    keep(ANIM_NEW, data, entry, 'AnimBlueprint (' + '; '.join(notes) + ')')
    anim_names = {n: n.replace('PC0000_00_Cloud_Standard_Animation', 'PC0000_00_Cloud_Standard' + SUFFIX + '_Animation')
                  for n in z0.names if 'PC0000_00_Cloud_Standard_Animation' in n}

    # 2. the blueprints: Cloud's (with the new AnimBlueprint), then the outfits' (their parent the new one)
    def bp_names(m):
        return {BP + m: BP + m + SUFFIX, m + '_C': m + SUFFIX + '_C', 'Default__' + m + '_C': 'Default__' + m + SUFFIX + '_C'}
    for m in OUTFITS:
        src = find_pkg('BluePrint/Character/Player/%s.uasset' % m)
        names = dict(anim_names)
        names.update(bp_names(BASE))
        names.update(bp_names(m))
        data, entry, mine, hits = rename(src, BP + m, BP + m + SUFFIX, names, gi_map, pid_map, need=(m + '_C', 'Default__' + m + '_C'))
        if m != BASE and hits == 0:
            raise AssertionError('%s names nothing of Cloud\'s blueprint (not his child?)' % m)
        gi_map.update(mine)
        renamed_pkg(BP + m, BP + m + SUFFIX)
        keep(BP + m + SUFFIX, data, entry, 'blueprint, %d reference(s) made his' % hits)

    # 3. the outfits' CharaSpec packs (each kind and variant), spawning his blueprints
    bp_all = {}
    for m in OUTFITS:
        bp_all.update(bp_names(m))
    for m in OUTFITS:
        for kind in KINDS:
            for var in VARIANTS:
                row = m + kind + var
                src = find_pkg('DataAsset/Game/CharaSpec/CharaSpec_%s.uasset' % row)
                nr = new_row(row)
                names = {'CharaSpec_' + row: 'CharaSpec_' + nr, row + '_Class': nr + '_Class', row + '_Data': nr + '_Data'}
                names.update(bp_all)
                data, entry, mine, hits = rename(src, CS + 'CharaSpec_' + row, CS + 'CharaSpec_' + nr, names, gi_map, pid_map,
                                                 need=('CharaSpec_' + row, row + '_Data'))
                if not var and hits == 0:
                    raise AssertionError('%s names nothing of the blueprint' % row)
                if var and hits:
                    raise AssertionError('%s (a minigame or voice pack) names the blueprint' % row)
                gi_map.update(mine)
                renamed_pkg(CS + 'CharaSpec_' + row, CS + 'CharaSpec_' + nr)
                keep(CS + 'CharaSpec_' + nr, data, entry, 'pack' + (', %d reference(s) to his blueprint' % hits if hits else ''))

    # 4. the weapons' CharaSpec packs (the game's own, renamed: their blueprints stay the game's)
    for w in WEAPONS:
        src = find_pkg('DataAsset/Game/CharaSpec/CharaSpec_%s.uasset' % w)
        nr = new_row(w)
        names = {'CharaSpec_' + w: 'CharaSpec_' + nr, w + '_Class': nr + '_Class', w + '_Data': nr + '_Data'}
        data, entry, mine, hits = rename(src, CS + 'CharaSpec_' + w, CS + 'CharaSpec_' + nr, names, gi_map, pid_map,
                                         need=('CharaSpec_' + w, w + '_Class'))
        assert hits == 0, (w, 'names a renamed package')
        gi_map.update(mine)
        renamed_pkg(CS + 'CharaSpec_' + w, CS + 'CharaSpec_' + nr)
        keep(CS + 'CharaSpec_' + nr, data, entry, 'weapon pack (the game\'s own)')

    # 5. CharaPopPack (what each pack loads) and CharaPopAsset (each asset's memory) with his rows
    asset_new = {pop_key(BP + m): pop_key(BP + m + SUFFIX) for m in OUTFITS}
    asset_new[pop_key(ANIM_OLD)] = pop_key(ANIM_NEW)
    for tname in ('CharaPopPack', 'CharaPopAsset'):
        src = find_pkg('DataObject/Resident/%s.uasset' % tname)
        tab = Table(src)
        added, missing = 0, []
        if tname == 'CharaPopPack':
            for m in OUTFITS + WEAPONS:
                for kind in (KINDS if m in OUTFITS else ['']):
                    for var in (VARIANTS if m in OUTFITS else ['']):
                        row = 'CharaSpec_' + m + kind + var
                        if row not in tab.at:
                            missing.append(row)
                            continue
                        vals = list(tab.row(row))
                        tab.set(vals, 'AssetName_Array', [asset_new.get(n, n) for n in tab.get(vals, 'AssetName_Array')])
                        tab.add('CharaSpec_' + new_row(m + kind + var), vals)
                        added += 1
        else:
            for old, new in asset_new.items():
                if old in tab.at:
                    tab.add(new, list(tab.row(old)))
                    added += 1
                else:
                    missing.append(old)
        data = tab.encode()
        pkg = '/Game/DataObject/Resident/' + tname
        keep(pkg, data, store_entry(pkg, data), 'the game\'s table, %d row(s) of his added%s' % (
            added, ('; no row for ' + ', '.join(missing)) if missing else ''))

    # 6. nothing he has names a renamed object or package
    for e in entries:
        data = open(os.path.join(out, 'pkgs', e['path'].replace('/', '__')), 'rb').read()
        left = old_refs(data, gi_map, pid_map)
        assert not left, (e['path'], left)
    ids = [e['id'] for e in entries]
    assert len(set(ids)) == len(ids), 'two packages share a package id'
    json.dump(dict(entries=entries), open(os.path.join(out, 'entries.json'), 'w'), indent=1)
    open(os.path.join(out, 'report.txt'), 'w').write('\n'.join(report) + '\n')
    print('\n'.join(report[:10]))
    print('...')
    print('\n'.join(report[-12:]))
    print('%d packages, %d bytes' % (len(entries), sum(e['size'] for e in entries)))


if __name__ == '__main__':
    main(sys.argv[1])
