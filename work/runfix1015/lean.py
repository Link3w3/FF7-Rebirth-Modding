import sys
sys.path[:0] = ['/work/runfix1015', '/work/acl', '/work/iostore']
import numpy as np, pose
from iostore import Toc
from render_cmp import load
I = pose.IDX
def lean_stats(label, data):
    c, GT, tr = load(data)
    hip = GT[:, I['C_Hip_a']]; neck = GT[:, I['C_Neck_a']]; head = GT[:, I['C_Head_a']]; chest = GT[:, I['C_Spine_d']]
    lf = GT[:, I['L_Foot_a']]; rf = GT[:, I['R_Foot_a']]
    def ang(a, b):  # angle of a->b from vertical in the X-Z plane, + = toward +X (forward)
        v = b - a
        return np.degrees(np.arctan2(v[:, 0], v[:, 2]))
    sp = ang(hip, neck); up = ang(chest, head)
    feet = (lf[:, 0] + rf[:, 0]) / 2 - hip[:, 0]
    print('%-26s spine(hip->neck) lean %+5.0f (min %+4.0f max %+4.0f) | chest->head %+5.0f | feet-hip X %+5.0f | hip z %4.0f' % (
        label, sp.mean(), sp.min(), sp.max(), up.mean(), feet.mean(), hip[:, 2].mean()))
L = '/work/fly1014/loco/'
t = Toc('/work/kh2data1015/moves/SephirothForms_P.utoc')
byname = {p.split('Content/')[-1]: i for i, p in t.files.items()}
B = 'RebirthSkelCompat/Built/SephirothForms/'
for n in ['B_Run01_1', 'B_Walk01_1', 'B_Idle01_1', 'B_Run01_0_L0', 'B_Run01_2l', 'B_WalkB01_1']:
    try:
        lean_stats('GAME ' + n, open(L + n + '.uasset', 'rb').read() + open(L + n + '.uexp', 'rb').read())
    except Exception as ex:
        print('GAME', n, ex)
    for s in ('Battle04', 'Battle03', 'Battle02'):
        k = B + s + '/' + n + '.uasset'
        if k in byname:
            lean_stats(s + ' ' + n, t.read(byname[k]))
