"""Remake material graphs: one description per master (and material function) that generates
  - the checker's C++ (per static permutation: the switches resolved as UE's material translator resolves them), and
  - the editor's node graph (a spec the UE Python builder turns into material expressions).
Nodes follow UE 4 material expression semantics (component counts, scalar broadcasting, ComponentMask, AppendVector,
StaticSwitchParameter, TextureSampleParameter2D, MaterialFunctionCall)."""
import itertools

_ids = itertools.count()


class Node:
    def __init__(self, cls, inputs=None, **props):
        self.cls = cls                 # UE expression class without "MaterialExpression"
        self.inputs = inputs or {}     # input name -> Out
        self.props = props
        self.id = next(_ids)
        self.name = props.pop('name', None)   # the original expression name, when known (e.g. "ComponentMask_2")

    def __getitem__(self, k):
        return Out(self, k)

    def out(self, k=0):
        return Out(self, k)

    def __repr__(self):
        return '%s#%d%s' % (self.cls, self.id, (':' + self.name) if self.name else '')


class Out:
    """an output of a node: an index (or name) and an optional component mask (r/g/b/a)"""
    def __init__(self, node, index=0, mask=None):
        self.node, self.index, self.mask = node, index, mask

    @property
    def r(self): return Out(self.node, self.index, 'r')

    @property
    def g(self): return Out(self.node, self.index, 'g')

    @property
    def b(self): return Out(self.node, self.index, 'b')

    @property
    def a(self): return Out(self.node, self.index, 'a')

    @property
    def rgb(self): return Out(self.node, self.index, 'rgb')

    def __repr__(self):
        return '%r[%s]%s' % (self.node, self.index, ('.' + self.mask) if self.mask else '')


def _o(x):
    if isinstance(x, Out):
        return x
    if isinstance(x, Node):
        return Out(x, 0)
    if isinstance(x, (int, float)):
        return Out(Node('Constant', R=float(x)), 0)
    raise TypeError(x)


# ---- constructors (UE expression classes)
def Constant(v, name=None): return Node('Constant', R=float(v), name=name)
def Constant2(x, y, name=None): return Node('Constant2Vector', R=float(x), G=float(y), name=name)
def Constant3(x, y, z, name=None): return Node('Constant3Vector', Constant=(float(x), float(y), float(z), 0.0), name=name)
def Constant4(x, y, z, w, name=None): return Node('Constant4Vector', Constant=(float(x), float(y), float(z), float(w)), name=name)
def TexCoord(index, name=None): return Node('TextureCoordinate', CoordinateIndex=index, name=name)
def Scalar(param, default=0.0, group=None, name=None): return Node('ScalarParameter', ParameterName=param, DefaultValue=float(default), Group=group, name=name)
def Vector(param, default=(0, 0, 0, 0), group=None, name=None): return Node('VectorParameter', ParameterName=param, DefaultValue=tuple(default), Group=group, name=name)
def TexObj(param, texture, group=None, sampler='LinearColor', name=None): return Node('TextureObjectParameter', ParameterName=param, Texture=texture, Group=group, SamplerType=sampler, name=name)


def TexSample(param, texture, uv, group=None, sampler='LinearColor', cube=False, name=None):
    return Node('TextureSampleParameterCube' if cube else 'TextureSampleParameter2D', {'Coordinates': _o(uv)}, ParameterName=param,
                Texture=texture, Group=group, SamplerType=sampler, name=name)


def Switch(param, a, b, default=False, group='Static', name=None):
    return Node('StaticSwitchParameter', {'A': _o(a), 'B': _o(b)}, ParameterName=param, DefaultValue=default, Group=group, name=name)


def Mask(x, comps, name=None): return Node('ComponentMask', {'Input': _o(x)}, R='r' in comps, G='g' in comps, B='b' in comps, A='a' in comps, name=name)
def Mul(a, b, name=None): return Node('Multiply', {'A': _o(a), 'B': _o(b)}, name=name)
def Add(a, b, name=None): return Node('Add', {'A': _o(a), 'B': _o(b)}, name=name)
def Sub(a, b, name=None): return Node('Subtract', {'A': _o(a), 'B': _o(b)}, name=name)
def Div(a, b, name=None): return Node('Divide', {'A': _o(a), 'B': _o(b)}, name=name)
def OneMinus(x, name=None): return Node('OneMinus', {'Input': _o(x)}, name=name)
def Append(a, b, name=None): return Node('AppendVector', {'A': _o(a), 'B': _o(b)}, name=name)
def Lerp(a, b, t, name=None): return Node('LinearInterpolate', {'A': _o(a), 'B': _o(b), 'Alpha': _o(t)}, name=name)
def Clamp(x, lo, hi, name=None): return Node('Clamp', {'Input': _o(x), 'Min': _o(lo), 'Max': _o(hi)}, name=name)
def Saturate(x, name=None): return Node('Saturate', {'Input': _o(x)}, name=name)
def Dot(a, b, name=None): return Node('DotProduct', {'A': _o(a), 'B': _o(b)}, name=name)
def Normalize(x, name=None): return Node('Normalize', {'VectorInput': _o(x)}, name=name)
def Abs(x, name=None): return Node('Abs', {'Input': _o(x)}, name=name)
def Sqrt(x, name=None): return Node('SquareRoot', {'Input': _o(x)}, name=name)
def Max(a, b, name=None): return Node('Max', {'A': _o(a), 'B': _o(b)}, name=name)
def Min(a, b, name=None): return Node('Min', {'A': _o(a), 'B': _o(b)}, name=name)
def Power(base, exp, name=None): return Node('Power', {'Base': _o(base), 'Exponent': _o(exp)}, name=name)
def Frac(x, name=None): return Node('Frac', {'Input': _o(x)}, name=name)
def Floor(x, name=None): return Node('Floor', {'Input': _o(x)}, name=name)
def Cross(a, b, name=None): return Node('CrossProduct', {'A': _o(a), 'B': _o(b)}, name=name)


def Custom(code, inputs, out=3, description='', name=None, outputs=None):
    """a Custom node: inputs {name: x}; out = the main output's component count; outputs: [(name, count)] more outputs"""
    return Node('Custom', {k: _o(v) for k, v in inputs.items()}, Code=code, OutputType=out, Description=description,
                AdditionalOutputs=outputs or [], name=name)


class Function:
    """a material function: FunctionInput nodes (by name, type), FunctionOutput nodes (by name)"""
    def __init__(self, name, inputs, outputs_fn, description=''):
        self.name = name
        self.input_specs = inputs        # [(name, components)]
        self.inputs = {n: Node('FunctionInput', InputName=n, InputType=c, SortPriority=i) for i, (n, c) in enumerate(inputs)}
        self.outputs = outputs_fn(self.inputs)   # {name: Out}
        self.description = description


def Call(fn, inputs, name=None):
    return Node('MaterialFunctionCall', {k: _o(v) for k, v in inputs.items()}, Function=fn, name=name)


class Material:
    def __init__(self, name, pins, props=None):
        self.name = name
        self.pins = {k: _o(v) for k, v in pins.items() if v is not None}   # BaseColor, Metallic, ... -> Out
        self.props = props or {}
