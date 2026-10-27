"""The Galian Beast form's AnimBlueprint: Vincent's player AnimBlueprint (Zen package; his is Cloud's graph without the
sword node: the player's locomotion, moves player, guard-walk, inertialization, the move slot, facial and movement
expression) under a name of its own, made for the beast's skeleton (EB2160_00_Skeleton), with its Control Rig node given
no rig (the common human rig places a person's hips by their legs; the beast's are not a person's), as Safer
Sephiroth's (make_safer_abp_v3.py, in game since 3.6.5).
    make_galian_abp.py <out dir>"""
import os, struct, sys
sys.path[:0] = ['/work/iostore', '/work/cs', '/work/vincentfix', '/work/weap1012/tools',
                '/work/evil1013/tools']
from zen import Zen
import zenrename
import iostore_write as W
import make_bp

NULL = 0xFFFFFFFFFFFFFFFF
imp = make_bp.imp
SRC_FILE = '/work/abp/pkgs/BluePrint__Animation__Player__PC0011_00_Vincent_Standard_Animation.uasset'
SRC_PKG = '/Game/BluePrint/Animation/Player/PC0011_00_Vincent_Standard_Animation'
SRC_BASE = 'PC0011_00_Vincent_Standard_Animation'
SRC_SKEL = ('/Game/Character/Player/PC0011_00_Vincent_Standard/Model/PC0011_00_Skeleton', 'PC0011_00_Skeleton')
NEW_BASE = 'PC0011_20_GalianBeast_Standard_Animation'
NEW_PKG = '/Game/BluePrint/Animation/Player/' + NEW_BASE
NEW_SKEL = ('/Game/Character/Enemy/EB2160_00_VincentValentine_Standard/Model/EB2160_00_Skeleton', 'EB2160_00_Skeleton')
RIG = ('/Game/Character/Common/ControlRig/CommonHuman00_Rig.CommonHuman00_Rig_C', '/Game/Character/Common/ControlRig/CommonHuman00_Rig.Default__CommonHuman00_Rig_C')
CLASS = NEW_PKG + '.' + NEW_BASE + '_C'    # (the form's "anim_class")


def make():
    src = open(SRC_FILE, 'rb').read()
    z = Zen(src)
    for i, e in enumerate(z.exports):
        if e['global_import'] != NULL:
            assert imp(make_bp.export_path(z, i, SRC_PKG)) == e['global_import'], e['name']
    renames = {SRC_PKG: NEW_PKG, SRC_SKEL[0]: NEW_SKEL[0], SRC_SKEL[1]: NEW_SKEL[1]}
    for n in z.names:
        if SRC_BASE in n and n not in renames:
            renames[n] = n.replace(SRC_BASE, NEW_BASE)
    for old in renames:
        assert old in z.names, old
    renamed = [dict(e, name=renames.get(e['name'], e['name'])) for e in z.exports]

    class Z2:
        pass
    z2 = Z2()
    z2.exports = renamed
    gis = {i: imp(make_bp.export_path(z2, i, NEW_PKG)) for i, e in enumerate(z.exports) if e['global_import'] != NULL}
    d = bytearray(zenrename.rebuild(src, renames, gis))
    nz = Zen(bytes(d))
    # the skeleton import (and the package it names in the import graph)
    old_skel, new_skel = imp(SRC_SKEL[0] + '.' + SRC_SKEL[1]), imp(NEW_SKEL[0] + '.' + NEW_SKEL[1])
    hits = [i for i, v in enumerate(nz.imports) if v == old_skel]
    assert len(hits) == 1, hits
    struct.pack_into('<Q', d, nz.imp_off + 8 * hits[0], new_skel)
    old_pid, new_pid = W.package_id(SRC_SKEL[0]), W.package_id(NEW_SKEL[0])
    g = make_bp.graph(bytes(d))
    assert sum(1 for pid, _ in g if pid == old_pid) == 1, g
    assert not any(pid == new_pid for pid, _ in g)
    g = sorted([(new_pid if pid == old_pid else pid, arcs) for pid, arcs in g], key=lambda x: x[0])
    gb = bytearray(struct.pack('<i', len(g)))
    for pid, arcs in g:
        gb += struct.pack('<Qi', pid, len(arcs) // 2) + struct.pack('<%di' % len(arcs), *arcs)
    assert len(gb) == nz.graph_size
    d[nz.graph_off:nz.graph_off + nz.graph_size] = gb
    # the Control Rig node: no rig (its class and default object imports null: the node passes the pose through)
    rig = {imp(p) for p in RIG}
    hits = [i for i, v in enumerate(nz.imports) if v in rig]
    assert len(hits) == 2, hits
    for i in hits:
        struct.pack_into('<Q', d, nz.imp_off + 8 * i, NULL)
    out = bytes(d)
    c = Zen(out)
    assert c.mapped(c.name_mapped) == NEW_PKG and c.mapped(c.srcname_mapped) == NEW_PKG
    assert [e['name'] for e in c.exports] == [renames.get(e['name'], e['name']) for e in z.exports]
    assert out[c.header_end:] == src[z.header_end:], 'export data changed'
    assert c.cooked_header_size == z.cooked_header_size
    for i, e in enumerate(c.exports):
        if e['global_import'] != NULL:
            assert e['global_import'] == imp(make_bp.export_path(c, i, NEW_PKG))
    left = [n for n in c.names if SRC_BASE in n or 'PC0011_00_Skeleton' in n]
    assert not left, left
    assert new_skel in c.imports and old_skel not in c.imports and not rig & set(c.imports)
    assert sum(1 for v in c.imports if v == NULL) == sum(1 for v in z.imports if v == NULL) + 2
    entry = dict(id=W.package_id(NEW_PKG), size=len(out), export_count=len(c.exports),
                 export_bundle_count=(c.graph_off - c.eb_off - 16 * len(c.exports)) // 8, load_order=0,
                 imports=[pid for pid, _ in make_bp.graph(out)])
    return out, entry


def main(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    data, entry = make()
    path = os.path.join(out_dir, NEW_BASE + '.uasset')
    open(path, 'wb').write(data)
    c = Zen(data)
    print('%s: %d bytes, %d exports (%s ... %s), skeleton %s; class %s; header entry %s' % (
        NEW_PKG, len(data), len(c.exports), c.exports[0]['name'], c.exports[-1]['name'], NEW_SKEL[0], CLASS,
        {k: (v if k != 'imports' else ['%016x' % x for x in v]) for k, v in entry.items()}))


if __name__ == '__main__':
    main(sys.argv[1])
