"""YoungSephiroth_P with the model of Fully Playable Young Sephiroth's OLDER SEPHIROTH form: the game's own Sephiroth
(Rebirth's PC0010_00 as the game ships it: its LODs, materials, Bonamik, KineDriver, condition data) copied under a
path of its own, /Game/Character/Player/PC0010_15_Sephiroth_Older/Model/PC0010_15, so the form shows him even while
KH2Sephiroth_P puts the KH2 model in PC0010_00's place. A copy at the Zen level of the game's package: its name and its
asset's name changed (name map rebuilt, the asset's public export hash for the new path), its export data and its .ubulk
(5 streamed LODs) byte for byte; everything it imports is the game's. Everything else is the base container's, byte for
byte. The container keeps its name and id.
    build_youngsephiroth_p_older.py <base YoungSephiroth_P.utoc> <game PC0010_00 .uasset (zen)> <its .ubulk> <out dir (new)>"""
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
import pack
import zenrename
import make_bp
import build_youngsephiroth_p as YSB

NAME = 'YoungSephiroth_P'
MOUNT = '../../../End/Content/'
NULL = 0xFFFFFFFFFFFFFFFF
SRC_PKG = '/Game/Character/Player/PC0010_00_Sephiroth_Standard/Model/PC0010_00'
SRC_ASSET = 'PC0010_00'
NEW_PKG = '/Game/Character/Player/PC0010_15_Sephiroth_Older/Model/PC0010_15'
NEW_ASSET = 'PC0010_15'
SRC_MD5 = {'uasset': None, 'ubulk': None}   # (filled in the report)
imp = make_bp.imp


def clone(src, bulk):
    z = Zen(src)
    assert z.mapped(z.name_mapped) == SRC_PKG and z.mapped(z.srcname_mapped) == SRC_PKG
    for i, e in enumerate(z.exports):
        if e['global_import'] != NULL:
            assert imp(make_bp.export_path(z, i, SRC_PKG)) == e['global_import'], e['name']
    renames = {SRC_PKG: NEW_PKG, SRC_ASSET: NEW_ASSET}
    for old in renames:
        assert old in z.names, old
    # the asset's own name is used by nothing in its data (only the export map names it)
    idx = z.names.index(SRC_ASSET)
    assert src.find(struct.pack('<II', idx, 0), z.header_end) == -1, 'the asset name is used inside the data'
    renamed = [dict(e, name=renames.get(e['name'], e['name'])) for e in z.exports]

    class Z2:
        pass
    z2 = Z2()
    z2.exports = renamed
    gis = {i: imp(make_bp.export_path(z2, i, NEW_PKG)) for i, e in enumerate(z.exports) if e['global_import'] != NULL}
    out = zenrename.rebuild(src, renames, gis)
    c = Zen(out)
    assert c.mapped(c.name_mapped) == NEW_PKG and c.mapped(c.srcname_mapped) == NEW_PKG
    assert [e['name'] for e in c.exports] == [renames.get(e['name'], e['name']) for e in z.exports]
    assert out[c.header_end:] == src[z.header_end:], 'export data changed'
    assert c.cooked_header_size == z.cooked_header_size
    assert c.imports == z.imports, 'imports changed'
    assert zenrename.graph_imports(out) == zenrename.graph_imports(src), 'imported packages changed'
    for i, e in enumerate(c.exports):
        if e['global_import'] != NULL:
            assert e['global_import'] == imp(make_bp.export_path(c, i, NEW_PKG)) == imp(NEW_PKG + '.' + NEW_ASSET)
    assert not [n for n in c.names if n == SRC_PKG or n == SRC_ASSET]
    # the bulk data the export reads from its .ubulk: five LODs, all of the file
    total = 0
    for o in range(c.header_end, len(out) - 20):
        flags, cnt, size = struct.unpack_from('<Iii', out, o)
        off = struct.unpack_from('<q', out, o + 12)[0]
        if flags == 0x10501 and cnt == size and 0 <= off and off + size <= len(bulk):
            total += size
    assert total == len(bulk), ('the streamed LODs do not cover the .ubulk', total, len(bulk))
    return out, c


