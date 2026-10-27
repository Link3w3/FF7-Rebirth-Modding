"""His hair and coat bones renamed the Rebirth way (C_/L_/R_ + part + _a.._e_Phy), so Create a Character System's Rebirth
KawaiiPhysics preset finds his chains (hair, front hair, long hair, coat) by name; the parts are his own (HairLongCC,
HairFrontCCA, CoatCCF, ...), never one of Rebirth Sephiroth's, so no Rebirth animation keys them. Also writes the preset's
rig JSON (component space) and mesh npz (pos, sparse weights, bone and material names).
    rename_phys.py <in npz> <out npz> <rig json> <mesh npz>"""
import json, sys
import numpy as np
RENAME = {
    'BackHair': 'C_HairLongCC_a_Phy', 'CenterHair1': 'C_HairLongCC_b_Phy', 'CenterHair2': 'C_HairLongCC_c_Phy',
    'CenterHair3': 'C_HairLongCC_d_Phy', 'CenterHair4': 'C_HairLongCC_e_Phy',
    'LB_hair': 'L_HairLongCCTip_a_Phy', 'RB_hair': 'R_HairLongCCTip_a_Phy',
    'LeftHair1': 'L_HairSideCC_a_Phy', 'RightHair1': 'R_HairSideCC_a_Phy',
    'LeftFrontHair': 'L_HairFrontCCA_a_Phy', 'LeftFrontHair1': 'L_HairFrontCCA_b_Phy',
    'LeftFrontHairB': 'L_HairFrontCCB_a_Phy', 'LeftFrontHairB1': 'L_HairFrontCCB_b_Phy',
    'RightFrontHair': 'R_HairFrontCCA_a_Phy', 'RightFrontHair1': 'R_HairFrontCCA_b_Phy',
    'Right_hair': 'R_HairTuftCC_a_Phy',
}
for side, s in (('Left', 'L'), ('Right', 'R')):
    for kind, k in (('FrontCoat', 'CCF'), ('Coat', 'CCS')):
        for i, lvl in enumerate('abc', 1):
            RENAME['%s%s%d' % (side, kind, i)] = '%s_Coat%s_%s_Phy' % (s, k, lvl)
for i, lvl in enumerate('abc', 1):
    RENAME['BackCoat%d' % i] = 'C_CoatCCB_%s_Phy' % lvl


def main(src, dst, rig_path, mesh_path):
    m = dict(np.load(src))
    names = [str(n) for n in m['bone_names']]
    missing = [k for k in RENAME if k not in names]
    assert not missing, missing
    new = [RENAME.get(n, n) for n in names]
    assert len(set(new)) == len(new)
    m['bone_names'] = np.array(new)
    np.savez(dst, **m)
    par = m['bone_parents']; cq, ct, lq, lt = m['bone_cq'], m['bone_ct'], m['bone_lq'], m['bone_lt']
    bones = [dict(name=n, parent=(new[par[i]] if par[i] >= 0 else None), q=cq[i].tolist(), t=ct[i].tolist(),
                  local_q=lq[i].tolist(), local_t=lt[i].tolist(), scale=[1.0, 1.0, 1.0]) for i, n in enumerate(new)]
    json.dump(dict(source=src, bones=bones), open(rig_path, 'w'), indent=0)
    wb, ww = m['wbone'], m['wweight']
    v, k = np.nonzero(ww > 0)
    vslot = np.zeros(len(m['pos']), np.int32); vslot[m['tri'].ravel()] = np.repeat(m['tmat'], 3)
    np.savez(mesh_path, pos=m['pos'], w_bone=wb[v, k], w_vert=v, w_weight=ww[v, k], bones=np.array(new), vmat=vslot,
             mats=m['slots'])
    print('renamed %d bones; rig %s (%d bones); mesh %s' % (len(RENAME), rig_path, len(bones), mesh_path))


if __name__ == '__main__':
    main(*sys.argv[1:5])
