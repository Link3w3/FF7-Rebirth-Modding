"""PC0010_13.fbx: ch049_001 (the same scene as CH049_001_cm.fbx: build_blend.build_scene, centimetres, facing +X) with
its armature rebuilt on rig.json's bones (Rebirth's names, parents and frames; rig_ys.py) and its vertex groups renamed
to match, exported with export_fbx.py's settings.

Unreal's FBX import of these scenes makes a bone's component-space rotation M R M and position M t from the armature's
bone matrix (R, t), M = diag(1, -1, 1) (the same relation retarget_from_seph uses to read CH049_001_Skeleton), so each
bone's matrix here is M R_ue M, M t_ue.
    build_rig_fbx.py <rig.json> <model dir> <out .fbx>"""
import json, os, sys
sys.path[:0] = ['/work/unityrip/scripts']
import numpy as np
import bpy
from mathutils import Matrix, Quaternion
import build_blend as BB

DOUBLE = {'hair_geo', 'hair_tp_geo', 'eyelash_geo'}
M = np.diag([1.0, -1.0, 1.0])


def quat_matrix(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def main(rig_path, model_dir, out):
    rig = json.load(open(rig_path))
    scene, coll, arm_ob = BB.build_scene(model_dir, double=DOUBLE, unit=100.0, turn=90.0)
    arm_ob.name = 'Armature'
    arm = arm_ob.data
    arm.name = 'PC0010_13'
    bpy.context.view_layer.objects.active = arm_ob
    bpy.ops.object.mode_set(mode='EDIT')
    for eb in list(arm.edit_bones):
        arm.edit_bones.remove(eb)
    kids = {}
    for b in rig['bones']:
        kids.setdefault(b['parent'], []).append(b)
    made = {}
    for b in rig['bones']:
        eb = arm.edit_bones.new(b['name'])
        t = np.array(b['t'])
        d = [np.linalg.norm(np.array(k['t']) - t) for k in kids.get(b['name'], [])]
        L = min(max(max(d) if d else 2.0, 1.0), 12.0)
        eb.head = (0, 0, 0)
        eb.tail = (0, L, 0)
        R = M @ quat_matrix(b['q']) @ M
        W = Matrix.Identity(4)
        for i in range(3):
            for j in range(3):
                W[i][j] = R[i, j]
        tb = M @ t
        W.translation = (tb[0], tb[1], tb[2])
        eb.matrix = W
        made[b['name']] = eb
    for b in rig['bones']:
        if b['parent']:
            made[b['name']].parent = made[b['parent']]
            made[b['name']].use_connect = False
    bpy.ops.object.mode_set(mode='OBJECT')
    rename = rig['rename']
    drop = set(rig['drop'])
    renamed = 0
    for ob in coll.objects:
        if ob.type != 'MESH':
            continue
        for g in list(ob.vertex_groups):
            if g.name in drop:
                ob.vertex_groups.remove(g)
            elif g.name in rename and rename[g.name] != g.name:
                g.name = rename[g.name]
                renamed += 1
        missing = [g.name for g in ob.vertex_groups if g.name not in made]
        assert not missing, (ob.name, missing)
    out = os.path.abspath(out)
    bpy.ops.export_scene.fbx(filepath=out, use_selection=False, object_types={'ARMATURE', 'MESH'},
                             apply_unit_scale=True, apply_scale_options='FBX_SCALE_NONE', global_scale=1.0,
                             axis_forward='-Z', axis_up='Y', use_mesh_modifiers=False, mesh_smooth_type='FACE',
                             use_tspace=False, add_leaf_bones=False, primary_bone_axis='Y', secondary_bone_axis='X',
                             armature_nodetype='NULL', bake_anim=False, path_mode='STRIP', embed_textures=False,
                             use_custom_props=False)
    print('wrote', out, os.path.getsize(out), 'bones', len(made), 'vertex groups renamed', renamed)
    # read it back: names, parents and each bone's matrix as Unreal will read it
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=out)
    arms = [o for o in bpy.data.objects if o.type == 'ARMATURE']
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    a = arms[0]
    back = {bb.name: bb for bb in a.data.bones}
    worst = 0.0
    for b in rig['bones']:
        bb = back[b['name']]
        assert (bb.parent.name if bb.parent else None) == b['parent'], (b['name'], bb.parent and bb.parent.name, b['parent'])
        R = np.array(bb.matrix_local.to_3x3())
        R_ue = M @ R @ M
        worst = max(worst, float(np.abs(R_ue - quat_matrix(b['q'])).max()))
    pts = [m.matrix_world @ v.co for m in meshes for v in m.data.vertices]
    print('read back: %d bones, %d meshes, largest frame difference %.2e, height %.1f' % (len(back), len(meshes), worst,
                                                                                      max(p.z for p in pts) - min(p.z for p in pts)))


if __name__ == '__main__':
    main(*sys.argv[1:4])
