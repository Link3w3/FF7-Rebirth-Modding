import bpy, sys
import numpy as np
from collections import defaultdict
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=sys.argv[-1])
for ob in bpy.data.objects:
    if ob.type != 'MESH' or ob.name not in ('hair_geo', 'hair_tp_geo', 'head_geo'):
        continue
    me = ob.data
    names = {g.index: g.name for g in ob.vertex_groups}
    tot = defaultdict(float)
    cnt = defaultdict(int)
    for v in me.vertices:
        for g in v.groups:
            tot[names[g.group]] += g.weight
            cnt[names[g.group]] += 1
    print(ob.name, len(me.vertices), 'groups', len(names))
    for n, w in sorted(tot.items(), key=lambda kv: -kv[1])[:60]:
        print('   %-28s weight sum %8.1f verts %5d' % (n, w, cnt[n]))
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
hb = [b.name for b in arm.data.bones if 'Hair' in b.name or 'hair' in b.name]
print('hair bones in rig:', len(hb), hb[:80])
