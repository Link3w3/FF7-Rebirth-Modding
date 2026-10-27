"""Crisis Core Reunion (UE 4.27) character material permutations as End editor (UE 4.26) material Custom nodes.

Each permutation's base pass pixel shader (TBasePassPSFNoLightMapPolicy on the GPU skin vertex factory: no light map,
no sky light, so its scene colour is the emissive alone), and for the masked ones the depth pass pixel shader that does
their opacity mask clip, lifted by dxbc2hlsl.py (lift_check.py checks every lift against the original), inside a
struct that the editor feeds:
  * the interpolants from the material's pixel parameters (the UVs from TextureCoordinate inputs; the facing worked
    out from the editor's two-sided sign);
  * the View and Primitive slots the shader reads from the editor's own (the same engine line: 4.26's layouts, which
    4.27's match), the debug overrides as identity, the pre-exposure as 1 (the editor's base pass applies its own),
    no subsurface checkerboard;
  * the Material uniform buffer rebuilt from the material's parameters through the game's own uniform expressions;
  * the material parameter collection (MPC_cm_VisCtrl, the game's global character look controls) at its defaults;
  * the textures from the material's texture parameters (and the fixed textures of its graph), by the game's names;
  * the eye adaptation from the editor's EyeAdaptation expression, the subsurface profiles' dual specular as none
    (the editor's own profile does that).
What the shader writes to the GBuffer (emissive; normal; metallic, specular, roughness, shading model; base colour;
custom data) is decoded into the node's outputs for the material's pins.

    cc_ue.py <permutation> [...]       writes gen427/<permutation>.json (the nodes: code, inputs, outputs, notes)"""
import json
import os
import re
import sys

sys.path[:0] = [os.path.dirname(os.path.abspath(__file__)), '/work/remake_mat/tools']
import dxbc2hlsl
import ublayout

ROOT = '/work/ccmat'
DIS = os.path.join(ROOT, 'dis427')
GEN = os.path.join(ROOT, 'gen427')
MPC_JSON = os.path.join(ROOT, 'mpc', 'MPC_cm_VisCtrl.json')
BASE_PS = 'TBasePassPSFNoLightMapPolicy'
DEPTH_PS = '7557e6252b46eb81'          # (its FHashedName: the depth pass pixel shader, the masked ones' clip)

VIEW_SLOTS = ublayout.slots(ublayout.view())
PRIM_SLOTS = ublayout.slots(ublayout.generic('PrimitiveUniformShaderParameters.h', 'FPrimitiveUniformShaderParameters'))

# View members the lift gets as constants (the rest: the editor's own View.<member>)
VIEW_CONST = {
    'PreExposure': '1.0', 'OneOverPreExposure': '1.0', 'NumSceneColorMSAASamples': '1.0',
    'DiffuseOverrideParameter': ['0.0', '0.0', '0.0', '1.0'], 'SpecularOverrideParameter': ['0.0', '0.0', '0.0', '1.0'],
    'NormalOverrideParameter': ['0.0', '0.0', '0.0', '1.0'], 'RoughnessOverrideParameter': ['0.0', '1.0'],
    'OutOfBoundsMask': '0.0', 'UnlitViewmodeMask': '0.0', 'DebugViewModeMask': '0.0',
    'RenderingReflectionCaptureMask': '0.0', 'RealTimeReflectionCapture': '0.0',
    'IndirectLightingColorScale': ['1.0', '1.0', '1.0'],
    'bCheckerboardSubsurfaceProfileRendering': '0.0', 'bSubsurfacePostprocessEnabled': '1.0',
    'TemporalAAParams': ['0.0', '1.0', '0.0', '0.0'],
}
VIEW_UINT = {'FrameNumber', 'StateFrameIndexMod8', 'StateFrameIndex', 'DebugViewModeMask'}


def ident(text):
    return re.sub(r'[^A-Za-z0-9_]', '_', text)


