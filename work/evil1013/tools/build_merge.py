"""Evil Cloud in Sephiroth's place, merged into the user's FullyPlayableSephirothDataAssets_P:
  * the user's container as it is (every package byte for byte, their header entries), except
  * Sephiroth's six CharaSpec packs spawn the Evil Cloud blueprints instead of Cloud's (Transform: the transformed one),
  * the CharaSpec table's Sephiroth rows name the blueprint their pack spawns (ContentsModel),
  * plus the two Evil Cloud blueprints (make_bp.py) and the user's three cooked Evil Cloud packages
    (EvilCloudOverSephiroth_P: the skeleton and both meshes, with their own header entries).
    build_merge.py <out dir>"""
import hashlib, os, shutil, struct, sys
sys.path.insert(0, '/work/iostore'); sys.path.insert(0, '/work/cs')
sys.path.insert(0, '/work/vincentfix'); sys.path.insert(0, '/work/weap1012/tools')
sys.path.insert(0, '/work/swap1012/tools'); sys.path.insert(0, '/work/evil1013/tools')
from iostore import Toc
from zen import Zen
import iostore_write as W
import charaspec_patch as cp
import gameids
from hdr import parse_header
import make_bp

PKG, OBJ = gameids.load()
objhash = gameids.objhash
NULL = 0xFFFFFFFFFFFFFFFF
NAME = 'FullyPlayableSephirothDataAssets_P'
BASE = '/work/evil1013/installed/' + NAME
MODELS = '/work/evil1013/pak/EvilCloudOverSephiroth_P'
MOUNT = '../../../End/Content/'
TABLE = 'DataObject/Resident/CharaSpec.uasset'
BP = '/Game/BluePrint/Character/Player/'
EVIL, EVIL_T = 'PC0000_10_Evil_Cloud', 'PC0000_11_EvilCloud_Transformed'
# Sephiroth's rows -> (the blueprint their pack spawns now, the Evil Cloud blueprint it spawns instead)
ROWS = {
    'PC0010_00_Sephiroth_Standard': ('PC0000_00_Cloud_Standard', EVIL),
    'PC0010_00_Sephiroth_Standard_NoBattle': ('PC0000_00_Cloud_Standard', EVIL),
    'PC0010_00_Sephiroth_Standard_Reserve': ('PC0000_00_Cloud_Standard', EVIL),
    'PC0010_01_Sephiroth_StandardWet': ('PC0000_22_Cloud_StandardWet', EVIL),
    'PC0010_10_Sephiroth_Transform': ('PC0000_00_Cloud_Standard', EVIL_T),
    'PC0010_20_Sephiroth_VRHard': ('PC0000_00_Cloud_Standard', EVIL),
}

def imp(path):
    return (2 << 62) | objhash(path)

def name_of(v):
    return OBJ.get(v & ~(3 << 62)) if v != NULL else None

def graph_entries(d):
    z = Zen(d)
    o = z.graph_off; n = struct.unpack_from('<i', d, o)[0]; o += 4; out = []
    for _ in range(n):
        pid, na = struct.unpack_from('<Qi', d, o)
        out.append((pid, bytes(d[o + 8:o + 12 + 8 * na]))); o += 12 + 8 * na
    assert o == z.graph_off + z.graph_size
    return out

def retarget_pack(data, old_bp, new_bp):
    """The pack's imports of old_bp's class and default object -> new_bp's; its graph lists new_bp's package."""
    z = Zen(data); d = bytearray(data)
    table = {imp(BP + old_bp + '.' + old_bp + '_C'): imp(BP + new_bp + '.' + new_bp + '_C'),
             imp(BP + old_bp + '.Default__' + old_bp + '_C'): imp(BP + new_bp + '.Default__' + new_bp + '_C')}
    done = 0
    for i, v in enumerate(z.imports):
        if v in table:
            struct.pack_into('<Q', d, z.imp_off + 8 * i, table[v]); done += 1
    assert done == 2, (old_bp, done)
    left = [name_of(v) for v in Zen(bytes(d)).imports if (name_of(v) or '').startswith(BP + old_bp + '.')]
    assert not left, left
    old_pid, new_pid = W.package_id(BP + old_bp), W.package_id(BP + new_bp)
    g = graph_entries(bytes(d))
    assert sum(1 for pid, _ in g if pid == old_pid) == 1
    g = sorted([(new_pid if pid == old_pid else pid, rest) for pid, rest in g], key=lambda x: x[0])
    gb = bytearray(struct.pack('<i', len(g)))
    for pid, rest in g: gb += struct.pack('<Q', pid) + rest
    assert len(gb) == z.graph_size
    d[z.graph_off:z.graph_off + z.graph_size] = gb
    assert len(d) == len(data)
    return bytes(d), old_pid, new_pid

def spawns(data):
    """The character blueprints a pack spawns (class imports under /BluePrint/Character/)."""
    out = []
    for v in Zen(data).imports:
        n = name_of(v) or ''
        if '/BluePrint/Character/' in n and n.endswith('_C') and '.Default__' not in n:
            out.append(n.rsplit('.', 1)[1][:-2])
    return out

