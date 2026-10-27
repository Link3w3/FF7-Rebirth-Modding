"""Bahamut Fused Sephiroth (the End editor's FBX export of PC0010_17) -> npz in Unreal's space: the skeleton (names,
parents, component-space bind transforms from the clusters' TransformLink, local transforms), the mesh (control points,
normals, 4 UV sets, triangles, material per triangle and the material names) and the skin weights (per control point,
up to 12 influences).

The editor's exporter writes Z-up, front -Y, right-handed: Unreal's space with Y mirrored. Back in Unreal's space:
p = S p_fbx, M = S M_fbx S with S = diag(1, -1, 1).
    bfs_load.py <in.fbx> <out.npz>"""
import re
import sys
import numpy as np
sys.path.insert(0, '/work/ccseph/tools')
import fbxread

S3 = np.diag([1.0, -1.0, 1.0])
S4 = np.diag([1.0, -1.0, 1.0, 1.0])


def euler_xyz_matrix(rx, ry, rz):
    """FBX's Lcl Rotation (degrees, XYZ order: X applied first): Rz @ Ry @ Rx"""
    a, b, c = np.radians([rx, ry, rz])
    Rx = np.array([[1, 0, 0], [0, np.cos(a), -np.sin(a)], [0, np.sin(a), np.cos(a)]])
    Ry = np.array([[np.cos(b), 0, np.sin(b)], [0, 1, 0], [-np.sin(b), 0, np.cos(b)]])
    Rz = np.array([[np.cos(c), -np.sin(c), 0], [np.sin(c), np.cos(c), 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def main(src, dst):
    text_f = fbxread.read(src)
    models = text_f['models']
    conns = text_f['conns']
    parent_of = {}
    for c, p in conns:
        if c in models and (p in models or p == 0):
            parent_of.setdefault(c, p)
    bones = {mid: m for mid, m in models.items() if m['kind'] in ('LimbNode', 'Root')}
    # parent-first order
    order = []
    seen = set()

    def visit(mid):
        if mid in seen:
            return
        p = parent_of.get(mid)
        if p in bones:
            visit(p)
        seen.add(mid)
        order.append(mid)
    for mid in sorted(bones, key=lambda k: bones[k]['name']):
        visit(mid)
    idx = {mid: i for i, mid in enumerate(order)}
    names = [bones[mid]['name'] for mid in order]
    parents = np.array([idx.get(parent_of.get(mid), -1) if parent_of.get(mid) in bones else -1 for mid in order])
    NB = len(order)
    local_fbx = np.zeros((NB, 4, 4))
    for i, mid in enumerate(order):
        m = bones[mid]
        R = euler_xyz_matrix(*m['r'])
        if any(m['pre']) or any(m['post']):
            raise SystemExit('pre/post rotation on %s' % m['name'])
        M = np.eye(4)
        M[:3, :3] = R * np.array(m['s'])[None, :]
        M[:3, 3] = m['t']
        local_fbx[i] = M
    glob_fbx = np.zeros_like(local_fbx)
    for i in range(NB):
        glob_fbx[i] = local_fbx[i] if parents[i] < 0 else glob_fbx[parents[i]] @ local_fbx[i]
    # clusters: bone -> (indices, weights, TransformLink)
    cl_of_bone = {}
    for cid, c in text_f['clusters'].items():
        for a, b in conns:
            if a in bones and b == cid:
                cl_of_bone[a] = c
    link_fbx = np.array([cl_of_bone[mid]['TL'] if mid in cl_of_bone and cl_of_bone[mid]['TL'] is not None else glob_fbx[i]
                         for i, mid in enumerate(order)])
    diff = np.abs(link_fbx - glob_fbx).max(axis=(1, 2))
    print('TransformLink vs Lcl chain: max diff %.4g (bone %s)' % (diff.max(), names[int(diff.argmax())]))
    glob = np.array([S4 @ M @ S4 for M in link_fbx])
    local = np.array([glob[i] if parents[i] < 0 else np.linalg.inv(glob[parents[i]]) @ glob[i] for i in range(NB)])
    g = text_f['geos']
    assert len(g) == 1, len(g)
    g = g[0]
    pos = g['verts'] @ S3
    nrm = g['normals']
    assert nrm['mapping'] == 'ByVertice' and nrm['ref'] == 'Direct'
    normals = nrm['data'].reshape(-1, 3) @ S3
    uvs = []
    for u in g['uvs']:
        assert u['mapping'] == 'ByVertice'
        d = u['data'].reshape(-1, 2)
        if u['index'] is not None and len(u['index']):
            d = d[u['index']]
        uvs.append(d)
    pvi = g['pvi'].copy()
    ends = np.nonzero(pvi < 0)[0]
    pvi[ends] = ~pvi[ends]
    starts = np.concatenate([[0], ends[:-1] + 1])
    assert np.all(ends - starts == 2), 'not all triangles'
    tri = pvi.reshape(-1, 3)
    mats = g['materials']
    # the mesh's materials (connected to the mesh model) in connection order
    mesh_model = [mid for mid, m in models.items() if m['kind'] == 'Mesh'][0]
    mat_objs = {}
    for mm in re.finditer(r'\n\tMaterial: (-?\d+), "Material::([^"]*)"', open(src, encoding='utf-8', errors='replace').read()):
        mat_objs[int(mm.group(1))] = mm.group(2)
    mat_names = [mat_objs[a] for a, b in conns if b == mesh_model and a in mat_objs]
    NV = len(pos)
    wb = np.zeros((NV, 12), dtype=np.int32)
    ww = np.zeros((NV, 12), dtype=np.float32)
    cnt = np.zeros(NV, dtype=np.int32)
    for i, mid in enumerate(order):
        c = cl_of_bone.get(mid)
        if c is None or c['idx'] is None:
            continue
        for v, w in zip(c['idx'], c['w']):
            k = cnt[v]
            if k >= 12:
                j = int(np.argmin(ww[v]))
                if w > ww[v, j]:
                    wb[v, j], ww[v, j] = i, w
                continue
            wb[v, k], ww[v, k] = i, w
            cnt[v] += 1
    print('bones %d, control points %d, triangles %d, materials %s, max influences %d, unweighted %d' % (
        NB, NV, len(tri), mat_names, cnt.max(), int((cnt == 0).sum())))
    np.savez_compressed(dst, names=np.array(names), parents=parents, glob=glob, local=local, pos=pos, normals=normals,
                        uv0=uvs[0], uv1=uvs[1] if len(uvs) > 1 else uvs[0], uv2=uvs[2] if len(uvs) > 2 else uvs[0],
                        uv3=uvs[3] if len(uvs) > 3 else uvs[0], nuv=len(uvs), tri=tri, mat=mats, mat_names=np.array(mat_names),
                        wb=wb, ww=ww, wcount=cnt)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
