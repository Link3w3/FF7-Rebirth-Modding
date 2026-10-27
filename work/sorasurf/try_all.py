import json, sys
from try_compile import run
tests = [
 ('p_ex011_mat01inst', 'RMI_Surface_Standard_Wide_Detail', True),
 ('p_ex011_mat01inst', 'RMI_Surface_Fabric_Coverage_Wide_Detail', False),
 ('p_ex011_mat02inst', 'RMI_Surface_Standard_Wide_Detail', True),
 ('p_ex011_mat02inst', 'RMI_Surface_Fabric_Coverage_Wide_Detail', False),
 ('p_ex011_hair_Inst', 'RMI_Surface_Hair_Wide', False),
 ('p_ex011_hair_Inst', 'RMI_Surface_Fabric_Coverage_Wide_Detail', False),
 ('p_ex011_EYE_Inst', 'RMI_Surface_Standard_Wide_Detail', True),
 ('p_ex011_Eyelens_Inst', 'RMI_Surface_Standard_Wide_Detail', True),
 ('p_ex011_M_mat0_Inst', 'RMI_Surface_Standard_Wide_Detail', True),
 ('p_ex011_E_mat3_Inst', 'RMI_Surface_Fabric_Coverage_Wide_Detail', False),
]
for e, c, ig in tests:
    r = run(e, c, ig)
    if 'error' in r:
        print(e, c, 'ERROR', r['error'][:300]); continue
    probs = {res: v['problems'] for res, v in r['variants'].items() if v['problems']}
    print(e, c, 'ignore_mask' if ig else 'masked', 'variants', len(r['variants']), 'problems', probs or 'none', 'slots', len(set(r['plan'].values())), r['secs'], 's')
