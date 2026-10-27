"""Reproduce the Taken build (custmat/taken/out) with the ported rebirth_fx.gamemat code, byte for byte."""
import hashlib, os, struct, sys, time
sys.path.insert(0, '/work/fxlink/src/Content/Python')
from rebirth_fx.gamemat import env
env.set_dxc('/home/user/microsoft/dxc-build/bin/dxc', dict(os.environ, LD_LIBRARY_PATH='/home/user/microsoft/dxc-build/lib'))
env.set_engine_shaders('/work/custmat/gamesh/engine/Shaders')
env.set_work('/tmp/scratch/gamemat_test')
from rebirth_fx.gamemat import shaderlib, carrier_build as cb, packages
from rebirth_fx.gamemat.material import Exported

C = '/work/custmat'
lib = shaderlib.Library(open('/data/uploads/FF7R2UProj/Saved/ModExtract/shlib/End_header.bin', 'rb').read(), prefixed=True)

def raw_bundle(path):
    raw = open(path, 'rb').read(); p = 0; out = []
    while p < len(raw):
        index, size, usize, freq = struct.unpack_from('<IIIB', raw, p); p += 13
        hsh = raw[p:p + 20]; p += 20
        out.append(dict(index=index, hash=hsh, code=raw[p:p + size], usize=usize, freq=freq)); p += size
    return out

CARRIER = 'RMI_Surface_Standard_Wide_Detail'
carrier_data = open('/work/anime/pkgs/Renderer__MaterialInstance__Surface__%s.uasset' % CARRIER, 'rb').read()
t = time.time()
cs = cb.CarrierShaders(CARRIER, carrier_data, lib, raw_bundle(C + '/seph/%s.bundle' % CARRIER))
print('carrier ready %.1fs' % (time.time() - t), 'variants', sorted(cs.variants), 'depth', sorted(cs.depth_variants))
exported = Exported(C + '/export/RebirthMatExport/Materials__Destiny2__Taken')
PREFER = ('Color', 'Metallic', 'Roughness', 'Normal', 'Detail', 'WideOcclusion', 'DetailNormal')
t = time.time()
built, plan = cb.build_blobs(exported, cs, env.work('taken_opaque'), prefer=PREFER, keep=('Coverage',), depth=False)
print('compiled %.1fs' % (time.time() - t), {res: (r['problems'][:1], len(r['blob'] or b'')) for res, r in built.items()})
named = dict(cs.named)
by_index = {tt['index']: tt for tt in exported.textures if tt['type'] == 'Texture2D'}
slot_textures = {named[j]: by_index[k]['texture'] for k, j in sorted(plan.items())}
carrier_name = '/Game/RebirthCustom/Taken/Taken_Standard_Wide_Detail'
car = packages.carrier_package(carrier_name, carrier_data, cs.raw, {res: r['blob'] for res, r in built.items()})
old = open(C + '/taken/out/Taken_Standard_Wide_Detail.uasset', 'rb').read()
print('carrier copy', len(car), 'old', len(old), 'SAME' if car == old else 'DIFFERENT', hashlib.md5(car).hexdigest(), hashlib.md5(old).hexdigest())
tmpl = open(C + '/seph/pkgs/Character__Player__PC0010_00_Sephiroth_Standard__Material__PC0010_00_BodyA.uasset', 'rb').read()
mi = packages.game_mi('/Game/RebirthCustom/Taken/MI_Taken_PC0010_00_BodyA', tmpl, carrier_name, slot_textures)
oldmi = open(C + '/taken/out/MI_Taken_PC0010_00_BodyA.uasset', 'rb').read()
print('MI', len(mi), 'old', len(oldmi), 'SAME' if mi == oldmi else 'DIFFERENT')
