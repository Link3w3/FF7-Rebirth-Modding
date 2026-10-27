"""Specs for the End editor's rebuilt FF7 Remake masters (build_remake_masters.py builds them in the editor).

Per master: every parameter it declares (from its FModel export: textures with their default textures and sampler types,
scalars, vectors, static switches), its material settings, and its permutations - the master's own and each of its
instances' (the shader maps the game ships) - each as Custom nodes made by remake_ue.py from the game's own shaders
(lift_check.py checks every lift), with the static switch values that pick it. The editor's master selects the
permutation with a tree of the game's own static switches over material attributes, so the game's instances, with their
own switches, get exactly their own shaders.

    remake_spec.py EndMaterial_Standard [...]   writes gen/masters/<master>.json"""
import collections
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import remake_ue

ROOT = remake_ue.ROOT
ZIP = os.path.join(ROOT, 'zip', 'Renderer')
OUT = os.path.join(ROOT, 'gen', 'masters')
ASSET_ROOT = '/Game/GameContents/Renderer'

# the editor's shading model for the game's (its hair model is the game's own: "Unknown" to 4.18's names)
SHADING = {'MSM_DefaultLit': 'MSM_DEFAULT_LIT', 'MSM_PreintegratedSkin': 'MSM_PREINTEGRATED_SKIN', 'MSM_Eye': 'MSM_EYE',
           'MSM_SubsurfaceProfile': 'MSM_SUBSURFACE_PROFILE', 'MSM_Subsurface': 'MSM_SUBSURFACE', 'MSM_ClearCoat': 'MSM_CLEAR_COAT',
           'MSM_Cloth': 'MSM_CLOTH', 'MSM_TwoSidedFoliage': 'MSM_TWO_SIDED_FOLIAGE', 'MSM_Hair': 'MSM_HAIR', 'Unknown': 'MSM_HAIR'}
SAMPLER = {None: 'SAMPLERTYPE_COLOR', 'EMaterialSamplerType::SAMPLERTYPE_Color': 'SAMPLERTYPE_COLOR',
           'EMaterialSamplerType::SAMPLERTYPE_LinearColor': 'SAMPLERTYPE_LINEAR_COLOR',
           'EMaterialSamplerType::SAMPLERTYPE_Alpha': 'SAMPLERTYPE_ALPHA', 'EMaterialSamplerType::SAMPLERTYPE_Normal': 'SAMPLERTYPE_NORMAL',
           'EMaterialSamplerType::SAMPLERTYPE_Grayscale': 'SAMPLERTYPE_GRAYSCALE', 'EMaterialSamplerType::SAMPLERTYPE_Masks': 'SAMPLERTYPE_MASKS',
           'EMaterialSamplerType::SAMPLERTYPE_LinearGrayscale': 'SAMPLERTYPE_LINEAR_GRAYSCALE'}


def obj_path(ref):
    """FModel's 'End/Content/GameContents/Renderer/Texture/X.0' -> '/Game/GameContents/Renderer/Texture/X'"""
    if not isinstance(ref, dict):
        return None
    p = ref.get('ObjectPath', '')
    if p.startswith('End/Content/'):
        p = '/Game/' + p[len('End/Content/'):]
    return p.rsplit('.', 1)[0]


def master_params(master):
    d = json.load(open(os.path.join(ZIP, 'Material', master + '.json')))
    tex, sca, vec, sw = {}, {}, {}, {}
    mat = None
    for x in d:
        t, p = x.get('Type'), x.get('Properties', {})
        name = p.get('ParameterName')
        if t == 'Material':
            mat = p
        elif t in ('MaterialExpressionTextureSampleParameter2D', 'MaterialExpressionTextureObjectParameter',
                   'MaterialExpressionTextureSampleParameterCube'):
            tex.setdefault(name, {'name': name, 'texture': obj_path(p.get('Texture')), 'cube': t.endswith('Cube'),
                                  'sampler': SAMPLER.get(p.get('SamplerType'), 'SAMPLERTYPE_COLOR'), 'group': p.get('Group') or 'Texture'})
        elif t == 'MaterialExpressionScalarParameter':
            sca.setdefault(name, {'name': name, 'default': float(p.get('DefaultValue') or 0.0), 'group': p.get('Group') or 'Scalar'})
        elif t == 'MaterialExpressionVectorParameter':
            dv = p.get('DefaultValue') or {}
            vec.setdefault(name, {'name': name, 'default': [float(dv.get(c, 0.0)) for c in 'RGBA'], 'group': p.get('Group') or 'Vector'})
        elif t == 'MaterialExpressionStaticSwitchParameter':
            sw.setdefault(name, {'name': name, 'group': p.get('Group') or 'Static'})
    return mat or {}, tex, sca, vec, sw


