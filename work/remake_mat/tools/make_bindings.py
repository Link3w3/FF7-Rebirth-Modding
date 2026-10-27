"""Each dumped shader's resource bindings (from the game's 4.18 shader headers): its constant buffers by uniform buffer
name, its textures and samplers as (uniform buffer, resource index), written to dis/<package>/bindings.json.
    make_bindings.py [name filter...]"""
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import d3dheader418
import shadermap418

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(ROOT, 'paks', 'GameContents', 'Renderer')


def main():
    flt = sys.argv[1:]
    index = json.load(open(os.path.join(ROOT, 'dis', 'index.json')))
    done = 0
    for name, entry in sorted(index.items()):
        if flt and not any(f in name for f in flt):
            continue
        path = os.path.join(R, 'Material' if name.startswith('EndMaterial_') else 'MaterialInstance', name + '.uasset')
        pk, sh = shadermap418.shaders(path)
        byhash = {s['hash']: s for s in sh}
        out = {}
        for key, info in entry['shaders'].items():
            s = byhash.get(info['hash'])
            if not s:
                out[key] = {'error': 'shader not found'}
                continue
            b = d3dheader418.binding(s['code'])
            cbn = b['cb']

            def nm(u):
                return cbn[u] if u < len(cbn) else str(u)
            out[key] = {'cb': cbn, 't': {str(k): [nm(u), r] for k, (u, r) in b['t'].items()},
                        's': {str(k): [nm(u), r] for k, (u, r) in b['s'].items()}}
        json.dump(out, open(os.path.join(ROOT, 'dis', name, 'bindings.json'), 'w'), indent=1)
        done += 1
    print(done, 'packages')


if __name__ == '__main__':
    main()
