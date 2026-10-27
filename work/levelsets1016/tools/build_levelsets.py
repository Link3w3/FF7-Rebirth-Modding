"""Every level animation set for Sephiroth, in FullyPlayableSephirothDataAssets_P (the container build_fieldsets.py made):
the CharaSpec rows he plays from list them all (OverrideAnimationSetString_Array):
  * his own rows (PC0010_00_Sephiroth_Standard, PC0010_01_Sephiroth_StandardWet, PC0010_00_Sephiroth_Standard_Reserve,
    PC0010_00_Sephiroth_Standard_NoBattle - AnimationSetParentFolder PC0010_Sephiroth), which listed none: Cloud's 20, in
    Cloud's order, then the 14 other level sets of Cloud's folder, which no row of Cloud's lists (the chocobo race, the moogle
    capture, ...);
  * Cloud's slot's rows (the 9 build_fieldsets.py gave Cloud's 20): the same 14 after them.
Every name is a set in Sephiroth's folder (build_fieldsets.py copied Cloud's there: /Game/Motion/Level/<name>/PC0010_Sephiroth).
The transformed Sephiroth's rows (PC0010_10, PC0010_20: folder PC0010_Sephiroth_Transform, the boss) stay as they are.

Only the CharaSpec table and the container header (the table's size) change. The new .ucas is the old one with their new
blocks after it, which the new .utoc points at (every other chunk keeps its blocks): <out>/<NAME>.ucas.tail is what to append
to the old .ucas; <out>/<NAME>.ucas is the whole of it, read back here chunk by chunk.
    build_levelsets.py <out dir (new)> <base .utoc>"""
import contextlib, hashlib, io, os, shutil, struct, sys
sys.path[:0] = ['/work/safer1016/tools', '/work/sephatb/tools', '/work/iostore', '/work/cs',
                '/work/tools', '/work/evil1013/tools', '/work/swap1012/tools', '/work/vincentfix',
                '/work/weap1012/tools', '/work/gunmoves', '/work/sephforms/tools', '/work/neutral20/tools']
import merge_fullyplayable as M
import build_atb as B
from iostore import Toc
import iostore_write as W
import hdr

NAME = M.NAME
MOUNT = M.MOUNT
BLOCK = W.BLOCK
LIST = 'OverrideAnimationSetString_Array'
FOLDER = 'AnimationSetParentFolder'
SEPH = 'PC0010_Sephiroth'
REFERENCE = 'PC0000_00_Cloud_Standard_NoBattle'   # a Cloud row as the game has it
SEPH_ROWS = ['PC0010_00_Sephiroth_Standard', 'PC0010_01_Sephiroth_StandardWet', 'PC0010_00_Sephiroth_Standard_Reserve',
             'PC0010_00_Sephiroth_Standard_NoBattle']
SLOT_ROWS = ['PC0000_00_Cloud_Standard', 'PC0000_04_Cloud_ZackCostume', 'PC0000_08_Cloud_SoldierNoHelmet', 'PC0000_09_Cloud_CostaClothing',
             'PC0000_10_Cloud_CostaClothing2', 'PC0000_12_Cloud_ZackCostumeDirty', 'PC0000_18_Cloud_ZackCostumeAge21',
             'PC0000_19_Cloud_ZackCostumeDirtyAge21', 'PC0000_23_Cloud_ZackCostumeWet']
EXTRAS = ['BizarroSephiroth00', 'Ch13Monument00', 'ChocoboRace00', 'ChocoboRace32', 'HandLight00', 'HandlePuzzle00', 'LockerRoom00',
          'MoogleCapture00', 'MoogleCapture01', 'MoogleCapture02', 'PushBMantle00', 'Resist00', 'SaboSearch00', 'Wheelie00']
SET_PACKAGES = '/work/fire1015'   # build_fieldsets.py's set packages (plan_*/pkgs): which sets Sephiroth's folder has