def with_names(data, extra):
    """The package with names appended to its name map (existing indices unchanged), header offsets rebuilt."""
    import zenrename
    z = Zen(data)
    add = [n for n in extra if n not in z.names]
    if not add:
        return data
    names = list(z.names) + add
    nb = bytearray()
    for s in names:
        h, b, wide = zenrename.encode_name(s)
        nb += h
        if wide and (64 + len(nb)) & 1: nb.append(0)
        nb += b
    nm_off = 64; nm_size = len(nb); p = nm_off + nm_size; pad = (8 - p % 8) % 8; nh_off = p + pad
    hashes = struct.pack('<Q', z.hash_version) + b''.join(struct.pack('<Q', zenrename.name_hash(s)) for s in names)
    rest = data[z.imp_off:z.header_end]
    shift = (nh_off + len(hashes)) - z.imp_off
    summary = struct.pack('<QQIIiiiiiiiiii', z.name_mapped, z.srcname_mapped, z.flags, z.cooked_header_size, nm_off, nm_size, nh_off, len(hashes),
                          z.imp_off + shift, z.exp_off + shift, z.eb_off + shift, z.graph_off + shift, z.graph_size, z.pad)
    out = summary + bytes(nb) + b'\0' * pad + hashes + rest + data[z.header_end:]
    c = Zen(out)
    assert c.names == names and c.imports == z.imports and [x['name'] for x in c.exports] == [x['name'] for x in z.exports]
    assert out[c.header_end:] == data[z.header_end:]
    return out

def text(v):
    if isinstance(v, tuple) and len(v) == 2 and isinstance(v[0], str): return v[0]
    return repr(v)

