"""SoraAssets_P: Sora's model, skeleton, Kingdom Key and every motion asset (cooked by the End editor, converted to zen by
retoc), made ready for the game:
  * every animation package (and blend space) laid out the way the game reads its own animations (align_moves: 16-byte
    exports at aligned cooked offsets, PKG_Cooked, alignment shift 4 in the container header), each animation checked
    against an emulation of the game's reader (its ACL block found and 16-aligned);
  * the Bonamik (hair / keychain physics) off for now: the KBD asset user data of Sora's mesh and of the Kingdom Key
    lists no Bonamik (their Bonamik assets are 2.x data, which crashed the game for Chaos), and the Bonamik packages are
    not in the meshes' imported packages;
  * (bone renames in place, by BONE_RENAMES: none now; the editor's skeleton was flattened and its 'trans' renamed
    'Transform' by Flatten Root, so cooked packages carry it as they are);
  * load orders: every package after the packages of this container it imports.
Read back chunk by chunk.

    build_sora_assets.py <retoc .utoc> <out dir> [name]
"""
import hashlib
import os
import shutil
import struct
import sys

sys.path[:0] = ['/work/iostore', '/work/cs', '/work/swap1012/tools',
                '/work/sephforms/tools', '/work/shooter1016/tools', '/work/fx1018/editor/Python']
from iostore import Toc                      # noqa: E402
from zen import Zen                          # noqa: E402
import iostore_write as W                    # noqa: E402
import hdr                                   # noqa: E402
import align_moves as A                      # noqa: E402
from rebirth_fx.fxcore import Package        # noqa: E402
from rebirth_fx import matcore, uwrite       # noqa: E402
import zenrename as ZR                       # noqa: E402

MOUNT = '../../../End/Content/'
# Sora's own KH2 moves (Battle00/1309, AirSpiral, ...): no pack uses them yet, and their animation data is laid out
# differently from the game's (13 bytes the game's reader would not read); they wait for the moveset step
def excluded(path):
    return path.startswith('Motion/Player/PC0000_00_Sora_KH2/Battle00/') and \
        not path.startswith('Motion/Player/PC0000_00_Sora_KH2/Battle00/FromCloud/')


MESHES = {
    'Character/Player/PC0000_00_Sora_KH2/Model/PC0000_00_S.uasset': '/Game/Character/Player/PC0000_00_Sora_KH2/Model/p_ex011_Bonamik',
    'Character/Weapon/WE0000_00_Kingdom_Key/Model/WE0000_00.uasset': '/Game/Character/Weapon/WE0000_00_Kingdom_Key/Model/w_so010_Bonamik',
}


# SORA_BONAMIK=1: Sora's mesh keeps a Bonamik, his regular one (sorabnm/make_sora_bonamik.py, cooked into the extra
# container below): the mesh's Bonamik import (his KH3 v2 p_ex011_Bonamik) points at PC0000_00_S_BNM instead.
SORA_BONAMIK = os.environ.get('SORA_BONAMIK') == '1'
BONAMIK_SWAP = {'Character/Player/PC0000_00_Sora_KH2/Model/PC0000_00_S.uasset':
                ('/Game/Character/Player/PC0000_00_Sora_KH2/Model/p_ex011_Bonamik',
                 '/Game/Character/Player/PC0000_00_Sora_KH2/Model/PC0000_00_S_BNM'),
                'Character/Weapon/WE0000_00_Kingdom_Key/Model/WE0000_00.uasset':
                ('/Game/Character/Weapon/WE0000_00_Kingdom_Key/Model/w_so010_Bonamik',
                 '/Game/Character/Weapon/WE0000_00_Kingdom_Key/Model/WE0000_00_BNM')}
EXTRA_UTOCS = ['/work/sorabnm/in2/SoraBonamik.utoc'] if SORA_BONAMIK else []


