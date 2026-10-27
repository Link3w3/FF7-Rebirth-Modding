"""Sephiroth in Cloud's slot gets Cloud's level, field-action and riding animation sets (the burning Nibelheim walk of
chapter 1, crawl spaces, carts, ropes, the chocobo...), in FullyPlayableSephirothDataAssets_P:

  * the CharaSpec table: Cloud's slot rows (PC0000_00, 04, 08, 09, 10, 12, 18, 19, 23) list the level sets Cloud's own rows
    list (OverrideAnimationSetString_Array: FireWalk00, FireWalk01, DmgWalk00, GBike01, ... - the swap had left it empty, so
    the game had no set to put on him when a level asks for one: the T-pose in burning Nibelheim). Their
    AnimationSetParentFolder stays PC0010_Sephiroth (Sephiroth's own Climb00, Ladder00, Narrow00 keep playing);
  * new packages: every level, field-action and riding set of Cloud's that Sephiroth's folder lacks, as a copy of Cloud's in
    Sephiroth's folder (/Game/Motion/Level/FireWalk00/PC0010_Sephiroth, /Game/Motion/FieldAction/Tunnel00/PC0010_Sephiroth,
    /Game/Motion/Player/PC0010_Sephiroth/Mount00, ...): the game's set (UEndAnimSet) byte for byte but its names (the
    package, and the object for the PC0000_Cloud ones) and its public export hash; it plays Cloud's animations, which the
    PC0010_00 family (Create a Character System) moves onto Sephiroth's skeleton as they load. Its container header entry
    loads the packages its graph names (as the game's entries do: checked against pakchunk4's).
Everything else of the container byte for byte, with its header entry.
    build_fieldsets.py <out dir (new)> <FullyPlayableSephirothDataAssets_P.utoc> <set packages dir>..."""
import glob, io, contextlib, os, shutil, struct, sys
sys.path[:0] = ['/work/safer1016/tools', '/work/sephatb/tools', '/work/iostore', '/work/cs',
                '/work/tools', '/work/evil1013/tools', '/work/swap1012/tools', '/work/vincentfix',
                '/work/weap1012/tools', '/work/gunmoves', '/work/sephforms/tools', '/work/neutral20/tools']
import merge_fullyplayable as M
import build_atb as B
from iostore import Toc
from zen import Zen
import iostore_write as W
import hdr
import gameids
import zenrename
import align_moves as A

NAME = M.NAME
MOUNT = M.MOUNT
ROWS = ['PC0000_00_Cloud_Standard', 'PC0000_04_Cloud_ZackCostume', 'PC0000_08_Cloud_SoldierNoHelmet', 'PC0000_09_Cloud_CostaClothing',
        'PC0000_10_Cloud_CostaClothing2', 'PC0000_12_Cloud_ZackCostumeDirty', 'PC0000_18_Cloud_ZackCostumeAge21',
        'PC0000_19_Cloud_ZackCostumeDirtyAge21', 'PC0000_23_Cloud_ZackCostumeWet']
LIST = 'OverrideAnimationSetString_Array'
REFERENCE = 'PC0000_00_Cloud_Standard_NoBattle'   # a Cloud row the swap left as the game has it
CLOUD, SEPH = 'PC0000_Cloud', 'PC0010_Sephiroth'


def quiet(f, *a):
    with contextlib.redirect_stdout(io.StringIO()):
        return f(*a)


def imp(path):
    return (2 << 62) | (gameids.objhash(path) & ~(3 << 62))


def sephiroth_copy(data):
    """Cloud's set package -> the same set in Sephiroth's folder: (package bytes, its package name, its object path)."""
    z = Zen(data)
    old_pkg = z.names[z.name_mapped & 0x3FFFFFFF]
    assert z.names[z.srcname_mapped & 0x3FFFFFFF] == old_pkg and len(z.exports) == 1, old_pkg
    head, folder, obj = old_pkg.rsplit('/', 2)
    renames = {}
    if obj == CLOUD:                                   # /Game/Motion/{Level,FieldAction}/<Set>/PC0000_Cloud
        assert head in ('/Game/Motion/Level', '/Game/Motion/FieldAction') and z.exports[0]['name'] == CLOUD, old_pkg
        new_pkg = '%s/%s/%s' % (head, folder, SEPH)
        renames = {old_pkg: new_pkg, CLOUD: SEPH}
        assert z.names.count(CLOUD) == 1
        new_obj = SEPH
    else:                                              # /Game/Motion/Player/PC0000_Cloud/Mount00
        assert '%s/%s' % (head, folder) == '/Game/Motion/Player/' + CLOUD and z.exports[0]['name'] == obj, old_pkg
        new_pkg = '/Game/Motion/Player/%s/%s' % (SEPH, obj)
        renames = {old_pkg: new_pkg}
        new_obj = obj
    assert z.names.count(old_pkg) == 1 and new_pkg not in z.names
    object_path = '%s.%s' % (new_pkg, new_obj)
    assert z.exports[0]['global_import'] == imp('%s.%s' % (old_pkg, z.exports[0]['name'])), old_pkg
    out = zenrename.rebuild(data, renames, {0: imp(object_path)})
    # checks: the new names, the export's hash, the rest of the package as it was
    z2 = Zen(out)
    assert z2.names == [renames.get(n, n) for n in z.names]
    assert z2.names[z2.name_mapped & 0x3FFFFFFF] == new_pkg and z2.exports[0]['name'] == new_obj
    assert z2.exports[0]['global_import'] == imp(object_path)
    assert z2.imports == z.imports and z2.flags == z.flags
    for key in ('serial_offset', 'serial_size', 'outer', 'cls', 'super', 'template', 'oflags', 'fflags'):
        assert z2.exports[0][key] == z.exports[0][key], key
    assert out[z2.header_end:] == data[z.header_end:]
    assert out[z2.graph_off:z2.graph_off + z2.graph_size] == data[z.graph_off:z.graph_off + z.graph_size]
    return out, new_pkg, object_path


