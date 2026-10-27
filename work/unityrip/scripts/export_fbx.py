"""The ch049_001 scene as an FBX for Unreal's importer: the hair, hair tips and eyelashes doubled with reversed back
faces (the materials are one-sided; the Unity materials were two-sided), the armature object named Armature (the
importer then does not add it as an extra root bone), built in centimetres (scene unit scale 0.01) so no object or
bone carries a scale: Unreal's skeleton then has an unscaled root and centimetre bone offsets.

    export_fbx.py <model dir> <out .fbx>
"""
import os, sys
sys.path.insert(0, '/work/unityrip/scripts')
import bpy
import build_blend as BB

DOUBLE = {'hair_geo', 'hair_tp_geo', 'eyelash_geo'}
TURN = 90.0   # the character faces +X in Unreal like Rebirth's characters (the root bone stays at rest)


def main(model_dir, out):
    scene, coll, arm_ob = BB.build_scene(model_dir, double=DOUBLE, unit=100.0, turn=TURN)
    arm_ob.name = 'Armature'
    out = os.path.abspath(out)
    bpy.ops.export_scene.fbx(filepath=out, use_selection=False, object_types={'ARMATURE', 'MESH'},
                             apply_unit_scale=True, apply_scale_options='FBX_SCALE_NONE', global_scale=1.0,
                             axis_forward='-Z', axis_up='Y', use_mesh_modifiers=False, mesh_smooth_type='FACE',
                             use_tspace=False, add_leaf_bones=False, primary_bone_axis='Y', secondary_bone_axis='X',
                             armature_nodetype='NULL', bake_anim=False, path_mode='STRIP', embed_textures=False,
                             use_custom_props=False)
    # read it back
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=out)
    arms = [o for o in bpy.data.objects if o.type == 'ARMATURE']
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    print('fbx', out, os.path.getsize(out), 'armatures', [(a.name, len(a.data.bones)) for a in arms],
          'meshes', sorted((m.name, len(m.data.vertices), len(m.data.polygons), [s.name for s in m.data.materials]) for m in meshes))
    pts = [m.matrix_world @ v.co for m in meshes for v in m.data.vertices]
    print('height %.3f (in scene units)' % (max(p.z for p in pts) - min(p.z for p in pts)), 'unit scale', bpy.context.scene.unit_settings.scale_length,
          'armature scale', [tuple(round(x, 4) for x in a.matrix_world.to_scale()) for a in arms],
          'left_leg head (armature space)', tuple(round(x, 3) for x in arms[0].data.bones['left_leg'].head_local),
          'left_toe', tuple(round(x, 2) for x in arms[0].data.bones['left_toe'].head_local), 'left_foot', tuple(round(x, 2) for x in arms[0].data.bones['left_foot'].head_local))


if __name__ == '__main__':
    main(*sys.argv[1:])
