"""Hair dither fix as a plain override (no runtime swap): the game's own /Engine/EngineResources/SpatiotemporalBlueNoiseVolume
package with only its red channel changed (build_variants.variant), under its own name, so the engine loads ours in
place of the game's at startup and nothing is ever swapped or unloaded."""
import json, os, sys
import numpy as np
sys.path[:0] = ['/work/iostore', '/work/cs', os.path.dirname(os.path.abspath(__file__))]
from zen import Zen
import build_variants as BV
import dump_tex

def main(out_dir, kind):
    data = open(BV.SRC, 'rb').read()
    t = dump_tex.parse(BV.SRC)
    m = t['mips'][0]
    at, size = m['data_at'], m['size']
    px = np.frombuffer(m['data'], np.uint8).reshape(64, 128, 128, 4)
    body = BV.variant(kind, px).tobytes()
    out = data[:at] + body + data[at + size:]
    assert len(out) == len(data)
    z = Zen(out)
    assert z.names[z.name_mapped & 0x3FFFFFFF] == BV.OLD_PKG and z.exports[0]['name'] == BV.OLD_OBJ
    name = BV.OLD_OBJ
    run = os.path.join(out_dir, kind)
    os.makedirs(run, exist_ok=True)
    open(os.path.join(run, name + '.zen'), 'wb').write(out)
    json.dump({'package': BV.OLD_PKG, 'report': {'variant': kind}}, open(os.path.join(run, 'report.json'), 'w'), indent=1)
    diff = int((np.frombuffer(out[at:at + size], np.uint8) != np.frombuffer(data[at:at + size], np.uint8)).sum())
    print(kind, BV.OLD_PKG, len(out), 'bytes;', diff, 'bytes of pixel data changed (red only)')
    return run

if __name__ == '__main__':
    for k in sys.argv[2:]:
        main(sys.argv[1], k)
