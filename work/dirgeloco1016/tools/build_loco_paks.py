"""Vincent's Dirge of Cerberus walk and run in the game: FullyPlayableVincentAssets_P (the prologue build) with
  * the walk, run and strafe moves build_dirge_locomotion.py built (the plan's names), taken from the project's packaging
    (pakchunk46: RebirthSkelCompat/Built/Vincent/Battle00/<name>), each laid out like the game's animations (align_moves:
    PKG_Cooked, 16-byte exports, shift 4) with its header entry,
  * his four strafing blend spaces (Motion/Player/PC0011_Vincent/Battle00/B_StrafingWalk01_0, _1, _2l, _2r: the game
    plays his locked-on strafes through them, and they name his Rebirth strafe animations themselves, not the set's
    entries) sampling the built strafes instead: each sample's import, the graph and the header entry name the built
    move's package (one export bundle, so the graph's arcs stay 0 -> 0); a blend space with a sample not built stays the
    game's.
Every other package as it was (byte for byte, with its header entry).
    build_loco_paks.py <out dir (new)> <base dir with FullyPlayableVincentAssets_P> <pakchunk46 .utoc> <plan json>"""
import json, os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = ['/work/iostore', '/work/cs', '/work/swap1012/tools', '/work/sephforms/tools',
                '/work/shooter1016/tools', '/work/prologue1016/tools', '/work/evil1013/tools',
                '/work/vincentfix', '/work/weap1012/tools']
from iostore import Toc
from zen import Zen
import iostore_write as W
import hdr
import align_moves as A
import build_dirge_paks as P
import pack_imports as PI

NAME = 'FullyPlayableVincentAssets_P'
MOUNT = '../../../End/Content/'
BUILT = 'RebirthSkelCompat/Built/Vincent/'
GAME_SET = '/Game/Motion/Player/PC0011_Vincent/Battle00/'
BUILT_SET = '/Game/' + BUILT + 'Battle00/'
BLEND_SPACES = ['B_StrafingWalk01_0', 'B_StrafingWalk01_1', 'B_StrafingWalk01_2l', 'B_StrafingWalk01_2r']
BS_FILE = '/work/galian1016/pkgs/Motion__Player__PC0011_Vincent__Battle00__%s.uasset'
RETAIL_HEADER = '/work/retailhdr/pakchunk4_header.bin'


def graph(d, z):
    o = z.graph_off
    n = struct.unpack_from('<i', d, o)[0]; o += 4
    out = []
    for _ in range(n):
        pid, na = struct.unpack_from('<Qi', d, o)
        out.append((pid, bytes(d[o + 8:o + 12 + 8 * na]))); o += 12 + 8 * na
    assert o == z.graph_off + z.graph_size
    return out


def patch_blend_space(data, built):
    """The blend space with every sample of his Rebirth strafes pointing at the built move of that name; None when a
    sample's move was not built. Returns (data, {old package id: new package id})."""
    z = Zen(data)
    names = PI.names(data, [])
    imports, packages = {}, {}
    for i, n in enumerate(names):
        if not n or not n.startswith(GAME_SET):
            continue
        key = n.rsplit('.', 1)[-1]          # (a sample: /Game/.../PC0011_Vincent/Battle00/B_WalkF01_1.B_WalkF01_1)
        assert key.startswith('B_Walk') and n == GAME_SET + key + '.' + key, n
        if key not in built:
            return None, key
        imports[i] = PI.import_index(BUILT_SET + key + '.' + key)
        packages[W.package_id(GAME_SET + key)] = W.package_id(BUILT_SET + key)
    assert imports, 'no sample'
    d = bytearray(data)
    for i, v in imports.items():
        struct.pack_into('<Q', d, z.imp_off + 8 * i, v)
    g = graph(data, z)
    assert sum(1 for pid, _ in g if pid in packages) == len(packages) == len(imports)
    for pid, rest in g:
        if pid in packages:
            assert rest == struct.pack('<iii', 1, 0, 0), ('arcs', hex(pid), rest.hex())
    g = sorted([(packages.get(pid, pid), rest) for pid, rest in g], key=lambda x: x[0])
    gb = struct.pack('<i', len(g)) + b''.join(struct.pack('<Q', pid) + rest for pid, rest in g)
    assert len(gb) == z.graph_size
    d[z.graph_off:z.graph_off + z.graph_size] = gb
    out = bytes(d)
    # read back: only those imports and the graph's packages changed
    z2 = Zen(out)
    assert out[z2.header_end:] == data[z.header_end:] and out[:z.imp_off] == data[:z.imp_off]
    assert [k for k in range(len(z.imports)) if z.imports[k] != z2.imports[k]] == sorted(imports)
    after = PI.names(out, [])
    assert not any(n and n.startswith(GAME_SET + 'B_Walk') for n in after), 'a sample of his Rebirth strafes left'
    return out, packages


