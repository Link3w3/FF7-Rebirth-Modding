"""Render Sephiroth's (PC0010_00 LOD0) HairCore section against his hair and head: three views, workbench engine."""
import sys, math
import numpy as np
import bpy
from mathutils import Vector

A = np.load(sys.argv[1])
out = sys.argv[2]
pos, idx, secs, names = A['pos'], A['idx'], A['secs'], [str(n) for n in A['names']]
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
cols = {'HairCore': (0.9, 0.15, 0.1, 1), 'Hair': (0.75, 0.78, 0.85, 1), 'Head': (0.95, 0.8, 0.7, 1), 'Skin': (0.95, 0.8, 0.7, 1), 'BodyA': (0.15, 0.15, 0.17, 1), 'BodyB': (0.25, 0.25, 0.3, 1)}
show = sys.argv[3].split(',')
for name in show:
    base, nt, vb, nv = [int(v) for v in secs[names.index(name)]]
    t = idx[base:base + 3 * nt].reshape(-1, 3) - vb
    P = pos[vb:vb + nv]
    co = P * np.array([1, -1, 1]) / 100.0          # Unreal cm -> Blender m (flip Y)
    me = bpy.data.meshes.new(name)
    me.from_pydata(co.tolist(), [], t[:, ::-1].tolist())
    me.validate()
    ob = bpy.data.objects.new(name, me)
    scene.collection.objects.link(ob)
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = cols.get(name, (0.5, 0.5, 0.5, 1))
    if name == 'Hair':
        mat.diffuse_color = (0.75, 0.78, 0.85, 0.35)
    me.materials.append(mat)
scene.render.engine = 'BLENDER_WORKBENCH'
scene.display.shading.light = 'STUDIO'
scene.display.shading.color_type = 'MATERIAL'
scene.display.shading.show_xray = False
scene.render.film_transparent = False
scene.render.resolution_x, scene.render.resolution_y = 600, 900
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
cam.data.type = 'ORTHO'
scene.collection.objects.link(cam)
scene.camera = cam
zc, zs = float(sys.argv[4]), float(sys.argv[5])
cam.data.ortho_scale = zs
views = [('front', (3, 0, zc), (math.pi / 2, 0, math.pi / 2)), ('side', (0, -3, zc), (math.pi / 2, 0, 0)), ('back', (-3, 0, zc), (math.pi / 2, 0, -math.pi / 2))]
from PIL import Image
tiles = []
for k, (nm, loc, rot) in enumerate(views):
    cam.location = loc
    cam.rotation_euler = rot
    p = out + '.%d.png' % k
    scene.render.filepath = p
    bpy.ops.render.render(write_still=True)
    tiles.append(Image.open(p).convert('RGB'))
W = sum(t.width for t in tiles)
sheet = Image.new('RGB', (W, tiles[0].height))
x = 0
for t in tiles:
    sheet.paste(t, (x, 0)); x += t.width
sheet.save(out)
print('wrote', out)
