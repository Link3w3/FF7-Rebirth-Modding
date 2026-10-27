"""AnimeShader on Cloud: the custom base pass pixel shaders for each carrier Cloud's materials use."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bundle import read_bundle
import psinfo, anime_ps, anime_material
from carriers import Carrier, PKGS, texture_parameters

B = '/data/uploads/FF7R2UProj/Saved/ModExtract/shlib/anime/'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'anime', 'ps')
CARRIERS = ['RMI_Surface_Standard_Wide', 'RMI_Surface_Standard_Coverage_Wide', 'RMI_Surface_Hair_Wide',
            'RMI_Surface_Skin_Wide_Detail', 'RMI_Surface_Fabric_Wide']


def skin_base_pass_ps(c):
    """{resource index: [shader type names]} of the carrier's base pass pixel shaders for the skinned vertex factories."""
    out = {}
    for s in c.shaders:
        if s['vf'].startswith('TGPUSkin') and s['freq'] == 5 and ('BasePassPS' in s['type'] or s['type'] == 'fa99734846c7227e'):
            out.setdefault(s['res'], set()).add(s['type'])
    return {k: sorted(v) for k, v in out.items()}


def build_carrier(name):
    c = Carrier(PKGS + 'Renderer__MaterialInstance__Surface__%s.uasset' % name)
    names = texture_parameters(c)
    shaders = read_bundle(B + name + '.bundle')
    result = {}
    os.makedirs(OUT, exist_ok=True)
    for res, types in sorted(skin_base_pass_ps(c).items()):
        blob = shaders[res]['code']
        info = psinfo.info(blob)
        variant = '/'.join(t for t in types if t != 'fa99734846c7227e')
        src = anime_ps.generate(info, names, anime_material.material, 'AnimeShader (KadeMats) on ' + name, name, variant)
        base = os.path.join(OUT, '%s_%d' % (name, res))
        open(base + '.hlsl', 'w').write(src)
        dxbc, warnings = anime_ps.compile_ps(src, base + '.dxbc')
        problems, text = anime_ps.verify(info, dxbc)
        open(base + '.txt', 'w').write(text)
        result[res] = dict(types=types, dxbc=base + '.dxbc', size=len(dxbc), problems=problems,
                           warnings=len([l for l in warnings.splitlines() if 'warning' in l]))
        print(name, res, types, len(dxbc), 'OK' if not problems else problems)
    return result


if __name__ == '__main__':
    report = {n: build_carrier(n) for n in (sys.argv[1:] or CARRIERS)}
    json.dump(report, open(os.path.join(OUT, 'report.json'), 'w'), indent=1)
