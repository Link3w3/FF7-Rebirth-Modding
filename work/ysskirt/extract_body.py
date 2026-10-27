"""Young Sephiroth's body mesh out of PC0010_13_v3.fbx: every vertex's position (Unreal component space, cm: the FBX's
Blender space flipped in Y) and weights, and the armature's bone heads, for sizing the coat's leg colliders.
    python3 extract_body.py <fbx> <out.npz>"""
import sys
import numpy as np
import bpy

M = np.diag([1.0, -1.0, 1.0])


def main(fbx, out):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=fbx)
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    arm = [o for o in bpy.data.objects if o.type == 'ARMATURE']
    print('meshes', [(o.name, len(o.data.vertices)) for o in meshes], 'armatures', [a.name for a in arm])
    allpos, wb, wv, ww, mats, vmat = [], [], [], [], [], []
    names = []
    base = 0
    for ob in meshes:
        me = ob.data
        W = np.array(ob.matrix_world)
        pos = np.array([list(v.co) + [1.0] for v in me.vertices]) @ W.T
        pos = pos[:, :3] * 100.0 @ M.T
        allpos.append(pos)
        gname = {g.index: g.name for g in ob.vertex_groups}
        for v in me.vertices:
            for ge in v.groups:
                if ge.weight > 0 and ge.group in gname:
                    wb.append(gname[ge.group]); wv.append(base + v.index); ww.append(ge.weight)
        slots = [s.material.name if s.material else '' for s in ob.material_slots]
        vm = np.full(len(me.vertices), -1)
        for p in me.polygons:
            for v in p.vertices:
                vm[v] = len(mats) + p.material_index
        mats += [ob.name + ':' + s for s in slots]
        vmat.append(vm)
        base += len(me.vertices)
    bones = sorted(set(wb))
    heads = {}
    if arm:
        a = arm[0]
        A = np.array(a.matrix_world)
        for b in a.data.bones:
            h = A @ np.array(list(b.head_local) + [1.0])
            heads[b.name] = (h[:3] * 100.0) @ M.T
    np.savez_compressed(out, pos=np.concatenate(allpos), w_bone=np.array([bones.index(b) for b in wb]), w_vert=np.array(wv),
                        w_weight=np.array(ww), bones=np.array(bones), vmat=np.concatenate(vmat), mats=np.array(mats),
                        head_names=np.array(list(heads.keys())), head_pos=np.array(list(heads.values())) if heads else np.zeros((0, 3)))
    print('vertices', base, 'bones weighting', len(bones), 'materials', mats)


if __name__ == '__main__':
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    main(*args[:2])
