"""Unity character bundle -> model.json + model.npz (skeleton, skinned meshes, materials) in Blender's space, and the
textures as PNG (normal maps rebuilt from Unity's DXT5nm packing into ordinary RGB normal maps, OpenGL / Y+).

Space: Unity (x, y, z) -> Blender (-x, -z, y), metres (the character faces -Y, Z up); triangle winding reversed.
Skeleton: every transform under the bone root; a bone that skins a mesh takes its bind pose (mesh world @ inverse
bindpose), any other bone its parent's matrix @ its own local transform from the prefab.

    extract_unity.py <bundle> <out dir> [bone root name (default root)]
"""
import json, os, sys
import numpy as np
import UnityPy
from UnityPy.helpers import MeshHelper
from PIL import Image

C3 = np.array([[-1.0, 0, 0], [0, 0, -1.0], [0, 1.0, 0]])
C4 = np.eye(4); C4[:3, :3] = C3


def rd(p):
    return p.deref_parse_as_object() if hasattr(p, 'deref_parse_as_object') else p.read()


def trs(t):
    p, q, s = t.m_LocalPosition, t.m_LocalRotation, t.m_LocalScale
    x, y, z, w = q.x, q.y, q.z, q.w
    n = (x * x + y * y + z * z + w * w) ** 0.5
    x, y, z, w = x / n, y / n, z / n, w / n
    R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                  [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                  [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    M = np.eye(4); M[:3, :3] = R * np.array([s.x, s.y, s.z]); M[:3, 3] = [p.x, p.y, p.z]
    return M


def mat4(b):
    return np.array([[getattr(b, 'e%d%d' % (i, j)) for j in range(4)] for i in range(4)], dtype=np.float64)


def normal_from_dxt5nm(img):
    a = np.asarray(img.convert('RGBA')).astype(np.float64) / 255.0
    x = a[..., 3] * 2 - 1
    y = a[..., 1] * 2 - 1
    z = np.sqrt(np.clip(1 - x * x - y * y, 0, 1))
    rgb = np.stack([x, y, z], -1) * 0.5 + 0.5
    return Image.fromarray(np.clip(np.round(rgb * 255), 0, 255).astype(np.uint8), 'RGB')


def main(bundle, out, bone_root='root'):
    os.makedirs(os.path.join(out, 'textures'), exist_ok=True)
    env = UnityPy.load(bundle)
    tr, go_name, comps = {}, {}, {}
    for o in env.objects:
        if o.type.name == 'Transform':
            t = o.read()
            tr[o.path_id] = t
            go_name[o.path_id] = rd(t.m_GameObject).m_Name
    parent = {c.path_id: pid for pid, t in tr.items() for c in t.m_Children}
    local = {pid: trs(t) for pid, t in tr.items()}

    def hier_world(pid):
        M = local[pid]
        while pid in parent:
            pid = parent[pid]
            M = local[pid] @ M
        return M

    # renderers
    smrs = []
    for o in env.objects:
        if o.type.name == 'SkinnedMeshRenderer':
            r = o.read()
            gname = rd(r.m_GameObject).m_Name
            tid = [pid for pid, n in go_name.items() if n == gname]
            assert len(tid) == 1, gname
            smrs.append((r, tid[0]))
    # bind worlds (Unity space) from the bind poses
    bind = {}
    for r, tid in smrs:
        m = rd(r.m_Mesh)
        Wm = hier_world(tid)
        for b, B in zip(r.m_Bones, m.m_BindPose):
            W = Wm @ np.linalg.inv(mat4(B))
            if b.path_id in bind:
                assert np.abs(bind[b.path_id] - W).max() < 1e-4, ('bind pose conflict', go_name[b.path_id])
            bind[b.path_id] = W
    # skeleton: the bone root and everything under it, parents first
    roots = [pid for pid, n in go_name.items() if n == bone_root]
    assert len(roots) == 1, bone_root
    order = []

    def walk(pid):
        order.append(pid)
        for c in tr[pid].m_Children:
            walk(c.path_id)
    walk(roots[0])
    missing = [go_name[p] for p in bind if p not in set(order)]
    assert not missing, ('bound bones outside the bone root', missing)
    world_u = {}
    for pid in order:
        if pid in bind:
            world_u[pid] = bind[pid]
        elif pid in parent and parent[pid] in world_u:
            world_u[pid] = world_u[parent[pid]] @ local[pid]
        else:
            world_u[pid] = hier_world(pid)
    names = [go_name[p] for p in order]
    assert len(set(n.lower() for n in names)) == len(names), 'bone names not unique'
    index = {p: i for i, p in enumerate(order)}
    bones = []
    worst = 0.0
    for pid in order:
        W = C4 @ world_u[pid] @ C4.T
        R = W[:3, :3]
        sc = np.linalg.norm(R, axis=0)
        worst = max(worst, float(np.abs(sc - 1).max()), float(abs(np.linalg.det(R) - 1)))
        U, _, Vt = np.linalg.svd(R)                       # (exactly orthonormal)
        R = U @ Vt
        W[:3, :3] = R
        bones.append(dict(name=go_name[pid], parent=index.get(parent.get(pid), -1) if pid != roots[0] else -1,
                          world=W.tolist(), skins=pid in bind))
    print('bones', len(bones), 'skinning', sum(b['skins'] for b in bones), 'worst scale/det error %.2e' % worst)

    # meshes
    arrays, meshes = {}, []
    for r, tid in smrs:
        m = rd(r.m_Mesh)
        h = MeshHelper.MeshHandler(m)
        h.process()
        Wm = hier_world(tid)
        Wn = np.linalg.inv(Wm[:3, :3]).T
        V = np.array(h.m_Vertices, dtype=np.float64).reshape(-1, 3)
        V = (Wm[:3, :3] @ V.T).T + Wm[:3, 3]
        N = np.array(h.m_Normals, dtype=np.float64).reshape(-1, 3)
        N = (Wn @ N.T).T
        N /= np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-12)
        key = m.m_Name
        arrays[key + '/co'] = (C3 @ V.T).T.astype(np.float32)
        arrays[key + '/no'] = (C3 @ N.T).T.astype(np.float32)
        arrays[key + '/uv0'] = np.array(h.m_UV0, dtype=np.float32).reshape(-1, 2)
        if h.m_UV1:
            arrays[key + '/uv1'] = np.array(h.m_UV1, dtype=np.float32).reshape(-1, 2)
        if h.m_Colors:
            col = np.array(h.m_Colors, dtype=np.float32).reshape(-1, 4)
            arrays[key + '/col'] = col / 255.0 if col.max() > 1.0 else col
        bi = np.array(h.m_BoneIndices, dtype=np.int64)
        bw = np.array(h.m_BoneWeights, dtype=np.float64)
        bnames = [go_name[b.path_id] for b in r.m_Bones]
        gidx = np.array([names.index(n) for n in bnames])
        vv, kk = np.nonzero(bw > 0)
        arrays[key + '/w_vert'] = vv.astype(np.int32)
        arrays[key + '/w_bone'] = gidx[bi[vv, kk]].astype(np.int32)
        arrays[key + '/w_val'] = bw[vv, kk].astype(np.float32)
        tri_lists = h.get_triangles()
        mats = [rd(x).m_Name for x in r.m_Materials]
        tris, tmat = [], []
        for si, tl in enumerate(tri_lists):
            t = np.array(tl, dtype=np.int64).reshape(-1, 3)
            tris.append(t[:, [0, 2, 1]])                  # winding reversed for the mirrored space
            tmat.append(np.full(len(t), min(si, len(mats) - 1)))
        arrays[key + '/tri'] = np.concatenate(tris).astype(np.int32)
        arrays[key + '/tri_mat'] = np.concatenate(tmat).astype(np.int32)
        meshes.append(dict(name=key, object=go_name[tid], materials=mats, vertices=len(V), triangles=int(sum(len(t) for t in tris)),
                           has_uv1=bool(h.m_UV1), has_colors=bool(h.m_Colors)))
        print(key, len(V), 'verts', meshes[-1]['triangles'], 'tris', mats)

    # materials and textures
    materials, used_tex = {}, {}
    for o in env.objects:
        if o.type.name == 'Material':
            mt = o.read()
            sp = mt.m_SavedProperties
            tex, ext = {}, {}
            for k, v in sp.m_TexEnvs:
                if not v.m_Texture.path_id:
                    continue
                if v.m_Texture.file_id == 0:
                    tname = rd(v.m_Texture).m_Name
                    tex[k] = dict(texture=tname, scale=[v.m_Scale.x, v.m_Scale.y], offset=[v.m_Offset.x, v.m_Offset.y])
                    used_tex.setdefault(tname, set()).add(k)
                else:
                    ext[k] = 'not in this bundle'
            kw = getattr(mt, 'm_ValidKeywords', None) or (getattr(mt, 'm_ShaderKeywords', '') or '').split()
            materials[mt.m_Name] = dict(textures=tex, external_textures=ext, keywords=list(kw or []),
                                        render_queue=mt.m_CustomRenderQueue,
                                        tags=dict(getattr(mt, 'stringTagMap', None) or []),
                                        floats={k: float(v) for k, v in sp.m_Floats},
                                        colors={k: [c.r, c.g, c.b, c.a] for k, c in sp.m_Colors})
    textures = {}
    for o in env.objects:
        if o.type.name == 'Texture2D':
            t = o.read()
            img = t.image
            slots = used_tex.get(t.m_Name, set())
            if '_BumpMap' in slots:
                img = normal_from_dxt5nm(img)
                kind = 'normal'
            else:
                a = np.asarray(img.convert('RGBA'))
                kind = 'mrox' if '_MetallicGlossMap' in slots else 'ramp' if '_RampMap' in slots else 'color'
                img = img.convert('RGBA') if a[..., 3].min() < 255 else img.convert('RGB')
            fn = t.m_Name + '.png'
            img.save(os.path.join(out, 'textures', fn), optimize=True)
            textures[t.m_Name] = dict(file='textures/' + fn, kind=kind, size=[t.m_Width, t.m_Height], slots=sorted(slots),
                                      alpha=img.mode == 'RGBA')
    np.savez_compressed(os.path.join(out, 'model.npz'), **arrays)
    json.dump(dict(bones=bones, meshes=meshes, materials=materials, textures=textures), open(os.path.join(out, 'model.json'), 'w'), indent=1)
    print('textures', len(textures), 'materials', len(materials))


if __name__ == '__main__':
    main(*sys.argv[1:])