def member_parts(name):
    """'SVPositionToTranslatedWorld[2].y' -> ('SVPositionToTranslatedWorld', '[2]', 'y')"""
    m = re.match(r'^(\w+)((?:\[\d+\])?)(?:\.([xyzw]))?$', name)
    return m.group(1), m.group(2), m.group(3)


def view_lane(slot, comp):
    """the editor's expression (as uint bits) for the game's View[slot].comp"""
    name = VIEW_SLOTS.get((slot, comp))
    if name is None:
        return '0u', None
    base, idx, sub = member_parts(name)
    if base in VIEW_CONST:
        c = VIEW_CONST[base]
        if isinstance(c, list):
            k = 'xyzw'.index(sub) if sub else 0
            v = c[k] if k < len(c) else '0.0'
        else:
            v = c
        return 'asuint(%s)' % v, None
    ref = 'View.%s%s%s' % (base, idx, ('.' + sub) if sub else '')
    if base in VIEW_UINT:
        return 'uint(%s)' % ref, base
    return 'asuint(%s)' % ref, base


def prim_lane(slot, comp):
    name = PRIM_SLOTS.get((slot, comp))
    if name is None:
        return '0u', None
    base, idx, sub = member_parts(name)
    return 'asuint(EMS_Prim.%s%s%s)' % (base, idx, ('.' + sub) if sub else ''), base


class Inputs:
    """the node's inputs: UVs, the game's parameters and textures (by their own names), engine values"""
    def __init__(self):
        self.items = []
        self.names = set()

    def add(self, name, kind, **extra):
        if name not in self.names:
            self.names.add(name)
            self.items.append(dict(name=name, kind=kind, **extra))
        return name


class Uniforms:
    """the game's uniform expressions (cc427's preshader trees) as HLSL float4s over the node's parameter inputs"""
    def __init__(self, inputs, textures):
        self.inputs = inputs
        self.textures = textures      # texture index (the material's referenced textures) -> input name
        self.pre = []

    def e(self, x):
        op = x['op']
        if op == 'const':
            return 'float4(%s)' % ', '.join(repr(float(c)) for c in x['value'])
        if op == 'vparam':
            if x['name'] == 'SelectionColor':
                return 'float4(0.0, 0.0, 0.0, 0.0)'     # (the editor draws its own selection)
            return self.inputs.add('V_' + ident(x['name']), 'vector', param=x['name'], default=x['default'])
        if op == 'sparam':
            n = self.inputs.add('S_' + ident(x['name']), 'scalar', param=x['name'], default=x['default'])
            return '%s.xxxx' % n if False else 'float4(%s, %s, %s, %s)' % (n, n, n, n)
        if op == 'binary':
            a, b, f = self.e(x['a']), self.e(x['b']), x['fn']
            if f == 'Div':
                return 'EMS_Div(%s, %s)' % (a, b)
            if f in ('Add', 'Sub', 'Mul'):
                return '(%s %s %s)' % (a, {'Add': '+', 'Sub': '-', 'Mul': '*'}[f], b)
            return '%s(%s, %s)' % ({'Fmod': 'EMS_Fmod', 'Min': 'min', 'Max': 'max', 'Atan2': 'atan2'}[f], a, b)
        if op == 'unary':
            f = x['fn']
            fn = {'Sin': 'sin', 'Cos': 'cos', 'Tan': 'tan', 'Asin': 'asin', 'Acos': 'acos', 'Atan': 'atan', 'Sqrt': 'sqrt',
                  'Saturate': 'saturate', 'Abs': 'abs', 'Floor': 'floor', 'Ceil': 'ceil', 'Round': 'EMS_Round', 'Trunc': 'trunc',
                  'Sign': 'sign', 'Frac': 'EMS_Frac', 'Fractional': 'frac', 'Log2': 'log2', 'Log10': 'EMS_Log10', 'Length': None}[f]
            if fn is None:
                raise NotImplementedError('preshader Length')
            return '%s(%s)' % (fn, self.e(x['x']))
        if op == 'clamp':
            return 'clamp(%s, %s, %s)' % (self.e(x['x']), self.e(x['lo']), self.e(x['hi']))
        if op == 'swizzle':
            a = self.e(x['x'])
            idx, n = x['index'], x['n']
            if n == 1:
                return '(%s).%s' % (a, 'xyzw'[idx[0]] * 4)
            comps = ['(%s).%s' % (a, 'xyzw'[i]) for i in idx[:n]] + ['0.0'] * (4 - n)
            return 'float4(%s)' % ', '.join(comps)
        if op == 'append':
            a, b, na = self.e(x['a']), self.e(x['b']), x['na']
            comps = ['(%s).%s' % (a, 'xyzw'[i]) for i in range(na)] + ['(%s).%s' % (b, 'xyzw'[i]) for i in range(4 - na)]
            return 'float4(%s)' % ', '.join(comps)
        if op == 'dot':
            k = {1: 1, 2: 2, 3: 3, 4: 4}.get(x['type'], 4)
            a, b = self.e(x['a']), self.e(x['b'])
            s = 'xyzw'[:k]
            return 'dot((%s).%s, (%s).%s).xxxx' % (a, s, b, s)
        if op in ('texturesize', 'texelsize'):
            t = self.textures.get(x['texture_index'])
            if t is None:
                raise ValueError('the texture size of a texture the node does not have (index %d)' % x['texture_index'])
            k = len(self.pre)
            self.pre.append('uint EMS_tw%d, EMS_th%d; %s.GetDimensions(EMS_tw%d, EMS_th%d);' % (k, k, t, k, k))
            if op == 'texturesize':
                return 'float4(float(EMS_tw%d), float(EMS_th%d), 0.0, 0.0)' % (k, k)
            return 'float4(1.0 / float(EMS_tw%d), 1.0 / float(EMS_th%d), 0.0, 0.0)' % (k, k)
        raise NotImplementedError('uniform expression %s' % op)


