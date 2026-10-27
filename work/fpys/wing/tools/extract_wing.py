"""The transformed Sephiroth's wing out of PC0010_10.fbx (the End editor's export of the game's PC0010_10): the faces of
material slot PC0010_10_Wing with their corners' normals, UVs (every UV layer) and colours, each vertex's position and
weights, in Unreal's component space (centimetres; the FBX's Blender space flipped in Y). Saved as an .npz.
    blender -b -P extract_wing.py -- <PC0010_10.fbx> <out .npz>     (or python3 with the bpy module)"""
import sys
import numpy as np
import bpy

M = np.diag([1.0, -1.0, 1.0])


def main(fbx, out):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=fbx)
    ob = [o for o in bpy.data.objects if o.type == 'MESH'][0]
    me = ob.data
    slots = [s.material.name if s.material else '' for s in ob.material_slots]
    wing = slots.index('PC0010_10_Wing')
    if hasattr(me, 'calc_normals_split'):
        me.calc_normals_split()
    polys = [p for p in me.polygons if p.material_index == wing]
    vids = sorted({v for p in polys for v in p.vertices})
    remap = {v: i for i, v in enumerate(vids)}
    W = np.array(ob.matrix_world)            # Blender world (m) <- mesh local (cm)
    pos = np.array([list(me.vertices[v].co) + [1.0] for v in vids]) @ W.T
    pos = pos[:, :3] * 100.0 @ M.T            # cm, Unreal component space
    R = W[:3, :3] / np.linalg.norm(W[:3, 0])
    faces, corner_normals, corner_uvs, corner_cols = [], [], [[] for _ in me.uv_layers], []
    cols = me.vertex_colors[0] if len(me.vertex_colors) else None
    for p in polys:
        faces.append([remap[v] for v in p.vertices])
        for li in p.loop_indices:
            n = R @ np.array(me.loops[li].normal)
            corner_normals.append(M @ (n / max(np.linalg.norm(n), 1e-9)))
            for k, uvl in enumerate(me.uv_layers):
                corner_uvs[k].append(list(uvl.data[li].uv))
            if cols is not None:
                corner_cols.append(list(cols.data[li].color))
    sizes = np.array([len(f) for f in faces])
    gname = {g.index: g.name for g in ob.vertex_groups}
    wb, wv, ww = [], [], []
    for v in vids:
        for ge in me.vertices[v].groups:
            if ge.weight > 0:
                wb.append(gname[ge.group]); wv.append(remap[v]); ww.append(ge.weight)
    bones = sorted(set(wb))
    np.savez_compressed(out, pos=pos, face_sizes=sizes, face_verts=np.concatenate([np.array(f) for f in faces]),
                        normals=np.array(corner_normals), uvs=np.array(corner_uvs), uv_names=np.array([u.name for u in me.uv_layers]),
                        colors=np.array(corner_cols) if corner_cols else np.zeros((0, 4)),
                        w_bone=np.array([bones.index(b) for b in wb]), w_vert=np.array(wv), w_weight=np.array(ww),
                        bones=np.array(bones))
    print('wing: %d vertices, %d faces (%s), %d corners, uv layers %s, colours %s, %d bones weighting it' % (
        len(vids), len(faces), dict(zip(*np.unique(sizes, return_counts=True))), len(corner_normals),
        [u.name for u in me.uv_layers], bool(corner_cols), len(bones)))
    print('bounds (cm, Unreal)', pos.min(0).round(2), pos.max(0).round(2))


if __name__ == '__main__':
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    main(*args[:2])
