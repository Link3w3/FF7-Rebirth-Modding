"""FullyPlayableVincentAssets_P hot fix: Cloud's CharaSpec pack spawns Vincent's character blueprint again
(and plays Vincent's action sounds), as every earlier version of the pak did. Everything else stays as built.
    fix_cloud_bp.py <installed base path without extension> <output dir>"""
import hashlib, os, shutil, struct, sys
sys.path.insert(0, '/work/iostore'); sys.path.insert(0, '/work/cs')
sys.path.insert(0, '/work/hang1012/tools')
from iostore import Toc
import iostore_write as W
from zen import Zen
import cityhash

PACK = '/Game/DataAsset/Game/CharaSpec/CharaSpec_PC0000_00_Cloud_Standard'
CLOUD_BP, VINCENT_BP = '/Game/BluePrint/Character/Player/PC0000_00_Cloud_Standard', '/Game/BluePrint/Character/Player/PC0011_00_Vincent_Standard'
CLOUD_AS, VINCENT_AS = '/Game/Sound/SE/Character/Player/AS_PC0000_00_Cloud_Standard', '/Game/Sound/SE/Character/Player/AS_PC0011_00_Vincent_Standard'
NULL = 0xFFFFFFFFFFFFFFFF

def import_index(path):
    s = ''.join('/' if c in '.:' else c.lower() for c in path)
    return (2 << 62) | (cityhash.CityHash64(s.encode('utf-16-le')) & ~(3 << 62))

def swaps():
    c, v = CLOUD_BP, VINCENT_BP
    out = {
        import_index(c + '.PC0000_00_Cloud_Standard_C'): import_index(v + '.PC0011_00_Vincent_Standard_C'),
        import_index(c + '.Default__PC0000_00_Cloud_Standard_C'): import_index(v + '.Default__PC0011_00_Vincent_Standard_C'),
        import_index(c + '.PC0000_00_Cloud_Standard_C:DefaultSceneRoot_GEN_VARIABLE'): import_index(v + '.PC0011_00_Vincent_Standard_C:DefaultSceneRoot_GEN_VARIABLE'),
        # Cloud's blueprint only (the earlier packs never imported it): no import.
        import_index(c + '.PC0000_00_Cloud_Standard_C:EndBodySubCollisionSetting_GEN_VARIABLE'): NULL,
        import_index(CLOUD_AS + '.AS_PC0000_00_Cloud_Standard'): import_index(VINCENT_AS + '.AS_PC0011_00_Vincent_Standard'),
    }
    for sub in ('CharMoveComp', 'CollisionCylinder', 'CharacterMesh0'):
        out[import_index(c + '.Default__PC0000_00_Cloud_Standard_C:' + sub)] = import_index(v + '.Default__PC0011_00_Vincent_Standard_C:' + sub)
    return out

PACKAGE_SWAPS = {W.package_id(CLOUD_BP): W.package_id(VINCENT_BP), W.package_id(CLOUD_AS): W.package_id(VINCENT_AS)}

def patch_pack(data):
    z = Zen(data)
    d = bytearray(data)
    table = swaps()
    done = []
    for i, v in enumerate(z.imports):
        if v in table:
            struct.pack_into('<Q', d, z.imp_off + 8 * i, table[v])
            done.append(i)
    assert len(done) == len(table), ('imports found', len(done), 'of', len(table))
    # Graph: imported packages (sorted by id, as the cooker writes them), each with its arcs.
    o = z.graph_off
    n = struct.unpack_from('<i', d, o)[0]; o += 4
    entries = []
    for _ in range(n):
        pid, na = struct.unpack_from('<Qi', d, o)
        entries.append((PACKAGE_SWAPS.get(pid, pid), d[o + 8:o + 12 + 8 * na]))
        o += 12 + 8 * na
    assert o == z.graph_off + z.graph_size
    swapped = sum(1 for pid, _ in entries if pid in PACKAGE_SWAPS.values())
    assert swapped == len(PACKAGE_SWAPS), swapped
    entries.sort(key=lambda e: e[0])
    g = bytearray(struct.pack('<i', n))
    for pid, rest in entries:
        g += struct.pack('<Q', pid) + rest
    d[z.graph_off:z.graph_off + z.graph_size] = g
    return bytes(d), done

def patch_header(h, pack_id):
    h = bytearray(h)
    o = 16
    o += 4 + struct.unpack_from('<i', h, o)[0]          # names
    o += 4 + struct.unpack_from('<i', h, o)[0]          # name hashes
    count = struct.unpack_from('<i', h, o)[0]; o += 4
    ids = struct.unpack_from('<%dQ' % count, h, o); o += 8 * count
    o += 4                                               # store size
    k = ids.index(pack_id)
    e = o + 32 * k
    num, off = struct.unpack_from('<II', h, e + 24)
    at = e + 24 + off
    deps = list(struct.unpack_from('<%dQ' % num, h, at))
    new = [PACKAGE_SWAPS.get(x, x) for x in deps]
    assert sum(1 for a, b in zip(deps, new) if a != b) == len(PACKAGE_SWAPS)
    struct.pack_into('<%dQ' % num, h, at, *new)
    return bytes(h)

def main():
    src, out_dir = sys.argv[1], sys.argv[2]
    name = os.path.basename(src)
    toc = Toc(src + '.utoc')
    chunks = [dict(id64=toc.chunk_id64(i), type=toc.chunk_type(i), data=toc.read(i), path=toc.files.get(i)) for i in range(toc.entries)]
    pack = next(i for i, c in enumerate(chunks) if c['path'] and c['path'].endswith('CharaSpec/CharaSpec_PC0000_00_Cloud_Standard.uasset'))
    header = next(i for i, c in enumerate(chunks) if c['type'] == 10)
    chunks[pack]['data'], done = patch_pack(chunks[pack]['data'])
    chunks[header]['data'] = patch_header(chunks[header]['data'], W.package_id(PACK))
    print('Cloud pack: %d imports retargeted (%s), 2 imported packages swapped in graph and container header' % (len(done), done))
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.join(out_dir, name)
    real = W.container_id_from_name
    W.container_id_from_name = lambda _n: toc.container_id
    mount = '../../../End/Content/'
    for c in chunks:
        if c['path']:
            assert c['path'].startswith(mount), c['path']
            c['path'] = c['path'][len(mount):]
    W.write_container(base, name, chunks, mount=mount)
    W.container_id_from_name = real
    shutil.copy(src + '.pak', base + '.pak')
    # Read back.
    back = Toc(base + '.utoc')
    assert back.container_id == toc.container_id and back.entries == toc.entries
    for i in range(back.entries):
        assert back.chunk_id64(i) == chunks[i]['id64'] and back.chunk_type(i) == chunks[i]['type'], i
        assert back.read(i) == chunks[i]['data'], i
        assert (back.files.get(i) or '') == ((mount + chunks[i]['path']) if chunks[i]['path'] else ''), i
    for f in sorted(os.listdir(out_dir)):
        p = os.path.join(out_dir, f)
        print('%-40s %9d %s' % (f, os.path.getsize(p), hashlib.md5(open(p, 'rb').read()).hexdigest()))

if __name__ == '__main__':
    main()
