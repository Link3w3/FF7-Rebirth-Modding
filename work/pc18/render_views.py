"""Workbench renders of PC0010_18 (the user's FBX in Blender), colored by material: front / side / back / 3-4, whole and
a close view of the head region. blender -b PC0010_18_in.blend -P render_views.py -- <out dir> [zmin zmax]"""
import bpy, sys, math, mathutils
argv = sys.argv[sys.argv.index('--') + 1:]
out = argv[0]
zr = (float(argv[1]), float(argv[2])) if len(argv) > 2 else None
scene = bpy.context.scene
scene.render.engine = 'BLENDER_WORKBENCH'
scene.display.shading.light = 'STUDIO'
scene.display.shading.color_type = 'MATERIAL'
scene.render.resolution_x = 900
scene.render.resolution_y = 1100
scene.render.film_transparent = False
import random
random.seed(3)
for m in bpy.data.materials:
    h = random.random()
    c = mathutils.Color((0, 0, 0)); c.hsv = (h, 0.55, 0.85)
    m.diffuse_color = (c.r, c.g, c.b, 1)
cam_data = bpy.data.cameras.new('cam'); cam_data.type = 'ORTHO'
cam = bpy.data.objects.new('cam', cam_data); scene.collection.objects.link(cam); scene.camera = cam
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
import numpy as np
pts = []
for o in meshes:
    M = np.array(o.matrix_world)
    co = np.array([v.co for v in o.data.vertices])
    pts.append((M[:3, :3] @ co.T).T + M[:3, 3])
P = np.concatenate(pts)
if zr:
    sel = (P[:, 2] >= zr[0]) & (P[:, 2] <= zr[1])
    P = P[sel]
lo, hi = P.min(0), P.max(0)
ctr = (lo + hi) / 2
size = max(hi[2] - lo[2], hi[1] - lo[1], hi[0] - lo[0]) * 1.08
cam_data.ortho_scale = size
views = {'front': (1, 0, 0), 'side': (0, -1, 0), 'back': (-1, 0, 0), 'three': (0.7, -0.7, 0.15)}
for name, d in views.items():
    d = mathutils.Vector(d).normalized()
    cam.location = mathutils.Vector(ctr) + d * 20
    cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = '%s/%s.png' % (out, name)
    bpy.ops.render.render(write_still=True)
print('rendered', out)
