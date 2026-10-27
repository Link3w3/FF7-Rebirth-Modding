"""SoraOverCloudMotion_P: Sora's riding, field-action and level animations in Cloud's own motion folders as well.

Some of the game asks for Cloud's motion folder by name, whatever the CharaSpec row's AnimationSetParentFolder says: the
riding sets come from DataAsset/Game/AnimSet/AnimSet_PC0000_Cloud_Mount00 (and _Mount01 ... _Mount33), which name
/Game/Motion/Player/PC0000_Cloud/Mount00 itself, and AnimSet_Hub00_PC0000_Cloud, _Capture00_, _GBike02_, _MoogleCapture0x_,
_SaboSearch00_ and _Wheelie00_ do the same for field-action and level sets. Those sets are Cloud's, on Cloud's skeleton,
and Sora (Cloud's AnimBlueprint running on Sora's skeleton) plays nothing from them: the T-pose on a chocobo.

So every set and animation of Sora's in SoraAssets_P under
    Motion/Player/PC0000_00_Sora_KH2/Mount??          (the riding sets)
    Motion/FieldAction/<set>/PC0000_00_Sora_KH2       (field actions)
    Motion/Level/<set>/PC0000_00_Sora_KH2             (level sets)
goes in this container a second time under Cloud's folder name (PC0000_Cloud), over the game's own packages there:
  * each package is Sora's byte for byte but its names: its package name, a field-action or level set's object (named
    after its folder) and each public export's hash (the object path the game looks it up by);
  * what it imports stays Sora's (his skeleton, his animations at his own paths): a copied set plays the very animations
    his own set plays, and a copied animation or blend space is his;
  * animation packages are laid out again the way the game reads them (header end aligned, exports at 16-aligned cooked
    offsets) and checked against the emulation of the game's reader (build_sora_assets.verify_anim);
  * load order: after the packages of SoraAssets_P each imports.
Cloud packages there that Sora has no copy of stay the game's (3: two AnimComposites the sets do not use and the G-Bike's
G_Guard01_F2, which is not ACL-compressed).

    build_overcloud.py <SoraAssets_P.utoc> <out dir (new)> [name]
"""
import hashlib, os, re, shutil, struct, sys
sys.path[:0] = ['/work/soradata', '/work/iostore', '/work/cs', '/work/swap1012/tools',
                '/work/sephforms/tools', '/work/shooter1016/tools', '/work/fx1018/editor/Python',
                '/work/weap1012/tools']
import build_sora_assets as B
from build_sora_assets import A, W, hdr, Toc, Zen, Package
import zenrename as ZR
import gameids

SORA, CLOUD = 'PC0000_00_Sora_KH2', 'PC0000_Cloud'
NULL = 0xFFFFFFFFFFFFFFFF
MOUNT = B.MOUNT
WANTED = (re.compile(r'Motion/Player/%s/Mount\d\d(\.uasset$|/)' % SORA),
          re.compile(r'Motion/(FieldAction|Level)/[^/]+/%s(\.uasset$|/)' % SORA))


def imp(path):
    return (2 << 62) | gameids.objhash(path)


def cloud_path(p):
    """/Game/Motion/.../PC0000_00_Sora_KH2[/...] -> the same under PC0000_Cloud (the folder component only)"""
    parts = p.split('/')
    assert parts.count(SORA) == 1, p
    return '/'.join(CLOUD if x == SORA else x for x in parts)


def no_pad(d):
    """The package without zero padding between its export bundles and its import graph (realign's padding: realign pads
    again, and the bundle parser allows less than 16 bytes of it)."""
    z = Zen(d)
    region = d[z.eb_off:z.graph_off]
    n = len(z.exports)
    for nb in range(1, 9):
        hdrs = [struct.unpack_from('<II', region, 8 * i) for i in range(nb)]
        total = sum(c for f, c in hdrs)
        size = 8 * nb + 8 * total
        if size == len(region) or (size < len(region) < size + A.ALIGN and not any(region[size:])):
            break
    else:
        raise ValueError('export bundles do not parse')
    assert total == 2 * n, (total, n)
    pad = len(region) - size
    if not pad:
        return d
    out = bytearray(d[:z.eb_off + size]) + d[z.graph_off:]
    struct.pack_into('<i', out, 52, z.graph_off - pad)       # GraphDataOffset
    back = Zen(bytes(out))
    assert back.header_end == z.header_end - pad and out[back.header_end:] == d[z.header_end:]
    return bytes(out)


