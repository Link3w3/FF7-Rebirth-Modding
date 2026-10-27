"""The long front strands (L/R_HairA) as part of the body: they lie under the mask, down his neck and on his chest
armour, so they follow his head above the jaw and his chest below the collar (a blend between), not the physics (a
strand hung from the head but lying on the chest would swing through the armour whenever his head turns).
    hair_pin_strands.py <hair_fit.npz> <out.npz>"""
import sys
import numpy as np
h = dict(np.load(sys.argv[1], allow_pickle=True))
bones = [str(b) for b in h['bones']]
for n in ('C_HairBase_a', 'C_Spine_d'):
    if n not in bones:
        bones.append(n)
hb, sd = bones.index('C_HairBase_a'), bones.index('C_Spine_d')
sel = np.isin(h['chain'], ['L_HairA', 'R_HairA'])
z = h['pos'][:, 2]
t = np.clip((175.0 - z) / (175.0 - 163.0), 0, 1)
t = t * t * (3 - 2 * t)
wb = h['wbone'].copy(); ww = h['wweight'].copy()
wb[sel] = 0; ww[sel] = 0
wb[sel, 0] = hb; ww[sel, 0] = 1 - t[sel]
wb[sel, 1] = sd; ww[sel, 1] = t[sel]
h['wbone'] = wb; h['wweight'] = ww; h['bones'] = np.array(bones)
np.savez_compressed(sys.argv[2], **h)
print('pinned %d strand verts (chest share mean %.2f)' % (sel.sum(), t[sel].mean()))