def swap_bonamik(data, old_pkg, new_pkg, label):
    """The package with its import of old_pkg's object -> new_pkg's object (same name scheme) and its import graph naming
    new_pkg instead (sorted again by package id, as the cooker writes it); everything else as it was."""
    sys.path.insert(0, '/work/weap1012/tools')
    import gameids
    imp = lambda path: (2 << 62) | gameids.objhash(path + '.' + path.rsplit('/', 1)[1])
    z = Zen(data)
    hits = [i for i, v in enumerate(z.imports) if v == imp(old_pkg)]
    assert len(hits) == 1, (label, hits)
    d = bytearray(data)
    struct.pack_into('<Q', d, z.imp_off + 8 * hits[0], imp(new_pkg))
    old_pid, new_pid = W.package_id(old_pkg), W.package_id(new_pkg)
    o = z.graph_off
    n, = struct.unpack_from('<i', data, o); o += 4
    g = []
    for _ in range(n):
        pid, na = struct.unpack_from('<Qi', data, o)
        g.append((pid, data[o + 8:o + 12 + 8 * na])); o += 12 + 8 * na
    assert sum(1 for pid, _ in g if pid == old_pid) == 1 and not any(pid == new_pid for pid, _ in g), label
    g = sorted([(new_pid if pid == old_pid else pid, rest) for pid, rest in g], key=lambda x: x[0])
    gb = bytearray(struct.pack('<i', len(g)))
    for pid, rest in g:
        gb += struct.pack('<Q', pid) + rest
    assert len(gb) == z.graph_size, label
    d[z.graph_off:z.graph_off + z.graph_size] = gb
    out = bytes(d)
    c = Zen(out)
    assert c.imports == [imp(new_pkg) if i == hits[0] else v for i, v in enumerate(z.imports)], label
    assert out[c.header_end:] == data[z.header_end:] and out[:z.imp_off] == data[:z.imp_off], label
    return out, old_pid, new_pid


def read(utoc):
    t = Toc(utoc)
    heads = [i for i in range(t.entries) if t.chunk_type(i) == 10]
    assert len(heads) == 1, utoc
    _, store = hdr.parse_header(t.read(heads[0]))
    chunks = []
    for i in range(t.entries):
        kind = t.chunk_type(i)
        if kind == 10:
            continue
        path = t.files.get(i)
        assert path and path.startswith(MOUNT), path
        chunks.append(dict(id64=t.chunk_id64(i), type=kind, data=t.read(i), path=path[len(MOUNT):]))
    assert sum(1 for c in chunks if c['type'] == 2) == len(store)
    return chunks, store


def no_bonamik(data, label):
    """The package with its SQEX_KBD_AssetUserData's BonamikDataList empty (the property stored as zero)."""
    pkg = Package(data, label)
    hits = [(i, v) for i, (cls, v, base) in pkg.exports.items() if cls == 'SQEX_KBD_AssetUserData']
    assert len(hits) == 1, (label, hits)
    index, v = hits[0]
    assert 'BonamikDataList' in v.value and len(v.value['BonamikDataList'].value) >= 1, label
    ex_start, ex_size = pkg.z.bundle_positions()[index]
    ex = data[ex_start:ex_start + ex_size]
    u = matcore.usmap()
    fields = {key: (None if x.zero else ex[x.at:x.at + x.size]) for key, x in v.value.items()}
    fields['BonamikDataList'] = None
    block = uwrite.struct_bytes(u, 'SQEX_KBD_AssetUserData', fields)
    new_ex = block + ex[v.at + v.size:]
    out = matcore.replace_export(data, index, new_ex)
    back = Package(out, label)
    bv = [v2 for i2, (c2, v2, b2) in back.exports.items() if c2 == 'SQEX_KBD_AssetUserData'][0]
    assert 'BonamikDataList' not in bv.value or bv.value['BonamikDataList'].zero or not bv.value['BonamikDataList'].value, label
    return out


