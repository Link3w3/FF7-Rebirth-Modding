"""The parameters a Remake (4.18) cooked master declares (its kept expressions): texture, scalar, vector and static switch
parameters with their names, defaults, groups and sampler types.   remake_params.py <master.uasset> [--json]"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pkg418


class Tolerant(pkg418.Package):
    def tagged(self, r, end):
        try:
            return super().tagged(r, end)
        except Exception:
            return []


def props(e):
    return {n: v for n, t, i, v in e['props']}


def params(path):
    pk = Tolerant(path)
    out = {'textures': [], 'scalars': [], 'vectors': [], 'switches': []}
    for e in pk.exports:
        cls = pk.classname(e)
        if not cls.startswith('MaterialExpression'):
            continue
        p = props(e)
        name = p.get('ParameterName')
        if name is None:
            continue
        group = p.get('Group')
        if cls in ('MaterialExpressionTextureSampleParameter2D', 'MaterialExpressionTextureObjectParameter',
                   'MaterialExpressionTextureSampleParameterCube'):
            tex = p.get('Texture')
            out['textures'].append({'name': name, 'class': cls, 'texture': pk.ref(tex) if isinstance(tex, int) else tex,
                                    'sampler': p.get('SamplerType'), 'group': group})
        elif cls == 'MaterialExpressionScalarParameter':
            out['scalars'].append({'name': name, 'default': p.get('DefaultValue', 0.0), 'group': group})
        elif cls == 'MaterialExpressionVectorParameter':
            out['vectors'].append({'name': name, 'default': p.get('DefaultValue'), 'group': group})
        elif cls == 'MaterialExpressionStaticSwitchParameter':
            out['switches'].append({'name': name, 'default': bool(p.get('DefaultValue', False)), 'group': group})
    return out


if __name__ == '__main__':
    r = params(sys.argv[1])
    if '--json' in sys.argv:
        print(json.dumps(r, indent=1))
    else:
        for k, v in r.items():
            print('==', k, len(v))
            for x in v:
                print('   ', x)
