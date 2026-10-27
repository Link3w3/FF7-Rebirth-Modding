import json, sys, numpy as np
import facerender as fr, build_poses as B
F = fr.Face()
IDLE = B.IDLE
MOUTH = [b for b in B.FACE if b not in B.EYES + B.LIDS + B.BROWS + ['G_eye', 'G_mouth', 'R_hole', 'L_hole']]
items = json.loads(sys.argv[1])
ims = []
for name, f in items:
    p = B.mix(IDLE, B.frame(name, f), MOUTH)
    ims.append(F.render(p, scale=16, box=(-6.5, 6.5, 134.5, 147.0), label='%s f%d' % (name[2:], f)))
print(fr.sheet(ims, 8, sys.argv[2]))
