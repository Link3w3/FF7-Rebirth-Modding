"""Safer Sephiroth's own AnimBlueprint: a copy of the game's enemy and summon AnimBlueprint (Zen package) under his name,
made for his skeleton. The game's bosses and summons share one AnimBlueprint graph (their locomotion state machine, the
moves player, inertialization, the move slot, facial and movement expression); Leviathan's is the one with no Control Rig
(the others drive their own body's helper bones with a rig made for it), so his is a copy of Leviathan's with every name
his and its skeleton import his.
    make_safer_abp.py <out dir>"""
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
NEW_BASE = 'PC0010_999_Safer_Sephiroth_Standard_Animation'
NEW_PKG = '/Game/BluePrint/Animation/Player/' + NEW_BASE
NEW_SKEL = ('/Game/Character/Player/PC0010_999_Safer_Sephiroth/Model/PC0010_999_Skeleton', 'PC0010_999_Skeleton')


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
    class Z2: pass
    z2 = Z2(); z2.exports = renamed
    gis = {i: imp(make_bp.export_path(z2, i, NEW_PKG)) for i, e in enumerate(z.exports) if e['global_import'] != NULL}
    d = bytearray(zenrename.rebuild(src, renames, gis))
    nz = Zen(bytes(d))
    old_skel, new_skel = imp(SRC_SKEL[0] + '.' + SRC_SKEL[1]), imp(NEW_SKEL[0] + '.' + NEW_SKEL[1])
    hits = [i for i, v in enumerate(nz.imports) if v == old_skel]
    assert len(hits) == 1, hits
    struct.pack_into('<Q', d, nz.imp_off + 8 * hits[0], new_skel)
    old_pid, new_pid = W.package_id(SRC_SKEL[0]), W.package_id(NEW_SKEL[0])
    g = make_bp.graph(bytes(d))
    assert sum(1 for pid, _ in g if pid == old_pid) == 1, g
    g = sorted([(new_pid if pid == old_pid else pid, arcs) for pid, arcs in g], key=lambda x: x[0])
    gb = bytearray(struct.pack('<i', len(g)))
    for pid, arcs in g:
        gb += struct.pack('<Qi', pid, len(arcs) // 2) + struct.pack('<%di' % len(arcs), *arcs)
    assert len(gb) == nz.graph_size
    d[nz.graph_off:nz.graph_off + nz.graph_size] = gb
    out = bytes(d)
    c = Zen(out)
    assert c.mapped(c.name_mapped) == NEW_PKG and c.mapped(c.srcname_mapped) == NEW_PKG
    assert [e['name'] for e in c.exports] == [renames.get(e['name'], e['name']) for e in z.exports]
    assert out[c.header_end:] == src[z.header_end:], 'export data changed'
    assert c.cooked_header_size == z.cooked_header_size
    for i, e in enumerate(c.exports):
        if e['global_import'] != NULL:
            assert e['global_import'] == imp(make_bp.export_path(c, i, NEW_PKG))
    assert not [n for n in c.names if 'PC0011_00_Vincent_Standard_Animation' in n or 'PC0011_00_Skeleton' in n], [n for n in c.names if 'PC0011_00_Vincent_Standard_Animation' in n or 'PC0011_00_Skeleton' in n]
    assert new_skel in c.imports and old_skel not in c.imports
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
    print('%s: %d bytes, %d exports (%s ... %s), skeleton %s; header entry %s' % (NEW_PKG, len(data), len(c.exports), c.exports[0]['name'],
          c.exports[-1]['name'], NEW_SKEL[0], {k: (v if k != 'imports' else ['%016x' % x for x in v]) for k, v in entry.items()}))


if __name__ == '__main__':
    main(sys.argv[1])