# preshader semantics (MaterialUniformExpressions.cpp): divide by a safe divisor, the engine's fmod, round, frac
PRESHADER_FUNCS = '''
float4 EMS_Div(float4 a, float4 b) { float4 s = (abs(b) < 1e-8) ? ((b < 0.0) ? -1e-8 : 1e-8) : b; return a / s; }
float4 EMS_Fmod(float4 a, float4 b) { return (abs(b) < 1e-8) ? 0.0 : (a - b * trunc(a / b)); }
float4 EMS_Round(float4 a) { return floor(a + 0.5); }
float4 EMS_Frac(float4 a) { return a - floor(a); }
float4 EMS_Log10(float4 a) { return log(a) * 0.43429448190325176; }
'''

SEMANTIC_V = {
    ('TEXCOORD', '10'): 'float4(Parameters.TangentToWorld[0], 0.0)',
    ('TEXCOORD', '11'): 'float4(Parameters.TangentToWorld[2], EMS_TangentSign)',
    ('TEXCOORD', '0'): 'float4(UV0, UV1)',
    ('TEXCOORD', '1'): 'float4(UV2, UV3)',
    ('COLOR', '0'): 'Parameters.VertexColor',
    ('COLOR', '1'): 'Parameters.VertexColor',
}


class Env(dxbc2hlsl.Env):
    def __init__(self, texnames):
        self.texnames = texnames

    def v(self, reg):
        return 'v%d' % reg

    def cb(self, buf, index):
        if not re.match(r'^\d+$', str(index)):
            raise NotImplementedError('a register-indexed constant buffer read (cb%d[%s])' % (buf, index))
        return 'cb%d_%s' % (buf, index)

    def tex(self, reg):
        return self.texnames.get(reg, 't%d' % reg)

    def samp(self, sreg, treg):
        return 's%d' % sreg