def build_tree(perms, switches, default_perm):
    """the static switch tree that picks each permutation by its own switch values (leaves: permutation names)"""
    if len(perms) == 1:
        return perms[0]['name']
    best = None
    for s in switches:
        on = [p for p in perms if p['switches'].get(s, False)]
        off = [p for p in perms if not p['switches'].get(s, False)]
        if on and off:
            score = abs(len(on) - len(off))
            if best is None or score < best[0]:
                best = (score, s, on, off)
    if best is None:
        # the same switch values (they differ in something else): the first one
        return perms[0]['name']
    _, s, on, off = best
    rest = [x for x in switches if x != s]
    return {'switch': s, 'true': build_tree(on, rest, default_perm), 'false': build_tree(off, rest, default_perm)}


def spec(master):
    inst = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'remake_inst.json')))
    usets = remake_ue.uniform_sets()
    mat, tex, sca, vec, sw = master_params(master)
    names = [master] + sorted(k for k, v in inst.items() if v['parent'] == master)
    perms, notes = [], []
    for name in names:
        if not os.path.exists(os.path.join(remake_ue.DIS, name, remake_ue.BASE_PS + '.asm')):
            notes.append('%s has no shader map of its own (it renders with its parent\'s permutation)' % name)
            continue
        r = remake_ue.build(name)
        r['shading_model_editor'] = SHADING.get(r['shading_model'], 'MSM_DEFAULT_LIT')
        perms.append(r)
        notes.extend(r['notes'])
    master_perm = next(p for p in perms if p['name'] == master)
    switch_defaults = {k: bool(master_perm['switches'].get(k, False)) for k in sw}
    for p in perms:
        for k in p['switches']:
            if k not in sw:
                sw[k] = {'name': k, 'group': 'Static'}
                switch_defaults.setdefault(k, False)
    varying = [s for s in sorted(sw) if len({bool(p['switches'].get(s, False)) for p in perms}) > 1]
    tree = build_tree(perms, varying, master)
    models = sorted({p['shading_model_editor'] for p in perms})
    # every input the permutations read that the master does not declare (it should declare them all)
    for p in perms:
        for node in (p['base'], p['coverage']):
            for i in (node or {}).get('inputs', []):
                if i['kind'] in ('texture2d', 'texturecube') and i['param'] not in tex:
                    notes.append('%s reads texture %s, which %s does not declare' % (p['name'], i['param'], master))
                    tex[i['param']] = {'name': i['param'], 'texture': None, 'cube': i['kind'] == 'texturecube',
                                       'sampler': 'SAMPLERTYPE_LINEAR_COLOR', 'group': 'Texture'}
                if i['kind'] == 'scalar' and i['param'] not in sca:
                    sca[i['param']] = {'name': i['param'], 'default': float(i.get('default') or 0.0), 'group': 'Scalar'}
                if i['kind'] == 'vector' and i['param'] not in vec:
                    vec[i['param']] = {'name': i['param'], 'default': list(i.get('default') or [0, 0, 0, 0]), 'group': 'Vector'}
    usage = [k[len('bUsedWith'):] for k, v in mat.items() if k.startswith('bUsedWith') and v is True]
    return {
        'asset': '%s/Material/%s' % (ASSET_ROOT, master),
        'master': master,
        'material': {'shading_models': models, 'blend_mode': 'BLEND_OPAQUE', 'two_sided': False, 'usage': usage,
                     'opacity_mask_clip_value': 0.5},
        'textures': sorted(tex.values(), key=lambda x: x['name']),
        'scalars': sorted(sca.values(), key=lambda x: x['name']),
        'vectors': sorted(vec.values(), key=lambda x: x['name']),
        'switches': [dict(sw[k], default=switch_defaults.get(k, False)) for k in sorted(sw)],
        'noise': '/Engine/EngineResources/SpatiotemporalBlueNoiseVolume.SpatiotemporalBlueNoiseVolume',
        'permutations': [{'name': p['name'], 'switches': p['switches'], 'shading_model': p['shading_model_editor'],
                          'masked': p['masked'], 'two_sided': p['two_sided'], 'base': p['base'], 'coverage': p['coverage']}
                         for p in perms],
        'tree': tree,
        'notes': notes,
    }


def main():
    os.makedirs(OUT, exist_ok=True)
    for m in sys.argv[1:]:
        s = spec(m)
        json.dump(s, open(os.path.join(OUT, m + '.json'), 'w'), indent=1)
        depth = 0

        def d(t):
            return 0 if isinstance(t, str) else 1 + max(d(t['true']), d(t['false']))
        print('%s: %d permutations, %d textures, %d scalars, %d vectors, %d switches, tree depth %d, models %s%s' % (
            m, len(s['permutations']), len(s['textures']), len(s['scalars']), len(s['vectors']), len(s['switches']),
            d(s['tree']), s['material']['shading_models'], ''.join('\n   note: ' + n for n in s['notes'])))


if __name__ == '__main__':
    main()
