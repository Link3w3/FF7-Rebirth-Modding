"""Taken (KadeMats/Materials/Destiny2/Taken) on Sephiroth's BodyA, as a mod of new packages only:

  /Game/RebirthCustom/Taken/Taken_Standard_Wide_Detail   copy of RMI_Surface_Standard_Wide_Detail (BodyA's parent) with
                                                          Taken's pixel shaders inline for its skinned base pass variants
  /Game/RebirthCustom/Taken/MI_Taken_PC0010_00_BodyA      PC0010_00_BodyA re-parented to it, Taken's textures on the
                                                          carrier's named texture parameters (the slot plan)
  the textures themselves                                 cooked by the End editor, converted to zen (zentex)

Nothing of the game or of other mods is replaced: the live link (or a mod) puts MI_Taken on a slot.
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CUSTMAT = os.path.dirname(HERE)
sys.path[:0] = [CUSTMAT, os.path.join(CUSTMAT, 'gamesh'), '/work/fx1018/editor/Python']

from custom_mi import rename_package, with_inline_shaders, unique_shader_map_id, replace_import   # noqa: E402
from carriers import Carrier, PKGS                     # noqa: E402
from pack_anime import raw_bundle                      # noqa: E402
from rebirth_fx import matcore                         # noqa: E402
import carrier_build as cb                             # noqa: E402
import material                                        # noqa: E402

ROOT = '/Game/RebirthCustom/Taken/'
CARRIER = 'RMI_Surface_Standard_Wide_Detail'
BUNDLE = os.path.join(CUSTMAT, 'seph', CARRIER + '.bundle')
SEPH = os.path.join(CUSTMAT, 'seph', 'pkgs', 'Character__Player__PC0010_00_Sephiroth_Standard__Material__%s.uasset')
EXPORT = 'Materials__Destiny2__Taken'
PREFER = ('Color', 'Metallic', 'Roughness', 'Normal', 'Detail', 'WideOcclusion', 'DetailNormal')


def object_path(package):
    return package + '.' + package.rsplit('/', 1)[-1]


def carrier_package(new_name, blobs, report, carrier=CARRIER, bundle_path=BUNDLE):
    path = PKGS + 'Renderer__MaterialInstance__Surface__%s.uasset' % carrier
    data = open(path, 'rb').read()
    c = Carrier(path)
    bundle = raw_bundle(bundle_path)
    if [b['index'] for b in bundle] != c.order:
        raise ValueError('the bundle order differs from the shader map')
    shaders = []
    for res, s in enumerate(bundle):
        if res in blobs:
            if s['freq'] != 5:
                raise ValueError('resource %d is not a pixel shader' % res)
            new = blobs[res]
            shaders.append(dict(hash=hashlib.sha1(new).digest(), code=new, usize=len(new), freq=s['freq']))
        else:
            shaders.append(dict(hash=s['hash'], code=s['code'], usize=s['usize'], freq=s['freq']))
    mi = rename_package(data, new_name)
    mi, _ = unique_shader_map_id(mi, new_name)
    mi = with_inline_shaders(mi, shaders)
    check = matcore.MaterialInstance(mi, 'check')
    if check.pkg.errors:
        raise ValueError('the carrier does not read back: %s' % check.pkg.errors)
    s1, z1 = check.z.bundle_positions()[check.index]
    s0, z0 = c.mi.z.bundle_positions()[c.mi.index]
    if mi[s1:s1 + check.v.size] != data[s0:s0 + c.mi.v.size]:
        raise ValueError('the carrier\'s property block changed')
    report.setdefault('carriers', {})[new_name] = dict(from_=carrier, replaced=sorted(blobs), size=len(mi), shaders=len(shaders))
    return mi


def taken_mi(new_name, carrier_name, slot_textures, report, source='PC0010_00_BodyA', old_parent_rmi=CARRIER):
    """slot_textures: {carrier parameter name: texture object path}."""
    data = open(SEPH % source, 'rb').read()
    old_parent = object_path('/Game/Renderer/MaterialInstance/Surface/' + old_parent_rmi)
    out = replace_import(data, old_parent, object_path(carrier_name))
    out = rename_package(out, new_name)
    mi = matcore.MaterialInstance(out, new_name.rsplit('/', 1)[-1])
    changes = [dict(kind='texture', name=n, value=v) for n, v in sorted(slot_textures.items())]
    out, lines = matcore.edit(mi, changes)
    back = matcore.MaterialInstance(out, 'check')
    if back.pkg.errors or back.parent != object_path(carrier_name):
        raise ValueError('%s does not read back: %s %s' % (new_name, back.pkg.errors, back.parent))
    for n, v in slot_textures.items():
        p = back.find('texture', n)
        if p is None or p['value'] != v:
            raise ValueError('%s: %s is %s, wanted %s' % (new_name, n, p and p['value'], v))
    report.setdefault('mis', {})[new_name] = dict(source=source, parent=back.parent, textures=dict(slot_textures), edits=lines,
                                                  size=len(out))
    return out


def build_set(carrier, bundle_path, carrier_name, mis, report, keep=('Coverage',), fixed=None, prefer=PREFER, work='set'):
    """Taken compiled onto `carrier` (its skinned base pass variants), the carrier copy `carrier_name`, and one MI per
    (new name, Sephiroth MI it is made from, that MI's parent) in `mis` with Taken's textures on the slot plan and the
    `fixed` {parameter: texture} values (the MI's own values stay for the `keep` parameters)."""
    cs = cb.CarrierShaders(carrier, bundle_path)
    exported = material.Exported(os.path.join(cb.EXPORTS, EXPORT))
    built, plan = cb.build_blobs(exported, cs, '/tmp/scratch/gamesh_work/taken_' + work, prefer=prefer,
                                 keep=tuple(keep) + tuple(fixed or ()))
    problems = {res: r['problems'] for res, r in built.items() if r['problems']}
    if problems:
        raise ValueError('%s: shader problems: %s' % (carrier, problems))
    named = dict(cs.named)
    by_index = {t['index']: t for t in exported.textures if t['type'] == 'Texture2D'}
    slot_textures = {}
    for k, j in sorted(plan.items()):
        slot_textures[named[j]] = by_index[k]['texture']
    for n, v in (fixed or {}).items():
        if n not in named.values():
            raise ValueError('%s has no parameter %s' % (carrier, n))
        slot_textures[n] = v
    packages = {carrier_name: carrier_package(carrier_name, {res: r['blob'] for res, r in built.items()}, report, carrier,
                                              bundle_path)}
    for new_name, source, old_parent in mis:
        packages[new_name] = taken_mi(new_name, carrier_name, slot_textures, report, source, old_parent)
    report.setdefault('plans', {})[carrier_name] = {('Texture2D_%d' % k): dict(slot=j, parameter=named[j], texture=by_index[k]['texture'])
                                                     for k, j in sorted(plan.items())}
    report.setdefault('shaders', {})[carrier_name] = {res: dict(types=r['types'], size=len(r['blob']),
                                                                sha1=hashlib.sha1(r['blob']).hexdigest()) for res, r in built.items()}
    textures = sorted(set(v for n, v in slot_textures.items() if n not in (fixed or {})))
    return packages, textures


COVERAGE = 'RMI_Surface_Fabric_Coverage_Wide_Detail'
WHITE = '/Game/Renderer/Texture/FFFFFFFF_BC4.FFFFFFFF_BC4'


def main(out_dir):
    """Every part of Sephiroth: the opaque ones (BodyA, Head, Skin, Eyelash) wear MI_Taken_PC0010_00_BodyA; the ones cut
    out by a coverage texture (BodyB, Eyebrow; Hair, HairCore) wear a Taken MI on a coverage carrier that keeps their
    own coverage texture (its detail coverage white, so the cut-out is exactly the character's)."""
    os.makedirs(out_dir, exist_ok=True)
    report = {}
    packages = {}
    p1, t1 = build_set(CARRIER, BUNDLE, ROOT + 'Taken_Standard_Wide_Detail',
                       [(ROOT + 'MI_Taken_PC0010_00_BodyA', 'PC0010_00_BodyA', CARRIER)], report, work='opaque')
    packages.update(p1)
    p2, t2 = build_set(COVERAGE, os.path.join(CUSTMAT, 'seph', COVERAGE + '.bundle'), ROOT + 'Taken_Fabric_Coverage_Wide_Detail',
                       [(ROOT + 'MI_Taken_PC0010_00_BodyB', 'PC0010_00_BodyB', 'RMI_Surface_Standard_Coverage_Wide'),
                        (ROOT + 'MI_Taken_PC0010_00_Hair', 'PC0010_00_Hair', 'RMI_Surface_Hair_Wide')],
                       report, keep=('Coverage',), fixed={'DetailCoverage': WHITE},
                       prefer=('Color', 'Normal', 'Roughness', 'WideOcclusion', 'Occlusion', 'Detail', 'Diffusion', 'DetailNormal'),
                       work='coverage')
    packages.update(p2)
    report['textures'] = sorted(set(t1) | set(t2))
    # which slot of Sephiroth wears which
    report['wear'] = {
        'PC0010_00_BodyA': ROOT + 'MI_Taken_PC0010_00_BodyA', 'PC0010_00_Head': ROOT + 'MI_Taken_PC0010_00_BodyA',
        'PC0010_00_Skin': ROOT + 'MI_Taken_PC0010_00_BodyA', 'PC0010_00_Eyelash': ROOT + 'MI_Taken_PC0010_00_BodyA',
        'PC0010_00_BodyB': ROOT + 'MI_Taken_PC0010_00_BodyB', 'PC0010_00_Eyebrow': ROOT + 'MI_Taken_PC0010_00_Hair',
        'PC0010_00_Hair': ROOT + 'MI_Taken_PC0010_00_Hair', 'PC0010_00_HairCore': ROOT + 'MI_Taken_PC0010_00_Hair',
    }
    for name, data in packages.items():
        open(os.path.join(out_dir, name.rsplit('/', 1)[-1] + '.uasset'), 'wb').write(data)
    json.dump(report, open(os.path.join(out_dir, 'report.json'), 'w'), indent=1)
    return packages, report


if __name__ == '__main__':
    packages, report = main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'out'))
    print(json.dumps(report, indent=1)[:4000])