# names renamed in place in these packages (each new name the same length as the old one)
# (none now: the editor's skeleton itself has the helper bone as 'Transform' and a flat root since Flatten Root, editor 1.13.1)
BONE_RENAMES = {}
# names renamed in these packages, any length (the name map and the header rebuilt, the export data as it was):
#   G_eye -> C_FaceBase_a, G_mouth -> C_FaceBase_b: Sora's two face group bones (identity under 'facial', every face bone
#   under one of them) by the names the game's facial blend looks for: the facial slot (AnimNode_EndFacialPrimary) copies a
#   facial montage's pose onto the bones under C_FaceBase_a and C_FaceBase_b only (its bone list is built from those two
#   names, game code at 0xdb4fb1), so with Sora's own names his facial set (SoraFace_P) never showed.
FACE_GROUPS = {'G_eye': 'C_FaceBase_a', 'G_mouth': 'C_FaceBase_b'}
BONE_RENAMES_ANY = {'Character/Player/PC0000_00_Sora_KH2/Model/PC0000_00_S.uasset': FACE_GROUPS,
                    'Character/Player/PC0000_00_Sora_KH2/Model/PC0000_00_S_Skeleton.uasset': FACE_GROUPS}


def rename_names_any(data, renames, label):
    """The package with name map entries renamed (any length): the header rebuilt (zenrename), the rest as it was."""
    z = Zen(data)
    low = [n.lower() for n in z.names]
    for a, b in renames.items():
        assert low.count(a.lower()) == 1 and a in z.names, (label, a)
        assert b.lower() not in low, (label, b, 'already in the name map')
        assert b.isascii(), (label, b)
    out = ZR.rebuild(data, renames)
    back = Zen(out)
    assert [renames.get(n, n) for n in z.names] == back.names, label
    assert all(back.hashes[i] == ZR.name_hash(n) for i, n in enumerate(back.names)), label
    assert back.imports == z.imports and [e['name'] for e in back.exports] == [e['name'] for e in z.exports], label
    assert out[back.imp_off:back.header_end] == data[z.imp_off:z.header_end], label
    assert out[back.header_end:] == data[z.header_end:], label
    assert back.cooked_header_size == z.cooked_header_size and back.flags == z.flags, label
    return out


def rename_names(data, renames, label):
    """The package with name map entries renamed in place (same length, plain ASCII) and their hashes updated."""
    z = Zen(data)
    d = bytearray(data)
    p = z.nm_off
    found = {}
    for i, n in enumerate(z.names):
        h0, h1 = d[p], d[p + 1]
        wide = h0 & 0x80
        ln = ((h0 & 0x7f) << 8) | h1
        assert not wide or n not in renames, (label, n)
        start = p + 2
        if wide and start & 1:
            start += 1
        if n in renames:
            new = renames[n]
            assert len(new) == len(n) and new.isascii(), (label, n, new)
            assert new.lower() not in [x.lower() for x in z.names], (label, new, 'already in the name map')
            d[start:start + ln] = new.encode('ascii')
            struct.pack_into('<Q', d, z.nh_off + 8 + 8 * i, ZR.name_hash(new))
            found[n] = i
        p = start + (ln * 2 if wide else ln)
    assert set(found) == set(renames), (label, set(renames) - set(found))
    out = bytes(d)
    back = Zen(out)
    assert len(back.names) == len(z.names) and back.header_end == z.header_end, label
    for i, (a, b) in enumerate(zip(z.names, back.names)):
        assert b == renames.get(a, a) and back.hashes[i] == ZR.name_hash(b), (label, i, a, b)
    assert out[z.header_end:] == data[z.header_end:], label
    return out


def entry(c, se):
    return dict(id=c['id64'], size=se['size'], export_count=se['export_count'], export_bundle_count=se['export_bundle_count'],
                load_order=se['load_order'], imports=list(se['imports']))