def main(base_utoc, src_uasset, src_ubulk, out):
    assert not os.path.exists(out), out + ' exists (use a new folder)'
    game = YSB.ids_of_files(line.rstrip('\n').split('\t')[-1] for line in gzip.open(YSB.GAME_FILES, 'rt'))
    src = open(src_uasset, 'rb').read()
    bulk = open(src_ubulk, 'rb').read()
    data, c = clone(src, bulk)
    pid = W.package_id(NEW_PKG)
    assert pid not in game, 'the new path is the game\'s'
    base = Toc(base_utoc)
    assert [i for i in range(base.entries) if base.chunk_type(i) == 10] == [0]
    cid, store = parse_header(base.read(0))
    assert cid == W.container_id_from_name(NAME) and pid not in store
    chunks, entries, names = [None], {}, {}
    for i in range(1, base.entries):
        f = base.files.get(i)
        kind = base.chunk_type(i)
        p = base.chunk_id64(i)
        chunks.append(dict(id64=p, type=kind, data=base.read(i), path=f[len(MOUNT):]))
        if kind == 2:
            se = store[p]
            entries[p] = dict(id=p, size=se['size'], export_count=se['export_count'], export_bundle_count=se['export_bundle_count'],
                              load_order=se['load_order'], imports=list(se['imports']))
            names[p] = '/Game/' + f[len(MOUNT):].rsplit('.', 1)[0]
    rel = NEW_PKG[len('/Game/'):]
    chunks.append(dict(id64=pid, type=2, data=data, path=rel + '.uasset'))
    chunks.append(dict(id64=pid, type=3, data=bulk, path=rel + '.ubulk'))
    imports = zenrename.graph_imports(data)
    entries[pid] = dict(id=pid, size=len(data), export_count=len(c.exports), export_bundle_count=pack._bundle_count(c), load_order=0,
                        imports=imports)
    names[pid] = NEW_PKG
    missing = ['%016x' % i for i in imports if i not in game and i not in entries]
    assert not missing, ('the copy imports packages that are neither the game\'s nor here', missing)

    order = {}

    def lo(p, stack=()):
        if p in order:
            return order[p]
        assert p not in stack, 'import cycle'
        deps = [lo(i, stack + (p,)) for i in entries[p]['imports'] if i in entries]
        order[p] = 1 + max(deps or [0])
        return order[p]
    for e in entries.values():
        e['load_order'] = 1000 + lo(e['id'])
    here = set(entries)
    unknown = sorted({'%016x (imported by %s)' % (i, names[e['id']].rsplit('/', 1)[1]) for e in entries.values() for i in e['imports'] if i not in here and i not in game})
    assert not unknown, unknown
    ent_list = [entries[ch['id64']] for ch in chunks[1:] if ch['type'] == 2]
    chunks[0] = dict(id64=cid, type=10, data=W.container_header(cid, ent_list), path=None)
    os.makedirs(out)
    basep = os.path.join(out, NAME)
    assert W.write_container(basep, NAME, chunks, mount=MOUNT) == cid
    shutil.copy(base_utoc[:-len('.utoc')] + '.pak', basep + '.pak')
    back = Toc(basep + '.utoc')
    assert back.container_id == cid and back.entries == len(chunks)
    for i, ch in enumerate(chunks):
        assert back.read(i) == ch['data'] and back.chunk_id64(i) == ch['id64'] and back.chunk_type(i) == ch['type']
        if ch['path']:
            assert back.files.get(i) == MOUNT + ch['path'], (back.files.get(i), ch['path'])
    cid2, ents = parse_header(back.read(0))
    assert cid2 == cid and set(ents) == here
    for e in ent_list:
        b = ents[e['id']]
        for k in ('size', 'export_count', 'export_bundle_count', 'load_order', 'imports'):
            assert b[k] == e[k], (k, names[e['id']])
    same = 0
    for i in range(1, base.entries):
        j = [k for k in range(1, back.entries) if back.chunk_id64(k) == base.chunk_id64(i) and back.chunk_type(k) == base.chunk_type(i)]
        assert len(j) == 1 and back.read(j[0]) == base.read(i)
        same += 1
    print('%s.%s: the game\'s %s.%s copied (%d bytes, %d exports, %d imported packages, all the game\'s; .ubulk %d bytes, md5 %s)' % (
        NEW_PKG, NEW_ASSET, SRC_PKG, SRC_ASSET, len(data), len(c.exports), len(imports), len(bulk), hashlib.md5(bulk).hexdigest()))
    print('%d chunks of the base byte for byte; %s: %d packages, %d bulk chunks; every import here or the game\'s' % (
        same, NAME, len(ent_list), sum(1 for ch in chunks[1:] if ch['type'] == 3)))
    for f in sorted(os.listdir(out)):
        p = os.path.join(out, f)
        print('  %-30s %9d %s' % (f, os.path.getsize(p), hashlib.md5(open(p, 'rb').read()).hexdigest()))


if __name__ == '__main__':
    main(*sys.argv[1:5])
