"""FullyPlayableYoungSephirothDataAssets_P v6: v5c with Young Sephiroth's own voice bank in his packs. Cloud's 9 character
packs (the rows he spawns from) list the young voice bank (VO_PC0010_13_YoungSephiroth, YoungSephirothVoice_P: the JP
package, the one everything imports; the game loads the voice language's in its place) next to Sephiroth's
VO_PC0010_00_Sephiroth in their asset list, so the game loads both with him: the forms speak with the young one and
OLDER SEPHIROTH with Sephiroth's (Create a Character System 3.9 "voice"). Each pack: one import added, the list's array
one longer (its three size fields), the graph and the header entry name the bank's package. Everything else of v5c is
byte for byte; the container keeps its name and id.
    build_fpys_data_v6.py <out dir (new)> <v5c .utoc>"""
import hashlib, os, shutil, struct, sys
sys.path[:0] = ['/work/fpys/tools', '/work/evilboss1016/data', '/work/iostore', '/work/cs',
                '/work/weap1012/tools', '/work/evil1013/tools', '/work/swap1012/tools', '/work/vincentfix']
from zen import Zen
from iostore import Toc
import iostore_write as W
import gameids
import hdr
import build_evilcloud_data as BED
import build_fpys_data as B

OLD_VOICE = '/Game/Sound/Voice/JP/Character/Player/VO_PC0010_00_Sephiroth'
YOUNG_VOICE = '/Game/Sound/Voice/JP/Character/Player/VO_PC0010_13_YoungSephiroth'
NULL = 0xFFFFFFFFFFFFFFFF


def imp(path):
    return (2 << 62) | gameids.objhash(path)


def leaf(p):
    return p.rsplit('/', 1)[1]


class Tags:
    """The tagged properties of an export (UE 4.26): each tag's position, name, type and size."""
    def __init__(self, names, b):
        self.names, self.b = names, b

    def fname(self, o):
        i, n = struct.unpack_from('<II', self.b, o)
        s = self.names[i]
        return (s if n == 0 else '%s_%d' % (s, n - 1)), o + 8

    def tag(self, o):
        start = o
        name, o = self.fname(o)
        if name == 'None':
            return dict(name=name, start=start, value=o, end=o)
        typ, o = self.fname(o)
        size_at = o
        size, _ = struct.unpack_from('<ii', self.b, o)
        o += 8
        extra = None
        if typ == 'StructProperty':
            extra, o = self.fname(o)
            o += 16
        elif typ in ('ArrayProperty', 'ByteProperty', 'EnumProperty', 'SetProperty'):
            extra, o = self.fname(o)
        elif typ == 'BoolProperty':
            o += 1
        if self.b[o]:
            o += 17
        else:
            o += 1
        return dict(name=name, type=typ, extra=extra, start=start, size_at=size_at, size=size, value=o, end=o + size)


def add_voice(data, old_obj, new_obj):
    """The pack with `new_obj` imported and listed right after `old_obj` in its AssetDataList entry."""
    z = Zen(data)
    old = imp(old_obj)
    assert z.imports.count(old) == 1, 'the pack does not import ' + old_obj
    assert imp(new_obj) not in z.imports
    old_index = -1 - z.imports.index(old)
    new_index = -1 - len(z.imports)            # appended
    start, size = z.bundle_positions()[0]
    assert len(z.exports) == 1
    e = bytearray(data[start:start + size])
    t = Tags(z.names, e)
    top = t.tag(0)
    assert top['name'] == 'AssetDataList' and top['type'] == 'ArrayProperty' and top['extra'] == 'StructProperty', top
    count = struct.unpack_from('<i', e, top['value'])[0]
    inner = t.tag(top['value'] + 4)
    assert inner['type'] == 'StructProperty' and inner['extra'] == 'EndAssetData'
    o = inner['value']
    hit = None
    for _ in range(count):
        while True:
            p = t.tag(o)
            if p['name'] == 'None':
                o = p['end']
                break
            if p['name'] == 'AssetUserData':
                assert p['type'] == 'ArrayProperty' and p['extra'] == 'ObjectProperty'
                n = struct.unpack_from('<i', e, p['value'])[0]
                objs = list(struct.unpack_from('<%di' % n, e, p['value'] + 4))
                if old_index in objs:
                    assert hit is None, 'the voice is listed twice'
                    hit = (p, n, objs)
            o = p['end']
    assert hit, 'no entry lists ' + old_obj
    p, n, objs = hit
    at = p['value'] + 4 + 4 * (objs.index(old_index) + 1)
    e[at:at] = struct.pack('<i', new_index)
    struct.pack_into('<i', e, p['value'], n + 1)
    struct.pack_into('<i', e, p['size_at'], p['size'] + 4)
    struct.pack_into('<i', e, inner['size_at'], inner['size'] + 4)
    struct.pack_into('<i', e, top['size_at'], top['size'] + 4)
    assert start == z.header_end and start + size == len(data)
    # the header: the import appended, the export 4 bytes longer, the bank's package in the graph (by id, one arc)
    imports = z.imports + [imp(new_obj)]
    new_pid = W.package_id(new_obj.split('.')[0])
    g = B.graph_entries(data)
    assert new_pid not in [x for x, _ in g]
    g = sorted(g + [(new_pid, struct.pack('<i', 1) + struct.pack('<ii', 0, 0))], key=lambda x: x[0])
    gb = bytearray(struct.pack('<i', len(g)))
    for pid, rest in g:
        gb += struct.pack('<Q', pid) + rest
    head = bytearray(data[:z.imp_off])
    head += b''.join(struct.pack('<Q', v) for v in imports)
    exp = bytearray(data[z.exp_off:z.eb_off])
    struct.pack_into('<Q', exp, 8, z.exports[0]['serial_size'] + 4)
    eb = data[z.eb_off:z.graph_off]
    delta = 8
    exp_off, eb_off, graph_off = z.exp_off + delta, z.eb_off + delta, z.graph_off + delta
    head += exp + eb + gb
    struct.pack_into('<iiiii', head, 40, z.imp_off, exp_off, eb_off, graph_off, len(gb))
    out = bytes(head) + bytes(e)
    c = Zen(out)
    assert c.imports == imports and c.exports[0]['serial_size'] == size + 4 and c.header_end == len(head)
    assert [x for x, _ in B.graph_entries(out)] == [x for x, _ in g]
    return out, new_pid, (n, n + 1)


