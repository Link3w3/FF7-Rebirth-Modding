"""Remake effect sidecar (rmcascade.py) -> nconvert options: for every emitter the game material instance, renderer
template, material parameter bindings and per-particle material parameter recipe that stand in for Remake's material.

    rmrebirth.py <sidecar .json> <options .json out> [--report]

Remake's particle master (EndMaterial_Particle) and Rebirth's (RM_Particle) are the same design: a gray or colour
layer graded between two tones, opacity / visibility layers on their own coordinates, the coordinates turned in
quarter turns, offset and scaled. What Remake keeps as material instance parameters Rebirth keeps as renderer
material bindings (static) and five per-particle Vector4s (IndependentParameter0..5) that a module writes:

  Remake                                         Rebirth
  SecondColor, SecondLuminance * Luminance       IndependentParameter1 = (bright tone rgb, luminance) * particle colour
  FirstColor                                     IndependentParameter2 = (dark tone rgb, 0) * particle colour
  ToneColor (2^x on the gray, the tone blend)    EmitterEmitTone
  ToneLuminance (2^x on the gray, brightness)    EmitterEmitTint + IndependentParameter4.x (when it moves)
  layer 0 coordinate (FlipBook, Rotation,        EmitterCoordinateEmit* (the opacity layer shares it: Visibility0)
    Offset, Scale, Distribution)
  a moving layer offset                          EmitterCoordinate*Offset = its direction, IndependentParameter5.x the
                                                 amount (Particles.DynamicMaterialParameter, from rmcascade)
  Identity (no grade)                            both tones the particle colour, EmitterEmitTint 0
"""
import glob, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
RBX = os.path.join(os.path.dirname(HERE), 'rbx')
RBTPL = os.path.join(os.path.dirname(HERE), 'rbtpl')
RES_TEX = '/Game/Effect/Resident/Texture/'
RES_MODEL = '/Game/Effect/Resident/Model/'
RMI_ROOT = '/Game/Renderer/MaterialInstance/Particle/'
WHITE = 'FX_R_White_01A_T'

_cache = {}


def _lines(name):
    if name not in _cache:
        _cache[name] = [x.strip() for x in open(os.path.join(RBX, name)) if x.strip()]
    return _cache[name]


def rebirth_texture(remake_path):
    """a Remake resident texture -> (Rebirth resident texture object path, its name) or None"""
    if not remake_path:
        return None
    nm = remake_path.rsplit('/', 1)[-1].split('.')[0]
    rel = {x.rsplit('/', 1)[-1]: x for x in _lines('rb_textures.txt')}
    m = re.match(r'^(FX_R_.+?)_T$', nm)
    if not m:
        return None
    base = m.group(1)
    for cand in (base + 'E', base + 'A', base, base + 'COL', base + 'C'):
        t = cand + '_T'
        if t in rel:
            return RES_TEX + rel[t] + '.' + t, t
    return None


def rebirth_mesh(remake_path):
    if not remake_path:
        return None
    nm = remake_path.rsplit('/', 1)[-1].split('.')[0]
    if nm in set(_lines('rb_models.txt')):
        return RES_MODEL + nm + '.' + nm
    return None


def rmi(name):
    return RMI_ROOT + name + '.' + name


def material_kind(emi):
    """Remake EMI_* name -> its parts"""
    nm = (emi or '').rsplit('.', 1)[-1]
    t = nm.split('_')
    return {'name': nm, 'lit': 'Lit' in t, 'lit_mode': t[t.index('Lit') + 1] if 'Lit' in t else None,
            'emit': 'Emit' in t, 'gray': 'Gray' in t, 'color': 'Color' in t, 'grade': 'Grade' in t,
            'identity': 'Identity' in t, 'opacity': 'Opacity' in t, 'visibility': 'Visibility' in t,
            'modifier': 'Modifier' in t, 'soft': 'Soft' in t, 'directional': 'Directional' in t,
            'diffuse': 'Diffuse' in t, 'normal': 'Normal' in t}


def choose_rmi(mk):
    have = set(_lines('rmi_list.txt'))
    parts = ['RMI_Particle']
    if mk['lit']:
        parts += ['Lit', {'Average': 'Average', 'Rough': 'Rough'}.get(mk['lit_mode'], 'Average')]
    if mk['emit']:
        parts.append('Emit')
    if mk['opacity'] or mk['visibility']:
        parts.append('Visibility')
    if mk['modifier']:
        parts.append('Distortion')
    if mk['soft']:
        parts.append('Soft')
    tries = ['_'.join(parts)]
    for drop in ('Distortion', 'Soft'):
        if drop in parts:
            p2 = [x for x in parts if x != drop]
            tries.append('_'.join(p2))
    for t in tries:
        if t in have:
            return t, tries
    return None, tries