def load_mpc():
    if os.path.exists(MPC_JSON):
        return json.load(open(MPC_JSON))
    return None


def shader_key(entry, want_type):
    for k, s in sorted(entry['shaders'].items()):
        if s['freq'] == 'ps' and (want_type in s['types'] or any(t.startswith(want_type) for t in s['types'])):
            if want_type == BASE_PS and s['types'][0] != BASE_PS and BASE_PS not in s['types']:
                continue
            return k
    return None


def texture_lists(uset):
    """the material uniform buffer's resources in order: [(kind, texture parameter info)], kind 2d / cube / ..."""
    order = []
    for kind, key in (('2d', 'Standard2D'), ('cube', 'Cube'), ('2darray', 'Array2D'), ('volume', 'Volume')):
        for t in uset['textures'][key]:
            order.append((kind, t))
    return order


def lift_node(perm, key, kind, inputs, notes, entry):
    uset = entry['uniform']
    asm = open(entry['shaders'][key]['asm'], encoding='latin-1').read()
    bindings = json.load(open(os.path.join(DIS, perm, 'bindings.json')))[key]
    cbn = bindings['cb']
    texlist = texture_lists(uset)
    ntex = len(texlist)
    referenced = entry.get('referenced_textures') or []

    # textures: the material's (parameters by name, fixed ones by their texture), the engine's
    texnames = {}
    run_params, run_args, special = [], [], {}
    tex_input_of_index = {}
    for t, (ub, res) in sorted(((int(k), v) for k, v in bindings['t'].items())):
        if ub == 'Material':
            if res % 2 or res // 2 >= ntex:
                raise ValueError('%s: t%d is the material resource %d' % (key, t, res))
            tk, info = texlist[res // 2]
            if info['name']:
                name = inputs.add('T_' + ident(info['name']), 'texturecube' if tk == 'cube' else 'texture2d', param=info['name'],
                                  texture_index=info['texture_index'],
                                  default=referenced[info['texture_index']] if info['texture_index'] < len(referenced) else None)
            else:
                tex = referenced[info['texture_index']] if info['texture_index'] < len(referenced) else None
                name = inputs.add('TF_%d' % info['texture_index'], 'fixed_' + ('texturecube' if tk == 'cube' else 'texture2d'),
                                  texture=tex, texture_index=info['texture_index'])
            tex_input_of_index[info['texture_index']] = name
            hl = 'TextureCube' if tk == 'cube' else 'Texture2D'
            run_params.append('%s t%d' % (hl, t))
            run_args.append(name)
        elif ub == 'View' and res == 2:
            run_params.append('Texture3D<uint4> t%d' % t)
            run_args.append('View.VolumetricLightmapIndirectionTexture')
        elif ub == 'View' and res == 11:
            run_params.append('Texture3D t%d' % t)
            run_args.append('View.DirectionalLightShadowingBrickTexture')
        elif ub == 'OpaqueBasePass' and res == 51:
            texnames[t] = 'EMS_EyeAdaptationTex'          # its texel (0, 0).x: the exposure
            special['eye'] = True
            inputs.add('EMS_Exposure', 'eye_adaptation')
        elif ub == 'OpaqueBasePass' and res == 34:
            texnames[t] = 'EMS_SSProfilesTex'             # the profiles' dual specular: none (the editor's profile does it)
            special['ssp'] = True
        else:
            raise ValueError('%s: t%d is %s resource %d' % (key, t, ub, res))
    samp_args = {}
    for s, (ub, res) in sorted(((int(k), v) for k, v in bindings['s'].items())):
        if ub == 'Material':
            if res % 2 == 1 and res // 2 < ntex:
                tk, info = texlist[res // 2]
                idx = info['texture_index']
                if idx in tex_input_of_index:
                    samp_args[s] = tex_input_of_index[idx] + 'Sampler'
                else:
                    tname = ('T_' + ident(info['name'])) if info['name'] else 'TF_%d' % idx
                    if info['name']:
                        inputs.add(tname, 'texture2d', param=info['name'], texture_index=idx,
                                   default=referenced[idx] if idx < len(referenced) else None)
                    else:
                        inputs.add(tname, 'fixed_texture2d', texture=referenced[idx] if idx < len(referenced) else None, texture_index=idx)
                    samp_args[s] = tname + 'Sampler'
            else:
                extra = res - 2 * ntex
                samp_args[s] = 'View.MaterialTextureBilinearWrapedSampler' if extra == 0 else 'View.MaterialTextureBilinearClampedSampler'
                notes.append('%s: s%d is the material\'s %s sampler (the editor\'s shared one here)' % (
                    key, s, 'Wrap_WorldGroupSettings' if extra == 0 else 'Clamp_WorldGroupSettings'))
        elif ub == 'View' and res == 0:
            samp_args[s] = 'View.MaterialTextureBilinearWrapedSampler'
        elif ub == 'View' and res == 1:
            samp_args[s] = 'View.MaterialTextureBilinearClampedSampler'
        elif ub == 'View' and res == 43:
            samp_args[s] = 'View.SharedBilinearClampedSampler'
        else:
            raise ValueError('%s: s%d is %s resource %d' % (key, s, ub, res))

    env = Env(texnames)
    L = dxbc2hlsl.Lifter(asm, env)
    body = L.body_lines()
    decls = L.decls()
    if L.dyn_cb:
        raise NotImplementedError('%s: register-indexed constant buffer reads %s' % (key, sorted(L.dyn_cb)))
    for s in sorted(L.samplers):
        if s not in samp_args:
            raise ValueError('%s: s%d is not bound' % (key, s))
        run_params.append('SamplerState s%d' % s)
        run_args.append(samp_args[s])
    # the textures the body reads that are not Run's parameters (the engine stand-ins) need no parameter
    unis = Uniforms(inputs, tex_input_of_index)

    # interpolants
    vset = []
    uses_uv = set()
    for sem, idx, mask, reg, sysv, fmt, used in L.input_sig:
        reg = int(reg)
        if sysv == 'POS':
            vset.append('E.v%d = asuint(Parameters.SvPosition);' % reg)
        elif sysv == 'FFACE':
            vset.append('E.v%d = uint4(EMS_FrontFace ? 0xffffffffu : 0u, 0u, 0u, 0u);' % reg)
        else:
            src = SEMANTIC_V.get((sem, idx))
            if src is None:
                if used:
                    notes.append('%s: interpolant %s%s (%s used) is not mapped (0)' % (key, sem, idx, used))
                src = 'float4(0.0, 0.0, 0.0, 0.0)'
            for u in re.findall(r'\bUV(\d)\b', src):
                uses_uv.add(int(u))
            vset.append('E.v%d = asuint(%s);' % (reg, src))
    for u in sorted(uses_uv):
        inputs.add('UV%d' % u, 'uv', index=u)

    # constant buffer slots
    mpc = load_mpc()
    cbset = []
    material_rows = None
    view_members, prim_members = set(), set()
    uses_prim = False
    for (buf, index) in sorted(L.cb_reads):
        bname = cbn[buf] if buf < len(cbn) else ''
        lanes = None
        if bname == 'View':
            lanes = []
            for c in range(4):
                e, m = view_lane(index, c)
                lanes.append(e)
                if m:
                    view_members.add(m)
        elif bname == 'Primitive':
            uses_prim = True
            lanes = []
            for c in range(4):
                e, m = prim_lane(index, c)
                lanes.append(e)
                if m:
                    prim_members.add(m)
        elif bname == 'Material':
            if material_rows is None:
                vec = [unis.e(x) for x in uset['vector_expressions']]
                sca = ['(%s).x' % unis.e(x) for x in uset['scalar_expressions']]
                material_rows = list(vec)
                for j in range(0, len(sca), 4):
                    part = (sca[j:j + 4] + ['0.0'] * 4)[:4]
                    material_rows.append('float4(%s)' % ', '.join(part))
            if index >= len(material_rows):
                notes.append('%s: Material[%d] is past the uniform buffer\'s %d rows (0)' % (key, index, len(material_rows)))
                cbset.append('E.cb%d_%d = uint4(0u, 0u, 0u, 0u);' % (buf, index))
            else:
                cbset.append('E.cb%d_%d = asuint(%s);' % (buf, index, material_rows[index]))
            continue
        elif bname == 'MaterialCollection0':
            if mpc is None:
                row = [0.0, 0.0, 1.0, 1.0] if index in (6, 8) else [1.0, 1.0, 1.0, 1.0] if index in (0,) else [0.0, 0.0, 0.0, 0.0]
                if 'MPC placeholder' not in ' '.join(notes):
                    notes.append('MPC placeholder: MPC_cm_VisCtrl\'s defaults are not in yet (%s)' % MPC_JSON)
            else:
                rows = mpc['rows']
                row = rows[index] if index < len(rows) else [0.0, 0.0, 0.0, 0.0]
            cbset.append('E.cb%d_%d = asuint(float4(%s));' % (buf, index, ', '.join(repr(float(v)) for v in row)))
            continue
        else:
            notes.append('%s: %s[%d] is not mapped (0)' % (key, bname or 'cb%d' % buf, index))
            lanes = ['0u'] * 4
        cbset.append('E.cb%d_%d = uint4(%s);' % (buf, index, ', '.join(lanes)))

    nouts = [int(r[3]) for r in L.output_sig]
    members = ['uint4 v%d;' % int(r[3]) for r in L.input_sig]
    members += ['uint4 cb%d_%d;' % (buf, index) for (buf, index) in sorted(L.cb_reads)]
    members += ['float4 o%d;' % o for o in nouts]
    members.append('bool Discarded;')
    if special.get('eye'):
        members.append('float EyeAdaptation;')
    sid = ident(perm)
    lines = ['// Crisis Core Reunion %s: the game\'s %s, lifted instruction by instruction (checked against it), fed by the editor.'
             % (perm, 'base pass pixel shader' if kind == 'base' else 'depth pass pixel shader (its opacity mask clip)')]
    lines.append('#if PIXELSHADER')
    lines.append('struct EMS_%s_%s' % (kind, sid))
    lines.append('{')
    lines.extend('    ' + m for m in members)
    if L.uses_bitfield:
        lines.extend('    ' + b for b in dxbc2hlsl.BITFIELD.strip().split('\n'))
    if special.get('eye'):
        lines.append('    struct FEyeTex { float Value; float4 Load(int3 p) { return float4(Value, Value, Value, Value); } };')
    if special.get('ssp'):
        lines.append('    struct FSSPTex { float4 Load(int3 p) { return float4(0.0, 0.0, 0.0, 0.5); } };')
    lines.append('    void Run(%s)' % ', '.join(run_params))
    lines.append('    {')
    if special.get('eye'):
        lines.append('        FEyeTex EMS_EyeAdaptationTex; EMS_EyeAdaptationTex.Value = EyeAdaptation;')
    if special.get('ssp'):
        lines.append('        FSSPTex EMS_SSProfilesTex;')
    lines.extend('        ' + d for d in decls)
    for b in body:
        b = b.replace('discard;', 'Discarded = true;')
        lines.append('    ' + b)
    lines.append('    }')
    lines.append('};')
    if uses_prim:
        lines.append('FPrimitiveSceneData EMS_Prim = GetPrimitiveData(Parameters.PrimitiveId);')
    lines.append('float EMS_TangentSign = dot(cross(Parameters.TangentToWorld[2], Parameters.TangentToWorld[0]), Parameters.TangentToWorld[1]) < 0.0 ? -1.0 : 1.0;')
    if any(r[4] == 'FFACE' for r in L.input_sig):
        lines.append('bool EMS_FrontFace = Parameters.TwoSidedSign * View.CullingSign * GetPrimitiveData(Parameters.PrimitiveId).InvNonUniformScaleAndDeterminantSign.w > 0.0;')
    lines.extend(unis.pre)
    lines.append('EMS_%s_%s E;' % (kind, sid))
    lines.extend(vset)
    lines.extend(cbset)
    lines.extend('E.o%d = float4(0.0, 0.0, 0.0, 0.0);' % o for o in nouts)
    lines.append('E.Discarded = false;')
    if special.get('eye'):
        lines.append('E.EyeAdaptation = EMS_Exposure;')
    lines.append('E.Run(%s);' % ', '.join(run_args))
    if kind == 'base':
        outs = [('EMS_Metallic', 1, 'E.o2.x'), ('EMS_Specular', 1, 'E.o2.y'), ('EMS_Roughness', 1, 'E.o2.z'),
                ('EMS_Normal', 3, 'normalize(E.o1.xyz * 2.0 - 1.0)'), ('EMS_Emissive', 3, 'E.o0.xyz'),
                ('EMS_ShadingModel', 1, 'float(uint(E.o2.w * 255.0 + 0.5) & 15u)'),
                ('EMS_CustomData', 4, 'E.o4' if 4 in nouts else 'float4(0.0, 0.0, 0.0, 0.0)')]
        for n, size, ex in outs:
            lines.append('%s = %s;' % (n, ex))
        lines.append('return E.o3.xyz;')
        lines.append('#else')
        for n, size, ex in outs:
            lines.append('%s = %s;' % (n, '0.0' if size == 1 else 'float%d(%s)' % (size, ', '.join(['0.0'] * size))))
        lines.append('return float3(0.5, 0.5, 0.5);')
        outputs = [{'name': n, 'size': size} for n, size, ex in outs]
        main = 3
    else:
        lines.append('return E.Discarded ? 0.0 : 1.0;')
        lines.append('#else')
        lines.append('return 1.0;')
        outputs = []
        main = 1
    lines.append('#endif')
    code = '\n'.join(lines)
    return {'code': code, 'outputs': outputs, 'main_size': main, 'instructions': len(body), 'textures': run_args,
            'discards': L.discards, 'view_members': sorted(view_members), 'primitive_members': sorted(prim_members),
            'preshader_funcs': PRESHADER_FUNCS}


def build(perm):
    index = json.load(open(os.path.join(DIS, 'index.json')))
    entry = index[perm]
    notes = []
    base_key = shader_key(entry, BASE_PS)
    base_inputs = Inputs()
    base = lift_node(perm, base_key, 'base', base_inputs, notes, entry)
    base['inputs'] = base_inputs.items
    cov = None
    dkey = shader_key(entry, DEPTH_PS)
    if dkey:
        cov_inputs = Inputs()
        cov = lift_node(perm, dkey, 'coverage', cov_inputs, notes, entry)
        cov['inputs'] = cov_inputs.items
        if not cov['discards']:
            notes.append('%s: its depth pass shader has no clip' % perm)
    return {'name': perm, 'map': entry['map'], 'base': base, 'coverage': cov, 'notes': notes, 'base_shader': base_key,
            'coverage_shader': dkey}


def main():
    os.makedirs(GEN, exist_ok=True)
    for perm in sys.argv[1:]:
        r = build(perm)
        json.dump(r, open(os.path.join(GEN, perm + '.json'), 'w'), indent=1)
        print('%-40s base %d instr, %d inputs%s%s' % (perm, r['base']['instructions'], len(r['base']['inputs']),
              ', coverage %d instr' % r['coverage']['instructions'] if r['coverage'] else '',
              ('; ' + '; '.join(r['notes'])) if r['notes'] else ''))


if __name__ == '__main__':
    main()
