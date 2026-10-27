"""SoraFaceRig_P: Sora's own face rig and Cloud's animation blueprint running it.

  * /Game/Character/Player/PC0000_00_Sora_KH2/Model/PC0000_00_S_FaceRig: a Control Rig made in the End editor
    (sorarig/stageA..C.py) on 21 of Sora's face bones (G_eye, the eyes, the eye holes, the lids and lashes): every
    frame it blinks (two trains of 0.26 s blinks, every 4.3 s and every 6.7 s: each lid's local transform toward its
    closed pose, from his KH3 blink F_0001EM) and moves the eyes in small saccades (random pitch/yaw offsets in each eye's
    own frame, a new target every 1.37 s and 2.11 s, eased in). Only units the game has (FRigUnit_*::Execute in its
    registry); its imports are a subset of the game's own rig's. Cooked by the editor, converted by retoc.
  * /Game/BluePrint/Animation/Player/PC0000_00_Cloud_Standard_Animation (Cloud's animation blueprint, which every one of
    Cloud's blueprints, all Sora's now, runs): the retail package with its Control Rig node's rig (the class and its
    default object imports, CommonHuman00_Rig) -> Sora's face rig, the import graph and the header entry naming its
    package instead. The game's human rig did nothing on Sora's body (none of its bones are his) and, with a facial
    control rig set, dragged his eyes to his feet.
Read back chunk by chunk.

    build_sora_facerig.py <rig .utoc (retoc)> <out dir>
"""
import hashlib
import os
import struct
import sys

sys.path[:0] = ['/work/soradata', '/work/iostore', '/work/cs']
import build_sora_bps as S                   # noqa: E402
from iostore import Toc                      # noqa: E402
from zen import Zen                          # noqa: E402

W, hdr, NULL, imp, graph = S.W, S.hdr, S.NULL, S.imp, S.graph
NAME = 'SoraFaceRig_P'
MOUNT = '../../../End/Content/'
ABP_FILE = '/work/abp/pkgs/BluePrint__Animation__Player__PC0000_00_Cloud_Standard_Animation.uasset'
ABP = '/Game/BluePrint/Animation/Player/PC0000_00_Cloud_Standard_Animation'
OLD_RIG = '/Game/Character/Common/ControlRig/CommonHuman00_Rig'
NEW_RIG = '/Game/Character/Player/PC0000_00_Sora_KH2/Model/PC0000_00_S_FaceRig'
RIG_LOAD_ORDER = 1001


def objects(pkg):
    base = pkg.rsplit('/', 1)[1]
    return [pkg + '.' + base + '_C', pkg + '.Default__' + base + '_C']


def swap_rig(data):
    z = Zen(data)
    old_objs = [imp(p) for p in objects(OLD_RIG)]
    new_objs = [imp(p) for p in objects(NEW_RIG)]
    hits = [[i for i, v in enumerate(z.imports) if v == o] for o in old_objs]
    assert all(len(h) == 1 for h in hits), hits
    of_pkg = [i for i, v in enumerate(z.imports) if v != NULL and (S.OBJ.get(v & ~(3 << 62)) or '').startswith(OLD_RIG + '.')]
    assert sorted(of_pkg) == sorted(h[0] for h in hits), of_pkg
    d = bytearray(data)
    for h, n in zip(hits, new_objs):
        struct.pack_into('<Q', d, z.imp_off + 8 * h[0], n)
    old_pid, new_pid = W.package_id(OLD_RIG), W.package_id(NEW_RIG)
    g = graph(data, z)
    assert sum(1 for pid, _ in g if pid == old_pid) == 1 and not any(pid == new_pid for pid, _ in g)
    g = sorted([(new_pid if pid == old_pid else pid, rest) for pid, rest in g], key=lambda x: x[0])
    gb = bytearray(struct.pack('<i', len(g)))
    for pid, rest in g:
        gb += struct.pack('<Q', pid) + rest
    assert len(gb) == z.graph_size
    d[z.graph_off:z.graph_off + z.graph_size] = gb
    out = bytes(d)
    c = Zen(out)
    swapped = {h[0]: n for h, n in zip(hits, new_objs)}
    assert c.imports == [swapped.get(i, v) for i, v in enumerate(z.imports)]
    assert out[c.header_end:] == data[z.header_end:] and out[:z.imp_off] == data[:z.imp_off]
    assert out[z.exp_off:z.graph_off] == data[z.exp_off:z.graph_off]
    arcs = [rest for pid, rest in graph(out, c) if pid == new_pid][0]
    return out, old_pid, new_pid, arcs