def anim_consumes(pkg, d, idx, s, e):
    """(bytes the game's UAnimSequence::Serialize reads of this export, where its ACL block sits) for an AnimSequence
    export with unversioned properties (align_moves.game_consumes, the property block measured by the usmap parser);
    (None, None) for any other export."""
    if idx not in pkg.exports:
        return None, None                                  # (an export the usmap parser does not read: not an animation)
    cls, v, base = pkg.exports[idx]
    if cls != 'AnimSequence':
        return None, None
    assert base == s, (base, s)
    p = s + v.at + v.size + 4                              # + UObject guid flag
    p += A.SKELETON_GUID_LEN                               # UAnimationAsset: SkeletonGuid
    size, = struct.unpack_from('<I', d, p); p += 4         # ff7rebirth 0x7bc124: memory-mapped block
    block = None
    if size:
        tag, = struct.unpack_from('<I', d, p); p += 4
        if tag > 0xffff:
            _align, pad = struct.unpack_from('<HH', d, p); p += 4 + pad
        block = p
        p += size
        n1, n2, n3 = struct.unpack_from('<III', d, p); p += 12   # 0xc22f50: fixups
        for _ in range(n1):
            p += 8; cnt, = struct.unpack_from('<I', d, p); p += 4 + 8 * cnt
        for _ in range(n2 + n3):
            p += 8; cnt, = struct.unpack_from('<I', d, p); p += 4 + 4 * cnt
    p += 2                                                 # FStripDataFlags
    bser, = struct.unpack_from('<I', d, p); p += 4         # bSerializeCompressedData
    if bser:
        p += 4                                             # CompressedRawDataSize
        ntracks, = struct.unpack_from('<i', d, p); p += 4 + 4 * ntracks
        ncurves, = struct.unpack_from('<i', d, p); p += 4 + 8 * ncurves
        p += 4                                             # codec data: CompressedNumberOfFrames
        p += 4                                             # bUseRawDataOnly
    assert p <= e, ('reads past the export', idx, p - e)
    return p - s, block


def verify_anim(d, label, need_block):
    """Every export where the game reads it from (each after the previous one's aligned end), and each AnimSequence's
    ACL block 16-aligned; returns the number of ACL blocks."""
    z = Zen(d)
    assert z.flags & A.PKG_COOKED and z.flags & A.PKG_ALIGNED_EXPORTS, label
    assert z.header_end % A.ALIGN == 0, label
    pkg = Package(d, label)
    spans = A.export_spans(d, z)
    pos = z.header_end
    blocks = 0
    for idx, s, e in spans:
        assert pos == s, (label, 'export %d starts at %d, the game reads it from %d' % (idx, s, pos))
        ex = z.exports[idx]
        assert ex['serial_offset'] % A.ALIGN == 0 and ex['serial_size'] % A.ALIGN == 0, (label, idx)
        used, block = anim_consumes(pkg, d, idx, s, e)
        if used is None:
            pos = e
            continue
        pos = s + (A.align_up(ex['serial_offset'] + used) - ex['serial_offset'])
        if block is not None:
            assert block % A.ALIGN == 0, (label, 'ACL block not 16-aligned in memory', block)
            blocks += 1
    assert pos == len(d), (label, pos, len(d))
    if need_block:
        assert blocks >= 1, (label, 'no ACL block read')
    return blocks


def load_orders(chunks, entries):
    """Each package after the packages of this container it imports (others: no constraint here)."""
    ours = {e['id']: e for e in entries}
    order = {}

    def lo(pid, stack=()):
        if pid in order:
            return order[pid]
        if pid in stack:
            raise ValueError('import cycle')
        deps = [lo(i, stack + (pid,)) for i in ours[pid]['imports'] if i in ours]
        order[pid] = 1 + max(deps or [0])
        return order[pid]

    for e in entries:
        e['load_order'] = 1000 + lo(e['id'])


