"""The checked Remake graphs (remake_graphs.py) as a spec the End editor builds them from (build_remake_materials.py):
every material function, master and default texture, at Remake's own paths and names.

    remake_editor_spec.py [out.json]

Per graph: its nodes (UE expression class, original name, properties, inputs as [node, output name] by the names UE's
MaterialEditingLibrary connects by) and a column/row layout; a master's pins and its instances' static permutations.
What the 4.26 editor cannot take as the game's 4.18 graph has it is rewritten here, keeping the arithmetic:
  - a texture sample's RGBA output (unreachable by name) as its single-channel outputs or RGB + A appended;
  - the Custom nodes that read a static switch's define (4.18) read the switch as an input instead;
  - the game's engine hooks (ExternalHook) as the editor's nearest expressions (in the builder);
  - the pins the 4.26 engine has no counterpart for (the game's vertex transforms, context vectors) kept as labelled
    nodes, not connected."""
import json
import os
import re
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import remake_graphs as rg
import ue_mat

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEX_JSON = os.path.join(ROOT, 'zip', 'Renderer', 'Texture')
MAT_JSON = os.path.join(ROOT, 'zip', 'Renderer', 'Material')
GAME_ROOT = '/Game/GameContents/Renderer'

# the master's pins: the editor's own (the same name), or one of the 4.26 engine's (EMaterialProperty), or none
PIN_MAP = {'BaseColor': 'MP_BaseColor', 'Metallic': 'MP_Metallic', 'Specular': 'MP_Specular', 'Roughness': 'MP_Roughness',
           'Normal': 'MP_Normal', 'EmissiveColor': 'MP_EmissiveColor', 'Opacity': 'MP_Opacity', 'OpacityMask': 'MP_OpacityMask',
           'AmbientOcclusion': 'MP_AmbientOcclusion', 'ClearCoat': 'MP_CustomData0', 'TangentOutput': 'MP_Tangent',
           # (4.26's eye: the iris mask in custom data 0)
           'IrisMask': 'MP_CustomData0', 'Distribution': 'MP_Distribution'}
TEX_OUT = {0: '', 1: 'R', 2: 'G', 3: 'B', 4: 'A'}
SHORT_PIN = {'Coordinates': 'UVs', 'TextureObject': 'Tex', 'Exponent': 'Exp', 'AGreaterThanB': 'A > B', 'AEqualsB': 'A == B',
             'ALessThanB': 'A < B', 'MipLevel': 'Level', 'MipBias': 'Bias'}
TEX_CLASSES = ('TextureSample', 'TextureSampleParameter2D', 'TextureSampleParameterCube', 'VectorParameter', 'ParticleColor')
SINGLE_INPUT = {'Abs', 'Ceil', 'Floor', 'Frac', 'OneMinus', 'Saturate', 'Normalize', 'DDX', 'DDY', 'Transform', 'ComponentMask'}
INPUT_NAMES = {'Coordinates': 'UVs', 'TextureObject': 'Tex', 'Input': '', 'Exponent': 'Exp', 'MipValue': 'Level',
               'CoordinatesDX': 'DDX(UVs)', 'CoordinatesDY': 'DDY(UVs)', 'A_switch': 'True', 'B_switch': 'False'}


def ue_input_name(cls, name, props):
    """the input's name as UE's MaterialEditingLibrary finds it (the material editor's short pin names)"""
    if cls == 'StaticSwitchParameter':
        return {'A': 'True', 'B': 'False'}[name]
    if cls == 'MaterialFunctionCall':
        return name   # (a function call's inputs are matched by their own names)
    if cls in SINGLE_INPUT or cls in ('FunctionOutput', 'Reroute'):
        return ''
    if cls in ('TextureSample', 'TextureSampleParameter2D', 'TextureSampleParameterCube', 'TextureProperty'):
        if name == 'MipValue':
            return 'Bias' if 'MipBias' in str(props.get('MipValueMode', '')) else 'Level'
        return INPUT_NAMES.get(name, name)
    if cls == 'Clamp' and name == 'Input':
        return ''
    # (the material editor's short pin names, which the library matches against: Custom inputs too)
    return SHORT_PIN.get(name, name)


