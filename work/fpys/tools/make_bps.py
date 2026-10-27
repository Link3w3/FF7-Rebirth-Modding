"""Fully Playable Young Sephiroth's own character blueprints: copies of retail blueprints (Zen packages) under new names
whose mesh import points at his models (evil1013/tools/make_bp.py's way; every other byte the original's):
  * PC0010_13_Young_Sephiroth  <- PC0010_00_Sephiroth_Standard (Sephiroth's player blueprint: his AnimBlueprint, config,
    components, AutoSE, control rigs), wearing /Game/Character/Player/PC0010_13_Young_Sephiroth/Model/PC0010_13;
  * WE1021_49_Nameless         <- WE1021_00_SephirothIllusion_Masamune (the Masamune's weapon blueprint), wearing
    /Game/Character/Weapon/WE1021_49_Nameless/Model/WE1021_49.
    make_bps.py <out dir>"""
import os, struct, sys
sys.path[:0] = ['/work/iostore', '/work/cs', '/work/vincentfix', '/work/weap1012/tools']
from zen import Zen
import zenrename
import iostore_write as W
import gameids

NULL = 0xFFFFFFFFFFFFFFFF
objhash = gameids.objhash
JOBS = [
    dict(src_file='/work/seph1012/Game__BluePrint__Character__Player__PC0010_00_Sephiroth_Standard.uasset',
         src_dir='/Game/BluePrint/Character/Player/', src='PC0010_00_Sephiroth_Standard',
         src_mesh=('/Game/Character/Player/PC0010_00_Sephiroth_Standard/Model/PC0010_00', 'PC0010_00'),
         new='PC0010_13_Young_Sephiroth', new_mesh=('/Game/Character/Player/PC0010_13_Young_Sephiroth/Model/PC0010_13', 'PC0010_13'),
         keep_names=('Sephiroth_Standard_Animation', 'Sephiroth_Standard_Index', 'Sephiroth_Standard_Detection')),
    dict(src_file='/work/seph1012/Game__BluePrint__Character__Weapon__WE1021_00_SephirothIllusion_Masamune.uasset',
         src_dir='/Game/BluePrint/Character/Weapon/', src='WE1021_00_SephirothIllusion_Masamune',
         src_mesh=('/Game/Character/Weapon/WE1021_00_SephirothIllusion_Masamune/Model/WE1021_00', 'WE1021_00'),
         new='WE1021_49_Nameless', new_mesh=('/Game/Character/Weapon/WE1021_49_Nameless/Model/WE1021_49', 'WE1021_49'),
         keep_names=()),
]


def imp(path):
    return (2 << 62) | objhash(path)


def export_path(z, i, pkg):
    chain = []
    while True:
        e = z.exports[i]
        chain.append(e['name'])
        if e['outer'] == NULL:
            break
        i = e['outer']
    chain.reverse()
    path = pkg + '.' + chain[0]
    if len(chain) > 1:
        path += ':' + chain[1]
    for sub in chain[2:]:
        path += '.' + sub
    return path


def graph(d):
    z = Zen(d)
    o = z.graph_off
    n = struct.unpack_from('<i', d, o)[0]
    o += 4
    out = []
    for _ in range(n):
        pid, na = struct.unpack_from('<Qi', d, o)
        out.append((pid, list(struct.unpack_from('<%di' % (2 * na), d, o + 12)) if na else []))
        o += 12 + 8 * na
    assert o == z.graph_off + z.graph_size
    return out


def make(job):
    src = open(job['src_file'], 'rb').read()
    z = Zen(src)
    src_pkg = job['src_dir'] + job['src']
    for i, e in enumerate(z.exports):
        if e['global_import'] != NULL:
            assert imp(export_path(z, i, src_pkg)) == e['global_import'], (e['name'], export_path(z, i, src_pkg))
    new_pkg = job['src_dir'] + job['new']
    (old_mesh_pkg, old_mesh_name), (mesh_pkg, mesh_name) = job['src_mesh'], job['new_mesh']
    renames = {src_pkg: new_pkg, job['src'] + '_C': job['new'] + '_C', 'Default__' + job['src'] + '_C': 'Default__' + job['new'] + '_C',
               old_mesh_pkg: mesh_pkg, old_mesh_name: mesh_name}
    for old in renames:
        assert old in z.names, old
    renamed = [dict(e, name=renames.get(e['name'], e['name'])) for e in z.exports]

    class Z2:
        pass
    z2 = Z2()
    z2.exports = renamed
    gis = {i: imp(export_path(z2, i, new_pkg)) for i, e in enumerate(z.exports) if e['global_import'] != NULL}
    d = bytearray(zenrename.rebuild(src, renames, gis))
    nz = Zen(bytes(d))
    old_mesh, new_mesh = imp(old_mesh_pkg + '.' + old_mesh_name), imp(mesh_pkg + '.' + mesh_name)
    hits = [i for i, v in enumerate(nz.imports) if v == old_mesh]
    assert len(hits) == 1, hits
    struct.pack_into('<Q', d, nz.imp_off + 8 * hits[0], new_mesh)
    old_pid, new_pid = W.package_id(old_mesh_pkg), W.package_id(mesh_pkg)
    g = graph(bytes(d))
    assert sum(1 for pid, _ in g if pid == old_pid) == 1
    g = sorted([(new_pid if pid == old_pid else pid, arcs) for pid, arcs in g], key=lambda x: x[0])
    gb = bytearray(struct.pack('<i', len(g)))
    for pid, arcs in g:
        gb += struct.pack('<Qi', pid, len(arcs) // 2) + struct.pack('<%di' % len(arcs), *arcs)
    assert len(gb) == nz.graph_size
    d[nz.graph_off:nz.graph_off + nz.graph_size] = gb
    out = bytes(d)
    c = Zen(out)
    assert c.mapped(c.name_mapped) == new_pkg and c.mapped(c.srcname_mapped) == new_pkg
    assert [e['name'] for e in c.exports] == [renames.get(e['name'], e['name']) for e in z.exports]
    assert out[c.header_end:] == src[z.header_end:], 'export data changed'
    assert c.cooked_header_size == z.cooked_header_size
    for i, e in enumerate(c.exports):
        if e['global_import'] != NULL:
            assert e['global_import'] == imp(export_path(c, i, new_pkg))
    assert new_mesh in c.imports and old_mesh not in c.imports
    left = [n for n in c.names if job['src'] in n and not any(k in n for k in job['keep_names'])]
    assert not left, left
    return out, new_pkg, old_pid, new_pid


def main(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    for job in JOBS:
        data, pkg, old_pid, new_pid = make(job)
        path = os.path.join(out_dir, pkg[len('/Game/'):].replace('/', '__') + '.uasset')
        open(path, 'wb').write(data)
        z = Zen(data)
        print('%s: %d bytes, exports %s ...; mesh %s (package %016x, was %016x)' % (pkg, len(data), [e['name'] for e in z.exports][:2],
                                                                                  job['new_mesh'][0], new_pid, old_pid))


if __name__ == '__main__':
    main(sys.argv[1])
