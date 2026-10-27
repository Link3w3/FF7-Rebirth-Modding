import sys, json, numpy as np
sys.path.insert(0, '/work/ccseph/tools')
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from shade import render
from render_check import skin
from rerig import q2m
m = np.load(sys.argv[1]); out = sys.argv[3]
S = json.load(open(sys.argv[2]))
rig = json.load(open('/work/kawaii_preset/rigs/PC0010_00.json'))
RB = {b['name']: b for b in rig['bones']}
names = [str(n) for n in m['bone_names']]; par = list(m['bone_parents'])
Rl = [q2m(q) for q in m['bone_lq']]; tl = [np.array(t) for t in m['bone_lt']]
hip_ratio = tl[names.index('C_Hip_a')][2] / RB['C_Hip_a']['local_t'][2]
def pose(bones):
    R = [None] * len(names); P = [None] * len(names)
    for i, n in enumerate(names):
        L = Rl[i]; t = tl[i]
        b = bones.get(n) if n != 'Trans' else None   # the game locks the root (its motion goes to the capsule)
        if b is not None:
            L = q2m(b[:4])
            if n == 'C_Hip_a':
                t = np.array(b[4:7]) * hip_ratio
            elif n == 'Trans':
                t = np.zeros(3)
        if par[i] < 0: R[i] = L; P[i] = t
        else: R[i] = R[par[i]] @ L; P[i] = P[par[i]] + R[par[i]] @ t
    return np.array(R), np.array(P)
picks = [('B_Idle01_1', 0), ('B_NAttack01_0', 2), ('B_NAttack01_0', 4), ('B_NAttack03_0', 2), ('B_SAttack01_0', 2), ('B_SAttack01_0', 4), ('N_Run01_1', 1), ('N_Run01_1', 3)]
fig, axs = plt.subplots(2, 4, figsize=(18, 14))
for ax, (a, k) in zip(axs.ravel(), picks):
    key = [x for x in S if x.endswith(a)][0]
    fr = S[key]['frames'][k]
    R, P = pose(fr['bones'])
    pp = skin(m, R, P)
    render(ax, pp, m['tri'], m['tmat'], 30, '%s t=%.2f' % (a, fr['time']))
plt.tight_layout(); plt.savefig(out, dpi=85); print('saved')
