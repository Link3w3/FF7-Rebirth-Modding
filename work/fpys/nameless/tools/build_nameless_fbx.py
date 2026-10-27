"""WE1021_49_v2.fbx: the Nameless rebuilt in centimetres with its root at scale 1 (the editor's import had made its root
Trans x100 over bones in metres; the game holds a weapon's root at its reference pose, so a scaled root is trouble),
and its string given a chain to swing on: phy_string_01 (at the guard, as it was) -> phy_string_02 (the string's middle)
-> phy_string_03 (its end), the string's vertices weighted along it (the knot at the guard stays on C_Body_a; from 6% of
the string on it goes over to the chain, phy_string_01 then phy_string_02 past the middle). Every other vertex, bone,
frame, UV, colour and normal as it was. Material named after its slot (mat_we049_001_body).
    build_nameless_fbx.py <nameless.npz> <out .fbx> <out chain.json>"""
import json, os, sys
import numpy as np
import bpy
from mathutils import Matrix

M = np.diag([1.0, -1.0, 1.0])
SLOT = 'mat_we049_001_body'


def smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def chain_points(pos, w_vert, w_bone, names, p1):
    si = names.index('phy_string_01')
    idx = np.array(sorted({int(v) for v, b in zip(w_vert, w_bone) if b == si}))
    P = pos[idx]
    c = P.mean(0)
    ax = np.linalg.svd(P - c)[2][0]
    proj = (P - p1) @ ax
    if np.corrcoef(proj, np.linalg.norm(P - p1, axis=1))[0, 1] < 0:
        ax, proj = -ax, -proj
    L = proj.max()
    mid = P[np.abs(proj - 0.5 * L) < 0.08 * L].mean(0)
    tip = P[proj > 0.92 * L].mean(0)
    tip = tip + (tip - mid) / np.linalg.norm(tip - mid) * 0.5     # just past the last vertices
    return idx, mid, tip


def arc_u(p, pts):
    """the point's place along the polyline pts (0 at pts[0], 1 at the end), from its nearest point on it"""
    lens = [np.linalg.norm(pts[k + 1] - pts[k]) for k in range(len(pts) - 1)]
    total, best = sum(lens), (1e18, 0.0)
    acc = 0.0
    for k in range(len(pts) - 1):
        a, b = pts[k], pts[k + 1]
        t = float(np.clip(np.dot(p - a, b - a) / max(np.dot(b - a, b - a), 1e-9), 0, 1))
        d = np.linalg.norm(a + t * (b - a) - p)
        if d < best[0]:
            best = (d, (acc + t * lens[k]) / total)
        acc += lens[k]
    return best[1]


