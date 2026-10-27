"""UE 4 material graphs (expressions, material functions, static switches) and what the engine's HLSL material translator
makes of them, for one static permutation at a time.

A graph is built from Node()s (class names without "MaterialExpression"); an input is (node, output index) or a
constant. translate() follows the translator's rules: each expression's result type (float1..4, textures), scalar
broadcasting in arithmetic, component masks, appends, static switches resolved by name, material functions inlined
(their inputs bound per call), texture samples with the sampler type's decode, Custom nodes as functions. The result is
HLSL that computes the material's pins - the same arithmetic the game's shader does, so it can be checked against it.

The same graph is what the editor builds (graph_spec() gives the nodes and links for build_remake_graphs.py)."""
import itertools
import re

_ids = itertools.count()
T2D, TCUBE, T3D = 'Texture2D', 'TextureCube', 'Texture3D'


class Node:
    def __init__(self, cls, inputs=None, name=None, **props):
        self.cls = cls
        self.inputs = {}
        for k, v in (inputs or {}).items():
            self.inputs[k] = link(v)
        self.props = props
        self.id = next(_ids)
        self.name = name or '%s_%d' % (cls, self.id)

    def __getitem__(self, k):
        return (self, k)

    def __repr__(self):
        return 'Node(%s %s)' % (self.cls, self.name)


def link(v):
    if v is None:
        return None
    if isinstance(v, Node):
        return (v, 0)
    if isinstance(v, tuple) and isinstance(v[0], Node):
        return v
    if isinstance(v, (int, float)):
        return float(v)
    raise TypeError(v)


class Function:
    """a material function: inputs (name, type, default) in order, outputs (name -> link) in order"""
    def __init__(self, name, inputs, description='', path=None):
        self.name = name
        self.description = description
        self.path = path
        self.input_nodes = []
        for i, (n, t, default) in enumerate(inputs):
            node = Node('FunctionInput', name='Input_' + re.sub(r'\W', '_', n), InputName=n, InputType=t, SortPriority=i,
                        PreviewValue=default)
            self.input_nodes.append(node)
        self.outputs = []   # [(name, link)]

    def inp(self, name):
        return next(n for n in self.input_nodes if n.props['InputName'] == name)

    def output(self, name, value):
        self.outputs.append((name, link(value)))
        return self


class Material:
    def __init__(self, name, path=None):
        self.name = name
        self.path = path
        self.pins = {}
        self.props = {}

    def pin(self, prop, value):
        self.pins[prop] = link(value)


# ---- the translator ---------------------------------------------------------------------------------------------
TYPE_NAMES = {1: 'float', 2: 'float2', 3: 'float3', 4: 'float4'}
COMP = 'xyzw'


class Value:
    def __init__(self, code, t):
        self.code, self.t = code, t     # t: 1..4, or a texture type name

    def __repr__(self):
        return 'Value(%s, %s)' % (self.code, self.t)


def cast(v, n):
    """the translator's ForceCast/implicit cast: a float1 broadcasts; a wider vector is masked; a narrower one is padded
    with zeros (only where the engine pads: AppendVector-free casts of float1 are broadcasts)"""
    if v.t == n:
        return v.code
    if v.t == 1:
        return '%s(%s)' % (TYPE_NAMES[n], ','.join([v.code] * n)) if n > 1 else v.code
    if isinstance(v.t, int) and v.t > n:
        return '(%s).%s' % (v.code, COMP[:n])
    if isinstance(v.t, int) and v.t < n:
        return '%s(%s, %s)' % (TYPE_NAMES[n], v.code, ', '.join(['0.0'] * (n - v.t)))
    raise TypeError('cast %r to %d' % (v, n))


def arith(a, b):
    if a.t == b.t:
        return a.t
    if a.t == 1:
        return b.t
    if b.t == 1:
        return a.t
    raise TypeError('arithmetic between float%d and float%d' % (a.t, b.t))


def fmt(x):
    r = repr(float(x))
    return r if ('e' in r or '.' in r or 'n' in r) else r + '.0'


