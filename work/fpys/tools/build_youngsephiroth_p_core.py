"""YoungSephiroth_P with a hair core: Young Sephiroth's model PC0010_13 gets the End project's new cook of it (the same
scene, rig, wing and slots, plus the section PC0010_13_HairCore: an opaque shell over his scalp and the back of his
neck, under his hair cards, as Rebirth's characters have), and the core's material instance PC0010_13_HairCore (a copy
of his PC0010_13_Hair on RMI_Surface_Hair_Wide with its Coverage white; its BasePropertyOverrides put in the game's
layout, micfix). Everything else is the base container's, byte for byte: his skeleton, Bonamik, the wing's Bonamik, the
wing's KineDriver with its fixed curves (the editor's copy has the spans the dump lost: never re-cooked), his other
material instances and textures, the Nameless. The container keeps its name and id.
Checks: the new mesh is the one the blueprints import (same path and export), its root at scale 1, one Asset User Data
export with the same three lists; every import here or the game's; load orders (each package after the ones here it
imports); the container read back.
    build_youngsephiroth_p_core.py <base YoungSephiroth_P.utoc> <zen YS13Zen4.utoc> <out dir (new)>"""
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
import gameids
import pack
import micfix
import flatroot
import build_youngsephiroth_p as YSB

NAME = 'YoungSephiroth_P'
MOUNT = '../../../End/Content/'
YS = '/Game/Character/Player/PC0010_13_Young_Sephiroth/'
MESH = YS + 'Model/PC0010_13'
CORE_MI = YS + 'Material/PC0010_13_HairCore'
KDI = YS + 'Model/PC0010_13_KDI'


def imp(path):
    return (2 << 62) | gameids.objhash(path)


def leaf(p):
    return p.rsplit('/', 1)[1]


def kbd_lists(data):
    """the mesh's SQEX_KBD_AssetUserData exports -> [(Bonamik imports, KineDriver imports)] as their import hashes"""
    z = Zen(data)
    pos = z.bundle_positions()
    out = []
    for k, e in enumerate(z.exports):
        if not e['name'].startswith('SQEX_KBD_AssetUserData'):
            continue
        st, sz = pos[k]
        b = data[st:st + sz]
        f1, f2 = struct.unpack_from('<HH', b, 0)
        o = 4
        nb = struct.unpack_from('<i', b, o)[0]
        bon = struct.unpack_from('<%di' % nb, b, o + 4)
        o += 4 + 4 * nb
        nk = struct.unpack_from('<i', b, o)[0]
        kin = struct.unpack_from('<%di' % nk, b, o + 4)
        out.append(([z.imports[-1 - x] for x in bon], [z.imports[-1 - x] for x in kin]))
    return out


