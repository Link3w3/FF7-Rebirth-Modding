"""Reproduce two of Sora's jobs (sorasurf/out_mats) with rebirth_fx.gamemat, byte for byte."""
import hashlib, os, struct, sys, time
sys.path.insert(0, '/work/fxlink/src/Content/Python')
from rebirth_fx.gamemat import env
env.set_dxc('/home/user/microsoft/dxc-build/bin/dxc', dict(os.environ, LD_LIBRARY_PATH='/home/user/microsoft/dxc-build/lib'))
env.set_engine_shaders('/work/custmat/gamesh/engine/Shaders')
env.set_work('/tmp/scratch/gamemat_test')
from rebirth_fx.gamemat import shaderlib, carrier_build as cb, packages
from rebirth_fx.gamemat.material import Exported
sys.path.insert(0, '/work/sorasurf')
from try_compile import BUNDLES

C = '/work/custmat'
lib = shaderlib.Library(open('/data/uploads/FF7R2UProj/Saved/ModExtract/shlib/End_header.bin', 'rb').read(), prefixed=True)
def raw_bundle(path):
    raw = open(path, 'rb').read(); p = 0; out = []
    while p < len(raw):
        index, size, usize, freq = struct.unpack_from('<IIIB', raw, p); p += 13
        hsh = raw[p:p + 20]; p += 20
        out.append(dict(index=index, hash=hsh, code=raw[p:p + size], usize=usize, freq=freq)); p += size
    return out
WHITE = '/Game/Renderer/Texture/FFFFFFFF_BC4.FFFFFFFF_BC4'
JOBS = [('/Game/KH3/Character/pc/p_ex011/mdl/mat0/p_ex011_mat01inst', 'p_ex011_mat01inst', 'RMI_Surface_Standard_Wide_Detail', True, 'Standard', 'PC0010_00_BodyA',
         ('Color', 'Metallic', 'Roughness', 'Normal', 'Detail', 'WideOcclusion', 'DetailNormal'), {}),
        ('/Game/KH3/Character/pc/p_ex011/mdl/mat0/p_ex011_hair_Inst', 'p_ex011_hair_Inst', 'RMI_Surface_Fabric_Coverage_Wide_Detail', False, 'Coverage', 'PC0010_00_Hair',
         ('Color', 'Normal', 'Roughness', 'Occlusion', 'Detail', 'Diffusion', 'WideOcclusion', 'DetailNormal'), {'Coverage': WHITE, 'DetailCoverage': WHITE})]
for mi_path, export, carrier, solid, short, template, prefer, fixed in JOBS:
    carrier_data = open('/work/anime/pkgs/Renderer__MaterialInstance__Surface__%s.uasset' % carrier, 'rb').read()
    cs = cb.CarrierShaders(carrier, carrier_data, lib, raw_bundle(BUNDLES[carrier]))
    exported = Exported(C + '/export/RebirthMatExport/KH3/' + export)
    t = time.time()
    built, plan = cb.build_blobs(exported, cs, env.work('sora_' + export), prefer=prefer, keep=('Coverage',) + tuple(fixed), ignore_mask=solid)
    print(export, 'compiled %.1fs' % (time.time() - t), {res: (r['kind'], r['problems'][:1], len(r['blob'] or b'')) for res, r in built.items()})
    named = dict(cs.named)
    by_index = {tt['index']: tt for tt in exported.textures if tt['type'] == 'Texture2D'}
    slot_textures = {named[j]: by_index[k]['texture'] for k, j in sorted(plan.items())}
    slot_textures.update(fixed)
    name = mi_path.rsplit('/', 1)[-1]
    carrier_name = '/Game/RebirthCustom/Sora/%s_%s' % (name, short)
    car = packages.carrier_package(carrier_name, carrier_data, cs.raw, {res: r['blob'] for res, r in built.items()})
    if exported.info.get('two_sided'):
        car = packages.set_two_sided(car, carrier_name)
    old = open('/work/sorasurf/out_mats/' + carrier_name.replace('/', '__').strip('_') + '.uasset', 'rb').read()
    print('  carrier copy', len(car), len(old), 'SAME' if car == old else 'DIFFERENT')
    tmpl = open(C + '/seph/pkgs/Character__Player__PC0010_00_Sephiroth_Standard__Material__%s.uasset' % template, 'rb').read()
    mi = packages.game_mi(mi_path, tmpl, carrier_name, slot_textures)
    oldmi = open('/work/sorasurf/out_mats/' + mi_path.replace('/', '__').strip('_') + '.uasset', 'rb').read()
    print('  MI', len(mi), len(oldmi), 'SAME' if mi == oldmi else 'DIFFERENT')
