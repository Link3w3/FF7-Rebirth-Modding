"""model.json/model.npz (extract_unity.py) -> a .blend: the armature (each bone's rest matrix is the Unity bone's, so a PSK
import of the same skeleton lines up), the eight skinned meshes (custom normals, UVs, vertex colours, weights) and the
seven materials with their textures packed.

Material mapping (Principled BSDF), from the Unity material's own textures and values:
  _BaseMap RGB -> Base Color, its alpha -> Alpha (clipped at _Cutoff when _ALPHATEST_ON; blended for the transparent ones)
  _BumpMap -> Normal Map (rebuilt from DXT5nm, OpenGL/Y+)
  _MetallicGlossMap (MROX) R x _Metallic -> Metallic, G -> Roughness (smoothness scaled by _GlossMapScale);
     B (occlusion / toon shadow mask) and _RampMap (toon ramp) are in the material but not connected
  _Cull 2 -> backface culling on; _SpecularIntensity -> Specular IOR Level (x0.5)
Every Unity value is kept on the material as the custom property "unity".

    build_blend.py <model dir> <out .blend> [preview .png]
"""
import json, math, os, sys
import numpy as np
import bpy
from mathutils import Matrix, Vector

SPACE = 220


def node(nodes, kind, x, y, label=None):
    n = nodes.new(kind)
    n.location = (x, y)
    if label:
        n.label = label
    return n


def math_node(nodes, op, x, y, a=None, b=None):
    n = node(nodes, 'ShaderNodeMath', x, y)
    n.operation = op
    if a is not None:
        n.inputs[0].default_value = a
    if b is not None:
        n.inputs[1].default_value = b
    return n


def image(model_dir, info, name, cache):
    if name in cache:
        return cache[name]
    t = info['textures'][name]
    img = bpy.data.images.load(os.path.join(model_dir, t['file']))
    img.name = name
    img.colorspace_settings.name = 'sRGB' if t['kind'] == 'color' else 'Non-Color'
    cache[name] = img
    return img


def build_material(name, u, model_dir, info, cache):
    mat = bpy.data.materials.new(name)
    try:
        mat.use_nodes = True
    except Exception:
        pass
    nt = mat.node_tree
    nodes, links = nt.nodes, nt.links
    for n in list(nodes):
        nodes.remove(n)
    out = node(nodes, 'ShaderNodeOutputMaterial', 3 * SPACE, 0)
    bsdf = node(nodes, 'ShaderNodeBsdfPrincipled', 1.5 * SPACE, 0)
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    f, tex, kw = u['floats'], u['textures'], set(u['keywords'])
    queue = u['render_queue']
    blended = f.get('_DstBlend', 0) == 10 or (u['tags'].get('RenderType') == 'Transparent' and '_ALPHATEST_ON' not in kw)
    clip = '_ALPHATEST_ON' in kw
    if '_ALPHATEST_ON' in kw and (queue >= 2500 or u['tags'].get('RenderType') == 'Transparent'):
        blended = True                                    # (hair_tp: blended above its cutoff)
    y = 300
    if '_BaseMap' in tex:
        t = node(nodes, 'ShaderNodeTexImage', -3 * SPACE, y, '_BaseMap')
        t.image = image(model_dir, info, tex['_BaseMap']['texture'], cache)
        links.new(t.outputs['Color'], bsdf.inputs['Base Color'])
        if info['textures'][tex['_BaseMap']['texture']]['alpha'] and (clip or blended):
            a = t.outputs['Alpha']
            if clip:
                g = math_node(nodes, 'GREATER_THAN', -1.5 * SPACE, y - 150, b=f.get('_Cutoff', 0.5))
                g.label = 'Cutoff %.2f' % f.get('_Cutoff', 0.5)
                links.new(a, g.inputs[0])
                a = g.outputs[0]
                if blended:
                    mm = math_node(nodes, 'MULTIPLY', -0.75 * SPACE, y - 150)
                    links.new(t.outputs['Alpha'], mm.inputs[0])
                    links.new(a, mm.inputs[1])
                    a = mm.outputs[0]
            links.new(a, bsdf.inputs['Alpha'])
        y -= 300
    if '_MetallicGlossMap' in tex:
        t = node(nodes, 'ShaderNodeTexImage', -3 * SPACE, y, '_MetallicGlossMap (MROX)')
        t.image = image(model_dir, info, tex['_MetallicGlossMap']['texture'], cache)
        sep = node(nodes, 'ShaderNodeSeparateColor', -2 * SPACE, y)
        links.new(t.outputs['Color'], sep.inputs['Color'])
        m = f.get('_Metallic', 1.0)
        if abs(m - 1) < 1e-6:
            links.new(sep.outputs[0], bsdf.inputs['Metallic'])
        else:
            mm = math_node(nodes, 'MULTIPLY', -1 * SPACE, y + 60, b=m)
            mm.label = '_Metallic %.2f' % m
            links.new(sep.outputs[0], mm.inputs[0])
            links.new(mm.outputs[0], bsdf.inputs['Metallic'])
        gs = f.get('_GlossMapScale', 1.0)
        if abs(gs - 1) < 1e-6:
            links.new(sep.outputs[1], bsdf.inputs['Roughness'])
        else:
            s1 = math_node(nodes, 'SUBTRACT', -1 * SPACE, y - 60, a=1.0)
            links.new(sep.outputs[1], s1.inputs[1])
            s2 = math_node(nodes, 'MULTIPLY', -0.5 * SPACE, y - 60, b=gs)
            s2.label = '_GlossMapScale %.2f' % gs
            links.new(s1.outputs[0], s2.inputs[0])
            s3 = math_node(nodes, 'SUBTRACT', 0, y - 60, a=1.0)
            links.new(s2.outputs[0], s3.inputs[1])
            links.new(s3.outputs[0], bsdf.inputs['Roughness'])
        y -= 300
    if '_BumpMap' in tex:
        t = node(nodes, 'ShaderNodeTexImage', -3 * SPACE, y, '_BumpMap')
        t.image = image(model_dir, info, tex['_BumpMap']['texture'], cache)
        nm = node(nodes, 'ShaderNodeNormalMap', -1 * SPACE, y)
        nm.uv_map = 'UVMap'
        links.new(t.outputs['Color'], nm.inputs['Color'])
        links.new(nm.outputs['Normal'], bsdf.inputs['Normal'])
        y -= 300
    if '_RampMap' in tex:
        t = node(nodes, 'ShaderNodeTexImage', -3 * SPACE, y, '_RampMap (toon ramp, not connected)')
        t.image = image(model_dir, info, tex['_RampMap']['texture'], cache)
        t.interpolation = 'Closest'
        t.extension = 'EXTEND'
        y -= 300
    spec = f.get('_SpecularIntensity')
    if spec is not None:
        bsdf.inputs['Specular IOR Level'].default_value = 0.5 * spec
        if spec == 0 and '_MetallicGlossMap' not in tex:
            bsdf.inputs['Roughness'].default_value = 1.0
    try:
        mat.surface_render_method = 'BLENDED' if blended else 'DITHERED'
    except Exception:
        mat.blend_method = 'BLEND' if blended else ('CLIP' if clip else 'OPAQUE')
    mat.use_backface_culling = f.get('_Cull', 2.0) == 2.0
    mat['unity'] = dict(keywords=' '.join(sorted(kw)), render_queue=queue, tags=u['tags'],
                        textures={k: v['texture'] for k, v in tex.items()},
                        external_textures=' '.join(sorted(u['external_textures'])),
                        floats=u['floats'], colors=u['colors'])
    return mat


