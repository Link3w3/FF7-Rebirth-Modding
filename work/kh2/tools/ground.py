import sys, os, glob, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pose import Anim
import numpy as np

def stats(path):
    a = Anim(path)
    name = os.path.basename(path).replace('_001_remap_remap.fbx', '').replace('_remap_remap.fbx', '')
    root = a.pos('Trans')
    pts = [a.pos(b) for b in ('R_Foot_a', 'L_Foot_a', 'R_Toe_a', 'L_Toe_a')]
    # contact height: min over feet/toes, relative to root Z, minus the ref heights (heel 12.1, toe 4.5)
    heel = np.minimum(pts[0][:, 2], pts[1][:, 2]) - root[:, 2] - 12.1
    toe = np.minimum(pts[2][:, 2], pts[3][:, 2]) - root[:, 2] - 4.5
    lift = np.minimum(heel, toe)
    return dict(name=name, frames=a.n, lift_min=round(float(lift.min()), 1), lift_med=round(float(np.median(lift)), 1), lift_max=round(float(lift.max()), 1))

if __name__ == '__main__':
    import multiprocessing as mp
    files = sorted(glob.glob('/data/uploads/Kh2Rebirth/Remap/*.fbx'))
    with mp.Pool(8) as pool:
        out = pool.map(stats, files)
    for o in out:
        print('%-20s %4d  lift min %6.1f  median %6.1f  max %6.1f' % (o['name'], o['frames'], o['lift_min'], o['lift_med'], o['lift_max']))
    json.dump(out, open('/work/kh2/ground.json', 'w'), indent=1)
