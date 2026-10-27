"""FF7 Remake (UE 4.18 SQEX) cooked SkeletalMesh native data."""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from binr import B

def ref_skeleton(r):
    bones = r.arr(lambda: (r.name(), r.i32()))
    poses = r.arr(lambda: r.un('<10f'))
    nmap = r.arr(lambda: (r.name(), r.i32()))
    return dict(bones=bones, poses=poses, name_map=nmap)

def section(r):
    s = {}
    s['strip'] = r.un('<BB')
    s['material'] = r.u16()
    s['base_index'] = r.u32()
    s['num_triangles'] = r.u32()
    s['tri_sort'] = r.u8()
    s['disabled'] = r.b32()
    s['cloth_section'] = r.i16()
    s['cloth_lod'] = r.u8()
    s['recompute_tangent'] = r.b32()
    s['cast_shadow'] = r.b32()
    s['base_vertex'] = r.u32()
    s['bone_map'] = r.arr(r.u16, 1024)
    s['num_vertices'] = r.i32()
    s['max_influences'] = r.i32()
    n = r.i32()
    if n: raise NotImplementedError('cloth mapping data %d at %d' % (n, r.p))
    pv = r.arr(lambda: r.un('<3f'))
    pn = r.arr(lambda: r.un('<3f'))
    s['cloth_asset'] = r.i16()
    s['clothing_guid'] = r.raw(16).hex(); s['clothing_lod'] = r.i32()
    s['sq_flag'] = r.i32()
    n = r.i32()
    if not 0 <= n < 1 << 22: raise ValueError('bad section extra count %d at %d' % (n, r.p - 4))
    s['sq_vertex_data'] = r.raw(16 * n)     # SQEX: 16 bytes a vertex (hair sections)
    return s

def index_container(r):
    size = r.u8()
    es, n, data = r.bulk_array()
    if es != size: raise ValueError('index size %d vs %d' % (es, size))
    return dict(size=size, count=n, data=data)

def lod(r, has_colors, dbg=False):
    L = {}
    L['strip'] = r.un('<BB')
    L['sections'] = r.arr(lambda: section(r), 256)
    if dbg: print('  sections', len(L['sections']), 'at', r.p)
    L['indices'] = index_container(r)
    if dbg: print('  indices', L['indices']['size'], L['indices']['count'], 'at', r.p)
    L['active_bones'] = r.arr(r.u16, 4096)
    L['a0'] = r.i32()
    L['num_vertices'] = r.u32()
    L['required_bones'] = r.arr(r.u16, 4096)
    L['a1'] = r.i32(); L['a2'] = r.i32()
    L['num_texcoords'] = r.u32()
    if dbg: print('  active %d a0 %d verts %d required %d a1 %d a2 %d uvs %d at %d' % (len(L['active_bones']), L['a0'], L['num_vertices'], len(L['required_bones']), L['a1'], L['a2'], L['num_texcoords'], r.p))
    # FSkeletalMeshVertexBuffer
    vb = {}
    vb['strip'] = r.un('<BB')
    vb['num_texcoords'] = r.u32()
    vb['full_uvs'] = r.b32()
    vb['extension'] = r.un('<3f'); vb['origin'] = r.un('<3f')
    vb['stride'], vb['count'], vb['data'] = r.bulk_array()
    L['vertices'] = vb
    if dbg: print('  vertices %d x %d uvs %d full %s at %d' % (vb['count'], vb['stride'], vb['num_texcoords'], vb['full_uvs'], r.p))
    sw = {}
    sw['strip'] = r.un('<BB')
    sw['extra_influences'] = r.b32()
    sw['num_vertices'] = r.u32()
    sw['stride'], sw['count'], sw['data'] = r.bulk_array()
    L['weights'] = sw
    if dbg: print('  weights %d x %d extra %s at %d: %s' % (sw['count'], sw['stride'], sw['extra_influences'], r.p, r.peek(48)))
    if has_colors:
        cv = {}
        cv['strip'] = r.un('<BB'); cv['stride'] = r.u32(); cv['num'] = r.u32()
        if cv['num']:
            cv['es'], cv['count'], cv['data'] = r.bulk_array()
        L['colors'] = cv
    if not (L['strip'][1] & 1):
        L['adjacency'] = index_container(r)
        if dbg: print('  adjacency %d x %d at %d: %s' % (L['adjacency']['count'], L['adjacency']['size'], r.p, r.peek(48)))
    if not any(sec['sq_flag'] for sec in L['sections']):
        return L
    # SQEX: the sections' 16-byte vertex records again, as one buffer
    L['sq_strip'] = r.un('<BB')
    L['sq_stride'], L['sq_count'], L['sq_data'] = r.bulk_array()
    # SQEX: per vertex, the index of its record in that buffer (-1: none)
    L['sq_map_strip'] = r.un('<BB')
    L['sq_map_stride'], L['sq_map_count'], L['sq_map'] = r.bulk_array()
    if dbg: print('  sq buffer %d x %d, map %d x %d, at %d: %s' % (L['sq_count'], L['sq_stride'], L['sq_map_count'], L['sq_map_stride'], r.p, r.peek(32)))
    return L

def read(pkg, export_index, props_end):
    e = pkg.exports[export_index]
    r = B(pkg.d, props_end, pkg.names, e['off'] + e['size'])
    M = {}
    M['guid'] = r.b32()
    M['strip'] = r.un('<BB')
    M['bounds'] = r.un('<7f')
    M['materials'] = r.arr(lambda: dict(material=r.i32(), slot=r.name(), a=r.u32(), b=r.u32(), uv_density=r.un('<4f')))
    M['ref'] = ref_skeleton(r)
    nl = r.i32()
    M['lods'] = []
    for i in range(nl):
        print('LOD', i, 'at', r.p)
        M['lods'].append(lod(r, False, True))
    print('after LODs at', r.p, 'of', r.end, r.peek(160))
    return M, r

if __name__ == '__main__':
    import pkg418, uprops
    from schema import Schema
    S = Schema()
    p = pkg418.Package(sys.argv[1])
    cls, v, end = uprops.read_export(S, p, 0)
    M, r = read(p, 0, end)