def main(out, base_utoc, dirs):
    assert not os.path.exists(out), out + ' exists (use a new folder)'
    PKG = gameids.load()[0]
    chunks, store = M.read(base_utoc)
    paths = [c['path'] for c in chunks]
    entries = []
    for c in chunks:
        if c['type'] == 2:
            se = store[c['id64']]
            entries.append(dict(id=c['id64'], size=se['size'], export_count=se['export_count'], export_bundle_count=se['export_bundle_count'],
                                load_order=se['load_order'], imports=list(se['imports'])))
    report = []
    # ---- the CharaSpec table: Cloud's level sets on Cloud's slot rows
    k = paths.index(B.CHARASPEC_TABLE)
    t = quiet(B.Table, chunks[k]['data'])
    before = {key: [t.get(t.row(key), f[0][0]) for f in t.fields] for key in t.at}
    ref = t.row(REFERENCE)
    sets = t.get(ref, LIST)
    assert 'FireWalk00' in sets and len(sets) == 20, sets
    for row in ROWS:
        r = t.row(row)
        assert t.get(r, LIST) == [], (row, t.get(r, LIST))
        assert t.get(r, 'AnimationSetParentFolder') == SEPH, row
        r[t.fi[LIST]] = list(ref[t.fi[LIST]])
    table = quiet(t.encode)
    t2 = quiet(B.Table, table)
    assert t2.keys == t.keys
    for key in t.at:
        now = [t2.get(t2.row(key), f[0][0]) for f in t2.fields]
        want = list(before[key])
        if key in ROWS:
            want[t.fi[LIST]] = sets
        assert now == want, key
    chunks[k]['data'] = table
    by = {e['id']: e for e in entries}
    e = by[chunks[k]['id64']]
    if e['size']:
        e['size'] = (e['size'] & (3 << 62)) | len(table)
    report.append('CharaSpec table: %s on %d rows (%s)' % (LIST, len(ROWS), ', '.join(sets)))
    # ---- Sephiroth's copies of Cloud's sets
    files = sorted(f for d in dirs for f in glob.glob(os.path.join(d, '*.uasset')))
    have = set(paths)
    added = []
    for f in files:
        data = open(f, 'rb').read()
        new, pkg, objpath = sephiroth_copy(data)
        rel = pkg[len('/Game/'):] + '.uasset'
        assert rel not in have, rel
        pid = W.package_id(pkg)
        assert pid not in PKG, pkg + ' is a package of the game'
        z = Zen(new)
        graph = zenrename.graph_imports(new)
        assert graph and all(p in PKG for p in graph), pkg
        chunks.append(dict(id64=pid, type=2, data=new, path=rel))
        entries.append(dict(id=pid, size=len(new), export_count=len(z.exports), export_bundle_count=1, load_order=0, imports=graph))
        have.add(rel)
        added.append(pkg)
    report.append('%d sets of Cloud\'s copied into Sephiroth\'s folder: %s' % (len(added), ', '.join(p.split('/Motion/', 1)[1] for p in added)))
    # ---- the container
    os.makedirs(out)
    cid = W.container_id_from_name(NAME)
    allchunks = [dict(id64=cid, type=10, data=W.container_header(cid, entries), path=None)] + chunks
    base = os.path.join(out, NAME)
    W.write_container(base, NAME, allchunks, mount=MOUNT)
    shutil.copy(base_utoc[:-len('.utoc')] + '.pak', base + '.pak')
    back = Toc(base + '.utoc')
    assert back.entries == len(allchunks)
    cid2, ents = hdr.parse_header(back.read(0))
    assert cid2 == cid and len(ents) == len(entries)
    old = Toc(base_utoc)
    old_by = {(old.chunk_id64(i), old.chunk_type(i)): i for i in range(old.entries)}
    byid = {e['id']: e for e in entries}
    changed = new_count = aligned = 0
    for i in range(1, back.entries):
        c = allchunks[i]
        data = back.read(i)
        assert data == c['data'] and back.chunk_id64(i) == c['id64'] and back.chunk_type(i) == c['type'], c['path']
        if c['path']:
            assert back.files.get(i) == MOUNT + c['path']
        key = (c['id64'], c['type'])
        if key not in old_by:
            new_count += 1
        elif data != old.read(old_by[key]):
            changed += 1
        if c['type'] == 2:
            e, b = byid[c['id64']], ents[c['id64']]
            assert (b['size'], b['export_count'], b['export_bundle_count'], b['load_order'], list(b['imports'])) == \
                   (e['size'], e['export_count'], e['export_bundle_count'], e['load_order'], e['imports']), c['path']
            if c['path'] and c['path'].startswith('RebirthSkelCompat/Built/'):
                aligned += A.verify(data, c['path'])
    assert changed == 1 and new_count == len(added), (changed, new_count)
    for line in report:
        print(line)
    print('%s: %d chunks (%d new, 1 changed: the CharaSpec table); read back as written; %d ACL blocks of the moves 16-aligned'
          % (NAME, len(allchunks) - 1, new_count, aligned))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
