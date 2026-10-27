"""PC0010_13 with the wing (build_rig_fbx_wing.py's scene, unchanged) and a hair core (hair_core.make_core: an opaque cap
inside his hair, material slot PC0010_13_HairCore). Exported with the same settings, then read back.
    build_rig_fbx_haircore.py <rig_wing.json> <model dir> <wing .npz> <head texture .png> <out .fbx> [report .json]"""
import json, os, sys
sys.path[:0] = ['/work/unityrip/scripts', '/work/ys/rig', '/work/fpys/wing/tools',
                os.path.dirname(os.path.abspath(__file__))]
import numpy as np
import bpy
from mathutils import Matrix
import build_blend as BB
import build_rig_fbx as BR
import build_rig_fbx_wing as BW
import hair_core as HC

M = BR.M


def build(rig_path, model_dir, npz_path, head_tex):
    rig = json.load(open(rig_path))
    scene, coll, arm_ob = BB.build_scene(model_dir, double=BR.DOUBLE, unit=100.0, turn=90.0)
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
        R = M @ BR.quat_matrix(b['q']) @ M
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
    BR.share_weights(rig, coll)
    for ob in list(coll.objects):
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
    BW.add_wing(rig, coll, arm_ob, npz_path, made)
    core, report = HC.make_core(coll, arm_ob, head_tex)
    missing = [g.name for g in core.vertex_groups if g.name not in made]
    assert not missing, ('core', missing)
    return rig, scene, coll, arm_ob, made, core, report


def main(rig_path, model_dir, npz_path, head_tex, out, report_path=None):
    rig, scene, coll, arm_ob, made, core, report = build(rig_path, model_dir, npz_path, head_tex)
    out = os.path.abspath(out)
    bpy.ops.export_scene.fbx(filepath=out, use_selection=False, object_types={'ARMATURE', 'MESH'},
                             apply_unit_scale=True, apply_scale_options='FBX_SCALE_NONE', global_scale=1.0,
                             axis_forward='-Z', axis_up='Y', use_mesh_modifiers=False, mesh_smooth_type='FACE',
                             use_tspace=False, add_leaf_bones=False, primary_bone_axis='Y', secondary_bone_axis='X',
                             armature_nodetype='NULL', bake_anim=False, path_mode='STRIP', embed_textures=False,
                             use_custom_props=False)
    print('wrote', out, os.path.getsize(out), 'bones', len(made))
    print('core:', json.dumps(report))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=out)
    a = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    back = {bb.name: bb for bb in a.data.bones}
    worst = 0.0
    for b in rig['bones']:
        bb = back[b['name']]
        assert (bb.parent.name if bb.parent else None) == b['parent'], (b['name'], bb.parent and bb.parent.name, b['parent'])
        R_ue = M @ np.array(bb.matrix_local.to_3x3()) @ M
        worst = max(worst, float(np.abs(R_ue - BR.quat_matrix(b['q'])).max()))
    mats = sorted({s.material.name for m in meshes for s in m.material_slots if s.material})
    cb = [m for m in meshes if m.name == HC.CORE_NAME]
    assert cb, 'the core did not come back'
    cme = cb[0].data
    report['read_back'] = dict(bones=len(back), meshes=len(meshes), frame_diff=worst, materials=mats,
                               core_vertices=len(cme.vertices), core_faces=len(cme.polygons),
                               core_groups=sorted(g.name for g in cb[0].vertex_groups))
    print('read back: %d bones, %d meshes, largest frame difference %.2e, materials %s, core %d verts %d faces' % (
        len(back), len(meshes), worst, mats, len(cme.vertices), len(cme.polygons)))
    if report_path:
        json.dump(report, open(report_path, 'w'), indent=1)


if __name__ == '__main__':
    main(*sys.argv[1:7])
