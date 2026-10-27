"""Cycles preview of his head and hair from an FBX: head, body, eyes with their textures; hair cards alpha-tested at the
game's clip value (0.3333, RMI_Surface_Hair_Wide's OpacityMaskClipValue) over his hair texture's alpha; the hair core
(if the FBX has one) opaque with the hair colour at its UVs. Renders each view with and without the core, side by side.
    preview_core.py <fbx> <textures dir> <out .png> [views: front,back,side,back34,top] [samples]"""
import math, os, sys
import bpy
from mathutils import Vector
from PIL import Image

fbx, tex_dir, out = sys.argv[1], sys.argv[2], sys.argv[3]
views = (sys.argv[4] if len(sys.argv) > 4 else 'front,side,back,back34').split(',')
samples = int(sys.argv[5]) if len(sys.argv) > 5 else 24
CORE = 'PC0010_13_HairCore_geo'
CLIP = 0.3333

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=fbx)
scene = bpy.context.scene


def image(name):
    p = os.path.join(tex_dir, name + '.png')
    img = bpy.data.images.load(p, check_existing=True)
    return img


def material(name, tex, alpha_clip=None, colour_only=False, tint=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    outn = nt.nodes.new('ShaderNodeOutputMaterial')
    bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.inputs['Roughness'].default_value = 0.55
    t = nt.nodes.new('ShaderNodeTexImage')
    t.image = image(tex)
    t.interpolation = 'Linear'
    col = t.outputs['Color']
    if tint is not None:
        mix = nt.nodes.new('ShaderNodeMix')
        mix.data_type = 'RGBA'
        mix.blend_type = 'MULTIPLY'
        mix.inputs['Factor'].default_value = 1.0
        nt.links.new(col, mix.inputs[6])
        mix.inputs[7].default_value = tint
        col = mix.outputs[2]
    nt.links.new(col, bsdf.inputs['Base Color'])
    if alpha_clip is None:
        nt.links.new(bsdf.outputs['BSDF'], outn.inputs['Surface'])
        return m
    gt = nt.nodes.new('ShaderNodeMath')
    gt.operation = 'GREATER_THAN'
    gt.inputs[1].default_value = alpha_clip
    nt.links.new(t.outputs['Alpha'], gt.inputs[0])
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    mx = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(gt.outputs[0], mx.inputs['Fac'])
    nt.links.new(tr.outputs['BSDF'], mx.inputs[1])
    nt.links.new(bsdf.outputs['BSDF'], mx.inputs[2])
    nt.links.new(mx.outputs['Shader'], outn.inputs['Surface'])
    return m


mats = {
    'head_geo': material('head', 'tex_ch049_001_head_AAAX'),
    'body_geo': material('body', 'tex_ch049_001_body_AAAT', alpha_clip=0.5),
    'hair_geo': material('hair', 'tex_ch049_001_hair_AAAT', alpha_clip=CLIP),
    'hair_tp_geo': material('hair_tp', 'tex_ch049_001_hair_AAAT', alpha_clip=CLIP),
    'eye_geo': material('eye', 'tex_ch049_001_eye_AAAX'),
    CORE: material('core', 'tex_ch049_001_hair_AAAT'),
}
keep = set(mats)
for ob in list(bpy.data.objects):
    if ob.type != 'MESH':
        continue
    if ob.name not in keep:
        bpy.data.objects.remove(ob)
        continue
    ob.data.materials.clear()
    ob.data.materials.append(mats[ob.name])
    for p in ob.data.polygons:
        p.material_index = 0

head = bpy.data.objects['head_geo']
pts = [head.matrix_world @ Vector(c) for c in head.bound_box]
lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
c = (lo + hi) / 2
c.z = hi.z - 0.11
world = bpy.data.worlds.new('w')
world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.32, 0.4, 0.5, 1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.9
scene.world = world
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN'))
sun.data.energy = 3.5
scene.collection.objects.link(sun)
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
cam.data.type = 'ORTHO'
cam.data.ortho_scale = 0.42
scene.collection.objects.link(cam)
scene.camera = cam
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = samples
scene.cycles.use_denoising = False
scene.cycles.transparent_max_bounces = 64
scene.cycles.max_bounces = 4
scene.render.resolution_x, scene.render.resolution_y = 420, 480
scene.view_settings.view_transform = 'Standard'
ANG = {'front': 0.0, 'side': 90.0, 'back': 180.0, 'back34': 140.0, 'front34': 35.0, 'otherside': -90.0}
core = bpy.data.objects.get(CORE)
tiles = []
for v in views:
    row = []
    a = math.radians(ANG[v])
    d = Vector((math.cos(a), -math.sin(a), 0.12))
    d.normalize()
    cam.location = c + d * 3.0
    look = (c - cam.location)
    cam.rotation_euler = look.to_track_quat('-Z', 'Y').to_euler()
    sun.rotation_euler = (math.radians(50), 0, math.radians(-30) + (math.pi / 2 - a))
    for with_core in (False, True):
        if core is not None:
            core.hide_render = not with_core
        elif with_core:
            continue
        p = out + '.%s.%d.png' % (v, int(with_core))
        scene.render.filepath = p
        bpy.ops.render.render(write_still=True)
        row.append(Image.open(p).convert('RGB'))
        os.remove(p)
    tiles.append(row)
W = max(sum(t.width for t in r) for r in tiles)
H = sum(r[0].height for r in tiles)
sheet = Image.new('RGB', (W, H), (40, 40, 40))
y = 0
for r in tiles:
    x = 0
    for t in r:
        sheet.paste(t, (x, y))
        x += t.width
    y += r[0].height
sheet.save(out)
print('wrote', out, sheet.size)