def copy_package(data, label):
    """Sora's package -> the same package in Cloud's folder: (bytes, old package name, new package name)."""
    z = Zen(data)
    idx, num = z.name_mapped & 0x3FFFFFFF, z.name_mapped >> 32
    assert z.srcname_mapped == z.name_mapped, label
    base = z.names[idx]
    old_pkg = base if num == 0 else '%s_%d' % (base, num - 1)
    assert '/Game/' + label[:-len('.uasset')] == old_pkg, (label, old_pkg)
    new_pkg = cloud_path(old_pkg)
    renames = {base: cloud_path(base)}
    folder_object = old_pkg.endswith('/' + SORA)          # a field-action or level set: its object is named after its folder
    if folder_object:
        assert len(z.exports) == 1 and z.exports[0]['name'] == SORA and z.names.count(SORA) == 1, label
        renames[SORA] = CLOUD
    low = [n.lower() for n in z.names]
    for a, b in renames.items():
        assert z.names.count(a) == 1 and b.lower() not in low and b.isascii(), (label, a, b)
    gis = {}
    for i, e in enumerate(z.exports):
        if e['global_import'] == NULL:
            continue
        assert e['outer'] == NULL, (label, e['name'], 'a public export inside another')
        assert e['global_import'] == imp(old_pkg + '.' + e['name']), (label, e['name'])
        new_name = CLOUD if (folder_object and e['name'] == SORA) else e['name']
        gis[i] = imp(new_pkg + '.' + new_name)
    aligned = bool(z.flags & A.PKG_ALIGNED_EXPORTS)
    src = no_pad(data) if aligned else data
    out = ZR.rebuild(src, renames, gis)
    if aligned:
        out = A.realign(out)
    # checks: only the names and hashes changed
    c = Zen(out)
    assert c.names == [renames.get(n, n) for n in z.names], label
    assert all(c.hashes[i] == ZR.name_hash(n) for i, n in enumerate(c.names)), label
    assert c.imports == z.imports and c.flags == z.flags and c.cooked_header_size == z.cooked_header_size, label
    pkgname = c.names[c.name_mapped & 0x3FFFFFFF]
    assert (pkgname if num == 0 else '%s_%d' % (pkgname, num - 1)) == new_pkg, label
    assert len(c.exports) == len(z.exports), label
    for i, (a, b) in enumerate(zip(z.exports, c.exports)):
        for key in ('serial_offset', 'serial_size', 'outer', 'cls', 'super', 'template', 'oflags', 'fflags'):
            assert a[key] == b[key], (label, i, key)
        assert b['global_import'] == gis.get(i, NULL), (label, i)
        assert b['name'] == (CLOUD if (folder_object and a['name'] == SORA) else a['name']), (label, i)
    assert ZR.graph_imports(out) == ZR.graph_imports(data), label
    ga, gb = Zen(data), c
    assert out[gb.graph_off:gb.graph_off + gb.graph_size] == data[ga.graph_off:ga.graph_off + ga.graph_size], label
    # the export data byte for byte, in the same order
    pa, pb = ga.bundle_positions(), gb.bundle_positions()
    for i in range(len(z.exports)):
        assert data[pa[i][0]:pa[i][0] + pa[i][1]] == out[pb[i][0]:pb[i][0] + pb[i][1]], (label, i)
    return out, old_pkg, new_pkg, aligned


def main(src_utoc, out, name='SoraOverCloudMotion_P'):
    assert not os.path.exists(out), out + ' exists (use a new folder)'
    chunks, store = B.read(src_utoc)
    sora_ids = {c['id64'] for c in chunks}
    picked = [c for c in chunks if any(w.match(c['path']) for w in WANTED)]
    assert all(c['type'] == 2 for c in picked), 'bulk data in a motion package'
    new_chunks, entries = [], []
    report = dict(sets=0, anims=0, blend_spaces=0, blocks=0, by_kind={})
    seen = set()
    for c in picked:
        data, old_pkg, new_pkg, aligned = copy_package(c['data'], c['path'])
        pid = W.package_id(new_pkg)
        assert pid not in sora_ids and pid not in seen, new_pkg
        seen.add(pid)
        se = store[c['id64']]
        e = B.entry(c, se)
        e['id'] = pid
        z = Zen(data)
        assert e['export_count'] == len(z.exports), new_pkg
        if aligned:
            blocks = B.verify_anim(data, new_pkg, need_block=False)
            pkg = Package(data, new_pkg)
            kinds = [cls for cls, v, b in pkg.exports.values()]
            if 'AnimSequence' in kinds:
                assert blocks >= 1, (new_pkg, 'no ACL block')
                report['anims'] += 1
                report['blocks'] += blocks
            else:
                report['blend_spaces'] += 1
            e['size'] = len(data) | (A.SHIFT << 60)
        else:
            e['size'] = len(data)
            report['sets'] += 1
        # after what it imports of SoraAssets_P (what it imports is Sora's, as his own package's is)
        e['load_order'] = 1 + max([store[i]['load_order'] for i in e['imports'] if i in store] or [1000])
        kind = new_pkg.split('/')[3]
        report['by_kind'][kind] = report['by_kind'].get(kind, 0) + 1
        rel = new_pkg[len('/Game/'):] + '.uasset'
        new_chunks.append(dict(id64=pid, type=2, data=data, path=rel))
        entries.append(e)
    os.makedirs(out)
    cid = W.container_id_from_name(name)
    allc = [dict(id64=cid, type=10, data=W.container_header(cid, entries), path=None)] + new_chunks
    base = os.path.join(out, name)
    W.write_container(base, name, allc, mount=MOUNT)
    shutil.copy(src_utoc[:-5] + '.pak', base + '.pak')
    # read back
    back = Toc(base + '.utoc')
    assert back.entries == len(allc)
    cid2, ents = hdr.parse_header(back.read(0))
    assert cid2 == cid and len(ents) == len(entries)
    by = {e['id']: e for e in entries}
    for i in range(1, back.entries):
        c = allc[i]
        d = back.read(i)
        assert d == c['data'] and back.chunk_id64(i) == c['id64'] and back.chunk_type(i) == c['type'], c['path']
        assert back.files.get(i) == MOUNT + c['path'], (back.files.get(i), c['path'])
        e, b = by[c['id64']], ents[c['id64']]
        assert (b['size'], b['export_count'], b['export_bundle_count'], b['load_order'], list(b['imports'])) == \
               (e['size'], e['export_count'], e['export_bundle_count'], e['load_order'], e['imports']), c['path']
    files = {}
    for ext in ('utoc', 'ucas', 'pak'):
        p = base + '.' + ext
        files[ext] = (os.path.getsize(p), hashlib.md5(open(p, 'rb').read()).hexdigest())
    report['packages'] = len(entries)
    report['files'] = files
    return report


if __name__ == '__main__':
    print(main(*sys.argv[1:4]))
