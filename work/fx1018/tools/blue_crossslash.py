"""Blue Cross Slash: recolours Cloud's Cross Slash limit break (all three parts) and packs it as a game mod.
    blue_crossslash.py <out dir> [--hue 215] [--spread 0.25] [--sat 1.0] [--bright 1.0] [--mode blue|swap_rb]
"""
import argparse, json, os, sys
sys.path.insert(0, '/work/fx1018/tools')
import fxlib

PKGS = ['/work/fx1018/pkgs/Effect__Character__Player__PC0000_Cloud__Particle__FX_PC0000_Limit01_CrossSlash_%s.uasset' % n
        for n in ('01', '02', '03')]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--hue', type=float, default=215.0)
    ap.add_argument('--spread', type=float, default=0.25)
    ap.add_argument('--sat', type=float, default=1.0)
    ap.add_argument('--bright', type=float, default=1.0)
    ap.add_argument('--mode', default='blue')
    ap.add_argument('--name', default='BlueCrossSlash_P')
    a = ap.parse_args()
    kw = {} if a.mode != 'blue' else dict(hue=a.hue, spread=a.spread, sat=a.sat, bright=a.bright)
    outs, report = [], {}
    for path in PKGS:
        pkg = fxlib.Package(open(path, 'rb').read(), os.path.basename(path))
        assert not pkg.errors, (path, pkg.errors)
        data, rep = fxlib.recolor(pkg, a.mode, **kw)
        # the changed package must parse exactly like the original, with only the LUT floats different
        again = fxlib.Package(data, 'patched')
        assert not again.errors and len(data) == len(pkg.data)
        before = fxlib.color_curves(pkg); after = fxlib.color_curves(again)
        assert [(c['export'], c['name'], c['at']) for c in before] == [(c['export'], c['name'], c['at']) for c in after]
        changed = sum(1 for x, y in zip(pkg.data, data) if x != y)
        lut_bytes = sum(4 * len(c['floats']) for c in before)
        assert changed <= lut_bytes
        outs.append(data)
        report[pkg.name] = dict(curves=rep, bytes_changed=changed)
        print('%s: %d colour curves recoloured (%d bytes changed)' % (pkg.name, len(rep), changed))
    files = fxlib.build_mod(outs, a.out, a.name)
    json.dump(dict(settings=vars(a), packages=report), open(os.path.join(a.out, a.name + '.report.json'), 'w'), indent=1)
    for f in files:
        print(f, os.path.getsize(f))


if __name__ == '__main__':
    main()
