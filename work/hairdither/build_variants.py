"""Hair dither fix: variants of Rebirth's SpatiotemporalBlueNoiseVolume (B8G8R8A8 128x128x64, one inline mip) with only
the red channel changed - the one RM_Surface's dithered coverage test reads (Coverage > Noise.x): renamed copies of the
game's cooked package under /Game/HairDitherFix, one run dir each (report.json + .zen) for build_pack2.py.

  Soft   : red pulled toward 0.5 (n' = 0.5 + (n - 0.5) * SOFT): only coverage within +-SOFT/2 of 0.5 still dithers
  Stable : red of the first frame in every frame: the same spatial pattern, no frame-to-frame crawl
  Off    : red 0.5 everywhere: a plain cut-out at coverage 0.5 (no dither)
"""
import json, os, sys
import numpy as np
sys.path[:0] = ['/work/iostore', '/work/cs', '/work/weap1012/tools', os.path.dirname(os.path.abspath(__file__))]
from zen import Zen
import zenrename, gameids
import dump_tex

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'game', 'SpatiotemporalBlueNoiseVolume.uasset')
OLD_PKG = '/Engine/EngineResources/SpatiotemporalBlueNoiseVolume'
OLD_OBJ = 'SpatiotemporalBlueNoiseVolume'
SOFT = float(os.environ.get('HDF_SOFT', '0.35'))


def variant(kind, rgba):
    a = rgba.copy()                          # (z, y, x, 4) in memory order B, G, R, A
    r = a[..., 2].astype(np.float32) / 255.0
    if kind == 'Soft':
        r = 0.5 + (r - 0.5) * SOFT
    elif kind == 'Stable':
        r = np.broadcast_to(r[0:1], r.shape)
    elif kind == 'Off':
        r = np.full_like(r, 128.0 / 255.0)
    a[..., 2] = np.clip(np.round(r * 255.0), 0, 255).astype(np.uint8)
    return a


def main(out_dir):
    data = open(SRC, 'rb').read()
    t = dump_tex.parse(SRC)
    m = t['mips'][0]
    assert t['fmt'] == 'PF_B8G8R8A8' and (m['x'], m['y'], m['z']) == (128, 128, 64) and len(t['mips']) == 1
    at, size = m['data_at'], m['size']
    assert data[at:at + size] == m['data']
    px = np.frombuffer(m['data'], np.uint8).reshape(64, 128, 128, 4)
    made = []
    for kind in ('Soft', 'Stable', 'Off'):
        new_obj = 'STBN_' + kind
        new_pkg = '/Game/HairDitherFix/' + new_obj
        body = variant(kind, px).tobytes()
        patched = data[:at] + body + data[at + size:]
        hashed = (2 << 62) | gameids.objhash(new_pkg + '.' + new_obj)
        out = zenrename.rebuild(patched, {OLD_PKG: new_pkg, OLD_OBJ: new_obj}, export_global_imports={0: hashed})
        z = Zen(out)
        assert z.names[z.name_mapped & 0x3FFFFFFF] == new_pkg and z.exports[0]['name'] == new_obj
        assert z.exports[0]['global_import'] == hashed
        assert out[z.header_end:].find(body) >= 0
        run = os.path.join(out_dir, new_obj)
        os.makedirs(run, exist_ok=True)
        open(os.path.join(run, new_obj + '.zen'), 'wb').write(out)
        json.dump({'package': new_pkg, 'report': {'variant': kind, 'soft': SOFT if kind == 'Soft' else None}},
                  open(os.path.join(run, 'report.json'), 'w'), indent=1)
        r = np.frombuffer(body, np.uint8).reshape(64, 128, 128, 4)[..., 2]
        print('%-7s %s %d bytes  red min %d max %d mean %.1f  (other channels unchanged: %s)' % (
            kind, new_pkg, len(out), r.min(), r.max(), r.mean(),
            bool((np.frombuffer(body, np.uint8).reshape(64, 128, 128, 4)[..., [0, 1, 3]] == px[..., [0, 1, 3]]).all())))
        made.append(run)
    return made


if __name__ == '__main__':
    main(sys.argv[1])
