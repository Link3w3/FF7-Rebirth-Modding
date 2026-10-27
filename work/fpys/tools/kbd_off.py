"""A copy of a container with the Bonamik / KineDriver lists of some meshes emptied: each mesh's SQEX_KBD_AssetUserData
export (the last of its package) is written with no properties (empty BonamikDataList and KineDriverDataList), so the
game puts no Bonamik or KineDriver on those meshes. Everything else is kept byte for byte (the Bonamik/KineDriver
packages stay, loaded but unused). The container keeps its name and id.
    kbd_off.py <base .utoc> <out dir (new)> <package path ending> [...]"""
import hashlib, os, shutil, struct, sys
sys.path[:0] = ['/work/iostore', '/work/cs', '/work/swap1012/tools', '/work/weap1012/tools',
                '/work/vincentfix', '/work/evil1013/tools']
from iostore import Toc
from hdr import parse_header
from zen import Zen
import iostore_write as W

EMPTY = b'\x00\x01' + b'\x00\x00\x00\x00'   # unversioned header: one last fragment, no values; then HasGuid = false


def kbd_off(data):
    z = Zen(data)
    pos = z.bundle_positions()
    ks = [k for k, e in enumerate(z.exports) if e['name'].startswith('SQEX_KBD_AssetUserData')]
    assert len(ks) == 1, [e['name'] for e in z.exports]
    k = ks[0]
    st, sz = pos[k]
    assert st + sz == len(data), 'the user data is not the last export'
    old = data[st:st + sz]
    assert old[-4:] == b'\0\0\0\0', old.hex()
    out = bytearray(data[:st] + EMPTY)
    o = z.exp_off + 72 * k
    so, ss = struct.unpack_from('<QQ', out, o)
    assert ss == sz
    struct.pack_into('<QQ', out, o, so, len(EMPTY))
    z2 = Zen(bytes(out))
    assert z2.bundle_positions()[k] == (st, len(EMPTY)) and z2.exports[k]['serial_size'] == len(EMPTY)
    return bytes(out), old


def main(base_utoc, out, *wanted):
    assert not os.path.exists(out), out + ' exists (use a new folder)'
    t = Toc(base_utoc)
    name = os.path.basename(base_utoc)[:-len('.utoc')]
    heads = [i for i in range(t.entries) if t.chunk_type(i) == 10]
    assert heads == [0], heads
    raw_header = t.read(0)
    cid, store = parse_header(raw_header)
    assert cid == t.container_id == W.container_id_from_name(name)
    entries = [dict(id=pid, size=e['size'], export_count=e['export_count'], export_bundle_count=e['export_bundle_count'],
                    load_order=e['load_order'], imports=list(e['imports'])) for pid, e in store.items()]
    assert W.container_header(cid, entries) == raw_header, 'the header does not write back as it is'
    by_id = {e['id']: e for e in entries}
    mount = None
    chunks, done = [None], []
    for i in range(1, t.entries):
        f = t.files.get(i)
        if mount is None and f:
            mount = f[:f.index('Content/') + len('Content/')]
        data = t.read(i)
        if t.chunk_type(i) == 2 and f and any(f.endswith(w) for w in wanted):
            data, old = kbd_off(data)
            e = by_id[t.chunk_id64(i)]
            if e['size']:
                e['size'] = len(data)
            done.append((f, old.hex(' ')))
        chunks.append(dict(id64=t.chunk_id64(i), type=t.chunk_type(i), data=data, path=f[len(mount):] if f else None))
    assert len(done) == len(wanted), (done, wanted)
    chunks[0] = dict(id64=cid, type=10, data=W.container_header(cid, entries), path=None)
    os.makedirs(out)
    base = os.path.join(out, name)
    assert W.write_container(base, name, chunks, mount=mount) == cid
    shutil.copy(base_utoc[:-len('.utoc')] + '.pak', base + '.pak')
    back = Toc(base + '.utoc')
    assert back.entries == t.entries and back.container_id == cid
    for i, c in enumerate(chunks):
        assert back.read(i) == c['data'] and back.chunk_id64(i) == c['id64'] and back.chunk_type(i) == c['type']
        assert back.files.get(i) == t.files.get(i), (i, back.files.get(i), t.files.get(i))
    for f, old in done:
        print('emptied the Bonamik/KineDriver lists of', f.rsplit('/', 1)[-1], '(was', old + ')')
    for f in sorted(os.listdir(out)):
        p = os.path.join(out, f)
        print('  %-28s %9d %s' % (f, os.path.getsize(p), hashlib.md5(open(p, 'rb').read()).hexdigest()))


if __name__ == '__main__':
    main(*sys.argv[1:])