def main(model_dir, out_blend, preview=None):
    scene, coll, arm_ob = build_scene(model_dir)
    for img in bpy.data.images:
        img.pack()
    for img in bpy.data.images:
        img.filepath = '//textures/' + img.name + '.png'    # (packed; the path only names it)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(out_blend), compress=True)
    print('saved', out_blend, os.path.getsize(out_blend))
    if preview:
        render_preview(scene, coll, preview)


def build_scene(model_dir, double=(), unit=1.0, turn=0.0):
    """The armature, meshes and materials in a fresh scene. Meshes named in double (Unity mesh names) get a second,
    reversed copy of every face with opposite normals (for targets whose materials cannot be two-sided). unit: Blender
    units per metre (100 builds it in centimetres, with the scene's unit scale 0.01 so it still measures in metres).
    turn: degrees about Z applied to everything below the root bone (the root itself keeps its rest matrix), e.g. 90
    makes the character face +X instead of -Y."""
    info = json.load(open(os.path.join(model_dir, 'model.json')))
    A = np.load(os.path.join(model_dir, 'model.npz'))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    if unit != 1.0:
        scene.unit_settings.scale_length = 1.0 / unit
    coll = bpy.data.collections.new('ch049_001')
    scene.collection.children.link(coll)

    # armature
    arm = bpy.data.armatures.new('skin_ch049_001')
    arm_ob = bpy.data.objects.new('skin_ch049_001', arm)
    coll.objects.link(arm_ob)
    arm_ob.show_in_front = True
    arm.display_type = 'STICK'
    bpy.context.view_layer.objects.active = arm_ob
    arm_ob.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bones = info['bones']
    W = [Matrix(b['world']) for b in bones]
    for w in W:
        w.translation = w.translation * unit
    T = Matrix.Rotation(math.radians(turn), 4, 'Z')
    if turn:
        assert bones[0]['parent'] < 0 and all(b['parent'] >= 0 for b in bones[1:])
        root = W[0]
        assert (root.to_3x3() - Matrix.Identity(3)).median_scale < 1e-6 or all(abs(root[i][j] - (1.0 if i == j else 0.0)) < 1e-5 for i in range(3) for j in range(3)), 'the root bone is not at rest'
        W = [W[0]] + [T @ w for w in W[1:]]
    T3 = np.array(T.to_3x3())
    kids = {}
    for i, b in enumerate(bones):
        kids.setdefault(b['parent'], []).append(i)
    ebs = []
    for i, b in enumerate(bones):
        eb = arm.edit_bones.new(b['name'])
        d = [(W[c].translation - W[i].translation).length for c in kids.get(i, [])]
        L = min(max(max(d) if d else 0.02 * unit, 0.01 * unit), 0.12 * unit)
        eb.head = (0, 0, 0)
        eb.tail = (0, L, 0)
        eb.matrix = W[i]
        ebs.append(eb)
    for i, b in enumerate(bones):
        if b['parent'] >= 0:
            ebs[i].parent = ebs[b['parent']]
            ebs[i].use_connect = False
    bpy.ops.object.mode_set(mode='OBJECT')

    cache = {}
    mats = {name: build_material(name, u, model_dir, info, cache) for name, u in info['materials'].items()}

    # meshes
    names = [b['name'] for b in bones]
    for m in info['meshes']:
        k = m['name']
        co, no, uv0, tri, tmat = A[k + '/co'] * unit, A[k + '/no'], A[k + '/uv0'], A[k + '/tri'], A[k + '/tri_mat']
        co, no = co @ T3.T, no @ T3.T
        uv1 = A[k + '/uv1'] if k + '/uv1' in A else None
        col = A[k + '/col'] if k + '/col' in A else None
        vv, bb, ww = A[k + '/w_vert'], A[k + '/w_bone'], A[k + '/w_val']
        if k in double:
            n = len(co)
            co, no, uv0 = np.concatenate([co, co]), np.concatenate([no, -no]), np.concatenate([uv0, uv0])
            uv1 = None if uv1 is None else np.concatenate([uv1, uv1])
            col = None if col is None else np.concatenate([col, col])
            tri, tmat = np.concatenate([tri, tri[:, ::-1] + n]), np.concatenate([tmat, tmat])
            vv, bb, ww = np.concatenate([vv, vv + n]), np.concatenate([bb, bb]), np.concatenate([ww, ww])
        me = bpy.data.meshes.new(m['object'])
        me.from_pydata(co.tolist(), [], tri.tolist())
        uvl = me.uv_layers.new(name='UVMap')
        uvl.uv.foreach_set('vector', uv0[tri.ravel()].ravel())
        if uv1 is not None:
            uvl2 = me.uv_layers.new(name='UV1')
            uvl2.uv.foreach_set('vector', uv1[tri.ravel()].ravel())
        if col is not None:
            ca = me.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')
            ca.data.foreach_set('color', col.ravel())
        for mn in m['materials']:
            me.materials.append(mats[mn])
        me.polygons.foreach_set('material_index', tmat)
        bad = me.validate(verbose=False)
        assert len(me.polygons) == len(tri), (k, 'faces dropped by validate', len(me.polygons), len(tri))
        me.shade_smooth()
        me.normals_split_custom_set_from_vertices(no.tolist())
        ob = bpy.data.objects.new(m['object'], me)
        coll.objects.link(ob)
        ob.parent = arm_ob
        groups = {}
        for bi in sorted(set(bb.tolist())):
            groups[bi] = ob.vertex_groups.new(name=names[bi])
        for v, bi, w in zip(vv.tolist(), bb.tolist(), ww.tolist()):
            groups[bi].add([v], w, 'ADD')
        mod = ob.modifiers.new('Armature', 'ARMATURE')
        mod.object = arm_ob
    return scene, coll, arm_ob