def main(npz, out, chain_out):
    A = np.load(npz)
    bones = json.loads(str(A['bones_json']))
    pos = A['pos'] * 100.0
    names = [str(n) for n in A['w_names']]
    by = {b['name']: b for b in bones}
    p1 = np.array(by['phy_string_01']['t']) * 100.0
    idx, mid, tip = chain_points(pos, A['w_vert'], A['w_bone'], names, p1)
    # the rig: Trans (identity, scale 1) + the bones as they were (cm) + the two new string bones
    rig = [dict(name='Trans', parent=None, R=np.eye(3), t=np.zeros(3))]
    for b in bones:
        rig.append(dict(name=b['name'], parent=b['parent'], R=np.array(b['R']), t=np.array(b['t']) * 100.0))
    R1 = np.array(by['phy_string_01']['R'])
    rig.append(dict(name='phy_string_02', parent='phy_string_01', R=R1, t=mid))
    rig.append(dict(name='phy_string_03', parent='phy_string_02', R=R1, t=tip))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.scale_length = 0.01
    arm = bpy.data.armatures.new('WE1021_49')
    arm_ob = bpy.data.objects.new('Armature', arm)
    scene.collection.objects.link(arm_ob)
    bpy.context.view_layer.objects.active = arm_ob
    bpy.ops.object.mode_set(mode='EDIT')
    made = {}
    for b in rig:
        eb = arm.edit_bones.new(b['name'])
        eb.head, eb.tail = (0, 0, 0), (0, 3.0, 0)
        R = M @ b['R'] @ M
        W = Matrix.Identity(4)
        for i in range(3):
            for j in range(3):
                W[i][j] = R[i, j]
        tb = M @ b['t']
        W.translation = (tb[0], tb[1], tb[2])
        eb.matrix = W
        made[b['name']] = eb
    for b in rig:
        if b['parent']:
            made[b['name']].parent = made[b['parent']]
            made[b['name']].use_connect = False
    bpy.ops.object.mode_set(mode='OBJECT')
    # the mesh
    sizes, fv = A['face_sizes'], A['face_verts']
    faces, k = [], 0
    for n in sizes:
        faces.append(fv[k:k + n].tolist())
        k += n
    me = bpy.data.meshes.new('WE1021_49_geo')
    me.from_pydata((pos @ M.T).tolist(), [], faces)
    for i, nm in enumerate(A['uv_names']):
        uvl = me.uv_layers.new(name='UVMap' if i == 0 else 'UV%d' % i)
        uvl.uv.foreach_set('vector', A['uvs'][i].ravel())
    if len(A['colors']):
        ca = me.color_attributes.new('Col', 'FLOAT_COLOR', 'CORNER')
        ca.data.foreach_set('color', A['colors'].ravel())
    mat = bpy.data.materials.new(SLOT)
    me.materials.append(mat)
    me.validate(verbose=False)
    assert len(me.polygons) == len(faces)
    me.shade_smooth()
    me.normals_split_custom_set((A['normals'] @ M.T).tolist())
    ob = bpy.data.objects.new('WE1021_49_geo', me)
    scene.collection.objects.link(ob)
    ob.parent = arm_ob
    groups = {}
    string = set(int(i) for i in idx)
    si = names.index('phy_string_01')
    for v, b, w in zip(A['w_vert'].tolist(), A['w_bone'].tolist(), A['w_weight'].tolist()):
        if v in string:
            continue
        g = groups.get(names[b]) or groups.setdefault(names[b], ob.vertex_groups.new(name=names[b]))
        g.add([v], w, 'ADD')
    for nm in ('C_Body_a', 'phy_string_01', 'phy_string_02'):
        groups.setdefault(nm, ob.vertex_groups.get(nm) or ob.vertex_groups.new(name=nm))
    pts = [p1, mid, tip]
    us = []
    for v in sorted(string):
        u = arc_u(pos[v], pts)
        us.append(u)
        on = smooth(0.06, 0.20, u)
        w2 = smooth(0.35, 0.65, u) * on
        w1 = on - w2
        for nm, w in (('C_Body_a', 1.0 - on), ('phy_string_01', w1), ('phy_string_02', w2)):
            if w > 1e-4:
                groups[nm].add([v], float(w), 'REPLACE')
    mod = ob.modifiers.new('Armature', 'ARMATURE')
    mod.object = arm_ob
    out = os.path.abspath(out)
    bpy.ops.export_scene.fbx(filepath=out, use_selection=False, object_types={'ARMATURE', 'MESH'},
                             apply_unit_scale=True, apply_scale_options='FBX_SCALE_NONE', global_scale=1.0,
                             axis_forward='-Z', axis_up='Y', use_mesh_modifiers=False, mesh_smooth_type='FACE',
                             use_tspace=False, add_leaf_bones=False, primary_bone_axis='Y', secondary_bone_axis='X',
                             armature_nodetype='NULL', bake_anim=False, path_mode='STRIP', embed_textures=False,
                             use_custom_props=False)
    us = np.array(us)
    chain = dict(p1=p1.tolist(), mid=mid.tolist(), tip=tip.tolist(), string_vertices=len(string),
                 length=float(np.linalg.norm(mid - p1) + np.linalg.norm(tip - mid)),
                 u_hist=np.histogram(us, bins=5, range=(0, 1))[0].tolist(),
                 bones=[dict(name=b['name'], parent=b['parent'], t=[round(float(x), 4) for x in b['t']]) for b in rig])
    json.dump(chain, open(chain_out, 'w'), indent=1)
    print('wrote', out, os.path.getsize(out), '; string: %d vertices, chain %s -> %s -> %s (%.1f cm), u spread %s' % (
        len(string), p1.round(2), mid.round(2), tip.round(2), chain['length'], chain['u_hist']))
    # read back
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=out)
    a = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
    m = [o for o in bpy.data.objects if o.type == 'MESH'][0]
    print('read back: bones', [(b.name, b.parent.name if b.parent else None) for b in a.data.bones], 'verts', len(m.data.vertices),
          'groups', [g.name for g in m.vertex_groups], 'material', [s.material.name for s in m.material_slots if s.material])


if __name__ == '__main__':
    main(*sys.argv[1:4])
