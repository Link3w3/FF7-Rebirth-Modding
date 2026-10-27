"""Bahamut Fused Sephiroth: the fitted hair (hair_fit.py) into the re-rigged model (bfs_rerig.py npz): PC0010_10's hair
bones added under his head (Rebirth's own frames: his head is Rebirth's, at Rebirth's place), the hair's vertices,
triangles, UVs, normals and weights appended, its two material slots after his own.
    hair_merge.py <rerig.npz> <pc10.npz> <hair_fit.npz> <out.npz>"""
import re
import sys
import numpy as np


def quat_of(R):
    """rotation matrix -> (x, y, z, w), the rerig npz's convention (R = qmat(x, y, z, w))"""
    t = np.trace(R)
    if t > 0:
        s = np.sqrt(t + 1.0) * 2
        w = 0.25 * s; x = (R[2, 1] - R[1, 2]) / s; y = (R[0, 2] - R[2, 0]) / s; z = (R[1, 0] - R[0, 1]) / s
    elif R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
        s = np.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2]) * 2
        w = (R[2, 1] - R[1, 2]) / s; x = 0.25 * s; y = (R[0, 1] + R[1, 0]) / s; z = (R[0, 2] + R[2, 0]) / s
    elif R[1, 1] > R[2, 2]:
        s = np.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2]) * 2
        w = (R[0, 2] - R[2, 0]) / s; x = (R[0, 1] + R[1, 0]) / s; y = 0.25 * s; z = (R[1, 2] + R[2, 1]) / s
    else:
        s = np.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1]) * 2
        w = (R[1, 0] - R[0, 1]) / s; x = (R[0, 2] + R[2, 0]) / s; y = (R[1, 2] + R[2, 1]) / s; z = 0.25 * s
    q = np.array([x, y, z, w])
    return q / np.linalg.norm(q)


def chain_of(n):
    m = re.match(r'(.*?)_([a-z])_Phy$', n)
    return m.group(1) if m else n


def main(rerig_path, pc10_path, hair_path, out_path):
    r = dict(np.load(rerig_path, allow_pickle=True))
    d = np.load(pc10_path, allow_pickle=True)
    h = np.load(hair_path, allow_pickle=True)
    names = [str(n) for n in r['bone_names']]
    pn = [str(n) for n in d['names']]
    ppar = d['parents']
    # every bone of the chains the hair uses (their unweighted tips too: the physics' last segments), and their ancestors
    used = [str(n) for n in h['bones']]
    chains = {chain_of(n) for n in used}
    want = set(n for n in pn if chain_of(n) in chains and ('Hair' in n))
    want |= {n for n in pn if n.endswith('_Spo') and chain_of(n.replace('_Spo', '_a_Phy')) in chains}
    want |= set(used)
    for n in list(want):                       # ancestors up to a bone he has
        p = ppar[pn.index(n)]
        while p >= 0 and pn[p] not in names:
            want.add(pn[p]); p = ppar[p]
    add = [n for n in pn if n in want and n not in names]          # pc10's own order: parents first
    # check the head is where pc10 has it (the hair's frames hang from it)
    hi, pi = names.index('C_Head_a'), pn.index('C_Head_a')
    assert np.abs(r['bone_ct'][hi] - d['glob'][pi][:3, 3]).max() < 1e-3, 'his head is not at Rebirth\'s place'
    new_names = names + add
    idx = {n: i for i, n in enumerate(new_names)}
    par, lq, lt, cq, ct = list(r['bone_parents']), list(r['bone_lq']), list(r['bone_lt']), list(r['bone_cq']), list(r['bone_ct'])
    for n in add:
        j = pn.index(n)
        p = pn[ppar[j]]
        par.append(idx[p])
        L = d['local'][j]
        G = d['glob'][j]
        lq.append(quat_of(L[:3, :3])); lt.append(L[:3, 3].copy())
        cq.append(quat_of(G[:3, :3])); ct.append(G[:3, 3].copy())
    out = dict(r)
    out['bone_names'] = np.array(new_names)
    out['bone_parents'] = np.array(par, dtype=np.int64)
    out['bone_lq'] = np.array(lq); out['bone_lt'] = np.array(lt)
    out['bone_cq'] = np.array(cq); out['bone_ct'] = np.array(ct)
    # the mesh
    nv0 = len(r['pos'])
    hb = [str(n) for n in h['bones']]
    wb = np.zeros((len(h['pos']), 8), np.int64); ww = np.zeros((len(h['pos']), 8))
    wb[:, :4] = np.vectorize(lambda b: idx[hb[int(b)]])(h['wbone']); ww[:, :4] = h['wweight']
    slots = [str(s) for s in r['slots']] + [str(s) for s in h['slot_names']]
    out['pos'] = np.concatenate([r['pos'], h['pos']])
    out['nz'] = np.concatenate([r['nz'], h['normals']])
    out['uv'] = np.concatenate([r['uv'], h['uv']])
    out['tri'] = np.concatenate([r['tri'], h['tri'] + nv0])
    out['tmat'] = np.concatenate([r['tmat'], h['slot'] + len(r['slots'])])
    out['slots'] = np.array(slots)
    out['wbone'] = np.concatenate([r['wbone'], wb]); out['wweight'] = np.concatenate([r['wweight'], ww])
    out['hair_slot_materials'] = h['slot_materials']
    np.savez_compressed(out_path, **out)
    print('bones %d (+%d hair), verts %d (+%d), tris %d (+%d), slots %s' % (len(new_names), len(add), len(out['pos']), len(h['pos']),
          len(out['tri']), len(h['tri']), slots[-2:]))


if __name__ == '__main__':
    main(*sys.argv[1:5])