def main():
    out_dir = sys.argv[1]
    base = Toc(BASE + '.utoc')
    head = [i for i in range(base.entries) if base.chunk_type(i) == 10]
    assert len(head) == 1
    cid, base_entries = parse_header(base.read(head[0]))
    assert cid == base.container_id == W.container_id_from_name(NAME)
    models = Toc(MODELS + '.utoc')
    mhead = [i for i in range(models.entries) if models.chunk_type(i) == 10]
    _, model_entries = parse_header(models.read(mhead[0]))

    # the new blueprints: their objects become known names for the checks below
    bps = {}
    for name in (EVIL, EVIL_T):
        data, pkg, exports = make_bp.make(name)
        bps[name] = data
        z = Zen(data)
        for i, e in enumerate(z.exports):
            if e['global_import'] != NULL:
                OBJ[e['global_import'] & ~(3 << 62)] = make_bp.export_path(z, i, pkg)
        PKG[W.package_id(pkg)] = pkg
    for i in range(models.entries):
        if models.chunk_type(i) == 2:
            path = '/Game/' + models.files[i].replace(MOUNT, '', 1)[:-len('.uasset')]
            PKG[models.chunk_id64(i)] = path
            z = Zen(models.read(i))
            for k, e in enumerate(z.exports):
                if e['global_import'] != NULL:
                    OBJ[e['global_import'] & ~(3 << 62)] = make_bp.export_path(z, k, path)

    # ---- the user's packages, Sephiroth's packs retargeted
    chunks, entries, patched = [None], [], {}
    table_index = None
    for i in range(base.entries):
        if base.chunk_type(i) != 2:
            assert base.chunk_type(i) == 10
            continue
        path = base.files[i].replace(MOUNT, '', 1)
        pid = base.chunk_id64(i)
        assert pid == W.package_id('/Game/' + path[:-len('.uasset')]), path
        data = base.read(i)
        e = dict(base_entries[pid])
        row = path.rsplit('CharaSpec_', 1)[1][:-len('.uasset')] if '/CharaSpec/CharaSpec_' in path else None
        if row in ROWS:
            old_bp, new_bp = ROWS[row]
            assert spawns(data) == [old_bp], (row, spawns(data))
            data, old_pid, new_pid = retarget_pack(data, old_bp, new_bp)
            assert spawns(data) == [new_bp]
            assert old_pid in e['imports']
            e['imports'] = [new_pid if x == old_pid else x for x in e['imports']]
            assert len(set(e['imports'])) == len(e['imports'])
            assert {pid for pid, _ in graph_entries(data)} <= set(e['imports']), 'graph package missing from the header entry'
            patched[row] = (old_bp, new_bp)
        if path == TABLE:
            table_index = len(chunks)
        chunks.append(dict(id64=pid, type=2, data=data, path=path))
        entries.append(dict(id=pid, size=e['size'], export_count=e['export_count'], export_bundle_count=e['export_bundle_count'],
                            load_order=e['load_order'], imports=e['imports']))
    assert set(patched) == set(ROWS), set(ROWS) - set(patched)

    # ---- the table: Sephiroth's rows name what their packs spawn
    tdata = with_names(chunks[table_index]['data'], sorted({new for _, new in ROWS.values()}))
    z, e, m, d = cp.decode(tdata)
    keys = [k[0] for k in d.keys]
    assert cp.encode(tdata, z, e, m, keys, d.fields, [list(r) for r in d.rows]) == tdata, 'table round trip differs'
    rows = [list(r) for r in d.rows]
    fi = {f[0][0]: i for i, f in enumerate(d.fields)}
    at = {k[0]: i for i, k in enumerate(keys)}
    for row, (old_bp, new_bp) in ROWS.items():
        r = rows[at[row]]
        before = text(r[fi['ContentsModel']])
        assert before == old_bp, (row, before)
        r[fi['ContentsModel']] = (new_bp, 0)
        print('%-40s ContentsModel %s -> %s' % (row, before, new_bp))
    table = cp.encode(tdata, z, e, m, keys, d.fields, rows)
    z2, e2, m2, d2 = cp.decode(table)
    for k, a, b in zip(keys, rows, d2.rows):
        assert list(b) == a, ('row differs after encode', k)
    chunks[table_index]['data'] = table
    tz = Zen(table)
    old = entries[table_index - 1]
    assert old['export_count'] == len(tz.exports)

    # ---- every pack in the container against its row
    for c in chunks[1:]:
        if '/CharaSpec/CharaSpec_' not in c['path']: continue
        row = c['path'].rsplit('CharaSpec_', 1)[1][:-len('.uasset')]
        sp = spawns(c['data'])
        model = text(rows[at[row]][fi['ContentsModel']])
        ok = sp == [model] or not sp
        print('%-46s spawns %-36s row model %-36s %s' % (row, ','.join(sp) or '-', model, 'agrees' if ok else 'DISAGREES'))
        assert ok, row

    # ---- the new packages
    for name, data in bps.items():
        path = 'BluePrint/Character/Player/%s.uasset' % name
        pid = W.package_id('/Game/' + path[:-7])
        z = Zen(data)
        chunks.append(dict(id64=pid, type=2, data=data, path=path))
        imports = []
        for gpid, _ in graph_entries(data):
            imports.append(gpid)
        entries.append(dict(id=pid, size=len(data), export_count=len(z.exports), export_bundle_count=(z.graph_off - z.eb_off - 16 * len(z.exports)) // 8,
                            load_order=0, imports=imports))
    for i in range(models.entries):
        if models.chunk_type(i) != 2: continue
        pid = models.chunk_id64(i)
        path = models.files[i].replace(MOUNT, '', 1)
        assert pid not in {c['id64'] for c in chunks[1:]}
        me = model_entries[pid]
        chunks.append(dict(id64=pid, type=2, data=models.read(i), path=path))
        entries.append(dict(id=pid, size=me['size'], export_count=me['export_count'], export_bundle_count=me['export_bundle_count'],
                            load_order=me['load_order'], imports=me['imports']))

    # ---- every package another one lists is in the game or in this container
    here = {c['id64'] for c in chunks[1:]}
    for c, ent in zip(chunks[1:], entries):
        for x in ent['imports']:
            assert x in here or x in PKG, (c['path'], '%016x' % x)
        for v in Zen(c['data']).imports:
            if v != NULL and (v >> 62) == 2 and c['path'] not in ('Motion/Player/PC0010_Sephiroth/Neutral00/N_Avoid01_0.uasset',):
                pass
    for name in (EVIL, EVIL_T):
        z = Zen(bps[name])
        for v in z.imports:
            if v != NULL and (v >> 62) == 2:
                assert name_of(v), ('blueprint import unknown', name, '%016x' % v)

    cid2 = W.container_id_from_name(NAME)
    chunks[0] = dict(id64=cid2, type=10, data=W.container_header(cid2, entries), path=None)
    os.makedirs(out_dir, exist_ok=True)
    outb = os.path.join(out_dir, NAME)
    W.write_container(outb, NAME, chunks, mount=MOUNT)
    shutil.copy(BASE + '.pak', outb + '.pak')
    back = Toc(outb + '.utoc')
    assert back.container_id == cid2 and back.entries == len(chunks)
    for i, c in enumerate(chunks):
        assert back.read(i) == c['data'] and back.chunk_id64(i) == c['id64'] and back.chunk_type(i) == c['type']
        if c['path']: assert back.files.get(i) == MOUNT + c['path'], back.files.get(i)
    _, ents = parse_header(back.read(0))
    assert set(ents) == {c['id64'] for c in chunks[1:]}
    for c in chunks[1:]:
        assert ents[c['id64']]['imports'] == [x for x in entries[[k['id64'] for k in chunks[1:]].index(c['id64'])]['imports']]
    print(len(chunks) - 1, 'packages:', base.entries - 1, 'from the user\'s', NAME, '(', len(patched), 'packs retargeted, table edited ),',
          len(bps), 'blueprints,', models.entries - 1, 'from EvilCloudOverSephiroth_P')
    for f in sorted(os.listdir(out_dir)):
        p = os.path.join(out_dir, f)
        print('%-44s %9d %s' % (f, os.path.getsize(p), hashlib.md5(open(p, 'rb').read()).hexdigest()))

if __name__ == '__main__':
    main()