def texture_specs():
    """the game's default textures (4x4, one colour; the name is the colour, RRGGBBAA)"""
    out = []
    for f in sorted(os.listdir(TEX_JSON)):
        if not f.endswith('.json'):
            continue
        d = json.load(open(os.path.join(TEX_JSON, f)))[0]
        name = f[:-5]
        m = re.match(r'([0-9A-F]{8})', name)
        if not m:
            continue   # (RepeatNormal: a real image, no graph uses it)
        rgba = [int(m.group(1)[i:i + 2], 16) for i in range(0, 8, 2)]
        p = d.get('Properties', {})
        out.append({'name': name, 'kind': 'cube' if d.get('Type') == 'TextureCube' else '2d', 'rgba': rgba,
                    'srgb': bool(p.get('SRGB', True)), 'compression': p.get('CompressionSettings', 'TextureCompressionSettings::TC_Default').split('::')[-1],
                    'format': d.get('PixelFormat')})
    return out


def material_props(name):
    """the master's own properties that 4.26 has"""
    d = json.load(open(os.path.join(MAT_JSON, name + '.json')))
    p = next(o for o in d if o.get('Type') == 'Material').get('Properties', {})
    keep = {}
    for k in ('BlendMode', 'MaterialDomain', 'ShadingModel', 'TranslucencyLightingMode', 'bComputeFogPerPixel', 'bEnableSeparateTranslucency',
              'bUseTranslucencyVertexFog', 'bUsedWithBeamTrails', 'bUsedWithInstancedStaticMeshes', 'bUsedWithMeshParticles',
              'bUsedWithParticleSprites', 'bUsedWithSkeletalMesh', 'bUsedWithStaticLighting', 'bCanMaskedBeAssumedOpaque', 'Masked'):
        if k in p:
            v = p[k]
            if isinstance(v, str) and '::' in v:
                v = v.split('::')[-1]
            if v == 'TLM_MAX':
                continue
            keep[k] = v
    return keep


class Exporter:
    def __init__(self, functions):
        self.functions = functions     # name -> ue_mat.Function (for the call outputs' names)
        self.nodes = []
        self.ids = {}
        self.extra = []

    def nid(self, n):
        return self.ids[id(n)]

    def new(self, cls, props=None, inputs=None, name=None):
        k = len(self.nodes)
        self.nodes.append({'id': k, 'cls': cls, 'name': name, 'props': props or {}, 'inputs': inputs or {}})
        return k

    def out_name(self, n, index):
        if n.cls in TEX_CLASSES:
            return TEX_OUT[index]
        if n.cls == 'MaterialFunctionCall':
            fn = n.props['Function']
            return fn.outputs[index][0]
        if n.cls == 'Custom':
            return '' if index == 0 else n.props['AdditionalOutputs'][index - 1][0]
        if n.cls == 'DynamicParameter':
            # (unnamed single-channel outputs: found by their channel)
            return 'RGBA'[index]
        if n.cls == 'ParticleSubUVProperties':
            return ['TextureCoordinate0', 'TextureCoordinate1', 'Blend'][index]
        if index != 0:
            raise ValueError('output %d of %s' % (index, n.cls))
        return ''

    def source(self, link, consumer=None):
        """an input's source as [node id, output name] (a constant as a Constant node)"""
        if isinstance(link, float):
            return [self.new('Constant', {'R': link}), '']
        n, index = link
        k = self.visit(n)
        if n.cls in ('TextureSample', 'TextureSampleParameter2D', 'TextureSampleParameterCube') and index == 5:
            # the RGBA output: RGB and A appended (a mask of it is rewired by the mask itself)
            return [self.new('AppendVector', {}, {'A': [k, ''], 'B': [k, 'A']}), '']
        return [k, self.out_name(n, index)]

    def visit(self, n):
        if id(n) in self.ids:
            return self.ids[id(n)]
        props = {}
        for key, v in n.props.items():
            if key in ('Function',):
                props['Function'] = v.name
            elif key == 'Definition':
                continue
            else:
                props[key] = v
        k = self.new(n.cls, props, {}, n.name if (n.name or '').startswith('MaterialExpression') else None)
        self.ids[id(n)] = k
        spec = self.nodes[k]
        inputs = {}
        for name, link in n.inputs.items():
            if link is None:
                continue
            if name in ('CoordinatesDX', 'CoordinatesDY') and 'Derivative' not in str(props.get('MipValueMode', '')):
                continue   # (wired in the game's graph but read only in derivative mode; the editor hides the pins)
            if n.cls == 'ComponentMask' and isinstance(link, tuple) and link[0].cls in ('TextureSample', 'TextureSampleParameter2D',
                                                                                          'TextureSampleParameterCube') and link[1] == 5:
                src = self.visit(link[0])
                chans = [c for c in 'RGBA' if props.get(c)]
                if len(chans) == 1:
                    inputs[name] = [src, chans[0]]
                    for c in 'RGBA':
                        props[c] = (c == 'R')
                elif 'A' not in chans:
                    inputs[name] = [src, '']
                else:
                    inputs[name] = [self.new('AppendVector', {}, {'A': [src, ''], 'B': [src, 'A']}), '']
                continue
            inputs[name] = self.source(link)
        spec['inputs'] = {ue_input_name(n.cls, k_, props): v for k_, v in inputs.items()}
        inputs = spec['inputs']
        # a Custom node reading a static switch's define: the switch as an input (1 or 0) instead
        if n.cls == 'Custom':
            code = props['Code']
            defs = sorted(set(re.findall(r'#if (STATIC_SWITCH_\w+)', code)))
            for d in defs:
                param = self.switch_param(d)
                one, zero = self.new('Constant', {'R': 1.0}), self.new('Constant', {'R': 0.0})
                sw = self.new('StaticSwitchParameter', {'ParameterName': param['ParameterName'], 'Group': param.get('Group', 'Static'),
                                                        'DefaultValue': param.get('DefaultValue', False)},
                              {'True': [one, ''], 'False': [zero, '']})
                inputs[d] = [sw, '']
                code = re.sub(r'#if %s\b' % d, 'if (%s > 0.5)\n{' % d, code)
            if defs:
                code = code.replace('#else', '}\nelse\n{').replace('#endif', '}')
                props['Code'] = code
                props['InputNames'] = list(props.get('InputNames') or []) + defs
        return k

    def switch_param(self, define):
        for s in self.switches:
            if s.get('Definition') == define:
                return s
        raise KeyError(define)


