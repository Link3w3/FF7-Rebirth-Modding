"""Sora's KH3 materials for the game: every material instance on his mesh (PC0000_00_S) compiled onto a game carrier
and written as game packages at the editor's own MI paths, so the cooked mesh finds them where it points:

  /Game/RebirthCustom/Sora/<MI>_<carrier>   copy of the carrier (RMI_Surface_*) with the MI's pixel shaders inline
                                             (base pass; for cut-out materials also the depth-only and shadow passes)
  <the MI's editor path>                     a game MI (from a Sephiroth MI of that carrier family) re-parented to it,
                                             the MI's textures on the carrier's texture parameters (the slot plan)
  the textures                               cooked by the End editor, converted to zen (zentex), at their editor paths

    python3 build_sora_mats.py [out folder]     -> out/<package>.uasset, out/report.json (textures to cook)
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CUSTMAT = '/work/custmat'
sys.path[:0] = [CUSTMAT, os.path.join(CUSTMAT, 'gamesh'), os.path.join(CUSTMAT, 'taken'), '/work/fx1018/editor/Python']

import carrier_build as cb          # noqa: E402
import material                      # noqa: E402
import build_taken as bt             # noqa: E402
from try_compile import BUNDLES      # noqa: E402
from two_sided import set_two_sided  # noqa: E402

EXPORTS = os.path.join(CUSTMAT, 'export', 'RebirthMatExport', 'KH3')
ROOT = '/Game/RebirthCustom/Sora/'
P011 = '/Game/KH3/Character/pc/p_ex011/mdl/mat0/'
P001 = '/Game/KH3/Character/pc/p_ex001/mdl/mat0/'
W010 = '/Game/KH3/Character/wep/w_so010/mdl/mat0/'
WHITE = '/Game/Renderer/Texture/FFFFFFFF_BC4.FFFFFFFF_BC4'

SKIN = 'RMI_Surface_Skin_Wide_Detail'
STANDARD = 'RMI_Surface_Standard_Wide_Detail'
COVERAGE = 'RMI_Surface_Fabric_Coverage_Wide_Detail'
SHORT = {SKIN: 'Skin', STANDARD: 'Standard', COVERAGE: 'Coverage'}

# the Sephiroth MI each carrier family's game MIs are made from (its parent is replaced by the carrier copy)
TEMPLATES = {
    SKIN: ('PC0010_00_Skin', 'RMI_Surface_Skin_Wide_Detail'),
    STANDARD: ('PC0010_00_BodyA', 'RMI_Surface_Standard_Wide_Detail'),
    COVERAGE: ('PC0010_00_Hair', 'RMI_Surface_Hair_Wide'),
}
# fixed texture values per carrier: the coverage carrier's own cut-out off (white), the material cuts out by itself
FIXED = {COVERAGE: {'Coverage': WHITE, 'DetailCoverage': WHITE}}
PREFER = {
    SKIN: ('Color', 'Normal', 'Roughness', 'Occlusion', 'Detail', 'WideOcclusion', 'DetailNormal'),
    STANDARD: ('Color', 'Metallic', 'Roughness', 'Normal', 'Detail', 'WideOcclusion', 'DetailNormal'),
    COVERAGE: ('Color', 'Normal', 'Roughness', 'Occlusion', 'Detail', 'Diffusion', 'WideOcclusion', 'DetailNormal'),
}

# (the MI's path, export folder, carrier, drawn solid: the KH3 mask only fades him out near the camera)
JOBS = [
    (P011 + 'p_ex011_F_mat0_Inst', 'p_ex011_F_mat0_Inst', SKIN, True),
    (P011 + 'p_ex011_mat04Inst', 'p_ex011_mat04Inst', SKIN, True),
    (P011 + 'p_ex011_mat01inst', 'p_ex011_mat01inst', STANDARD, True),
    (P011 + 'p_ex011_mat02inst', 'p_ex011_mat02inst', STANDARD, True),
    (P011 + 'p_ex011_mat03inst', 'p_ex011_mat03inst', STANDARD, True),
    (P011 + 'p_ex011_mat05inst', 'p_ex011_mat05inst', STANDARD, True),
    (P011 + 'p_ex011_EYE_Inst', 'p_ex011_EYE_Inst', STANDARD, True),
    (P001 + 'p_ex001_M_mat0_Inst', 'p_ex001_M_mat0_Inst', STANDARD, True),
    (P011 + 'p_ex011_Eyelens_Inst', 'p_ex011_Eyelens_Inst', COVERAGE, False),
    (P011 + 'p_ex011_hair_Inst', 'p_ex011_hair_Inst', COVERAGE, False),
    (P011 + 'p_ex011_hair_Inst_Inst', 'p_ex011_hair_Inst_Inst', COVERAGE, False),
    (P011 + 'p_ex011_E_mat3_Inst', 'p_ex011_E_mat3_Inst_masked', COVERAGE, False),
    (P011 + 'p_ex011_E_mat2_Inst', 'p_ex011_E_mat2_Inst_masked', COVERAGE, False),
    # the Kingdom Key (/Game/Character/Weapon/WE0000_00_Kingdom_Key/Model/WE0000_00): no cut-outs of its own
    (W010 + 'w_so010_mat0_Inst', 'w_so010_mat0_Inst', STANDARD, True),
]


def build_job(mi_path, export, carrier, solid, carriers, report, work):
    exported = material.Exported(os.path.join(EXPORTS, export))
    cs = carriers[carrier]
    fixed = FIXED.get(carrier, {})
    built, plan = cb.build_blobs(exported, cs, os.path.join(work, export), prefer=PREFER[carrier],
                                 keep=('Coverage',) + tuple(fixed), ignore_mask=solid)
    problems = {res: r['problems'] for res, r in built.items() if r['problems']}
    if problems:
        raise ValueError('%s on %s: %s' % (export, carrier, problems))
    named = dict(cs.named)
    by_index = {t['index']: t for t in exported.textures if t['type'] == 'Texture2D'}
    slot_textures = {named[j]: by_index[k]['texture'] for k, j in sorted(plan.items())}
    slot_textures.update(fixed)
    name = mi_path.rsplit('/', 1)[-1]
    carrier_name = ROOT + '%s_%s' % (name, SHORT[carrier])
    blobs = {res: r['blob'] for res, r in built.items()}
    carrier_data = bt.carrier_package(carrier_name, blobs, report, carrier, BUNDLES[carrier])
    # the game's character carriers are one-sided; a two-sided KH3 material (hair cards, eyelashes) keeps both faces
    two_sided = bool(exported.info.get('two_sided'))
    if two_sided:
        carrier_data = set_two_sided(carrier_data, carrier_name)
    packages = {carrier_name: carrier_data}
    source, old_parent = TEMPLATES[carrier]
    packages[mi_path] = bt.taken_mi(mi_path, carrier_name, slot_textures, report, source, old_parent)
    report.setdefault('jobs', {})[mi_path] = dict(
        export=export, carrier=carrier, carrier_copy=carrier_name, solid=solid, template=source, two_sided=two_sided,
        passes={res: r['kind'] for res, r in built.items()},
        plan={'Texture2D_%d' % k: dict(parameter=named[j], texture=by_index[k]['texture']) for k, j in sorted(plan.items())},
        textures=slot_textures,
        shaders={res: dict(kind=r['kind'], size=len(r['blob']), sha1=hashlib.sha1(r['blob']).hexdigest()) for res, r in built.items()})
    own = sorted(set(v for n, v in slot_textures.items() if n not in fixed))
    return packages, own


def main(out_dir, only=None):
    os.makedirs(out_dir, exist_ok=True)
    carriers = {c: cb.CarrierShaders(c, BUNDLES[c]) for c in (SKIN, STANDARD, COVERAGE)}
    report = {}
    packages = {}
    textures = set()
    missing = []
    for mi_path, export, carrier, solid in JOBS:
        if only and mi_path.rsplit('/', 1)[-1] not in only:
            continue
        if not os.path.isfile(os.path.join(EXPORTS, export, 'material.json')):
            missing.append(export)
            continue
        p, t = build_job(mi_path, export, carrier, solid, carriers, report, '/tmp/scratch/gamesh_work/sora_mats')
        packages.update(p)
        textures.update(t)
    report['textures'] = sorted(textures)
    report['missing_exports'] = missing
    for name, data in packages.items():
        open(os.path.join(out_dir, name.replace('/', '__').strip('_') + '.uasset'), 'wb').write(data)
    json.dump(report, open(os.path.join(out_dir, 'report.json'), 'w'), indent=1)
    return packages, report


if __name__ == '__main__':
    packages, report = main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'out_mats'))
    print(len(packages), 'packages', sum(len(d) for d in packages.values()), 'bytes')
    print('missing exports', report['missing_exports'])
    print(len(report['textures']), 'textures')
    for t in report['textures']:
        print('  ', t)
    for k, v in report['jobs'].items():
        print(k.rsplit('/', 1)[-1], v['carrier'], 'passes', sorted(set(v['passes'].values())), {n: t.rsplit('.', 1)[-1] for n, t in v['textures'].items()})