def quiet(f, *a):
    with contextlib.redirect_stdout(io.StringIO()):
        return f(*a)


def folder_sets(base):
    """Level sets the container has in Sephiroth's folder."""
    return sorted(c['path'].split('/')[2] for c in base if c['path'] and c['path'].startswith('Motion/Level/') and
                  c['path'].endswith('/' + SEPH + '.uasset'))


def edit_table(data):
    t = quiet(B.Table, data)
    before = {key: [t.get(t.row(key), f[0][0]) for f in t.fields] for key in t.at}
    cloud = list(t.get(t.row(REFERENCE), LIST))
    assert len(cloud) == 20 and 'FireWalk00' in cloud and not set(EXTRAS) & set(cloud), cloud
    full = cloud + EXTRAS
    for row in SEPH_ROWS:
        r = t.row(row)
        assert t.get(r, FOLDER) == SEPH and t.get(r, LIST) == [], (row, t.get(r, FOLDER), t.get(r, LIST))
        t.set(r, LIST, full)
    for row in SLOT_ROWS:
        r = t.row(row)
        assert t.get(r, FOLDER) == SEPH and t.get(r, LIST) == cloud, (row, t.get(r, FOLDER), t.get(r, LIST))
        t.set(r, LIST, full)
    out = quiet(t.encode)
    t2 = quiet(B.Table, out)
    assert t2.keys == t.keys
    for key in t.at:
        now = [t2.get(t2.row(key), f[0][0]) for f in t2.fields]
        want = list(before[key])
        if key in SEPH_ROWS or key in SLOT_ROWS:
            want[t.fi[LIST]] = full
        assert now == want, key
    return out, full


def append_container(old, base_ucas, changes, utoc_path, tail_path):
    """The old container with `changes` (chunk index -> new data): their data in new blocks after the old .ucas, the
    rest as it is. Writes the new .utoc and the tail (the bytes to append to the old .ucas)."""
    b = old.b
    size = os.path.getsize(base_ucas)
    last = old.blocks[-1]
    assert size % 16 == 0 and last[0] + ((last[1] + 15) & ~15) == size, 'the .ucas does not end with its last block'
    assert old.nmethods == 0 and not old.flags & 0x4 and old.partcount == 1 and old.blocksz == BLOCK
    blocks = list(old.blocks)
    offlen = list(old.offlen)
    tail = bytearray()
    for i in sorted(changes):
        data = changes[i]
        offlen[i] = (len(blocks) * BLOCK, len(data))
        for k in range(0, len(data), BLOCK):
            piece = data[k:k + BLOCK]
            blocks.append((size + len(tail), len(piece), len(piece), 0))
            tail += piece
            while len(tail) % 16:
                tail.append(0)
    head = bytearray(b[:old.hdrsize])
    struct.pack_into('<I', head, 28, len(blocks))
    o = old.hdrsize
    ids = b[o:o + 12 * old.entries]
    dstart = o + 22 * old.entries + 12 * old.ncblocks
    assert dstart + old.diridxsize == old.metas_off
    metas = bytearray(b[old.metas_off:])
    assert len(metas) == 33 * old.entries
    for i, data in changes.items():
        metas[33 * i:33 * i + 20] = hashlib.sha1(data).digest()
    toc = bytearray(head) + ids
    for off, ln in offlen:
        toc += off.to_bytes(5, 'big') + ln.to_bytes(5, 'big')
    for pos, cs, us, m in blocks:
        toc += pos.to_bytes(5, 'little') + cs.to_bytes(3, 'little') + us.to_bytes(3, 'little') + bytes([m])
    toc += b[dstart:dstart + old.diridxsize] + metas
    open(utoc_path, 'wb').write(toc)
    open(tail_path, 'wb').write(tail)


