"""Vincent in the prologue's Cloud (his SOLDIER uniform: PC0000_04 ZackCostume, _12 Dirty, _18 Age21, _19 DirtyAge21,
_23 Wet) as he is in Cloud's own slot: FullyPlayableVincentAssets_P (out1: the CharaSpec rows already name Vincent's model,
build_prologue.py) plus those five rows' CharaSpec packs, the game's own with what the mod's pack of Cloud's row has:
  * Vincent's blueprint spawned (its class, default object and the four subobjects the pack points at:
    DefaultSceneRoot, CharMoveComp, CollisionCylinder, CharacterMesh0) in place of the costume's,
  * Vincent's action sounds (AS_PC0011_00_Vincent_Standard) in place of Cloud's,
  * the graph and the container header entry naming Vincent's blueprint and sound packages in place of those two.
Every other import, the export (its AssetDataList, every hard reference) and the graph's arcs as the game's packs have them.
    build_prologue_packs.py <in dir (out1)> <out dir (new)>"""
import os, shutil, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, '/work/iostore', '/work/cs', '/work/swap1012/tools', '/work/shooter1016/tools',
                '/work/sephforms/tools']
from iostore import Toc
from zen import Zen
import iostore_write as W
import hdr
import pack_imports as PI
import build_dirge_paks as P

NAME = 'FullyPlayableVincentAssets_P'
MOUNT = '../../../End/Content/'
RETAIL = '/work/galian1016/pkgs/DataAsset__Game__CharaSpec__CharaSpec_%s.uasset'
RETAIL_HEADER = '/work/retailhdr/pakchunk4_header.bin'
ROWS = ['PC0000_04_Cloud_ZackCostume', 'PC0000_12_Cloud_ZackCostumeDirty', 'PC0000_18_Cloud_ZackCostumeAge21',
        'PC0000_19_Cloud_ZackCostumeDirtyAge21', 'PC0000_23_Cloud_ZackCostumeWet']
VINCENT = 'PC0011_00_Vincent_Standard'
BP = PI.BPDIR
CLOUD_AS = '/Game/Sound/SE/Character/Player/AS_PC0000_00_Cloud_Standard'
VINCENT_AS = '/Game/Sound/SE/Character/Player/AS_PC0011_00_Vincent_Standard'
NULL = 0xFFFFFFFFFFFFFFFF
LANGS = ['JP', 'US', 'DE', 'FR']
LOCALIZED = ('/Game/Sound/Voice/', '/Game/LipSync/Lsd/')


def import_swaps(old):
    """old blueprint's objects -> Vincent's (the ones a pack imports; any other of old's is an error)."""
    ii = PI.import_index
    o, v = BP + old, BP + VINCENT
    out = {ii('%s.%s_C' % (o, old)): ii('%s.%s_C' % (v, VINCENT)),
           ii('%s.Default__%s_C' % (o, old)): ii('%s.Default__%s_C' % (v, VINCENT)),
           ii('%s.%s_C:DefaultSceneRoot_GEN_VARIABLE' % (o, old)): ii('%s.%s_C:DefaultSceneRoot_GEN_VARIABLE' % (v, VINCENT)),
           ii(CLOUD_AS + '.AS_PC0000_00_Cloud_Standard'): ii(VINCENT_AS + '.AS_PC0011_00_Vincent_Standard')}
    for sub in ('CharMoveComp', 'CollisionCylinder', 'CharacterMesh0'):
        out[ii('%s.Default__%s_C:%s' % (o, old, sub))] = ii('%s.Default__%s_C:%s' % (v, VINCENT, sub))
    return out


def graph(d, z):
    o = z.graph_off
    n = struct.unpack_from('<i', d, o)[0]; o += 4
    out = []
    for _ in range(n):
        pid, na = struct.unpack_from('<Qi', d, o)
        out.append((pid, bytes(d[o + 8:o + 12 + 8 * na]))); o += 12 + 8 * na
    assert o == z.graph_off + z.graph_size
    return out