def _templates():
    if 'tpl' not in _cache:
        d = json.load(open(os.path.join(os.path.dirname(HERE), 'rbtpl_renderers.json')))
        paths = {os.path.basename(p): p for p in glob.glob(os.path.join(RBTPL, 'End', 'Content', '**', '*.uasset'), recursive=True)}
        _cache['tpl'] = (d, paths)
    return _cache['tpl']


def choose_template(rmi_name, kind, ips, cull):
    d, paths = _templates()
    cls = 'NiagaraMeshRendererProperties' if kind == 'mesh' else 'NiagaraSpriteRendererProperties'
    best = None
    for r in d:
        if r['cls'] != cls:
            continue
        m = r.get('material')
        m = m[0] if isinstance(m, list) else m
        if not m or m.rsplit('.', 1)[-1] != rmi_name:
            continue
        bound = set(int(k) for k in (r.get('ips') or {}))
        if not set(ips) <= bound:
            continue
        score = 0
        score += 4 if r['emitter'][2] == 'CPU' else 0
        score += 2 if r['emitter'][1] else 0
        sq = r.get('sqex') or {}
        score += 2 if bool(sq.get('VfxOverrideCullMode')) == bool(cull) else 0
        score -= sum(1 for b in r.get('binds', []) if b.get('var'))
        if best is None or score > best[0]:
            best = (score, r)
    if best is None:
        return None
    r = best[1]
    return {'template_from': paths[r['pkg']], 'template_export': r['export'], 'template_of': '%s %s' % (r['pkg'], r['emitter'][0])}


COORD = re.compile(r'^(\d):0:Coo?rdinate:(\d):(\w+)\(')


def layer_coords(params, layer):
    """Remake layer coordinate parameters -> {FlipBook, Rotation, Offset, Scale, Distribution} first values"""
    out = {'FlipBook': 0.0, 'Rotation': 0.0, 'Offset': [0.0, 0.0], 'Scale': [1.0, 1.0], 'Distribution': [0.0, 0.0, 0.0, 0.0]}
    for sec in ('scalars', 'vectors'):
        for nm, v in params.get(sec, {}).items():
            m = COORD.match(nm)
            if not m or m.group(1) != str(layer):
                continue
            key = m.group(3)
            val = v['const'] if 'const' in v else v['curve'][0]
            if key in ('FlipBook', 'Rotation', 'Parallax'):
                out[key] = float(val if not isinstance(val, list) else val[0])
            elif key in ('Offset', 'Scale'):
                out[key] = [float(val[0]), float(val[1])]
            elif key == 'Distribution':
                out[key] = [float(x) for x in val[:4]]
    return out


def scalar(params, name, default):
    v = params.get('scalars', {}).get(name)
    if v is None:
        return default
    return float(v['const'] if 'const' in v else v['curve'][0])


def vector(params, name, default):
    v = params.get('vectors', {}).get(name)
    if v is None:
        return list(default)
    x = v['const'] if 'const' in v else v['curve'][0]
    return [float(a) for a in x[:4]]


def layer_textures(params):
    """{layer: {slot name: remake texture path}}"""
    out = {}
    for nm, path in params.get('textures', {}).items():
        parts = nm.split(':')
        if len(parts) < 3 or not parts[0].isdigit():
            continue
        out.setdefault(int(parts[0]), {})[parts[-1]] = path
    return out


