"""Builds Taken (build_taken.main) and packs RebirthCustomTaken_P: the carriers, the MIs (store entries like the game
packages they were made from), Taken's textures (zen/, loaded first). Load order as the game's: what a package imports
comes before it. Read back chunk by chunk.

    python3 pack_taken.py [out folder] [mod folder]
"""
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE]

import build_taken as bt                    # noqa: E402
import pack                                 # noqa: E402
from rebirth_fx import iostore_write as W   # noqa: E402

MOD_NAME = 'RebirthCustomTaken_P'
SURFACE = '/Game/Renderer/MaterialInstance/Surface/'
SEPH_PACKAGE = '/Game/Character/Player/PC0010_00_Sephiroth_Standard/Material/'
TEXTURE_ORDER = 580000


def main(out_dir, mod_dir):
    packages, report = bt.main(out_dir)
    like = {bt.ROOT + 'Taken_Standard_Wide_Detail': SURFACE + bt.CARRIER,
            bt.ROOT + 'Taken_Fabric_Coverage_Wide_Detail': SURFACE + bt.COVERAGE}
    for name, mi in report['mis'].items():
        like[name] = SEPH_PACKAGE + mi['source']
    retail = pack.retail_entries()
    order = {name: retail[W.package_id(like[name])]['load_order'] for name in packages}
    for name in packages:
        if '/MI_' in name:
            carrier = [c for c in packages if '/MI_' not in c and c in report['mis'][name]['parent']][0]
            order[name] = max(order[name], order[carrier] + 1, TEXTURE_ORDER + 1)
    names = sorted([n for n in packages if '/MI_' not in n], key=lambda n: 'Fabric' in n) + sorted(n for n in packages if '/MI_' in n)
    items = [dict(data=packages[n], bulk=None, like=like[n], load_order=order[n]) for n in names]
    zdir = os.path.join(HERE, 'zen')
    for obj in report['textures']:
        short = obj.rsplit('.', 1)[-1]
        items.append(dict(data=open(os.path.join(zdir, short + '.uasset'), 'rb').read(),
                          bulk=open(os.path.join(zdir, short + '.ubulk'), 'rb').read(), like=None, load_order=TEXTURE_ORDER))
    paths, entries = pack.build(items, mod_dir, MOD_NAME)
    back = pack.read_back(paths[0])
    for it in items:
        pid = W.package_id(pack.package_name(it['data']))
        if back.get((pid, 2)) != it['data'] or (it['bulk'] is not None and back.get((pid, 3)) != it['bulk']):
            raise ValueError('%s does not read back' % pack.package_name(it['data']))
    return paths, entries, report


if __name__ == '__main__':
    paths, entries, report = main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'out'),
                                  sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, 'mod'))
    for p in paths:
        print(p, os.path.getsize(p), hashlib.md5(open(p, 'rb').read()).hexdigest())
    for e in entries:
        print('  %-62s exports %d bundles %d load_order %d imports %d' % (e['name'], e['export_count'], e['export_bundle_count'],
                                                                         e['load_order'], len(e['imports'])))