def render_preview(scene, coll, path):
    """Cycles (CPU) front and back views, side by side, for checking the textures and alpha."""
    from PIL import Image
    pts = [o.matrix_world @ Vector(c) for o in coll.objects if o.type == 'MESH' for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    c = (lo + hi) / 2
    h = hi.z - lo.z
    world = bpy.data.worlds.new('w')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.55, 0.57, 0.6, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.8
    scene.world = world
    sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN'))
    sun.data.energy = 3.0
    sun.rotation_euler = (math.radians(50), 0, math.radians(-30))
    scene.collection.objects.link(sun)
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = h * 1.08
    scene.collection.objects.link(cam)
    scene.camera = cam
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 48
    scene.cycles.use_denoising = False
    scene.render.resolution_x, scene.render.resolution_y = 520, 900
    scene.view_settings.view_transform = 'Standard'
    tiles = []
    for k, (yy, rz) in enumerate([(-1, 0.0), (1, math.pi)]):
        cam.location = (c.x, c.y + yy * 6.0, c.z)
        cam.rotation_euler = (math.pi / 2, 0, rz)
        sun.rotation_euler = (math.radians(55), 0, math.radians(-30) + rz)
        p = path + '.%d.png' % k
        scene.render.filepath = p
        bpy.ops.render.render(write_still=True)
        tiles.append(Image.open(p).convert('RGB'))
    w = sum(t.width for t in tiles)
    sheet = Image.new('RGB', (w, tiles[0].height))
    x = 0
    for t in tiles:
        sheet.paste(t, (x, 0)); x += t.width
    sheet.save(path)
    for k in range(len(tiles)):
        os.remove(path + '.%d.png' % k)
    print('preview', path)


if __name__ == '__main__':
    main(*sys.argv[1:])