def main(utoc, out, name='SoraAssets_P'):
    chunks, store = read(utoc)
    for extra in EXTRA_UTOCS:                       # (packages cooked on their own: Sora's Bonamik)
        more, more_store = read(extra)
        assert not set(c['id64'] for c in more) & set(c['id64'] for c in chunks), extra
        chunks += more
        store.update(more_store)
    left_out = [c['path'] for c in chunks if excluded(c['path'])]
    chunks = [c for c in chunks if not excluded(c['path'])]
    ids = set(c['id64'] for c in chunks)
    for c in chunks:
        if c['type'] == 2:
            assert not [i for i in store[c['id64']]['imports'] if i not in ids and i in set(store) - ids], c['path']
    entries = []
    report = dict(anims=0, blend_spaces=0, blocks=0, meshes=[], left_out=len(left_out))
    for c in chunks:
        if c['type'] != 2:
            continue
        e = entry(c, store[c['id64']])
        if SORA_BONAMIK and c['path'] in BONAMIK_SWAP:
            c['data'], old_pid, new_pid = swap_bonamik(c['data'], *BONAMIK_SWAP[c['path']], c['path'])
            assert old_pid in e['imports'] and new_pid not in e['imports'], c['path']
            e['imports'] = sorted(new_pid if i == old_pid else i for i in e['imports']) \
                if list(e['imports']) == sorted(e['imports']) else [new_pid if i == old_pid else i for i in e['imports']]
            e['size'] = len(c['data'])
            report.setdefault('bonamik', []).append(c['path'])
        elif c['path'] in MESHES:
            c['data'] = no_bonamik(c['data'], c['path'])
            bnm = W.package_id(MESHES[c['path']])
            assert bnm in e['imports'], c['path']
            e['imports'] = [i for i in e['imports'] if i != bnm]
            e['size'] = len(c['data'])
            z = Zen(c['data'])
            e['export_count'] = len(z.exports)
            report['meshes'].append(c['path'])
        if c['path'] in BONE_RENAMES:
            c['data'] = rename_names(c['data'], BONE_RENAMES[c['path']], c['path'])
            report.setdefault('renamed', []).append(c['path'])
        if c['path'] in BONE_RENAMES_ANY:
            c['data'] = rename_names_any(c['data'], BONE_RENAMES_ANY[c['path']], c['path'])
            e['size'] = len(c['data'])
            report.setdefault('renamed', []).append(c['path'])
        z = Zen(c['data'])
        if z.flags & A.PKG_ALIGNED_EXPORTS:
            assert e['size'] >> 60 == 0, c['path']
            c['data'] = A.realign(c['data'])
            is_seq = c['path'].rsplit('/', 1)[-1].startswith(('B_', 'N_', 'F_', 'E_', 'L_')) or True
            blocks = verify_anim(c['data'], c['path'], need_block=False)
            if Package(c['data'], c['path']).exports and any(cls == 'AnimSequence' for cls, v, b in Package(c['data'], c['path']).exports.values()):
                assert blocks >= 1, (c['path'], 'no ACL block')
            if blocks:
                report['anims'] += 1
                report['blocks'] += blocks
            else:
                report['blend_spaces'] += 1
            e['size'] = len(c['data']) | (A.SHIFT << 60)
        entries.append(e)
    load_orders(chunks, entries)
    os.makedirs(out, exist_ok=True)
    cid = W.container_id_from_name(name)
    allc = [dict(id64=cid, type=10, data=W.container_header(cid, entries), path=None)] + chunks
    base = os.path.join(out, name)
    W.write_container(base, name, allc, mount=MOUNT)
    shutil.copy(os.path.join(os.path.dirname(utoc), os.path.basename(utoc)[:-5] + '.pak'), base + '.pak')
    # read back
    back = Toc(base + '.utoc')
    assert back.entries == len(allc)
    cid2, ents = hdr.parse_header(back.read(0))
    assert cid2 == cid and len(ents) == len(entries)
    by = {e['id']: e for e in entries}
    for i in range(1, back.entries):
        c = allc[i]
        data = back.read(i)
        assert data == c['data'] and back.chunk_id64(i) == c['id64'] and back.chunk_type(i) == c['type'], c['path']
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