def recipe(ename, e, system, notes):
    mk = material_kind(e.get('material'))
    params = e.get('params') or {}
    kind = 'mesh' if e.get('typedata') == 'ParticleModuleTypeDataMesh' else 'sprite'
    rmi_name, tried = choose_rmi(mk)
    if rmi_name is None:
        notes.append('%s: no game material for %s (tried %s)' % (ename, mk['name'], ', '.join(tried)))
        return None
    if mk['lit'] and not mk['emit']:
        ips = [0, 3, 4, 5]
    elif mk['lit']:
        ips = [0, 1, 2, 3, 4, 5]
    else:
        ips = [0, 1, 2, 4, 5]
    cull = params.get('CullMode') if params.get('OverrideCullMode') else None
    tpl = choose_template(rmi_name, kind, ips, cull)
    if tpl is None:
        notes.append('%s: no %s renderer template with %s binding %s' % (ename, kind, rmi_name, ips))
        return None
    dyn = {d['param']: d for d in (e.get('dynamic') or [])}
    texs = layer_textures(params)
    binds = []
    missing = []

    def tex(name, remake_path, fallback=WHITE):
        r = rebirth_texture(remake_path) if remake_path else None
        if r is None:
            if remake_path:
                missing.append(remake_path)
            t = fallback
            binds.append({'name': name, 'type': 'texture', 'value': RES_TEX + t + '.' + t, 'resident': True})
        else:
            binds.append({'name': name, 'type': 'texture', 'value': r[0], 'resident': True})

    def coords(prefix, layer):
        c = layer_coords(params, layer)
        off = c['Offset']
        d = next((x for x in dyn.values() if x['kind'] == 'offset' and x.get('layer') == str(layer)), None)
        if d is not None:
            off = d['dir']
        binds.append({'name': 'EmitterCoordinate%sFlipBook' % prefix, 'type': 'bool', 'value': [c['FlipBook']]})
        binds.append({'name': 'EmitterCoordinate%sOffset' % prefix, 'type': 'vector2', 'value': off})
        dist = c['Distribution']
        if any(abs(x) > 1e-6 for x in dist):
            binds.append({'name': 'EmitterCoordinate%sOffsetDistribution' % prefix, 'type': 'vector2', 'value': [dist[1], dist[3]]})
            if abs(dist[0]) > 1e-6 or abs(dist[2]) > 1e-6:
                notes.append('%s: layer %d offset spread by its own size (%s) left out' % (ename, layer, dist))
        else:
            binds.append({'name': 'EmitterCoordinate%sOffsetDistribution' % prefix, 'type': 'vector2', 'value': [0.0, 0.0]})
        binds.append({'name': 'EmitterCoordinate%sRotation' % prefix, 'type': 'float', 'value': [c['Rotation']]})
        binds.append({'name': 'EmitterCoordinate%sScale' % prefix, 'type': 'vector2', 'value': c['Scale']})
        if c['FlipBook'] >= 0.5:
            notes.append('%s: layer %d is a flip-book (sub images are not set up yet)' % (ename, layer))

    # -- emissive
    lum = scalar(params, 'L:0:Luminance(Float1)', 1.0)
    if mk['emit']:
        gray = texs.get(0, {}).get('Gray') or texs.get(0, {}).get('Color')
        tex('Emissive', gray)
        binds.append({'name': 'EmitterEmitChrome', 'type': 'bool', 'value': [1.0 if mk['color'] else 0.0]})
        coords('Emit', 0)
        tone_lum_moves = 'L:6:ToneLuminance(Float1)' in dyn
        if mk['grade']:
            tone_color = scalar(params, 'L:5:ToneColor(Float1)', 0.0)
            tone_lum = scalar(params, 'L:6:ToneLuminance(Float1)', 0.0)
        else:
            tone_color, tone_lum = 0.0, 0.0
        binds.append({'name': 'EmitterEmitTint', 'type': 'float', 'value': [0.0 if tone_lum_moves else tone_lum]})
        binds.append({'name': 'EmitterEmitTone', 'type': 'float', 'value': [tone_color]})
        binds.append({'name': 'EmitterEmitExposureCondition', 'type': 'bool', 'value': [1.0]})
    # -- lit
    if mk['lit']:
        op = texs.get(0, {}).get('Opacity')
        if op or mk['opacity']:
            tex('Opacity', op)
        coords('Lit', 0)
        if mk['diffuse'] or texs.get(0, {}).get('Diffuse'):
            tex('Diffuse', texs.get(0, {}).get('Diffuse'))
    # -- visibility layers: Remake's opacity (layer 0's coordinate) and visibility (layer 2's)
    vis = []
    if mk['emit'] and mk['opacity']:
        vis.append((texs.get(0, {}).get('Opacity'), 0))
    if mk['visibility']:
        vis.append((texs.get(2, {}).get('Visibility'), 2))
    if 'Visibility' in rmi_name:
        for i in range(2):
            if i < len(vis):
                path, layer = vis[i]
                tex('Visibility%d' % i, path)
                coords('Visibility%d' % i, layer)
            else:
                tex('Visibility%d' % i, None)
                binds.append({'name': 'EmitterCoordinateVisibility%dFlipBook' % i, 'type': 'bool', 'value': [0.0]})
        binds.append({'name': 'EmitterVisibilityTone', 'type': 'float',
                      'value': [scalar(params, 'L:I:ToneOpacity(Float1)', 0.0)]})
    for nm in ('EmitterDistanceFadeFarawayNear', 'EmitterDistanceFadeFarawayFar', 'EmitterDistanceFadeVicinityNear',
               'EmitterDistanceFadeVicinityFar'):
        binds.append({'name': nm, 'type': 'float', 'value': [0.0]})
    if mk['modifier']:
        notes.append('%s: the modifier layer (UV distortion) is left out' % ename)
    # -- per-particle parameters
    def dmp(param):
        d = dyn.get(param)
        return ['attr', 'DynamicMaterialParameter', d['slot']] if d else None

    ip = {0: [[['const', 0.0]], [['const', 1.0]], [['const', 0.0]], [['const', 0.0]]]}
    if mk['emit']:
        lum_f = dmp('L:0:Luminance(Float1)')
        lum_k = 1.0 if lum_f else lum
        if mk['grade']:
            first = vector(params, 'L:7:Tone:0:FirstColor(RGBA)', [1, 1, 1, 1])
            second = vector(params, 'L:7:Tone:2:SecondColor(RGBA)', [1, 1, 1, 1])
            sl = scalar(params, 'L:7:Tone:3:SecondLuminance(Float1)', 1.0)
            fl = scalar(params, 'L:7:Tone:1:FirstLuminance(Float1)', 0.0)
            if fl > 1e-6:
                notes.append('%s: the dark tone has a luminance of its own (%g) - left out' % (ename, fl))
            w = [['color', 3], ['const', lum_k * sl * second[3]]] + ([lum_f] if lum_f else [])
            ip[1] = [[['color', c], ['const', second[c]]] for c in range(3)] + [w]
            ip[2] = [[['color', c], ['const', first[c]]] for c in range(3)] + [[['const', 0.0]]]
        else:
            w = [['color', 3], ['const', lum_k]] + ([lum_f] if lum_f else [])
            ip[1] = [[['color', c]] for c in range(3)] + [w]
            ip[2] = [[['color', c]] for c in range(3)] + [[['const', 0.0]]]
    if mk['lit']:
        diff = vector(params, 'L:A:Diffuse(RGBA)', [1, 1, 1, 1])
        ip[3] = [[['color', c], ['const', diff[c]]] for c in range(3)] + [[['color', 3], ['const', diff[3]]]]
    tl = dmp('L:6:ToneLuminance(Float1)')
    ip[4] = [[tl] if tl else [['const', 0.0]], [['const', 0.0]], [['const', 0.0]], [['const', 0.0]]]
    off = next((d for d in dyn.values() if d['kind'] == 'offset'), None)
    ip[5] = [[['attr', 'DynamicMaterialParameter', off['slot']]] if off else [['const', 1.0]],
             [['const', 0.0]], [['const', 0.0]], [['const', 0.0]]]
    ip = {k: v for k, v in ip.items() if k in ips}
    for k in ips:
        if k not in ip:
            ip[k] = [[['const', 0.0]], [['const', 0.0]], [['const', 0.0]], [['const', 0.0]]]
    r = {'kind': kind, 'material': rmi(rmi_name), 'bindings': binds, 'ip': {str(k): v for k, v in sorted(ip.items())},
         'remake_material': mk['name']}
    r.update(tpl)
    if cull:
        r['cull'] = cull
    if kind == 'mesh':
        m = rebirth_mesh(e.get('mesh'))
        if m is None:
            notes.append('%s: mesh %s is not in the game (import it)' % (ename, e.get('mesh')))
            return None
        r['mesh'] = m
    if missing:
        r['missing_textures'] = missing
        notes.append('%s: textures not in the game (white for now): %s' % (ename, ', '.join(missing)))
    return r


def build(sidecar):
    notes = []
    out = {'remake': {}}
    for ename, e in sidecar['emitters'].items():
        r = recipe(ename, e, sidecar, notes)
        if r is not None:
            out['remake'][ename] = r
    b = sidecar.get('bounds') or {}
    if b.get('IsValid'):
        mx = max(abs(b['Min'][k]) for k in 'XYZ')
        mx = max(mx, max(abs(b['Max'][k]) for k in 'XYZ'))
        out['bounds'] = float(mx)
    out['notes'] = notes
    return out


if __name__ == '__main__':
    sc = json.load(open(sys.argv[1]))
    opts = build(sc)
    json.dump(opts, open(sys.argv[2], 'w'), indent=1)
    for n in opts['notes']:
        print('note:', n)
    for en, r in opts['remake'].items():
        print(en, r['kind'], r['material'].rsplit('.', 1)[-1], 'template', r['template_of'], 'ips', list(r['ip']))