def main(out, base_utoc):
    assert not os.path.exists(out), out + ' exists (use a new folder)'
    base_ucas = base_utoc[:-len('.utoc')] + '.ucas'
    old = Toc(base_utoc)
    heads = [i for i in range(old.entries) if old.chunk_type(i) == 10]
    tables = [i for i in range(old.entries) if old.files.get(i) == MOUNT + B.CHARASPEC_TABLE]
    assert heads == [0] and len(tables) == 1, (heads, tables)
    ti = tables[0]
    # every chunk as its hash says (the container to build on is the one made)
    for i in range(old.entries):
        assert hashlib.sha1(old.read(i)).digest() == old.b[old.metas_off + 33 * i:old.metas_off + 33 * i + 20], i
    head = old.read(0)
    cid, store = hdr.parse_header(head)
    assert cid == W.container_id_from_name(NAME)
    order = [old.chunk_id64(i) for i in range(old.entries) if old.chunk_type(i) == 2]
    assert len(order) == len(store) and set(order) == set(store)
    entries = [dict(id=p, size=store[p]['size'], export_count=store[p]['export_count'], export_bundle_count=store[p]['export_bundle_count'],
                    load_order=store[p]['load_order'], imports=list(store[p]['imports'])) for p in order]
    assert W.container_header(cid, entries) == head, 'the header does not write back as it is'
    base, _ = M.read(base_utoc)
    have = folder_sets(base)
    # the table
    table, full = edit_table(old.read(ti))
    missing = [n for n in full if n not in have]
    assert not missing, ('not in Sephiroth\'s folder', missing)
    e = [x for x in entries if x['id'] == old.chunk_id64(ti)][0]
    if e['size']:
        e['size'] = (e['size'] & (3 << 62)) | len(table)
    new_head = W.container_header(cid, entries)
    assert len(new_head) == len(head) and sum(x != y for x, y in zip(new_head, head)) <= 8
    # the container
    os.makedirs(out)
    path = os.path.join(out, NAME)
    changes = {0: new_head, ti: table}
    append_container(old, base_ucas, changes, path + '.utoc', path + '.ucas.tail')
    with open(path + '.ucas', 'wb') as f:
        with open(base_ucas, 'rb') as g:
            shutil.copyfileobj(g, f, 1 << 24)
        f.write(open(path + '.ucas.tail', 'rb').read())
    shutil.copy(base_utoc[:-len('.utoc')] + '.pak', path + '.pak')
    # read back: every chunk, its id, file and hash; the header's entries
    new = Toc(path + '.utoc')
    assert new.entries == old.entries and new.chunk_ids == old.chunk_ids and new.files == old.files
    for i in range(new.entries):
        data = new.read(i)
        assert data == (changes[i] if i in changes else old.read(i)), i
        assert hashlib.sha1(data).digest() == new.b[new.metas_off + 33 * i:new.metas_off + 33 * i + 20], i
    cid2, store2 = hdr.parse_header(new.read(0))
    assert cid2 == cid and len(store2) == len(store)
    for p in order:
        a, z = store[p], store2[p]
        for key in ('export_count', 'export_bundle_count', 'load_order', 'imports'):
            assert a[key] == z[key], (p, key)
        assert a['size'] == z['size'] or p == old.chunk_id64(ti), p
    chunks2, _ = M.read(path + '.utoc')
    t = quiet(B.Table, [c for c in chunks2 if c['path'] == B.CHARASPEC_TABLE][0]['data'])
    for row in SEPH_ROWS + SLOT_ROWS:
        assert t.get(t.row(row), LIST) == full, row
    print('CharaSpec table: %s on %d of Sephiroth\'s rows (%s) and %d of Cloud\'s slot (%d names: %s)'
          % (LIST, len(SEPH_ROWS), ', '.join(SEPH_ROWS), len(SLOT_ROWS), len(full), ', '.join(full)))
    print('%s: %d chunks, 2 changed (the table %d -> %d bytes, the header), read back as written; the .ucas is the old one plus %d bytes'
          % (NAME, new.entries, len(old.read(ti)), len(table), os.path.getsize(path + '.ucas.tail')))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