def collect_switches(roots):
    out, seen = [], set()

    def walk(n):
        if id(n) in seen:
            return
        seen.add(id(n))
        if n.cls == 'StaticSwitchParameter':
            out.append(n.props)
        for v in n.inputs.values():
            if isinstance(v, tuple):
                walk(v[0])
    for r in roots:
        if isinstance(r, tuple):
            walk(r[0])
    return out


def layout(nodes, roots):
    """columns by the longest path to an output (the outputs at the right), rows in order within a column"""
    depth = {}
    consumers = {}
    for n in nodes:
        for src, _ in n['inputs'].values():
            consumers.setdefault(src, []).append(n['id'])
    order = sorted(range(len(nodes)), reverse=True)

    def d(k, stack=()):
        if k in depth:
            return depth[k]
        cs = consumers.get(k, [])
        depth[k] = 0 if not cs else 1 + max(d(c, stack + (k,)) for c in cs)
        return depth[k]
    sys.setrecursionlimit(100000)
    rows = {}
    for k in range(len(nodes)):
        col = d(k)
        r = rows.get(col, 0)
        h = 260 if nodes[k]['cls'] in ('Custom', 'MaterialFunctionCall', 'TextureSampleParameter2D', 'TextureSample') else 140
        nodes[k]['x'] = -420 * (col + 1)
        nodes[k]['y'] = r
        rows[col] = r + h


def export_function(fn, functions):
    e = Exporter(functions)
    e.switches = []
    inputs = []
    for node in fn.input_nodes:
        k = e.visit(node)
        inputs.append(k)
    outputs = []
    for name, link in fn.outputs:
        src = e.source(link)
        k = e.new('FunctionOutput', {'OutputName': name, 'SortPriority': len(outputs)}, {'': src})
        outputs.append(k)
    layout(e.nodes, outputs)
    return {'name': fn.name, 'path': fn.path, 'description': fn.description, 'nodes': e.nodes}