def main(rig_utoc, out_dir):
    # the rig, as retoc made it, and its header entry
    t = Toc(rig_utoc)
    heads = [i for i in range(t.entries) if t.chunk_type(i) == 10]
    assert len(heads) == 1
    _, rig_ents = hdr.parse_header(t.read(heads[0]))
    rig_pid = W.package_id(NEW_RIG)
    assert list(rig_ents) == [rig_pid], rig_ents
    rig_i = [i for i in range(t.entries) if t.chunk_type(i) == 2]
    assert len(rig_i) == 1 and t.files.get(rig_i[0]) == MOUNT + NEW_RIG[len('/Game/'):] + '.uasset'
    rig = t.read(rig_i[0])
    rz = Zen(rig)
    assert [e['name'] for e in rz.exports] == ['PC0000_00_S_FaceRig_C', 'Default__PC0000_00_S_FaceRig_C', 'DataSourceRegistry', 'VM']
    assert [rz.exports[i]['global_import'] for i in (0, 1)] == [imp(p) for p in objects(NEW_RIG)], 'export ids'
    re = dict(rig_ents[rig_pid])
    re['load_order'] = RIG_LOAD_ORDER
    re['size'] = len(rig)                    # (as the game's own entries: the package's size; retoc leaves 0)
    # Cloud's animation blueprint with the rig swapped
    abp = open(ABP_FILE, 'rb').read()
    abp_pid = W.package_id(ABP)
    chunk_name, e = S.retail_entries()[abp_pid]
    assert e['size'] == len(abp) and e['export_count'] == len(Zen(abp).exports)
    out, old_pid, new_pid, arcs = swap_rig(abp)
    na, = struct.unpack_from('<i', arcs, 0)
    froms = struct.unpack_from('<%di' % (2 * na), arcs, 4)[0::2] if na else ()
    assert all(f < re['export_bundle_count'] for f in froms), froms
    imports = [new_pid if x == old_pid else x for x in e['imports']]
    if list(e['imports']) == sorted(e['imports']):
        imports = sorted(imports)
    assert {p for p, _ in graph(out, Zen(out))} <= set(imports)
    assert e['load_order'] > RIG_LOAD_ORDER
    chunks = [None,
              dict(id64=t.chunk_id64(rig_i[0]), type=2, data=rig, path=NEW_RIG[len('/Game/'):] + '.uasset'),
              dict(id64=abp_pid, type=2, data=out, path=ABP[len('/Game/'):] + '.uasset')]
    assert chunks[1]['id64'] == rig_pid
    entries = [dict(id=rig_pid, size=re['size'], export_count=re['export_count'], export_bundle_count=re['export_bundle_count'],
                    load_order=re['load_order'], imports=list(re['imports'])),
               dict(id=abp_pid, size=e['size'], export_count=e['export_count'], export_bundle_count=e['export_bundle_count'],
                    load_order=e['load_order'], imports=imports)]
    cid = W.container_id_from_name(NAME)
    chunks[0] = dict(id64=cid, type=10, data=W.container_header(cid, entries), path=None)
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.join(out_dir, NAME)
    W.write_container(base, NAME, chunks, mount=MOUNT)
    open(base + '.pak', 'wb').write(open(rig_utoc[:-5] + '.pak', 'rb').read())
    back = Toc(base + '.utoc')
    assert back.container_id == cid and back.entries == len(chunks)
    _, ents = hdr.parse_header(back.read(0))
    by = {x['id']: x for x in entries}
    for i in range(1, back.entries):
        c = chunks[i]
        assert back.read(i) == c['data'] and back.chunk_id64(i) == c['id64'] and back.chunk_type(i) == c['type'], c['path']
        assert back.files.get(i) == MOUNT + c['path'], back.files.get(i)
        b, x = ents[c['id64']], by[c['id64']]
        assert (b['size'], b['export_count'], b['export_bundle_count'], b['load_order'], list(b['imports'])) == \
               (x['size'], x['export_count'], x['export_bundle_count'], x['load_order'], x['imports']), c['path']
    print('rig %s: %d bytes, %d exports, %d bundles, load order %d' % (NEW_RIG, len(rig), re['export_count'], re['export_bundle_count'], re['load_order']))
    print('ABP %s (%s): rig %s -> %s, arcs %s, load order %d, %d bytes' % (ABP, chunk_name, OLD_RIG.rsplit('/', 1)[1], NEW_RIG.rsplit('/', 1)[1],
                                                                         froms, e['load_order'], len(out)))
    for ext in ('utoc', 'ucas', 'pak'):
        p = base + '.' + ext
        print('%-22s %8d %s' % (os.path.basename(p), os.path.getsize(p), hashlib.md5(open(p, 'rb').read()).hexdigest()))


if __name__ == '__main__':
    main(*sys.argv[1:3])