class Translator:
    """one permutation of one material: switches {name: bool}; textures {param: (register expression, sampler)}"""
    def __init__(self, switches, textures, params, uv_expr, extra=None, vertex=False):
        self.vertex = vertex         # a vertex shader: textures sampled at mip 0
        self.switches = switches
        self.textures = textures     # param name -> (texture code, sampler code)
        self.params = params         # param name -> code (scalar or float4)
        self.uv_expr = uv_expr       # index -> float2 code
        self.extra = extra or {}     # hooks: e.g. 'TwoSidedSign', 'PixelNormalWS'
        self.lines = []
        self.memo = {}
        self.n = 0
        self.custom_funcs = []
        self.used_switches = set()
        self.used_textures = set()
        self.used_params = set()

    def tmp(self, t, code):
        self.n += 1
        name = 'L%d' % self.n
        self.lines.append('%s %s = %s;' % (TYPE_NAMES[t], name, code))
        return Value(name, t)

    def get(self, lk, scope):
        if lk is None:
            return None
        if isinstance(lk, float):
            return Value(fmt(lk), 1)
        node, out = lk
        key = (id(node), out, scope)
        if key not in self.memo:
            self.memo[key] = self.compile(node, out, scope)
        return self.memo[key]

    def inp(self, node, name, scope, default=None):
        lk = node.inputs.get(name)
        if lk is None:
            if default is None:
                return None
            return Value(fmt(default), 1) if not isinstance(default, Value) else default
        return self.get(lk, scope)

    # scope: a tuple of (function call node id, bound inputs) for material function bodies
    def compile(self, node, out, scope):
        c, p = node.cls, node.props
        if c == 'Constant':
            return Value(fmt(p['R']), 1)
        if c == 'Constant2Vector':
            return Value('float2(%s, %s)' % (fmt(p['R']), fmt(p['G'])), 2)
        if c == 'Constant3Vector':
            v = p['Constant']
            return Value('float3(%s, %s, %s)' % tuple(fmt(x) for x in v[:3]), 3)
        if c == 'Constant4Vector':
            v = p['Constant']
            return Value('float4(%s, %s, %s, %s)' % tuple(fmt(x) for x in v[:4]), 4)
        if c == 'ScalarParameter':
            self.used_params.add(p['ParameterName'])
            return Value(self.params[p['ParameterName']], 1)
        if c == 'VectorParameter':
            self.used_params.add(p['ParameterName'])
            v = Value(self.params[p['ParameterName']], 4)
            return [Value('(%s).xyz' % v.code, 3), Value('(%s).x' % v.code, 1), Value('(%s).y' % v.code, 1),
                    Value('(%s).z' % v.code, 1), Value('(%s).w' % v.code, 1), v][out]
        if c == 'StaticSwitchParameter':
            name = p['ParameterName']
            self.used_switches.add(name)
            on = self.switches.get(name, p.get('DefaultValue', False))
            return self.get(node.inputs.get('A' if on else 'B'), scope)
        if c == 'StaticBool':
            return Value('1.0' if p['Value'] else '0.0', 1)
        if c == 'TextureCoordinate':
            uv = self.uv_expr[p.get('CoordinateIndex', 0)]
            ut, vt = p.get('UTiling', 1.0), p.get('VTiling', 1.0)
            if ut != 1.0 or vt != 1.0:
                return Value('(%s * float2(%s, %s))' % (uv, fmt(ut), fmt(vt)), 2)
            return Value(uv, 2)
        if c in ('TextureObjectParameter', 'TextureObject'):
            name = p.get('ParameterName') or p.get('TextureName')
            self.used_textures.add(name)
            tex, smp = self.textures[name]
            v = Value((tex, smp), TCUBE if p.get('Cube') else T2D)
            v.param = name
            return v
        if c in ('TextureSampleParameter2D', 'TextureSampleParameterCube', 'TextureSample'):
            if c == 'TextureSample' and node.inputs.get('TextureObject') is not None:
                to = self.get(node.inputs['TextureObject'], scope)
                (tex, smp), ttype = to.code, to.t
            else:
                name = p['ParameterName']
                self.used_textures.add(name)
                tex, smp = self.textures[name]
                ttype = TCUBE if c.endswith('Cube') else T2D
            # the sampler: the texture's own, or the material's shared wrap / clamp one (SamplerSource)
            src = (p.get('SamplerSource') or '').split('::')[-1]
            if src in ('SSM_Wrap_WorldGroupSettings', 'SSM_Clamp_WorldGroupSettings'):
                smp = self.extra[src[4:]]
            co = node.inputs.get('Coordinates')
            if co is None:
                uvv = Value(self.uv_expr[p.get('ConstCoordinate', 0)], 2)
            else:
                uvv = self.get(co, scope)
            n = 3 if ttype == TCUBE else 2
            grad = None
            if (p.get('MipValueMode') or '').endswith('TMVM_Derivative'):
                grad = (self.get(node.inputs['CoordinatesDX'], scope), self.get(node.inputs['CoordinatesDY'], scope))
            level = bias = None
            if (p.get('MipValueMode') or '').endswith('TMVM_MipLevel'):
                level = self.inp(node, 'MipValue', scope, p.get('ConstMipValue', 0.0))
            if (p.get('MipValueMode') or '').endswith('TMVM_MipBias'):
                bias = self.inp(node, 'MipValue', scope, p.get('ConstMipValue', 0.0))
            key = ('sample', tex, smp, uvv.code, p.get('SamplerType'), p.get('MipValueMode'), grad and (grad[0].code, grad[1].code),
                   level and level.code, bias and bias.code)
            if key not in self.memo:
                if level is not None:
                    s = '%s.SampleLevel(%s, %s, %s)' % (tex, smp, cast(uvv, n), cast(level, 1))
                elif bias is not None and not self.vertex:
                    s = '%s.SampleBias(%s, %s, %s)' % (tex, smp, cast(uvv, n), cast(bias, 1))
                elif self.vertex:
                    s = '%s.SampleLevel(%s, %s, 0.0)' % (tex, smp, cast(uvv, n))
                elif grad:
                    s = '%s.SampleGrad(%s, %s, %s, %s)' % (tex, smp, cast(uvv, n), cast(grad[0], n), cast(grad[1], n))
                else:
                    s = '%s.Sample(%s, %s)' % (tex, smp, cast(uvv, n))
                st = p.get('SamplerType', 'Color')
                if st == 'Normal':
                    s = 'UnpackNormalMap(%s)' % s
                elif st == 'Alpha':
                    s = 'ProcessMaterialAlphaTextureLookup(%s)' % s
                elif st in ('Grayscale', 'LinearGrayscale'):
                    s = 'ProcessMaterialGreyscaleTextureLookup(%s)' % s
                self.memo[key] = self.tmp(4, s)
            v = self.memo[key]
            return [Value('%s.xyz' % v.code, 3), Value('%s.x' % v.code, 1), Value('%s.y' % v.code, 1),
                    Value('%s.z' % v.code, 1), Value('%s.w' % v.code, 1), v][out]
        if c == 'ComponentMask':
            x = self.get(node.inputs['Input'], scope)
            comps = ''.join(ch for ch, flag in zip('xyzw', [p.get('R'), p.get('G'), p.get('B'), p.get('A')]) if flag)
            if any(COMP.index(ch) >= x.t for ch in comps):
                raise TypeError('%s: mask %s of float%d' % (node.name, comps, x.t))
            if x.t == 1 and comps == 'x':
                return x
            return Value('(%s).%s' % (x.code, comps), len(comps))
        if c == 'Fmod':
            # the engine's Fmod expression: fmod(A, B)
            a = self.inp(node, 'A', scope, 0.0)
            b = self.inp(node, 'B', scope, 1.0)
            t = arith(a, b)
            return self.tmp(t, 'fmod(%s, %s)' % (cast(a, t), cast(b, t)))
        if c in ('Add', 'Subtract', 'Multiply', 'Divide', 'Min', 'Max'):
            a = self.inp(node, 'A', scope, p.get('ConstA', 0.0 if c in ('Add', 'Subtract') else 1.0))
            b = self.inp(node, 'B', scope, p.get('ConstB', 0.0 if c in ('Add', 'Subtract') else 1.0))
            t = arith(a, b)
            op = {'Add': '+', 'Subtract': '-', 'Multiply': '*', 'Divide': '/'}.get(c)
            if op:
                return self.tmp(t, '(%s %s %s)' % (cast(a, t), op, cast(b, t)))
            return self.tmp(t, '%s(%s, %s)' % (c.lower(), cast(a, t), cast(b, t)))
        if c == 'LinearInterpolate':
            a = self.inp(node, 'A', scope, p.get('ConstA', 0.0))
            b = self.inp(node, 'B', scope, p.get('ConstB', 1.0))
            al = self.inp(node, 'Alpha', scope, p.get('ConstAlpha', 0.5))
            t = arith(a, b)
            t = arith(Value('', t), al)
            return self.tmp(t, 'lerp(%s, %s, %s)' % (cast(a, t), cast(b, t), cast(al, t)))
        if c == 'OneMinus':
            x = self.get(node.inputs['Input'], scope)
            return self.tmp(x.t, '(1.0 - %s)' % x.code)
        if c in ('DDX', 'DDY'):
            x = self.get(node.inputs['Value'], scope)
            return self.tmp(x.t, '%s(%s)' % (c.lower(), x.code))
        if c in ('Saturate', 'Abs', 'Floor', 'Ceil', 'Frac', 'Sine', 'Cosine', 'SquareRoot'):
            x = self.get(node.inputs['Input'], scope)
            f = {'Saturate': 'saturate', 'Abs': 'abs', 'Floor': 'floor', 'Ceil': 'ceil', 'Frac': 'frac', 'Sine': 'sin',
                 'Cosine': 'cos', 'SquareRoot': 'sqrt'}[c]
            return self.tmp(x.t, '%s(%s)' % (f, x.code))
        if c == 'Normalize':
            # the engine's Normalize expression: Div(V, SquareRoot(Dot(V, V)))
            x = self.get(node.inputs['VectorInput'], scope)
            return self.tmp(x.t, '(%s / sqrt(dot(%s, %s)))' % (x.code, x.code, x.code))
        if c == 'Transform':
            # a vector from tangent space to world space (TransformTangentVectorToWorld)
            x = self.get(node.inputs['Input'], scope)
            st = (p.get('TransformSourceType', 'TRANSFORMSOURCE_Tangent'), p.get('TransformType', 'TRANSFORM_World'))
            if st == ('TRANSFORMSOURCE_Tangent', 'TRANSFORM_World'):
                return self.tmp(3, 'mul(%s, Parameters.TangentToWorld)' % cast(x, 3))
            if st == ('TRANSFORMSOURCE_World', 'TRANSFORM_Tangent'):
                return self.tmp(3, 'mul(Parameters.TangentToWorld, %s)' % cast(x, 3))
            raise NotImplementedError('transform %s -> %s' % st)
        if c == 'DotProduct':
            a, b = self.get(node.inputs['A'], scope), self.get(node.inputs['B'], scope)
            t = arith(a, b)
            return self.tmp(1, 'dot(%s, %s)' % (cast(a, t), cast(b, t)))
        if c == 'CrossProduct':
            a, b = self.get(node.inputs['A'], scope), self.get(node.inputs['B'], scope)
            return self.tmp(3, 'cross(%s, %s)' % (cast(a, 3), cast(b, 3)))
        if c == 'Power':
            a = self.get(node.inputs['Base'], scope)
            e = self.inp(node, 'Exponent', scope, p.get('ConstExponent', 2.0))
            return self.tmp(a.t, 'ClampedPow(%s, %s)' % (a.code, cast(e, a.t)))
        if c == 'Clamp':
            x = self.get(node.inputs['Input'], scope)
            lo = self.inp(node, 'Min', scope, p.get('MinDefault', 0.0))
            hi = self.inp(node, 'Max', scope, p.get('MaxDefault', 1.0))
            return self.tmp(x.t, 'min(max(%s, %s), %s)' % (x.code, cast(lo, x.t), cast(hi, x.t)))
        if c == 'AppendVector':
            a, b = self.get(node.inputs['A'], scope), self.get(node.inputs['B'], scope)
            t = a.t + b.t
            if t > 4:
                raise TypeError('%s: append float%d and float%d' % (node.name, a.t, b.t))
            return self.tmp(t, '%s(%s, %s)' % (TYPE_NAMES[t], a.code, b.code))
        if c == 'If':
            a = self.get(node.inputs['A'], scope)
            b = self.inp(node, 'B', scope, p.get('ConstB', 0.0))
            gt = self.get(node.inputs['AGreaterThanB'], scope)
            lt = self.get(node.inputs['ALessThanB'], scope)
            eq = self.get(node.inputs.get('AEqualsB'), scope) if node.inputs.get('AEqualsB') is not None else None
            t = max(gt.t, lt.t, eq.t if eq else 1)
            th = fmt(p.get('EqualsThreshold', 0.00001))
            if eq is None:
                return self.tmp(t, '((%s >= %s) ? %s : %s)' % (a.code, b.code, cast(gt, t), cast(lt, t)))
            return self.tmp(t, '((%s >= %s + %s) ? %s : (((%s <= %s - %s)) ? %s : %s))' % (
                a.code, b.code, th, cast(gt, t), a.code, b.code, th, cast(lt, t), cast(eq, t)))
        if c == 'TextureProperty':
            # the texture's size (the game's uniform expression)
            to = self.get(node.inputs['TextureObject'], scope)
            name = getattr(to, 'param', None)
            self.used_params.add('TEXSIZE:%s' % name)
            return Value('(%s).xy' % self.params['TEXSIZE:%s' % name].rsplit('.', 1)[0], 2)
        if c == 'Custom':
            return self.custom(node, out, scope)
        if c == 'MaterialFunctionCall':
            fn = p['Function']
            bound = {}
            for inode in fn.input_nodes:
                nm = inode.props['InputName']
                lk = node.inputs.get(nm)
                bound[nm] = self.get(lk, scope) if lk is not None else None
            sub = scope + ((node.id, tuple(sorted((k, v.code if v else None) for k, v in bound.items()))),)
            self.bindings = getattr(self, 'bindings', {})
            self.bindings[sub] = bound
            name, lk = fn.outputs[out]
            return self.get(lk, sub)
        if c == 'FunctionInput':
            bound = self.bindings[scope][p['InputName']]
            if bound is None:
                pv = p.get('PreviewValue')
                if isinstance(pv, (list, tuple)):
                    n = {'Scalar': 1, 'Vector2': 2, 'Vector3': 3, 'Vector4': 4}[p['InputType']]
                    return Value('%s(%s)' % (TYPE_NAMES[n], ', '.join(fmt(x) for x in list(pv)[:n])), n) if n > 1 else Value(fmt(pv[0]), 1)
                return Value(fmt(pv or 0.0), 1)
            want = {'Scalar': 1, 'Vector2': 2, 'Vector3': 3, 'Vector4': 4}.get(p['InputType'])
            if want and bound.t != want and isinstance(bound.t, int):
                return Value(cast(bound, want), want)
            return bound
        if c == 'PixelNormalWS':
            return Value(self.extra['PixelNormalWS'], 3)
        if c == 'VertexNormalWS':
            return Value(self.extra['VertexNormalWS'], 3)
        if c == 'CameraVectorWS':
            return Value(self.extra['CameraVectorWS'], 3)
        if c == 'ObjectPositionWS':
            return Value(self.extra['ObjectPositionWS'], 3)
        if c == 'WorldPosition':
            return Value(self.extra['WorldPosition'], 3)
        if c == 'TwoSidedSign':
            return Value(self.extra['TwoSidedSign'], 1)
        # the particle's values the vertex factory gives (the local one: its defaults, Color white)
        if c == 'ParticleColor':
            v = 'Parameters.Particle.Color'
            return [Value(v + '.xyz', 3), Value(v + '.x', 1), Value(v + '.y', 1), Value(v + '.z', 1), Value(v + '.w', 1)][out]
        if c == 'DynamicParameter':
            v = 'Parameters.Particle.DynamicParameter'
            return [Value(v + '.x', 1), Value(v + '.y', 1), Value(v + '.z', 1), Value(v + '.w', 1), Value(v + '.xyz', 3)][out]
        if c == 'ParticleSubUVProperties':
            return [Value('Parameters.Particle.SubUVCoords[0].xy', 2), Value('Parameters.Particle.SubUVCoords[1].xy', 2),
                    Value('Parameters.Particle.SubUVLerp', 1)][out]
        if c == 'ParticlePositionWS':
            return Value('(Parameters.Particle.TranslatedWorldPositionAndSize.xyz - %s)' % self.extra['PreViewTranslation'], 3)
        if c == 'CameraPositionWS':
            return Value(self.extra['CameraPositionWS'], 3)
        if c == 'PixelDepth':
            return Value(self.extra['PixelDepth'], 1)
        if c == 'Time':
            return Value(self.extra['Time'], 1)
        if c == 'ExternalHook':
            # an engine value the graph reads (the editor graph uses the node named in the spec)
            return Value(self.extra[p['Hook']], p.get('Type', 1))
        raise NotImplementedError('translate %s' % c)

    def custom(self, node, out, scope):
        p = node.props
        args, params = [], []
        for nm in p['InputNames']:
            v = self.get(node.inputs.get(nm), scope)
            if v is None:
                v = Value('0.0', 1)
            if v.t in (T2D, TCUBE, T3D):
                tex, smp = v.code
                params += ['%s %s' % (v.t, nm), 'SamplerState %sSampler' % nm]
                args += [tex, smp]
            else:
                params.append('%s %s' % (TYPE_NAMES[v.t], nm))
                args.append(v.code)
        outs = p.get('AdditionalOutputs', [])
        k = len(self.custom_funcs)
        fname = 'CustomExpression%d' % k
        for on, ot in outs:
            params.append('inout %s %s' % (TYPE_NAMES[ot], on))
        rt = p['OutputType']
        self.custom_funcs.append('%s %s(%s)\n{\n%s\n}\n' % (TYPE_NAMES[rt], fname, ', '.join(['FMaterialPixelParameters Parameters'] + params), p['Code']))
        outvals = []
        for on, ot in outs:
            outvals.append(self.tmp(ot, '(%s)0' % TYPE_NAMES[ot]))
        call = self.tmp(rt, '%s(%s)' % (fname, ', '.join(['Parameters'] + args + [o.code for o in outvals])))
        allv = [call] + outvals
        return allv[out]