# What the game's base pass shaders store for a shading model's extra inputs where its graph leaves them unwired and
# this engine's default differs (read from each master's shaders: the GBuffer custom data, SV_Target4, they write):
#   preintegrated skin (Skin, Blood): custom data (0, 0, 0, 1), no subsurface colour. Unwired, this engine's subsurface
#     colour is white, which it adds to the diffuse colour under sky and bounce light: the skin washes out to white.
#   hair: custom data rgb = the UV1 bent normal in world space * 0.5 + 0.5 (the graph's TangentOutput), over the
#     cylindrical normal in GBuffer A: the layout the End engine's recovered retail hair lighting reads, through the
#     RebirthMaterialPreview plugin's Rebirth Hair Data output (optional: built only where the plugin is loaded).
BLACK_SUBSURFACE = ('MSM_PreintegratedSkin', 'MSM_Subsurface', 'MSM_TwoSidedFoliage')


def editor_additions(name, m, e, pins):
    notes = []
    shading = material_props(name).get('ShadingModel') or m.props.get('shading_model')
    if shading in BLACK_SUBSURFACE and 'SubsurfaceColor' not in pins:
        k = e.new('Constant3Vector', {'Constant': [0.0, 0.0, 0.0, 0.0]})
        pins['SubsurfaceColor'] = {'property': 'MP_SubsurfaceColor', 'from': [k, '']}
        notes.append({'node': k, 'text': 'Remake: no subsurface colour. The game stores 0 here; unwired, this engine uses '
                                         'white and adds it to the skin under sky and bounce light (white skin).'})
    if shading == 'MSM_Hair' and 'TangentOutput' in pins:
        mul = e.new('Multiply', {'ConstB': 0.5}, {'A': list(pins['TangentOutput']['from'])})
        add = e.new('Add', {'ConstB': 0.5}, {'A': [mul, '']})
        out = e.new('RebirthHairOutput', {}, {'EncodedWideBentNormal': [add, '']})
        e.nodes[out]['optional'] = True
        notes.append({'node': out, 'text': 'Remake hair data: the UV1 bent normal (world, * 0.5 + 0.5) the game stores '
                                           'in custom data, read by the End engine\'s recovered hair lighting.'})
    return notes


def export_material(name, m, functions, inst):
    e = Exporter(functions)
    e.switches = collect_switches(m.pins.values())
    pins, others = {}, {}
    for pin, link in m.pins.items():
        if link is None:
            continue
        src = e.source(link)
        if pin in PIN_MAP:
            pins[pin] = {'property': PIN_MAP[pin], 'from': src}
        else:
            # (no 4.26 pin for it: the value kept in the graph on a reroute, boxed and labelled with the game's pin)
            k = e.new('Reroute', {}, {'': src})
            others[pin] = k
    notes = editor_additions(name, m, e, pins)
    layout(e.nodes, [])
    perms = [{'name': k, 'on': v['on'], 'masked': bool((v.get('ovr') or {}).get('Masked'))} for k, v in sorted(inst.items())
             if v['parent'] == name]
    return {'name': name, 'path': m.path, 'props': material_props(name), 'graph_props': m.props, 'nodes': e.nodes,
            'pins': pins, 'remake_pins': others, 'permutations': perms, 'editor_notes': notes}


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'gen', 'remake_editor_spec.json')
    inst = json.load(open(os.path.join(ROOT, 'remake_inst.json')))
    masters = {k: f() for k, f in rg.MASTERS.items()}
    functions = dict(rg._FUNCTIONS)
    # the functions in the order they can be built (the ones a function calls first)
    order, done = [], set()

    def add(fn):
        if fn.name in done:
            return
        seen = set()

        def walk(n):
            if id(n) in seen:
                return
            seen.add(id(n))
            if n.cls == 'MaterialFunctionCall':
                add(n.props['Function'])
            for v in n.inputs.values():
                if isinstance(v, tuple):
                    walk(v[0])
        for _, link in fn.outputs:
            if isinstance(link, tuple):
                walk(link[0])
        done.add(fn.name)
        order.append(fn)
    for fn in functions.values():
        add(fn)
    spec = {'root': GAME_ROOT, 'textures': texture_specs(),
            'functions': [export_function(fn, functions) for fn in order],
            'materials': [export_material(k, m, functions, inst) for k, m in sorted(masters.items())]}
    json.dump(spec, open(out, 'w'), indent=1)
    n_nodes = sum(len(x['nodes']) for x in spec['functions'] + spec['materials'])
    print('%s: %d textures, %d functions, %d masters, %d nodes, %d permutations' % (
        out, len(spec['textures']), len(spec['functions']), len(spec['materials']), n_nodes,
        sum(len(m['permutations']) for m in spec['materials'])))


if __name__ == '__main__':
    main()
