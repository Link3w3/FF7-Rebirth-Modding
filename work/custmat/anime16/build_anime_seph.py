"""AnimeShader (KadeMats/Materials/AnimeShader) on Sephiroth: every part keeps its own Color and Normal textures (the
carrier's Color / Normal slots, as the part's material has them) and its own cut-outs (Coverage), AnimeShader's masks
go on spare slots. New packages only; the live link puts the parts' anime materials on.

    python3 build_anime_seph.py <out folder>
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CUSTMAT = os.path.dirname(HERE)
sys.path[:0] = [CUSTMAT, os.path.join(CUSTMAT, 'gamesh'), os.path.join(CUSTMAT, 'taken'), '/work/fx1018/editor/Python']

import carrier_build as cb                      # noqa: E402
import material                                 # noqa: E402
import zentex                                   # noqa: E402
from build_taken import carrier_package, taken_mi, BUNDLE, CARRIER, COVERAGE, WHITE   # noqa: E402

ROOT = '/Game/RebirthCustom/Anime/'
EXPORT = 'Materials__AnimeShader'
ROLES_NAMES = {'BaseColor': 'Color', 'Normal': 'Normal'}      # AnimeShader parameter -> the character's own texture
OPAQUE_PARTS = [('BodyA', CARRIER), ('Head', 'RMI_Surface_Skin_Wide_Detail'), ('Skin', 'RMI_Surface_Skin_Wide_Detail'),
                ('Eyelash', 'RMI_Surface_Standard_Wide')]
COVERAGE_PARTS = [('BodyB', 'RMI_Surface_Standard_Coverage_Wide'), ('Eyebrow', 'RMI_Surface_Standard_Coverage_Wide'),
                  ('Hair', 'RMI_Surface_Hair_Wide'), ('HairCore', 'RMI_Surface_Hair_Wide')]
TEXTURE_SOURCES = os.path.join(CUSTMAT, 'anime16', 'tex')
# the eye: AnimeShaderEye (made in the project for this: Rebirth's eye mapping with AnimeShader's tones) on a copy of
# Rebirth's eye material, the eye keeping its own sclera, iris and gaze textures
EYE_EXPORT = 'Materials__AnimeShaderEye'
EYE_CARRIER = 'RMI_Surface_Eye_Migration'
EYE_PARTS = [('Eye', EYE_CARRIER)]
EYE_ROLES = {'Color': 'Color', 'IrisColor': 'IrisColor', 'GazeNormal': 'GazeNormal'}
BLACK = '/Game/Renderer/Texture/000000FF_sRGB.000000FF_sRGB'
# AnimeShader's ShadowMask / FaceMaskR default to a KadeMats hair template drawn for another model's UVs: on Sephiroth
# they put shadow patches in random places, so they are off (black), as for Cloud
SWAP = {'ShadowMask': BLACK, 'FaceMaskR': BLACK}
# the exposure the AnimeShader look is shown at, as the editor would (it divides its emissive by the exposure twice):
# 0.2 puts his skin's mid tone near its texture colour and keeps whites just below glowing (from the screenshots)
EDITOR_EXPOSURE = 0.2


def build_set(exported, carrier, bundle, carrier_name, parts, report, keep, fixed=None, prefer=(), names=None, roles_names=None):
    cs = cb.CarrierShaders(carrier, bundle)
    roles = {}
    for t in exported.textures:
        if t['type'] == 'Texture2D' and t['parameter'] in (roles_names or ROLES_NAMES):
            roles[t['index']] = (roles_names or ROLES_NAMES)[t['parameter']]
    built, plan = cb.build_blobs(exported, cs, '/tmp/scratch/gamesh_work/anime_' + carrier, prefer=prefer,
                                 keep=tuple(keep) + tuple(fixed or ()), roles=roles, ignore_mask=True, exposure='editor',
                                 editor_exposure=EDITOR_EXPOSURE)
    problems = {res: r['problems'] for res, r in built.items() if r['problems']}
    if problems:
        raise ValueError('%s: shader problems: %s' % (carrier, problems))
    named = dict(cs.named)
    by_index = {t['index']: t for t in exported.textures if t['type'] == 'Texture2D'}
    shipped = {}
    for k, j in sorted(plan.items()):
        if k in roles:
            continue                                   # the part's own texture of that parameter
        shipped[named[j]] = SWAP.get(by_index[k]['parameter'], by_index[k]['texture'])
    overrides = dict(shipped)
    overrides.update(fixed or {})
    packages = {carrier_name: carrier_package(carrier_name, {res: r['blob'] for res, r in built.items()}, report, carrier, bundle)}
    for part, old_parent in parts:
        name = ROOT + (names or 'MI_Anime_PC0010_00_%s') % part
        packages[name] = taken_mi(name, carrier_name, overrides, report, 'PC0010_00_' + part, old_parent)
    report.setdefault('plans', {})[carrier_name] = {('Texture2D_%d' % k): dict(
        slot=j, parameter=named[j], texture=('(the part\'s own %s)' % roles[k]) if k in roles
        else SWAP.get(by_index[k]['parameter'], by_index[k]['texture']))
        for k, j in sorted(plan.items())}
    report.setdefault('shaders', {})[carrier_name] = {res: dict(types=r['types'], size=len(r['blob']),
                                                                sha1=hashlib.sha1(r['blob']).hexdigest()) for res, r in built.items()}
    return packages, sorted(set(t for t in shipped.values() if not t.startswith('/Game/Renderer/')))


def main(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    report = {}
    exported = material.Exported(os.path.join(cb.EXPORTS, EXPORT))
    packages = {}
    p1, t1 = build_set(exported, CARRIER, BUNDLE, ROOT + 'Anime_Standard_Wide_Detail', OPAQUE_PARTS, report,
                       keep=('Coverage',), prefer=('Metallic', 'Roughness', 'Occlusion', 'Detail'))
    packages.update(p1)
    p2, t2 = build_set(exported, COVERAGE, os.path.join(CUSTMAT, 'seph', COVERAGE + '.bundle'), ROOT + 'Anime_Fabric_Coverage_Wide_Detail',
                       COVERAGE_PARTS, report, keep=('Coverage',), fixed={'DetailCoverage': WHITE},
                       prefer=('Roughness', 'Occlusion', 'Detail', 'Diffusion'))
    packages.update(p2)
    eye = material.Exported(os.path.join(cb.EXPORTS, EYE_EXPORT))
    p3, t3 = build_set(eye, EYE_CARRIER, os.path.join(CUSTMAT, 'seph', EYE_CARRIER + '.bundle'), ROOT + 'Anime_Eye_Migration',
                       EYE_PARTS, report, keep=(), roles_names=EYE_ROLES)
    packages.update(p3)
    textures = sorted(set(t1) | set(t2) | set(t3))
    report['textures'] = textures
    report['wear'] = dict(('PC0010_00_' + part, ROOT + 'MI_Anime_PC0010_00_' + part) for part, _ in OPAQUE_PARTS + COVERAGE_PARTS + EYE_PARTS)
    for name, data in packages.items():
        open(os.path.join(out_dir, name.rsplit('/', 1)[-1] + '.uasset'), 'wb').write(data)
    # the shipped textures, cooked by the editor, as the game holds them
    zdir = os.path.join(out_dir, 'zen')
    os.makedirs(zdir, exist_ok=True)
    for obj in textures:
        short = obj.rsplit('.', 1)[-1]
        zen, bulk, info = zentex.convert(open(os.path.join(TEXTURE_SOURCES, short + '.uasset'), 'rb').read(),
                                         open(os.path.join(TEXTURE_SOURCES, short + '.ubulk'), 'rb').read())
        open(os.path.join(zdir, short + '.uasset'), 'wb').write(zen)
        open(os.path.join(zdir, short + '.ubulk'), 'wb').write(bulk)
        report.setdefault('texture_info', {})[obj] = dict(format=info['format'], size=info['size'], mips=len(info['mips']))
    json.dump(report, open(os.path.join(out_dir, 'report.json'), 'w'), indent=1)
    return packages, report


MOD_NAME = 'RebirthCustomAnime_P'
SEPH_PACKAGE = '/Game/Character/Player/PC0010_00_Sephiroth_Standard/Material/'
SURFACE = '/Game/Renderer/MaterialInstance/Surface/'


def pack_mod(out_dir, packages, report, mod_dir):
    """The container: the two carriers and the eight MIs (store entries like the game packages they were made from),
    the textures (loaded before what uses them). Read back chunk by chunk."""
    import pack
    like = {ROOT + 'Anime_Standard_Wide_Detail': SURFACE + CARRIER,
            ROOT + 'Anime_Fabric_Coverage_Wide_Detail': SURFACE + COVERAGE, ROOT + 'Anime_Eye_Migration': SURFACE + EYE_CARRIER}
    for part, _ in OPAQUE_PARTS + COVERAGE_PARTS + EYE_PARTS:
        like[ROOT + 'MI_Anime_PC0010_00_' + part] = SEPH_PACKAGE + 'PC0010_00_' + part
    from rebirth_fx import iostore_write as W
    retail = pack.retail_entries()
    items = []
    TEXTURE_ORDER = 580000
    for obj in report['textures']:
        short = obj.rsplit('.', 1)[-1]
        zdir = os.path.join(out_dir, 'zen')
        items.append(dict(data=open(os.path.join(zdir, short + '.uasset'), 'rb').read(),
                          bulk=open(os.path.join(zdir, short + '.ubulk'), 'rb').read(), like=None, load_order=TEXTURE_ORDER))
    # load order as the game's: what a package imports comes before it (an MI after its carrier and the textures)
    order = {name: retail[W.package_id(like[name])]['load_order'] for name in packages}
    for name in packages:
        if '/MI_' in name:
            carrier = [c for c in packages if '/MI_' not in c and c in report['mis'][name]['parent']][0]
            order[name] = max(order[name], order[carrier] + 1, TEXTURE_ORDER + 1)
    for name, data in packages.items():
        items.append(dict(data=data, bulk=None, like=like[name], load_order=order[name]))
    paths, entries = pack.build(items, mod_dir, MOD_NAME)
    back = pack.read_back(paths[0])
    for it in items:
        pid = W.package_id(pack.package_name(it['data']))
        if back.get((pid, 2)) != it['data']:
            raise ValueError('%s does not read back' % pack.package_name(it['data']))
        if it['bulk'] is not None and back.get((pid, 3)) != it['bulk']:
            raise ValueError('%s bulk does not read back' % pack.package_name(it['data']))
    return paths, entries


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'out')
    packages, report = main(out)
    for n, d in packages.items():
        print(n, len(d))
    print(json.dumps(report['plans'], indent=1))
    print(report['textures'], report.get('texture_info'))
    paths, entries = pack_mod(out, packages, report, os.path.join(HERE, 'mod'))
    for p in paths:
        print(p, os.path.getsize(p), hashlib.md5(open(p, 'rb').read()).hexdigest())
    for e in entries:
        print('  %-70s exports %d bundles %d load_order %d imports %d' % (e['name'], e['export_count'], e['export_bundle_count'],
                                                                         e['load_order'], len(e['imports'])))
