"""PC0010_13 with the transformed Sephiroth's wing: build_rig_fbx.py's scene (ch049_001 on rig.json's bones, his face
weights shared out) on make_rig_wing.py's rig (the wing's bones on his back), plus the wing itself (extract_wing.py's
faces of PC0010_10, moved and scaled with the rig's "wing" map: positions, corner normals, its three UV layers, colours
and weights to the wing bones and C_Spine_d), material PC0010_10_Wing (the forms' wing part). Exported with
build_rig_fbx.py's settings, then read back.
    build_rig_fbx_wing.py <rig_wing.json> <model dir> <wing .npz> <out .fbx>"""
import json, os, sys
sys.path[:0] = ['/work/unityrip/scripts', '/work/ys/rig']
import numpy as np
import bpy
from mathutils import Matrix
import build_blend as BB
import build_rig_fbx as BR

M = BR.M
UV_NAMES = ['UVMap', 'UV1', 'UV2']     # the wing's DiffuseUV, LightMapUV, DiffuseUV.001 in the order his meshes have them


def add_wing(rig, coll, arm_ob, npz_path, made):
    A = np.load(npz_path)
    w = rig['wing']
    turn, r_s, r_y, s = np.array(w['turn']), np.array(w['seph_root']), np.array(w['root']), float(w['scale'])
    pos = r_y + (A['pos'] - r_s) * s @ turn.T                      # Unreal component space
    co = pos @ M.T                                                  # Blender (this scene: Unreal flipped in Y, cm)
    nrm = (A['normals'] @ turn.T) @ M.T
    sizes, fv = A['face_sizes'], A['face_verts']
    faces, k = [], 0
    for n in sizes:
        faces.append(fv[k:k + n].tolist())
        k += n
    me = bpy.data.meshes.new('PC0010_10_Wing_geo')
    me.from_pydata(co.tolist(), [], faces)
    uvs = A['uvs']
    for i in range(uvs.shape[0]):
        uvl = me.uv_layers.new(name=UV_NAMES[i])
        uvl.uv.foreach_set('vector', uvs[i].ravel())
    if len(A['colors']):
        ca = me.color_attributes.new('Col', 'FLOAT_COLOR', 'CORNER')
        ca.data.foreach_set('color', A['colors'].ravel())
    mat = bpy.data.materials.get('PC0010_10_Wing') or bpy.data.materials.new('PC0010_10_Wing')
    me.materials.append(mat)
    me.validate(verbose=False)
    assert len(me.polygons) == len(faces), ('faces dropped', len(me.polygons), len(faces))
    me.shade_smooth()
    me.normals_split_custom_set(nrm.tolist())
    ob = bpy.data.objects.new('PC0010_10_Wing_geo', me)
    coll.objects.link(ob)
    ob.parent = arm_ob
    bones = [str(b) for b in A['bones']]
    missing = [b for b in bones if b not in made]
    assert not missing, ('the wing is weighted to bones the rig lacks', missing)
    groups = {i: ob.vertex_groups.new(name=b) for i, b in enumerate(bones)}
    for v, bi, wt in zip(A['w_vert'].tolist(), A['w_bone'].tolist(), A['w_weight'].tolist()):
        groups[bi].add([v], wt, 'ADD')
    mod = ob.modifiers.new('Armature', 'ARMATURE')
    mod.object = arm_ob
    print('wing: %d vertices, %d faces, bounds %s .. %s (Unreal cm)' % (len(co), len(faces), pos.min(0).round(1), pos.max(0).round(1)))
    return ob


def main(rig_path, model_dir, npz_path, out):
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
    add_wing(rig, coll, arm_ob, npz_path, made)
    out = os.path.abspath(out)
    bpy.ops.export_scene.fbx(filepath=out, use_selection=False, object_types={'ARMATURE', 'MESH'},
                             apply_unit_scale=True, apply_scale_options='FBX_SCALE_NONE', global_scale=1.0,
                             axis_forward='-Z', axis_up='Y', use_mesh_modifiers=False, mesh_smooth_type='FACE',
                             use_tspace=False, add_leaf_bones=False, primary_bone_axis='Y', secondary_bone_axis='X',
                             armature_nodetype='NULL', bake_anim=False, path_mode='STRIP', embed_textures=False,
                             use_custom_props=False)
    print('wrote', out, os.path.getsize(out), 'bones', len(made), 'vertex groups renamed', renamed)
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
    print('read back: %d bones, %d meshes, largest frame difference %.2e, materials %s' % (len(back), len(meshes), worst, mats))


if __name__ == '__main__':
    main(*sys.argv[1:5])
