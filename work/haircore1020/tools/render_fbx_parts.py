"""Render chosen mesh objects of an FBX (workbench, three ortho views).
    render_fbx_parts.py <fbx> <out.png> <obj,obj,...> <z centre m> <ortho scale m> [colour overrides obj=r:g:b,...]"""
import sys, math
import bpy
from PIL import Image
fbx, out, show, zc, zs = sys.argv[1], sys.argv[2], sys.argv[3].split(','), float(sys.argv[4]), float(sys.argv[5])
over = {}
if len(sys.argv) > 6 and sys.argv[6]:
    for kv in sys.argv[6].split(','):
        k, v = kv.split('=')
        over[k] = tuple(float(c) for c in v.split(':')) + (1.0,)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=fbx)
scene = bpy.context.scene
for ob in list(bpy.data.objects):
    if ob.type == 'MESH' and ob.name not in show:
        bpy.data.objects.remove(ob)
    elif ob.type == 'MESH':
        mat = bpy.data.materials.new('v_' + ob.name)
        mat.diffuse_color = over.get(ob.name, (0.8, 0.8, 0.8, 1))
        ob.data.materials.clear()
        ob.data.materials.append(mat)
scene.render.engine = 'BLENDER_WORKBENCH'
scene.display.shading.light = 'STUDIO'
scene.display.shading.color_type = 'MATERIAL'
scene.render.resolution_x, scene.render.resolution_y = 600, 900
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
cam.data.type = 'ORTHO'
cam.data.ortho_scale = zs
scene.collection.objects.link(cam)
scene.camera = cam
views = [((3, 0, zc), (math.pi / 2, 0, math.pi / 2)), ((0, -3, zc), (math.pi / 2, 0, 0)), ((-3, 0, zc), (math.pi / 2, 0, -math.pi / 2))]
tiles = []
for k, (loc, rot) in enumerate(views):
    cam.location = loc
    cam.rotation_euler = rot
    p = out + '.%d.png' % k
    scene.render.filepath = p
    bpy.ops.render.render(write_still=True)
    tiles.append(Image.open(p).convert('RGB'))
sheet = Image.new('RGB', (sum(t.width for t in tiles), tiles[0].height))
x = 0
for t in tiles:
    sheet.paste(t, (x, 0)); x += t.width
sheet.save(out)
import os
for k in range(len(tiles)):
    os.remove(out + '.%d.png' % k)
print('wrote', out)
