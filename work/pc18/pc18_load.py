"""PC0010_18 (the user's binary FBX 7.4 from Blender: Neo Bahamut BlackFeeler's skeleton and Whisper body with Rebirth
Sephiroth's head and hair, the armature object scaled (0.2037, 0.4810, 0.3237) on its own axes) -> npz in Unreal's space.

The file: Y up (the armature and meshes turned -90 about X: Blender's Z-up space, "A" below, inside it), cm. The bones'
local transforms are the game skeletons' own (Neo Bahamut's SU2050_00_Skeleton, Sephiroth's head) with Y mirrored, the
armature's scale applied on top of all of them. Unreal's space from the file's: (x, y, z)_ue = (X, Z, Y)_fbx; from A:
p_ue = M p_A, R_ue = M R_A M (M = diag(1, -1, 1)), as the game's own local transforms are the file's with Y mirrored.

Writes:
  bones   names, parents (parents first), P (component-space joints, cm, the scale applied: where they are in the model),
          R (each bone's frame with the scale left out: the game skeleton's own frame), bind_link (the clusters'
          TransformLink in Unreal's space, for the check)
  mesh    the three meshes as one: cp (control points), wb/ww (up to 12 influences each), corners: tri (corner -> control
          point), nrm, uv0..uv2, col (RGBA), tmat (material of each triangle), mat_names
    pc18_load.py <in.fbx> <out.npz>"""
import sys
import numpy as np
import bpy  # noqa: F401  (Blender's FBX reader lives in its add-ons)
from io_scene_fbx.parse_fbx import parse

M3 = np.diag([1.0, -1.0, 1.0])
P_SWAP = np.array([[1.0, 0, 0], [0, 0, 1.0], [0, 1.0, 0]])   # Unreal from the file's world


