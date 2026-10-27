"""Character blueprints for custom models: a copy of a retail character blueprint (Zen package) under a new name whose
mesh import points at another skeletal mesh. Everything else (AnimBlueprint, config, components, AutoSE, the Toad
transformation) stays the original's.
    make_bp.py <out dir>"""
import os, struct, sys
sys.path.insert(0, '/work/iostore'); sys.path.insert(0, '/work/cs')
sys.path.insert(0, '/work/vincentfix'); sys.path.insert(0, '/work/weap1012/tools')
from zen import Zen
import zenrename
import iostore_write as W
import gameids

NULL = 0xFFFFFFFFFFFFFFFF
objhash = gameids.objhash
BP_DIR = '/Game/BluePrint/Character/Player/'
SRC_BP = 'PC0000_00_Cloud_Standard'
SRC_FILE = '/work/seph1012/Game__BluePrint__Character__Player__PC0000_00_Cloud_Standard.uasset'
SRC_MESH = ('/Game/Character/Player/PC0000_00_Cloud_Standard/Model/PC0000_00', 'PC0000_00')
# new blueprint -> (mesh package, mesh object name, the mesh export's global index in the user's cooked pak)
NEW = {
    'PC0000_10_Evil_Cloud': ('/Game/Character/Player/PC0000_10_Evil_Cloud/Model/PC0000_10', 'PC0000_10', 0x8102af0288776dc2),
    'PC0000_11_EvilCloud_Transformed': ('/Game/Character/Player/PC0000_11_EvilCloud_Transformed/Model/PC0000_11', 'PC0000_11', 0xa6f3ad3b19889512),
}

def imp(path):
    return (2 << 62) | objhash(path)

def export_path(z, i, pkg):
    chain = []
    while True:
        e = z.exports[i]; chain.append(e['name'])
        if e['outer'] == NULL: break
        i = e['outer']
    chain.reverse()
    path = pkg + '.' + chain[0]
    if len(chain) > 1: path += ':' + chain[1]
    for sub in chain[2:]: path += '.' + sub
    return path

def graph(d):
    z = Zen(d)
    o = z.graph_off; n = struct.unpack_from('<i', d, o)[0]; o += 4; out = []
    for _ in range(n):
        pid, na = struct.unpack_from('<Qi', d, o)
        out.append((pid, list(struct.unpack_from('<%di' % (2 * na), d, o + 12)) if na else []))
        o += 12 + 8 * na
    assert o == z.graph_off + z.graph_size
    return out

def make(name):
    mesh_pkg, mesh_name, mesh_gi = NEW[name]
    src = open(SRC_FILE, 'rb').read()
    z = Zen(src)
    src_pkg = BP_DIR + SRC_BP
    # the original's public export indices are what this computes
    for i, e in enumerate(z.exports):
        if e['global_import'] != NULL:
            assert imp(export_path(z, i, src_pkg)) == e['global_import'], (e['name'], export_path(z, i, src_pkg))
    new_pkg = BP_DIR + name
    assert imp(mesh_pkg + '.' + mesh_name) == mesh_gi, 'mesh index differs from the cooked mesh'
    renames = {src_pkg: new_pkg, SRC_BP + '_C': name + '_C', 'Default__' + SRC_BP + '_C': 'Default__' + name + '_C',
               SRC_MESH[0]: mesh_pkg, SRC_MESH[1]: mesh_name}
    for old in renames: assert old in z.names, old
    renamed_exports = []
    for e in z.exports:
        renamed_exports.append(dict(e, name=renames.get(e['name'], e['name'])))
    class Z2: pass
    z2 = Z2(); z2.exports = renamed_exports
    gis = {i: imp(export_path(z2, i, new_pkg)) for i, e in enumerate(z.exports) if e['global_import'] != NULL}
    d = bytearray(zenrename.rebuild(src, renames, gis))
    nz = Zen(bytes(d))
    # mesh import
    old_mesh, new_mesh = imp(SRC_MESH[0] + '.' + SRC_MESH[1]), mesh_gi
    hits = [i for i, v in enumerate(nz.imports) if v == old_mesh]
    assert len(hits) == 1, hits
    struct.pack_into('<Q', d, nz.imp_off + 8 * hits[0], new_mesh)
    # graph: the mesh package
    old_pid, new_pid = W.package_id(SRC_MESH[0]), W.package_id(mesh_pkg)
    g = graph(bytes(d))
    assert sum(1 for pid, _ in g if pid == old_pid) == 1
    g = sorted([(new_pid if pid == old_pid else pid, arcs) for pid, arcs in g], key=lambda x: x[0])
    gb = bytearray(struct.pack('<i', len(g)))
    for pid, arcs in g:
        gb += struct.pack('<Qi', pid, len(arcs) // 2) + struct.pack('<%di' % len(arcs), *arcs)
    assert len(gb) == nz.graph_size
    d[nz.graph_off:nz.graph_off + nz.graph_size] = gb
    out = bytes(d)
    # checks
    c = Zen(out)
    assert c.mapped(c.name_mapped) == new_pkg and c.mapped(c.srcname_mapped) == new_pkg
    assert [e['name'] for e in c.exports] == [renames.get(e['name'], e['name']) for e in z.exports]
    assert out[c.header_end:] == src[z.header_end:], 'export data changed'
    assert c.cooked_header_size == z.cooked_header_size
    for i, e in enumerate(c.exports):
        if e['global_import'] != NULL:
            assert e['global_import'] == imp(export_path(c, i, new_pkg))
    left = [n for n in c.names if 'Cloud_Standard' in n and 'Animation' not in n and 'AutoSe' not in n and 'Detection' not in n and 'Index' not in n]
    assert not left, left
    return out, new_pkg, {e['name'] for e in c.exports}

def main():
    out_dir = sys.argv[1]
    os.makedirs(out_dir, exist_ok=True)
    for name in NEW:
        data, pkg, exports = make(name)
        path = os.path.join(out_dir, 'Game__BluePrint__Character__Player__%s.uasset' % name)
        open(path, 'wb').write(data)
        z = Zen(data)
        print(name, len(data), 'bytes; exports', [e['name'] for e in z.exports][:3], '...; mesh', NEW[name][0])
        g = graph(data)
        print('    graph packages:', len(g), 'mesh package listed:', any(pid == W.package_id(NEW[name][0]) for pid, _ in g),
              'arcs from mesh:', [arcs for pid, arcs in g if pid == W.package_id(NEW[name][0])])

if __name__ == '__main__':
    main()