def check_pack(data, old_obj, new_obj):
    z = Zen(data)
    start, size = z.bundle_positions()[0]
    e = data[start:start + size]
    t = Tags(z.names, e)
    o = 0
    seen = []
    def walk(o, end):
        while o < end:
            p = t.tag(o)
            if p['name'] == 'None':
                return p['end']
            if p['type'] == 'ArrayProperty' and p['extra'] == 'StructProperty':
                cnt = struct.unpack_from('<i', e, p['value'])[0]
                inner = t.tag(p['value'] + 4)
                q = inner['value']
                for _ in range(cnt):
                    q = walk(q, inner['end'])
                assert q == inner['end'] == p['end'], (q, inner['end'], p['end'])
            elif p['type'] == 'ArrayProperty' and p['extra'] == 'ObjectProperty':
                cnt = struct.unpack_from('<i', e, p['value'])[0]
                assert p['size'] == 4 + 4 * cnt
                seen.extend(z.imports[-1 - v] for v in struct.unpack_from('<%di' % cnt, e, p['value'] + 4) if v < 0)
            o = p['end']
        return o
    end = walk(0, len(e))
    assert end <= len(e)
    assert imp(old_obj) in seen and imp(new_obj) in seen
    return len(seen)


def main(out, base_utoc):
    assert not os.path.exists(out), out + ' exists (use a new folder)'
    base_ucas = base_utoc[:-len('.utoc')] + '.ucas'
    old = Toc(base_utoc)
    assert [i for i in range(old.entries) if old.chunk_type(i) == 10] == [0]
    cid, store = hdr.parse_header(old.read(0))
    assert cid == W.container_id_from_name(B.NAME)
    order = [old.chunk_id64(i) for i in range(old.entries) if old.chunk_type(i) == 2]
    entries = [dict(id=p, size=store[p]['size'], export_count=store[p]['export_count'], export_bundle_count=store[p]['export_bundle_count'],
                    load_order=store[p]['load_order'], imports=list(store[p]['imports'])) for p in order]
    assert W.container_header(cid, entries) == old.read(0), 'the header does not write back as it is'
    entry_of = {e['id']: e for e in entries}
    by_path = {old.files[i][len(B.MOUNT):]: i for i in old.files}
    old_obj = OLD_VOICE + '.' + leaf(OLD_VOICE)
    new_obj = YOUNG_VOICE + '.' + leaf(YOUNG_VOICE)
    changes, report = {}, []
    for row in B.CHAR_PACKS:
        i = by_path[B.PACK % row]
        data = old.read(i)
        new, new_pid, (n0, n1) = add_voice(data, old_obj, new_obj)
        listed = check_pack(new, old_obj, new_obj)
        e = entry_of[old.chunk_id64(i)]
        assert e['size'] in (0, len(data)) and e['export_count'] == 1, (row, e['size'], len(data))
        if e['size']:
            e['size'] = len(new)   # (an entry of 0 stays 0, as FPS has it)
        assert new_pid not in e['imports']
        e['imports'] = e['imports'] + [new_pid]
        changes[i] = new
        report.append('CharaSpec_%s: lists %s (its entry %d -> %d objects; %d -> %d bytes; %d objects in its lists)' % (
            row, leaf(YOUNG_VOICE), n0, n1, len(data), len(new), listed))
    changes[0] = W.container_header(cid, entries)
    os.makedirs(out)
    path = os.path.join(out, B.NAME)
    BED.append_container(old, base_ucas, changes, [], path + '.utoc', path + '.ucas.tail')
    with open(path + '.ucas', 'wb') as f:
        with open(base_ucas, 'rb') as g:
            shutil.copyfileobj(g, f, 1 << 24)
        f.write(open(path + '.ucas.tail', 'rb').read())
    shutil.copy(base_utoc[:-len('.utoc')] + '.pak', path + '.pak')
    new = Toc(path + '.utoc')
    assert new.container_id == cid and new.entries == old.entries
    same = 0
    for k in range(new.entries):
        d = new.read(k)
        assert hashlib.sha1(d).digest() == new.b[new.metas_off + 33 * k:new.metas_off + 33 * k + 20]
        if k in changes:
            assert d == changes[k]
        else:
            assert d == old.read(k) and new.files.get(k) == old.files.get(k)
            same += 1
    cid2, ents = hdr.parse_header(new.read(0))
    for e in entries:
        b = ents[e['id']]
        for key in ('size', 'export_count', 'export_bundle_count', 'load_order', 'imports'):
            assert b[key] == e[key], key
    report.append('%d chunks byte for byte v5c\'s; the header and %d packs changed' % (same, len(changes) - 1))
    for line in report:
        print(line)
    for f in sorted(os.listdir(out)):
        p = os.path.join(out, f)
        print('  %-48s %10d %s' % (f, os.path.getsize(p), hashlib.md5(open(p, 'rb').read()).hexdigest()))


if __name__ == '__main__':
    main(*sys.argv[1:3])
