"""Test build: Cloud's weapon rows in the Vincent pak's CharaSpec table describe the gun the packs spawn
(model, shared spec, effects, sounds), the way SephirothOverCloud describes its Masamune.
    weapon_rows.py <installed base path without extension> <output dir>"""
import hashlib, os, shutil, struct, sys
sys.path.insert(0, '/work/iostore'); sys.path.insert(0, '/work/cs')
sys.path.insert(0, '/work/vincentfix'); sys.path.insert(0, '/work/hang1012/tools')
from iostore import Toc
import iostore_write as W
import charaspec_patch as cp
from repack import parse_header

GUN = 'WE0011_00_Vincent_Quiksilver'
ROWS = ['WE0000_00_Cloud_BusterSword', 'WE0000_05_Cloud_NailBat', 'WE0000_11_Cloud_END2Weapon1', 'WE0000_12_Cloud_END2Weapon2',
        'WE0000_13_Cloud_END2Weapon3', 'WE0000_14_Cloud_END2Weapon4', 'WE0000_15_Cloud_END2Weapon5', 'WE0000_16_Cloud_END2Weapon6',
        'WE0000_17_Cloud_Umbrella']
def fstr(s): return s.encode('utf-16-le') + b'\0\0'
# What each pack in this pak loads besides the gun's blueprint (its AssetDataList).
PACK_EFFECTS = {'WE0000_00_Cloud_BusterSword': [fstr('WE1021_00_SephirothIllusion_Masamune_Effect__Pack')]}

def edit(keys, fields, rows):
    fi = {f[0][0]: i for i, f in enumerate(fields)}
    at = {k: i for i, k in enumerate(keys)}
    gun = rows[at[GUN]]
    changed = {}
    for name in ROWS:
        r = rows[at[name]]
        before = list(r)
        r[fi['ContentsModel']] = gun[fi['ContentsModel']]
        r[fi['SharedCharaSpecList_Array']] = [(GUN, 0)]
        r[fi['ContentsEffect_Array']] = list(PACK_EFFECTS.get(name, []))
        r[fi['ContentsSoundSE_Array']] = []
        changed[name] = [(fields[i][0][0], before[i], r[i]) for i in range(len(r)) if before[i] != r[i]]
    return changed

def main():
    src, out_dir = sys.argv[1], sys.argv[2]
    name = os.path.basename(src)
    toc = Toc(src + '.utoc')
    chunks = [dict(id64=toc.chunk_id64(i), type=toc.chunk_type(i), data=toc.read(i), path=toc.files.get(i)) for i in range(toc.entries)]
    ti = next(i for i, c in enumerate(chunks) if c['path'] and c['path'].endswith('DataObject/Resident/CharaSpec.uasset'))
    hi = next(i for i, c in enumerate(chunks) if c['type'] == 10)
    data = chunks[ti]['data']
    z, e, m, d = cp.decode(data)
    keys = [k[0] for k in d.keys]
    rows = [list(r) for r in d.rows]
    orig = [list(r) for r in d.rows]
    # The writer reproduces the unmodified table exactly.
    assert cp.encode(data, z, e, m, keys, d.fields, orig) == data, 'table round trip differs'
    changed = edit([k[0] for k in keys], d.fields, rows)
    new = cp.encode(data, z, e, m, keys, d.fields, rows)
    # Read back: the edited rows as intended, every other row unchanged.
    z2, e2, m2, d2 = cp.decode(new)
    assert [k[0] for k in d2.keys] == keys
    for k, a, b, c in zip(keys, orig, rows, d2.rows):
        assert list(c) == b, ('row differs after encode', k)
        if k[0] not in ROWS:
            assert a == b
    for n, ch in changed.items():
        print(n); [print('    %s: %r -> %r' % x) for x in ch]
    chunks[ti]['data'] = new
    # Container header: the table's store entry carries the package size.
    cid, names, hashes, entries, rest = parse_header(chunks[hi]['data'])
    tid = W.package_id('/Game/DataObject/Resident/CharaSpec')
    for en in entries:
        if en['id'] == tid:
            assert en['size'] == len(data)
            en['size'] = len(new)
    header = W.container_header(cid, entries)
    pad = len(chunks[hi]['data']) - len(header)
    chunks[hi]['data'] = header + b'\0' * max(pad, 0)
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.join(out_dir, name)
    real = W.container_id_from_name
    W.container_id_from_name = lambda _n: toc.container_id
    mount = '../../../End/Content/'
    for c in chunks:
        if c['path']:
            c['path'] = c['path'][len(mount):]
    W.write_container(base, name, chunks, mount=mount)
    W.container_id_from_name = real
    shutil.copy(src + '.pak', base + '.pak')
    back = Toc(base + '.utoc')
    assert back.container_id == toc.container_id and back.entries == len(chunks)
    for i, c in enumerate(chunks):
        assert back.read(i) == c['data'] and back.chunk_id64(i) == c['id64'] and back.chunk_type(i) == c['type']
    bh = parse_header(back.read(hi))
    assert [x['id'] for x in bh[3]] == [x['id'] for x in entries]
    print('table %d -> %d bytes; chunks %d' % (len(data), len(new), back.entries))
    for f in sorted(os.listdir(out_dir)):
        p = os.path.join(out_dir, f)
        print('%-40s %9d %s' % (f, os.path.getsize(p), hashlib.md5(open(p, 'rb').read()).hexdigest()))

if __name__ == '__main__':
    main()