def euler_xyz(rx, ry, rz):
    a, b, c = np.radians([rx, ry, rz])
    Rx = np.array([[1, 0, 0], [0, np.cos(a), -np.sin(a)], [0, np.sin(a), np.cos(a)]])
    Ry = np.array([[np.cos(b), 0, np.sin(b)], [0, 1, 0], [-np.sin(b), 0, np.cos(b)]])
    Rz = np.array([[np.cos(c), -np.sin(c), 0], [np.sin(c), np.cos(c), 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def name_of(o):
    return o.props[1].split(b'\x00\x01')[0].decode()


def props70(o):
    out = {}
    for p in o.elems:
        if p.id == b'Properties70':
            for q in p.elems:
                out[q.props[0].decode()] = q.props[4:]
    return out


def child(o, key):
    for c in o.elems:
        if c.id == key:
            return c
    return None


def arr(o, key):
    c = child(o, key)
    return None if c is None else np.array(c.props[0])


def lcl(p):
    t = np.array(p.get('Lcl Translation', [0, 0, 0]), dtype=float)
    r = np.array(p.get('Lcl Rotation', [0, 0, 0]), dtype=float)
    s = np.array(p.get('Lcl Scaling', [1, 1, 1]), dtype=float)
    M = np.eye(4)
    M[:3, :3] = euler_xyz(*r) * s[None, :]
    M[:3, 3] = t
    R = np.eye(4)
    R[:3, :3] = euler_xyz(*r)
    R[:3, 3] = t
    return M, R, s


def main(src, dst):
    root, _ver = parse(src)
    objs = child(root, b'Objects')
    conns = child(root, b'Connections')
    by_uid = {}
    for o in objs.elems:
        by_uid[o.props[0]] = o
    links = [(c.props[1], c.props[2]) for c in conns.elems if c.props[0] == b'OO']
    parent = {}
    for a, b in links:
        if a in by_uid and by_uid[a].id == b'Model':
            parent.setdefault(a, b)
    models = {u: o for u, o in by_uid.items() if o.id == b'Model'}
    kind = {u: o.props[2].decode() for u, o in models.items()}
    bones = [u for u in models if kind[u] == 'LimbNode']
    # world matrices (the file's), with and without the scales
    W, Wr = {}, {}

    def world(u):
        if u in W:
            return W[u], Wr[u]
        M, R, _s = lcl(props70(models[u]))
        p = parent.get(u)
        if p in models:
            PW, PR = world(p)
            W[u], Wr[u] = PW @ M, PR @ R
        else:
            W[u], Wr[u] = M, R
        return W[u], Wr[u]
    order, seen = [], set()

    def visit(u):
        if u in seen:
            return
        p = parent.get(u)
        if p in models and kind[p] == 'LimbNode':
            visit(p)
        seen.add(u)
        order.append(u)
    for u in sorted(bones, key=lambda k: name_of(models[k])):
        visit(u)
    idx = {u: i for i, u in enumerate(order)}
    names = [name_of(models[u]) for u in order]
    parents = np.array([idx[parent[u]] if parent.get(u) in idx else -1 for u in order])
    arm = [u for u in models if kind[u] == 'Null']
    arm_p = props70(models[arm[0]])
    arm_rot = euler_xyz(*arm_p.get('Lcl Rotation', [0, 0, 0]))
    arm_scale = np.array(arm_p.get('Lcl Scaling', [1, 1, 1]), dtype=float)
    # bone frames in A (the armature's own space): the file's world rotation without the armature's turn and scales
    NB = len(order)
    P = np.zeros((NB, 3))
    R = np.zeros((NB, 3, 3))
    for i, u in enumerate(order):
        Wm, Wrm = world(u)
        P[i] = P_SWAP @ Wm[:3, 3]
        RA = arm_rot.T @ Wrm[:3, :3]          # the chain of local turns (in A)
        R[i] = M3 @ RA @ M3
    # the clusters: per mesh model, its skin's clusters
    geos = {u: o for u, o in by_uid.items() if o.id == b'Geometry'}
    mats = {u: name_of(o) for u, o in by_uid.items() if o.id == b'Material'}
    deformers = {u: o for u, o in by_uid.items() if o.id == b'Deformer'}
    mesh_models = [u for u in models if kind[u] == 'Mesh']
    cps, wbs, wws, tris, nrms, uvs, cols, tmats, ccps = [], [], [], [], [], [[], [], []], [], [], []
    mat_names = []
    link = np.zeros((NB, 4, 4))
    have_link = np.zeros(NB, dtype=bool)
    base = 0          # control points so far
    corners = 0       # corners so far
    report = []
    for mm in sorted(mesh_models, key=lambda k: name_of(models[k])):
        geo = [a for a, b in links if b == mm and a in geos][0]
        g = geos[geo]
        mw, _ = world(mm)
        v = arr(g, b'Vertices').reshape(-1, 3)
        vw = (mw[:3, :3] @ v.T).T + mw[:3, 3]
        cp = (P_SWAP @ vw.T).T
        nv = len(cp)
        # materials of this mesh model, in connection order
        mlist = [mats[a] for a, b in links if b == mm and a in mats]
        pvi = arr(g, b'PolygonVertexIndex').astype(np.int64)
        ends = np.nonzero(pvi < 0)[0]
        cpi = pvi.copy()
        cpi[ends] = ~cpi[ends]
        starts = np.concatenate([[0], ends[:-1] + 1])

        def layer(tag, data_key, index_key, width):
            out = []
            for e in [c for c in g.elems if c.id == tag]:
                mapping = child(e, b'MappingInformationType').props[0]
                ref = child(e, b'ReferenceInformationType').props[0]
                d = np.array(child(e, data_key).props[0]).reshape(-1, width)
                if ref == b'IndexToDirect':
                    d = d[np.array(child(e, index_key).props[0])]
                assert mapping in (b'ByPolygonVertex', b'ByVertice', b'ByControlPoint'), mapping
                if mapping in (b'ByVertice', b'ByControlPoint'):
                    d = d[cpi]
                out.append(d)
            return out
        n_corner = layer(b'LayerElementNormal', b'Normals', b'NormalsIndex', 3)[0]
        n_corner = (P_SWAP @ (mw[:3, :3] @ n_corner.T)).T
        n_corner /= np.linalg.norm(n_corner, axis=1, keepdims=True) + 1e-12
        uv_l = layer(b'LayerElementUV', b'UV', b'UVIndex', 2)
        col_l = layer(b'LayerElementColor', b'Colors', b'ColorIndex', 4)
        ml = [c for c in g.elems if c.id == b'LayerElementMaterial'][0]
        pmat = np.array(child(ml, b'Materials').props[0])
        if child(ml, b'MappingInformationType').props[0] == b'AllSame':
            pmat = np.full(len(starts), pmat[0])
        gmat = []
        for m in mlist:
            if m not in mat_names:
                mat_names.append(m)
            gmat.append(mat_names.index(m))
        # triangles by corner (fans)
        t_c, t_m = [], []
        for k, (s, e) in enumerate(zip(starts, ends)):
            for j in range(s + 1, e):
                t_c.append((s, j, j + 1))
                t_m.append(gmat[pmat[k]])
        t_c = np.array(t_c, dtype=np.int64)
        tris.append(t_c + corners)
        ccps.append(cpi + base)
        nrms.append(n_corner)
        for k in range(3):
            uvs[k].append(uv_l[k] if k < len(uv_l) else uv_l[0])
        cols.append(col_l[0] if col_l else np.ones((len(cpi), 4)))
        tmats.append(np.array(t_m))
        cps.append(cp)
        # skin
        skin = [a for a, b in links if b == geo and a in deformers and deformers[a].props[2] == b'Skin']
        wb = np.zeros((nv, 12), dtype=np.int32)
        ww = np.zeros((nv, 12), dtype=np.float32)
        cnt = np.zeros(nv, dtype=np.int32)
        if skin:
            for c in [a for a, b in links if b == skin[0] and a in deformers]:
                bone = [a for a, b in links if b == c and a in idx]
                if not bone:
                    continue
                bi = idx[bone[0]]
                co = deformers[c]
                ii = arr(co, b'Indexes')
                wts = arr(co, b'Weights')
                tl = arr(co, b'TransformLink').reshape(4, 4).T
                L = np.eye(4)
                L[:3, :3] = P_SWAP @ tl[:3, :3] @ P_SWAP
                L[:3, 3] = P_SWAP @ tl[:3, 3]
                if not have_link[bi]:
                    link[bi] = L
                    have_link[bi] = True
                if ii is None:
                    continue
                for vi, w in zip(ii.tolist(), wts.tolist()):
                    k = cnt[vi]
                    if k >= 12:
                        j = int(np.argmin(ww[vi]))
                        if w > ww[vi, j]:
                            wb[vi, j], ww[vi, j] = bi, w
                        continue
                    wb[vi, k], ww[vi, k] = bi, w
                    cnt[vi] += 1
        wbs.append(wb)
        wws.append(ww)
        report.append('%s: %d control points, %d polygons, %d triangles, materials %s, skin %s, unweighted %d, max influences %d' % (
            name_of(models[mm]), nv, len(starts), len(t_c), mlist, bool(skin), int((cnt == 0).sum()), int(cnt.max())))
        base += nv
        corners += len(cpi)
    corner_cp = np.concatenate(ccps)
    out = dict(names=np.array(names), parents=parents, P=P, R=R, bind_link=link, have_link=have_link,
               arm_scale=arm_scale, cp=np.concatenate(cps), wb=np.concatenate(wbs), ww=np.concatenate(wws),
               corner_cp=corner_cp, tri=np.concatenate(tris), nrm=np.concatenate(nrms),
               uv0=np.concatenate(uvs[0]), uv1=np.concatenate(uvs[1]), uv2=np.concatenate(uvs[2]), col=np.concatenate(cols),
               tmat=np.concatenate(tmats), mat_names=np.array(mat_names))
    # the check: each cluster's TransformLink against the joints and frames worked out from the local transforms
    dp = np.linalg.norm(link[have_link][:, :3, 3] - P[have_link], axis=1)
    print('\n'.join(report))
    print('bones %d (with a cluster %d); TransformLink vs joints: max %.4f cm' % (NB, int(have_link.sum()), dp.max()))
    print('armature scale', arm_scale.tolist(), 'materials', mat_names)
    np.savez_compressed(dst, **out)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
