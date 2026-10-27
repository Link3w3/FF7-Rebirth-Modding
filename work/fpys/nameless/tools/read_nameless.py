"""WE1021_49.fbx (the End editor's export of the Nameless) -> nameless.npz: its bones (Unreal component space, cm: the
FBX's root Trans x100 taken into the bones) and its mesh (positions, corner normals, UV layers, colours, weights)."""
import sys, json
import numpy as np
import bpy
M = np.diag([1.0, -1.0, 1.0])


def main(fbx, out):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=fbx)
    a = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
    ob = [o for o in bpy.data.objects if o.type == 'MESH'][0]
    AW = np.array(a.matrix_world)
    unit = 100.0 / np.linalg.norm(AW[:3, 0]) if np.linalg.norm(AW[:3, 0]) < 1.0 else 100.0
    bones = []
    for b in a.data.bones:
        W = AW @ np.array(b.matrix_local)
        R = W[:3, :3] / np.linalg.norm(W[:3, 0])
        t = W[:3, 3]
        bones.append(dict(name=b.name, parent=b.parent.name if b.parent else 'Trans', R=(M @ R @ M).tolist(), t=(M @ t).tolist()))
    me = ob.data
    if hasattr(me, 'calc_normals_split'):
        me.calc_normals_split()
    W = np.array(ob.matrix_world)
    pos = (np.array([list(v.co) + [1.0] for v in me.vertices]) @ W.T)[:, :3] @ M.T
    Rn = W[:3, :3] / np.linalg.norm(W[:3, 0])
    faces, normals = [], []
    uvs = [[] for _ in me.uv_layers]
    cols = []
    ca = me.vertex_colors[0] if len(me.vertex_colors) else None
    mats = []
    for p in me.polygons:
        faces.append(list(p.vertices))
        mats.append(p.material_index)
        for li in p.loop_indices:
            n = Rn @ np.array(me.loops[li].normal)
            normals.append(M @ (n / max(np.linalg.norm(n), 1e-9)))
            for k, uvl in enumerate(me.uv_layers):
                uvs[k].append(list(uvl.data[li].uv))
            if ca is not None:
                cols.append(list(ca.data[li].color))
    gname = {g.index: g.name for g in ob.vertex_groups}
    wv, wb, ww = [], [], []
    for v in me.vertices:
        for ge in v.groups:
            if ge.weight > 0:
                wv.append(v.index); wb.append(gname[ge.group]); ww.append(ge.weight)
    names = sorted(set(wb))
    np.savez_compressed(out, pos=pos, face_sizes=np.array([len(f) for f in faces]), face_verts=np.concatenate([np.array(f) for f in faces]),
                        face_mats=np.array(mats), normals=np.array(normals), uvs=np.array(uvs), uv_names=np.array([u.name for u in me.uv_layers]),
                        colors=np.array(cols) if cols else np.zeros((0, 4)), w_vert=np.array(wv), w_bone=np.array([names.index(b) for b in wb]),
                        w_weight=np.array(ww), w_names=np.array(names), materials=np.array([s.material.name if s.material else '' for s in ob.material_slots]),
                        bones_json=np.array(json.dumps(bones)))
    print('bones', [(b['name'], b['parent'], [round(x, 2) for x in b['t']]) for b in bones])
    print('mesh: %d vertices, %d faces, uv layers %s, colours %s, materials %s, bounds %s .. %s' % (
        len(pos), len(faces), [u.name for u in me.uv_layers], bool(cols), [s.material.name if s.material else '' for s in ob.material_slots],
        pos.min(0).round(2), pos.max(0).round(2)))


if __name__ == '__main__':
    main(*sys.argv[1:3])
