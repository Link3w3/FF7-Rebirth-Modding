"""A copy of a container with one mesh's Bonamik list emptied and its KineDriver list kept: the mesh's
SQEX_KBD_AssetUserData export (the last of its package; unversioned properties) holds BonamikDataList (property 0) and
KineDriverDataList (property 2); it is written with property 2 only, so the game runs the mesh's KineDriver (its KDI)
but no Bonamik (KawaiiPhysics moves those bones instead: Create a Character System 3.14.0). Everything else is kept
byte for byte (the BNM packages stay, loaded but unused). The container keeps its name and id. The inverse of
kdi_off.py.
    bnm_off.py <base .utoc> <out dir (new)> <package path ending>"""
import hashlib, os, shutil, struct, sys
sys.path[:0] = ['/work/fpys/tools', '/work/iostore', '/work/cs', '/work/swap1012/tools',
                '/work/weap1012/tools', '/work/vincentfix', '/work/evil1013/tools']
from iostore import Toc
from hdr import parse_header
from zen import Zen
import iostore_write as W


def bnm_off(data):
    z = Zen(data)
    pos = z.bundle_positions()
    ks = [k for k, e in enumerate(z.exports) if e['name'].startswith('SQEX_KBD_AssetUserData')]
    assert len(ks) == 1, [e['name'] for e in z.exports]
    k = ks[0]
    st, sz = pos[k]
    assert st + sz == len(data), 'the user data is not the last export'
    old = data[st:st + sz]
    # two fragments: property 0 (one value), then skip 1, property 2 (one value, last)
    frag1, frag2 = struct.unpack_from('<HH', old, 0)
    assert frag1 == (1 << 9) and frag2 == (1 << 9) | (1 << 8) | 1, old.hex(' ')
    o = 4
    nb = struct.unpack_from('<i', old, o)[0]
    bonamik = struct.unpack_from('<%di' % nb, old, o + 4)
    o += 4 + 4 * nb
    nk = struct.unpack_from('<i', old, o)[0]
    kine = old[o:o + 4 + 4 * nk]
    o += 4 + 4 * nk
    assert old[o:] == b'\0\0\0\0', old.hex(' ')
    assert nb > 0 and nk > 0, (nb, nk)
    new = struct.pack('<H', (1 << 9) | (1 << 8) | 2) + kine + b'\0\0\0\0'   # skip 2: property 2 only (one value, last)
    out = bytearray(data[:st] + new)
    eo = z.exp_off + 72 * k
    so, ss = struct.unpack_from('<QQ', out, eo)
    assert ss == sz
    struct.pack_into('<QQ', out, eo, so, len(new))
    z2 = Zen(bytes(out))
    assert z2.bundle_positions()[k] == (st, len(new)) and z2.exports[k]['serial_size'] == len(new)
    return bytes(out), old, new, bonamik, nk


def main(base_utoc, out, wanted):
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
        if t.chunk_type(i) == 2 and f and f.endswith(wanted):
            data, old, new, bonamik, nk = bnm_off(data)
            e = by_id[t.chunk_id64(i)]
            if e['size']:
                e['size'] = len(data)
            done.append((f, old.hex(' '), new.hex(' '), bonamik, nk))
        chunks.append(dict(id64=t.chunk_id64(i), type=t.chunk_type(i), data=data, path=f[len(mount):] if f else None))
    assert len(done) == 1, done
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
    for f, old, new, bonamik, nk in done:
        print('%s: Bonamik list emptied (it named import(s) %s), its %d KineDriver kept\n  was %s\n  now %s' % (
            f.rsplit('/', 1)[-1], [-1 - x for x in bonamik], nk, old, new))
    for f in sorted(os.listdir(out)):
        p = os.path.join(out, f)
        print('  %-28s %9d %s' % (f, os.path.getsize(p), hashlib.md5(open(p, 'rb').read()).hexdigest()))


if __name__ == '__main__':
    main(*sys.argv[1:4])
