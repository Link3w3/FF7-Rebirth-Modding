"""FullyPlayableVincentAssets_P with Cloud's CharaSpec row fixed for Vincent over Cloud:
  AnimationSetParentFolder PC0011_Vincent -> PC0000_Cloud    (field actions and minigame sets are Cloud's)
  NoBattleCharaSpec / ReserveCharaSpec PC0011_00_Cloud_Standard (no such row) -> PC0000_00_Cloud_Standard (itself)
Every other chunk, the container id, the paths and the load order stay as the installed container has them.
    make_fixed_pak.py <installed base path without extension> <output dir>"""
import hashlib, os, shutil, struct, sys
sys.path.insert(0, '/work/vincentfix'); sys.path.insert(0, '/work/iostore'); sys.path.insert(0, '/work/cs')
from iostore import Toc
import iostore_write as W
import charaspec_patch as cp

src, out_dir = sys.argv[1], sys.argv[2]
name = os.path.basename(src)
toc = Toc(src + '.utoc')
chunks = []
for i in range(toc.entries):
    chunks.append(dict(id64=toc.chunk_id64(i), type=toc.chunk_type(i), data=toc.read(i), path=toc.files.get(i)))
charaspec = next(i for i, c in enumerate(chunks) if c['path'] and c['path'].endswith('DataObject/Resident/CharaSpec.uasset'))
header = next(i for i, c in enumerate(chunks) if c['type'] == 10)

# CharaSpec: Cloud's row.
data = chunks[charaspec]['data']
z, e, m, d = cp.decode(data)
keys = [k[0] for k in d.keys]
rows = [list(r) for r in d.rows]
fi = cp.field_index(d)
row = rows[keys.index(('PC0000_00_Cloud_Standard', 0))]
changes = {'AnimationSetParentFolder': ('PC0000_Cloud', 0), 'NoBattleCharaSpec': ('PC0000_00_Cloud_Standard', 0), 'ReserveCharaSpec': ('PC0000_00_Cloud_Standard', 0)}
for field, value in changes.items():
    print('PC0000_00_Cloud_Standard.%s: %s -> %s' % (field, row[fi[field]], value))
    row[fi[field]] = value
fixed = cp.encode(data, z, e, m, keys, d.fields, rows)
print('CharaSpec package %d -> %d bytes (the name patch table changes with the names used)' % (len(data), len(fixed)))
chunks[charaspec]['data'] = fixed

# Container header: the CharaSpec package's new size.
h = bytearray(chunks[header]['data'])
o = 16
o += 4 + struct.unpack_from('<i', h, o)[0]          # names
o += 4 + struct.unpack_from('<i', h, o)[0]          # name hashes
count = struct.unpack_from('<i', h, o)[0]; o += 4
ids = struct.unpack_from('<%dQ' % count, h, o); o += 8 * count
o += 4                                               # store size
pid = W.package_id('/Game/DataObject/Resident/CharaSpec')
k = ids.index(pid)
struct.pack_into('<Q', h, o + 32 * k, len(fixed))
chunks[header]['data'] = bytes(h)

# Same container id as the installed one (its tool derives ids differently from the name).
os.makedirs(out_dir, exist_ok=True)
base = os.path.join(out_dir, name)
real_cid = W.container_id_from_name
W.container_id_from_name = lambda _name: toc.container_id
mount = '../../../End/Content/'
for c in chunks:
    if c['path']:
        assert c['path'].startswith(mount), c['path']
        c['path'] = c['path'][len(mount):]
W.write_container(base, name, chunks, mount=mount)
W.container_id_from_name = real_cid
shutil.copy(src + '.pak', base + '.pak')

# Read back: every chunk as intended, the row as intended.
back = Toc(base + '.utoc')
assert back.container_id == toc.container_id and back.entries == toc.entries
for i in range(back.entries):
    assert back.chunk_id64(i) == chunks[i]['id64'] and back.chunk_type(i) == chunks[i]['type'], i
    assert back.read(i) == chunks[i]['data'], i
    assert (back.files.get(i) or '') == ((mount + chunks[i]['path']) if chunks[i]['path'] else ''), (i, back.files.get(i))
z2, e2, m2, d2 = cp.decode(back.read(charaspec))
keys2 = [k[0] for k in d2.keys]
row2 = d2.rows[keys2.index(('PC0000_00_Cloud_Standard', 0))]
print('read back:', {f: row2[fi[f]] for f in list(changes) + ['ContentsModel', 'AnimationSetList_Array']})
diff = [k for k, a, b in zip(keys, d.rows, d2.rows) if list(a) != list(b)]
print('rows that differ from the input:', diff)
for f in sorted(os.listdir(out_dir)):
    p = os.path.join(out_dir, f)
    print('%-40s %9d %s' % (f, os.path.getsize(p), hashlib.md5(open(p, 'rb').read()).hexdigest()))
