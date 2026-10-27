"""VincentChaos_P without Chaos's Bonamik (his wing physics, PC0011_10_BNM: Bonamik 2.x data that crashes the game):
  * the PC0011_10 mesh no longer lists its asset user data (its "AssetUserData" property tag renamed to a name the
    SkeletalMesh class does not have, so the game's loader skips the property by its size: nothing else in the package
    moves), and that user data (SQEX_KBD_AssetUserData_0) no longer lists the Bonamik asset (its "BonamikDataList"
    tag renamed the same way),
  * the Bonamik asset itself left out of the container (and out of the mesh's imported packages), so it never loads,
everything else as installed; every chunk read back and checked.
    chaos_no_bonamik.py <installed VincentChaos_P dir> <out dir (new)>"""
import os, struct, sys
sys.path[:0] = ['/work/iostore', '/work/cs', '/work/swap1012/tools', '/work/sephforms/tools',
                '/work/shooter1016/tools']
import build_dirge_paks as P
import align_moves as A
import iostore_write as W
from zen import Zen

NAME = 'VincentChaos_P'
MESH = 'Character/Player/PC0011_10_Chaos/Model/PC0011_10.uasset'
BNM = 'Character/Player/PC0011_10_Chaos/Model/PC0011_10_BNM.uasset'
# (export, property tag to hide, the name it gets: one its class does not have)
HIDE = [('PC0011_10', 'AssetUserData', 'BonamikDataList'), ('SQEX_KBD_AssetUserData_0', 'BonamikDataList', 'AssetUserData')]


def tags(blob, names):
    """The tagged properties of an export: (offset of the tag, name, type, size of the value)."""
    out, j = [], 0
    def fname(k):
        i, n = struct.unpack_from('<iI', blob, k)
        return names[i] if 0 <= i < len(names) else None
    while j + 8 <= len(blob):
        start = j
        name = fname(j)
        if name is None:
            raise ValueError('not a tag at %d' % j)
        j += 8
        if name == 'None':
            break
        typ = fname(j); j += 8
        size, index = struct.unpack_from('<ii', blob, j); j += 8
        if typ == 'StructProperty':
            j += 8 + 16
        elif typ == 'BoolProperty':
            j += 1
        elif typ in ('ByteProperty', 'EnumProperty', 'ArrayProperty', 'SetProperty'):
            j += 8
        elif typ == 'MapProperty':
            j += 16
        has_guid = blob[j]; j += 1
        if has_guid:
            j += 16
        out.append((start, name, typ, size))
        j += size
    return out


def main(base_dir, out):
    assert not os.path.exists(out), out + ' exists (use a new folder)'
    chunks, store = P.read(os.path.join(base_dir, NAME + '.utoc'))
    by = {c['path']: c for c in chunks if c['path']}
    mesh = by[MESH]
    bnm_id = by[BNM]['id64']
    data = bytearray(mesh['data'])
    z = Zen(bytes(data))
    spans = {z.exports[i]['name']: (s, e) for i, s, e in A.export_spans(bytes(data), z)}
    report = []
    for export, prop, other in HIDE:
        s, e = spans[export]
        found = [t for t in tags(bytes(data[s:e]), z.names) if t[1] == prop]
        assert len(found) == 1, (export, prop, found)
        at = s + found[0][0]
        assert other in z.names and prop in z.names
        struct.pack_into('<i', data, at, z.names.index(other))
        report.append('%s: its %s (%s, %d bytes) is skipped now (the tag is named %s)' % (export, prop, found[0][2], found[0][3], other))
    # read back: the tags as meant
    z2 = Zen(bytes(data))
    for export, prop, other in HIDE:
        s, e = spans[export]
        names = [t[1] for t in tags(bytes(data[s:e]), z2.names)]
        assert prop not in names and other in names, (export, names)
    kept = []
    for c in chunks:
        if c['path'] == BNM:
            continue
        c = dict(c)
        if c['path'] == MESH:
            c['data'] = bytes(data)
        kept.append(c)
    entries = []
    for c in kept:
        if c['type'] != 2:
            continue
        e = P.entry(c, store[c['id64']])
        if c['path'] == MESH:
            assert bnm_id in e['imports']
            e['imports'] = [i for i in e['imports'] if i != bnm_id]
        assert bnm_id not in e['imports'], c['path']
        entries.append(e)
    anims, blocks = P.lay_out(kept, entries)
    os.makedirs(out)
    cid, files = P.write(out, NAME, kept, entries, os.path.join(base_dir, NAME + '.pak'))
    report.append('%s: %d packages (%d animations laid out, %d ACL blocks), the Bonamik asset left out; %s' % (NAME, len(entries), anims, blocks, files))
    open(os.path.join(out, 'no_bonamik_report.txt'), 'w').write('\n'.join(report) + '\n')
    print('\n'.join(report))


if __name__ == '__main__':
    main(*sys.argv[1:3])
