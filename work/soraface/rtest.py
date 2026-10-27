import json, time, numpy as np
import facerender as fr
F = fr.Face()
FACEB = set(n for n in fr.NAMES if n not in ('kubi', 'atama', 'facial'))
def tr(name):
    return json.load(open('all/tracks/%s.json' % name))
def fpose(name, f):
    p = fr.pose_from_track(tr(name), f)
    return {b: v for b, v in p.items() if b in FACEB}
t0 = time.time()
ims = [F.render({}, label='ref pose')]
print('ref', time.time() - t0)
for n, f in [('F_9998EM', 0), ('F_9999EM', 0), ('F_0001EM', 0), ('F_0000EM', 0), ('F_0002M', 5), ('F_0200EM', 0), ('F_0204EM', 30)]:
    ims.append(F.render(fpose(n, f), label='%s f%d' % (n[2:], f)))
print('all', time.time() - t0)
fr.sheet(ims, 4, '/tmp/scratch/sheet_test.png')