def walk(material):
    """every node the material's pins reach (through both inputs of every switch, and inside each function called)"""
    seen, out = set(), []

    def visit(lk):
        if lk is None or isinstance(lk, float):
            return
        node = lk[0]
        if node.id in seen:
            return
        seen.add(node.id)
        out.append(node)
        for v in node.inputs.values():
            visit(v)
        if node.cls == 'MaterialFunctionCall':
            for _, olk in node.props['Function'].outputs:
                visit(olk)
    for lk in material.pins.values():
        visit(lk)
    return out


def definitions(material, switches):
    """the defines the game's static switches with a Definition make: on (1) where the switch is on in the permutation"""
    d = {}
    for n in walk(material):
        if n.cls == 'StaticSwitchParameter' and n.props.get('Definition'):
            on = switches.get(n.props['ParameterName'], n.props.get('DefaultValue', False))
            d[n.props['Definition']] = d.get(n.props['Definition'], False) or bool(on)
    return d


def translate(material, switches, textures, params, uv_expr, pins, extra=None, vertex=False, after_normal=None):
    """HLSL lines computing the pins (name -> (type, default)) of one permutation; returns (lines, results, translator).
    The normal first (as the engine computes it before the other inputs, which may read the pixel normal): after_normal,
    a line with {normal} for the normal pin's code, is emitted right after it"""
    tr = Translator(switches, textures, params, uv_expr, extra, vertex)
    res = {}
    order = sorted(pins, key=lambda k: k != 'Normal')
    for pin in order:
        t, default = pins[pin]
        if pin != 'Normal' and after_normal and 'Normal' in res and not getattr(tr, '_after_normal_done', False):
            tr.lines.append(after_normal.format(normal=res['Normal'].code))
            tr._after_normal_done = True
        lk = material.pins.get(pin)
        if lk is None:
            res[pin] = Value(default, t)
            continue
        v = tr.get(lk, ())
        res[pin] = Value(cast(v, t), t)
    return tr.lines, res, tr
