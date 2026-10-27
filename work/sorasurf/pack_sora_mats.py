"""Builds Sora's game materials (build_sora_mats.main) and packs them: the carrier copies, the MIs (store entries like the
Sephiroth MIs they were made from) and his textures (zen/, converted from the End editor's cooked copies in tex/).
Load order as the game's: what a package imports comes before it. Read back chunk by chunk.

    python3 pack_sora_mats.py [out folder] [mod folder]
"""
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, '/work/custmat/taken', '/work/custmat']

import build_sora_mats as bs                # noqa: E402
import pack                                 # noqa: E402
import zentex                               # noqa: E402
from rebirth_fx import iostore_write as W   # noqa: E402

MOD_NAME = 'SoraKH3_Materials_P'
SURFACE = '/Game/Renderer/MaterialInstance/Surface/'
SEPH_PACKAGE = '/Game/Character/Player/PC0010_00_Sephiroth_Standard/Material/'
TEXTURE_ORDER = 580000


def zen_textures(objects):
    out = {}
    for obj in objects:
        short = obj.rsplit('.', 1)[-1]
        ua = open(os.path.join(HERE, 'tex', short + '.uasset'), 'rb').read()
        bulk_path = os.path.join(HERE, 'tex', short + '.ubulk')
        ub = open(bulk_path, 'rb').read() if os.path.isfile(bulk_path) else b''
        pkg, bulk, rep = zentex.convert(ua, ub)
        if rep['package'] != obj.split('.')[0]:
            raise ValueError('%s holds %s' % (short, rep['package']))
        os.makedirs(os.path.join(HERE, 'zen'), exist_ok=True)
        open(os.path.join(HERE, 'zen', short + '.uasset'), 'wb').write(pkg)
        open(os.path.join(HERE, 'zen', short + '.ubulk'), 'wb').write(bulk)
        out[obj] = (pkg, bulk)
    return out


def main(out_dir, mod_dir):
    packages, report = bs.main(out_dir)
    if report['missing_exports']:
        raise ValueError('missing exports: %s' % report['missing_exports'])
    like = {}
    for mi, job in report['jobs'].items():
        like[job['carrier_copy']] = SURFACE + job['carrier']
        like[mi] = SEPH_PACKAGE + job['template']
    retail = pack.retail_entries()
    order = {name: retail[W.package_id(like[name])]['load_order'] for name in packages}
    for mi, job in report['jobs'].items():
        order[mi] = max(order[mi], order[job['carrier_copy']] + 1, TEXTURE_ORDER + 1)
    carriers = sorted(job['carrier_copy'] for job in report['jobs'].values())
    mis = sorted(report['jobs'])
    items = [dict(data=packages[n], bulk=None, like=like[n], load_order=order[n]) for n in carriers + mis]
    for obj, (pkg, bulk) in sorted(zen_textures(report['textures']).items()):
        items.append(dict(data=pkg, bulk=bulk if bulk else None, like=None, load_order=TEXTURE_ORDER))
    paths, entries = pack.build(items, mod_dir, MOD_NAME)
    back = pack.read_back(paths[0])
    for it in items:
        pid = W.package_id(pack.package_name(it['data']))
        if back.get((pid, 2)) != it['data'] or (it['bulk'] is not None and back.get((pid, 3)) != it['bulk']):
            raise ValueError('%s does not read back' % pack.package_name(it['data']))
    return paths, entries, report


if __name__ == '__main__':
    paths, entries, report = main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'out_mats'),
                                  sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, 'mod_mats'))
    for p in paths:
        print(p, os.path.getsize(p), hashlib.md5(open(p, 'rb').read()).hexdigest())
    for e in entries:
        print('  %-80s exports %d bundles %d load_order %d imports %d' % (e['name'], e['export_count'], e['export_bundle_count'],
                                                                         e['load_order'], len(e['imports'])))