def main(base_utoc, zen_utoc, out):
    assert not os.path.exists(out), out + ' exists (use a new folder)'
    game = YSB.ids_of_files(line.rstrip('\n').split('\t')[-1] for line in gzip.open(YSB.GAME_FILES, 'rt'))
    base = Toc(base_utoc)
    assert [i for i in range(base.entries) if base.chunk_type(i) == 10] == [0]
    cid, store = parse_header(base.read(0))
    assert cid == W.container_id_from_name(NAME)
    zt = Toc(zen_utoc)
    zh = [i for i in range(zt.entries) if zt.chunk_type(i) == 10]
    assert len(zh) == 1
    _, zstore = parse_header(zt.read(zh[0]))
    newpk = {}
    for i in range(zt.entries):
        if zt.chunk_type(i) == 10:
            continue
        assert zt.chunk_type(i) == 2, ('a chunk this builder does not expect', zt.files.get(i), zt.chunk_type(i))
        d = zt.read(i)
        z = Zen(d)
        newpk[z.mapped(z.name_mapped)] = (zt.chunk_id64(i), d)
    assert set(newpk) == {MESH, CORE_MI}, sorted(newpk)
    report = []

    # the mesh
    mid, mdata = newpk[MESH]
    assert mid == W.package_id(MESH)
    mz = Zen(mdata)
    ex = [k for k, e in enumerate(mz.exports) if e['name'] == 'PC0010_13']
    assert len(ex) == 1
    assert mz.exports[ex[0]]['global_import'] == imp(MESH + '.PC0010_13'), 'the blueprints would not find it'
    st, sz = mz.bundle_positions()[ex[0]]
    p, n = flatroot._find_refskel(mz.names, mdata[st:st + sz])
    assert p is not None
    _, rot, tr, sc = flatroot._root(mdata[st:st + sz], p, n)
    assert abs(sc[0] - 1.0) < 1e-4, ('root scale', sc)
    report.append('PC0010_13: %d bones, root at scale %.4f' % (n, sc[0]))
    old_mesh = None
    for i in range(1, base.entries):
        if base.chunk_type(i) == 2 and base.chunk_id64(i) == mid:
            old_mesh = base.read(i)
    assert old_mesh is not None
    kb_new, kb_old = kbd_lists(mdata), kbd_lists(old_mesh)
    assert len(kb_new) == 1 and len(kb_old) == 1, (len(kb_new), len(kb_old))
    assert [sorted(x) for x in kb_new[0]] == [sorted(x) for x in kb_old[0]], 'the Asset User Data lists differ'
    assert imp(KDI + '.' + leaf(KDI)) in kb_new[0][1], 'no KineDriver'
    report.append('PC0010_13: Asset User Data as before (%d Bonamik, %d KineDriver)' % (len(kb_new[0][0]), len(kb_new[0][1])))

    # the core's material instance
    cmid, cdata = newpk[CORE_MI]
    assert cmid == W.package_id(CORE_MI) and cmid not in store and cmid not in game
    cdata, notes = micfix.fix_package(cdata)
    for nn in notes:
        report.append('PC0010_13_HairCore: material fix %s %s -> %s, kept %s, left out %s' % (nn['export'], nn['size'][0], nn['size'][1], nn['kept'], nn['dropped']))
    cz = Zen(cdata)
    assert cz.mapped(cz.name_mapped) == CORE_MI

    chunks, entries, names = [None], {}, {}
    replaced = False
    for i in range(1, base.entries):
        f = base.files.get(i)
        data = base.read(i)
        pid = base.chunk_id64(i)
        kind = base.chunk_type(i)
        pkg = '/Game/' + f[len(MOUNT):].rsplit('.', 1)[0]
        if pid == mid:
            assert kind == 2, ('the old mesh has a chunk of kind', kind)
            data = mdata
            se = zstore[mid]
            e = dict(id=pid, size=se['size'], export_count=se['export_count'], export_bundle_count=se['export_bundle_count'],
                     load_order=0, imports=list(se['imports']))
            assert e['export_count'] == len(mz.exports) and e['export_bundle_count'] == pack._bundle_count(mz)
            if e['size']:
                e['size'] = len(data)
            replaced = True
            report.append('PC0010_13: replaced (%d -> %d bytes, %d -> %d exports, imports %d -> %d)' % (
                len(old_mesh), len(mdata), store[pid]['export_count'], e['export_count'], len(store[pid]['imports']), len(e['imports'])))
            entries[pid] = e
            names[pid] = pkg
        elif kind == 2:
            se = store[pid]
            entries[pid] = dict(id=pid, size=se['size'], export_count=se['export_count'], export_bundle_count=se['export_bundle_count'],
                                load_order=se['load_order'], imports=list(se['imports']))
            names[pid] = pkg
        chunks.append(dict(id64=pid, type=kind, data=data, path=f[len(MOUNT):]))
    assert replaced
    se = zstore[cmid]
    chunks.append(dict(id64=cmid, type=2, data=cdata, path=CORE_MI[len('/Game/'):] + '.uasset'))
    entries[cmid] = dict(id=cmid, size=se['size'] and len(cdata), export_count=len(cz.exports), export_bundle_count=pack._bundle_count(cz),
                         load_order=0, imports=list(se['imports']))
    assert entries[cmid]['export_count'] == se['export_count'] and entries[cmid]['export_bundle_count'] == se['export_bundle_count']
    names[cmid] = CORE_MI
    report.append('PC0010_13_HairCore: added (%d bytes, %d imported packages)' % (len(cdata), len(se['imports'])))

    # load orders: each package after the ones here it imports
    order = {}

    def lo(pid, stack=()):
        if pid in order:
            return order[pid]
        assert pid not in stack, 'import cycle'
        deps = [lo(i, stack + (pid,)) for i in entries[pid]['imports'] if i in entries]
        order[pid] = 1 + max(deps or [0])
        return order[pid]
    for e in entries.values():
        e['load_order'] = 1000 + lo(e['id'])
    here = set(entries)
    unknown = sorted({'%016x (imported by %s)' % (i, leaf(names[e['id']])) for e in entries.values() for i in e['imports'] if i not in here and i not in game})
    assert not unknown, unknown
    assert cmid in entries[mid]['imports'], 'the mesh does not import the core material'
    ent_list = [entries[c['id64']] for c in chunks[1:] if c['type'] == 2]
    chunks[0] = dict(id64=cid, type=10, data=W.container_header(cid, ent_list), path=None)
    os.makedirs(out)
    basep = os.path.join(out, NAME)
    assert W.write_container(basep, NAME, chunks, mount=MOUNT) == cid
    shutil.copy(base_utoc[:-len('.utoc')] + '.pak', basep + '.pak')
    back = Toc(basep + '.utoc')
    assert back.container_id == cid and back.entries == len(chunks)
    for i, c in enumerate(chunks):
        assert back.read(i) == c['data'] and back.chunk_id64(i) == c['id64'] and back.chunk_type(i) == c['type']
        if c['path']:
            assert back.files.get(i) == MOUNT + c['path'], (back.files.get(i), c['path'])
    cid2, ents = parse_header(back.read(0))
    assert cid2 == cid and set(ents) == here
    for e in ent_list:
        b = ents[e['id']]
        for k in ('size', 'export_count', 'export_bundle_count', 'load_order', 'imports'):
            assert b[k] == e[k], (k, names[e['id']])
    # every other chunk byte for byte the base's
    same = 0
    for i in range(1, base.entries):
        pid, kind = base.chunk_id64(i), base.chunk_type(i)
        if pid == mid:
            continue
        j = [k for k in range(1, back.entries) if back.chunk_id64(k) == pid and back.chunk_type(k) == kind]
        assert len(j) == 1 and back.read(j[0]) == base.read(i), names.get(pid, hex(pid))
        same += 1
    report.append('%d other chunks byte for byte the base\'s (the fixed KineDriver among them)' % same)
    for line in report:
        print(line)
    print('%s: %d packages, %d bulk chunks; every import here or the game\'s' % (NAME, len(ent_list), sum(1 for c in chunks[1:] if c['type'] == 3)))
    for f in sorted(os.listdir(out)):
        p = os.path.join(out, f)
        print('  %-30s %9d %s' % (f, os.path.getsize(p), hashlib.md5(open(p, 'rb').read()).hexdigest()))


if __name__ == '__main__':
    main(*sys.argv[1:4])