def patch(data, row):
    z = Zen(data)
    old = [n.split('/')[-1] for n in z.names if n.startswith(BP)]
    assert old == [row], (row, old)
    table = import_swaps(row)
    d = bytearray(data)
    done = []
    for i, v in enumerate(z.imports):
        if v in table:
            struct.pack_into('<Q', d, z.imp_off + 8 * i, table[v]); done.append(i)
    assert len(done) == len(table) == 7, (row, done)
    pkg = {W.package_id(BP + row): W.package_id(BP + VINCENT), W.package_id(CLOUD_AS): W.package_id(VINCENT_AS)}
    g = graph(data, z)
    assert sum(1 for pid, _ in g if pid in pkg) == 2, row
    g = sorted([(pkg.get(pid, pid), rest) for pid, rest in g], key=lambda x: x[0])
    gb = struct.pack('<i', len(g)) + b''.join(struct.pack('<Q', pid) + rest for pid, rest in g)
    assert len(gb) == z.graph_size
    d[z.graph_off:z.graph_off + z.graph_size] = gb
    out = bytes(d)
    # read back: only those seven imports and the graph's two packages changed; nothing of the costume's blueprint left
    z2 = Zen(out)
    assert z2.names == z.names and len(z2.imports) == len(z.imports) and z2.exports == z.exports
    assert out[z2.header_end:] == data[z.header_end:] and out[:z.imp_off] == data[:z.imp_off]
    changed = [i for i in range(len(z.imports)) if z.imports[i] != z2.imports[i]]
    assert changed == done
    named = PI.names(out, [row, VINCENT])
    assert not any(n and n.startswith(BP + row + '.') for n in named), row
    assert sum(1 for n in named if n and n.startswith(BP + VINCENT + '.')) == 6
    assert [pid for pid, _ in graph(out, z2)] == sorted(pkg.get(pid, pid) for pid, _ in graph(data, z))
    return out, pkg


def store_entry(row, data, retail, pkg):
    """The pack's header entry: the game's (pakchunk4) with Vincent's packages, or (PC0000_18, pakchunk10) the same made
    from its graph as the game makes the others (its voice and lip sync by their JP package, which the loader turns into
    the voice language's)."""
    z = Zen(data)
    pid = W.package_id('/Game/DataAsset/Game/CharaSpec/CharaSpec_' + row)
    g = [p for p, _ in graph(data, z)]
    from_graph = []
    for p in g:
        path = PI.PKG.get(p, '')
        if path.startswith(LOCALIZED) and '/JP/' not in path:
            assert any('/%s/' % L in path for L in LANGS[1:]), path
            continue
        from_graph.append(p)
    e = retail.get(pid)
    if e is not None:
        imports = [pkg.get(p, p) for p in e['imports']]
        assert sorted(imports) == sorted(from_graph), (row, 'the rule for the header entry does not hold')
        assert e['size'] == len(data) and e['size'] >> 60 == 0
        return dict(id=pid, size=len(data), export_count=e['export_count'], export_bundle_count=e['export_bundle_count'],
                    load_order=e['load_order'], imports=imports), 'the game\'s'
    bundles = (z.graph_off - z.eb_off - 16 * len(z.exports)) // 8
    return dict(id=pid, size=len(data), export_count=len(z.exports), export_bundle_count=bundles, load_order=0,
                imports=sorted(from_graph)), 'made from its graph'


def main(src, out):
    assert not os.path.exists(out), out + ' exists (use a new folder)'
    chunks, store = P.read(os.path.join(src, NAME + '.utoc'))
    entries = [P.entry(c, store[c['id64']]) for c in chunks if c['type'] == 2]
    paths = [c['path'] for c in chunks]
    _, retail = hdr.parse_header(open(RETAIL_HEADER, 'rb').read())
    report = []
    for row in ROWS:
        path = 'DataAsset/Game/CharaSpec/CharaSpec_%s.uasset' % row
        assert path not in paths, path
        data = open(RETAIL % row, 'rb').read()
        new, pkg = patch(data, row)
        e, how = store_entry(row, new, retail, pkg)
        chunks.append(dict(id64=e['id'], type=2, data=new, path=path))
        entries.append(e)
        report.append('%s: spawns %s (7 imports), header entry %s, %d packages loaded with it' % (row, VINCENT, how, len(e['imports'])))
    os.makedirs(out)
    cid, files = P.write(out, NAME, chunks, entries, os.path.join(src, NAME + '.pak'))
    # read back: every chunk and header entry as written
    back = Toc(os.path.join(out, NAME + '.utoc'))
    head = [i for i in range(back.entries) if back.chunk_type(i) == 10]
    _, ents = hdr.parse_header(back.read(head[0]))
    by = {(back.chunk_id64(i), back.chunk_type(i)): i for i in range(back.entries)}
    for c in chunks:
        i = by[(c['id64'], c['type'])]
        assert back.read(i) == c['data'] and back.files.get(i) == MOUNT + c['path'], c['path']
    for e in entries:
        b = ents[e['id']]
        assert (b['size'], b['export_count'], b['export_bundle_count'], b['load_order'], b['imports']) == \
               (e['size'], e['export_count'], e['export_bundle_count'], e['load_order'], e['imports']), hex(e['id'])
    report.append('container %s: %d packages (5 added); %s' % (NAME, len(entries), files))
    print('\n'.join(report))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
