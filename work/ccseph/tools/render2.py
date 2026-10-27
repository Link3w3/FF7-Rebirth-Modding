import sys, numpy as np
sys.path.insert(0, '/work/ccseph/tools')
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from shade import render
from render_check import fk, skin
from rerig import q2m, axis_angle
m = np.load(sys.argv[1]); out = sys.argv[2]
names = list(m['bone_names'])
Rl = {n: q2m(q) for n, q in zip(names, m['bone_lq'])}
lr = {}
lr['L_UpperArm_a'] = Rl['L_UpperArm_a'] @ axis_angle([0, 0, 1], np.radians(-50))
lr['L_Forearm_a'] = Rl['L_Forearm_a'] @ axis_angle([0, 0, 1], np.radians(-70))
lr['L_Hand_a'] = Rl['L_Hand_a'] @ axis_angle([1, 0, 0], np.radians(60))
lr['R_UpperLeg_a'] = Rl['R_UpperLeg_a'] @ axis_angle([0, 0, 1], np.radians(-40))
lr['R_Foreleg_a'] = Rl['R_Foreleg_a'] @ axis_angle([0, 0, 1], np.radians(80))
lr['C_Spine_b'] = Rl['C_Spine_b'] @ axis_angle([1, 0, 0], np.radians(20))
lr['C_Head_a'] = Rl['C_Head_a'] @ axis_angle([1, 0, 0], np.radians(25))
R, P = fk(m, lr)
pp = skin(m, R, P)
fig, axs = plt.subplots(2, 4, figsize=(18, 14))
render(axs[0, 0], m['pos'], m['tri'], m['tmat'], 0, 'rest front', joints=m['bone_ct'])
render(axs[0, 1], m['pos'], m['tri'], m['tmat'], 90, 'rest side (left)')
render(axs[0, 2], m['pos'], m['tri'], m['tmat'], 0, 'left hand', zoom=((-80, -45), (100, 135)), joints=m['bone_ct'])
render(axs[0, 3], m['pos'], m['tri'], m['tmat'], 0, 'head', zoom=((-15, 15), (165, 200)), joints=m['bone_ct'])
render(axs[1, 0], pp, m['tri'], m['tmat'], 0, 'test pose front')
render(axs[1, 1], pp, m['tri'], m['tmat'], 90, 'test pose side')
render(axs[1, 2], pp, m['tri'], m['tmat'], 45, 'test pose 3/4')
render(axs[1, 3], pp, m['tri'], m['tmat'], -45, 'test pose 3/4 other')
plt.tight_layout(); plt.savefig(out, dpi=90)
print('saved')