def main(out, base_dir, chunk46_utoc, plan_file):
    assert not os.path.exists(out), out + ' exists (use a new folder)'
    plan = json.load(open(plan_file))
    want = {m['name'] for m in plan['moves']}
    chunks, store = P.read(os.path.join(base_dir, NAME + '.utoc'))
    entries = [P.entry(c, store[c['id64']]) for c in chunks if c['type'] == 2]
    by_path = {c['path']: k for k, c in enumerate(chunks) if c['path']}
    new, new_store = P.read(chunk46_utoc)
    report = []
    # 1. the built walk and run moves
    moves = {}
    for c in new:
        if c['path'] and c['path'].startswith(BUILT + 'Battle00/'):
            key = c['path'][len(BUILT + 'Battle00/'):-len('.uasset')]
            if key in want:
                assert c['type'] == 2 and c['id64'] == W.package_id(BUILT_SET + key), c['path']
                moves[key] = c
    assert not any(c['type'] != 2 for c in new if c['path'] is None and c['type'] not in (10,)), 'pakchunk46 has bulk data'
    missing = sorted(want - set(moves))
    replaced, added = [], []
    for key in sorted(moves):
        m = moves[key]
        e = P.entry(m, new_store[m['id64']])
        assert e['export_bundle_count'] == 1, (key, e['export_bundle_count'])
        if m['path'] in by_path:
            k = by_path[m['path']]
            chunks[k] = dict(m)
            entries = [x for x in entries if x['id'] != m['id64']] + [e]
            replaced.append(key)
        else:
            chunks.append(dict(m))
            entries.append(e)
            added.append(key)
    anims, blocks = P.lay_out(chunks, entries)
    report.append('moves: %d of %d (%d added, %d replaced)%s; %d animations laid out like the game\'s (%d ACL blocks)' % (
        len(moves), len(want), len(added), len(replaced), ('; NOT in pakchunk46: ' + ', '.join(missing)) if missing else '', anims, blocks))
    # 2. the strafing blend spaces
    _, retail = hdr.parse_header(open(RETAIL_HEADER, 'rb').read())
    patched = []
    for bs in BLEND_SPACES:
        data = open(BS_FILE % bs, 'rb').read()
        new_data, packages = patch_blend_space(data, set(moves))
        if new_data is None:
            report.append('%s: the game\'s (its sample %s was not built)' % (bs, packages))
            continue
        path = 'Motion/Player/PC0011_Vincent/Battle00/%s.uasset' % bs
        assert path not in by_path, path
        pid = W.package_id(GAME_SET + bs)
        r = retail[pid]
        assert r['size'] == len(data) and r['size'] >> 60 == 0, (bs, hex(r['size']), len(data))
        imports = [packages.get(x, x) for x in r['imports']]
        assert sorted(imports) == sorted(p for p, _ in graph(new_data, Zen(new_data))), bs
        chunks.append(dict(id64=pid, type=2, data=new_data, path=path))
        entries.append(dict(id=pid, size=len(new_data), export_count=r['export_count'], export_bundle_count=r['export_bundle_count'],
                            load_order=r['load_order'], imports=imports))
        patched.append('%s (%d samples)' % (bs, len(packages)))
    report.append('blend spaces sampling the built strafes: ' + (', '.join(patched) or 'none'))
    os.makedirs(out)
    cid, files = P.write(out, NAME, chunks, entries, os.path.join(base_dir, NAME + '.pak'))
    # read back: every package of the base as it was but the moves replaced; the moves and blend spaces as made
    back = Toc(os.path.join(out, NAME + '.utoc'))
    old = Toc(os.path.join(base_dir, NAME + '.utoc'))
    old_by = {(old.chunk_id64(i), old.chunk_type(i)): i for i in range(old.entries)}
    same = changed = 0
    for i in range(back.entries):
        k = (back.chunk_id64(i), back.chunk_type(i))
        if k in old_by and k[1] != 10:
            if back.read(i) == old.read(old_by[k]):
                same += 1
            else:
                changed += 1
    assert changed == len(replaced), (changed, replaced)
    report.append('container %s: %d packages (%d of the base as they were, %d added); %s' % (NAME, len(entries), same, len(added) + len(patched), files))
    open(os.path.join(out, 'loco_report.txt'), 'w').write('\n'.join(report) + '\n')
    print('\n'.join(report))


if __name__ == '__main__':
    main(*sys.argv[1:5])
