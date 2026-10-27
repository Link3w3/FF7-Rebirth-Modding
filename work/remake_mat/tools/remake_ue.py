"""FF7 Remake (UE 4.18) EndMaterial permutations as End editor (UE 4.26) material Custom nodes.

Each permutation's base pass pixel shader, and the depth-only pixel shader that does its coverage clip, lifted by
dxbc2hlsl.py (lift_check.py checks each lift against the original), inside a struct that the editor feeds:
  * the interpolants from the material's pixel parameters (UVs from TextureCoordinate inputs),
  * the View and Primitive slots the shader reads from the editor's own (the debug overrides as identity, the
    pre-exposure as 1: the editor's base pass applies its own),
  * the Material uniform buffer rebuilt from the material's parameters (the game's uniform expressions),
  * the textures from the material's texture parameters, by the game's own names (the shader's resource table says
    which is which), and the game's 64^3 blue noise from the engine's spatiotemporal blue noise.
What the shader writes to the GBuffer (4.18: emissive; normal; metallic, specular, roughness, shading model; base colour,
occlusion; custom data) is decoded into the node's outputs for the material's pins.

    remake_ue.py <material name> [...]     writes gen/<name>.json (both nodes: code, inputs, outputs, switches, notes)"""
import json
import os
import re
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dxbc2hlsl

ROOT = '/work/remake_mat'
DIS = os.path.join(ROOT, 'dis')
GEN = os.path.join(ROOT, 'gen')
USETS = None

BASE_PS = 'TBasePassPSFNoLightMapPolicyNoSkylightNoPerObjectCoverage'
DEPTH_PS = 'FDepthOnlyPS'

# ---- the game's View uniform buffer (float4 slots) as the editor spells them; the values are float4s unless 'uint:'
VIEW = {}
for _i in range(4):
    VIEW[_i] = 'View.TranslatedWorldToClip[%d]' % _i
    VIEW[36 + _i] = 'View.SVPositionToTranslatedWorld[%d]' % _i
VIEW.update({
    62: 'float4(View.PreViewTranslation, 0.0)',
    128: 'float4(1.0, 0.0, 0.0, 0.0)',       # pre-exposure (the editor's base pass applies its own)
    132: 'float4(0.0, 0.0, 0.0, 1.0)',       # diffuse override (none)
    133: 'float4(0.0, 0.0, 0.0, 1.0)',       # specular override (none)
    134: 'float4(0.0, 0.0, 0.0, 1.0)',       # normal override (none)
    135: 'float4(0.0, 1.0, 0.0, 0.0)',       # roughness override (none)
    136: 'float4(0.0, 0.0, 0.0, 0.0)',       # a debug view mode (off)
    139: 'uint:uint4(0u, 0u, View.StateFrameIndexMod8, 0u)',  # .z: the frame index the blue noise steps with
    140: 'float4(0.0, 0.0, 0.0, 0.0)',       # a debug view mode (off)
    159: 'float4(0.0, 0.0, 0.0, 0.0)',       # .w: a view switch that drops the non-radiative base colour (off)
})
PRIMITIVE = {}
for _i in range(4):
    PRIMITIVE[_i] = 'EMS_Prim.LocalToWorld[%d]' % _i
    PRIMITIVE[4 + _i] = 'EMS_Prim.WorldToLocal[%d]' % _i
PRIMITIVE.update({
    8: 'EMS_Prim.ObjectWorldPositionAndRadius',
    9: 'float4(EMS_Prim.ObjectBounds, EMS_Prim.InvNonUniformScaleAndDeterminantSign.w)',
    10: 'float4(EMS_Prim.ActorWorldPosition, EMS_Prim.DecalReceiverMask)',
    11: 'uint:uint4(0u, 0u, 0u, 0u)',       # the game's per-object flags (none)
})


def uniform_sets():
    global USETS
    if USETS is None:
        USETS = json.load(open(os.path.join(ROOT, 'uniform_sets.json')))
    return USETS


def ident(text):
    return re.sub(r'[^A-Za-z0-9_]', '_', text)


def parse_debug(debug):
    """the shader map's description: shading model, blend mode, two sided, masked, and every static switch"""
    out = {'switches': {}}
    for k, v in re.findall(r"StaticSwitch'([^']+)'=(True|False)", debug):
        out['switches'][k] = v == 'True'
    m = re.search(r'LightingModel=(\w+)', debug)
    out['shading_model'] = m.group(1) if m else 'MSM_DefaultLit'
    m = re.search(r'BlendMode=(\w+)', debug)
    out['blend_mode'] = m.group(1) if m else 'BLEND_Opaque'
    for key in ('TwoSided', 'Masked', 'TSNormal', 'Distorted'):
        m = re.search(r'\b%s=(\d)' % key, debug)
        out[key.lower()] = bool(m and m.group(1) == '1')
    return out


class Inputs:
    """the node's inputs: UVs, the game's parameters and textures (by their own names), the blue noise"""
    def __init__(self):
        self.items = []
        self.names = set()

    def add(self, name, kind, **extra):
        if name not in self.names:
            self.names.add(name)
            self.items.append(dict(name=name, kind=kind, **extra))
        return name


class UniformBuilder:
    """the game's uniform expressions (FMaterialUniformExpression trees) as HLSL over the node's parameter inputs"""
    def __init__(self, inputs):
        self.inputs = inputs
        self.tex_dims = []
        self.textures = {}   # the material's texture list index -> input name (set by the caller)

    def e(self, x):
        op = x['op']
        if op == 'const':
            v = (list(x['value']) + [0.0] * 4)[:4]
            return 'float4(%s)' % ', '.join(repr(float(c)) for c in v)
        if op == 'vparam':
            if x['name'] == 'SelectionColor':
                return 'float4(0.0, 0.0, 0.0, 0.0)'   # the editor draws its own selection
            n = self.inputs.add('V_' + ident(x['name']), 'vector', param=x['name'], default=x.get('default', [0, 0, 0, 0]))
            return n
        if op == 'sparam':
            n = self.inputs.add('S_' + ident(x['name']), 'scalar', param=x['name'], default=x.get('default', 0.0))
            return 'float4(%s, %s, %s, %s)' % (n, n, n, n)
        if op == 'swizzle':
            a = self.e(x['x'])
            idx = x['index']
            comps = ['(%s).%s' % (a, 'xyzw'[i]) if i >= 0 else '0.0' for i in idx[:x.get('n', 4)]]
            comps = (comps + ['0.0'] * 4)[:4]
            return 'float4(%s)' % ', '.join(comps)
        if op == 'append':
            a, b, na = self.e(x['a']), self.e(x['b']), x['na']
            comps = ['(%s).%s' % (a, 'xyzw'[i]) for i in range(na)] + ['(%s).%s' % (b, 'xyzw'[i]) for i in range(4 - na)]
            return 'float4(%s)' % ', '.join(comps)
        if op == 'math':
            a, b, m = self.e(x['a']), self.e(x['b']), x['math']
            if m == 'dot':
                return 'dot(%s, %s).xxxx' % (a, b)
            return '(%s %s %s)' % (a, m, b)
        if op == 'clamp':
            return 'clamp(%s, %s, %s)' % (self.e(x['x']), self.e(x['lo']), self.e(x['hi']))
        if op == 'max':
            return 'max(%s, %s)' % (self.e(x['a']), self.e(x['b']))
        if op == 'frac':
            return 'frac(%s)' % self.e(x['x'])
        if op == 'squareroot':
            return 'sqrt(%s)' % self.e(x['x'])
        if op == 'texprop':
            t = x['texture']
            n = self.inputs.add('T_' + ident(t['name']), 'texture2d', param=t['name'])
            k = len(self.tex_dims)
            self.tex_dims.append('uint EMS_tw%d, EMS_th%d; %s.GetDimensions(EMS_tw%d, EMS_th%d);' % (k, k, n, k, k))
            if x.get('property') == 'size':
                return 'float4(float(EMS_tw%d), float(EMS_th%d), 0.0, 0.0)' % (k, k)
            return 'float4(1.0 / float(EMS_tw%d), 1.0 / float(EMS_th%d), 0.0, 0.0)' % (k, k)
        raise NotImplementedError('uniform expression %s' % op)


class UEEnv(dxbc2hlsl.Env):
    def __init__(self, bindings):
        self.bindings = bindings
        self.cbnames = bindings['cb']

    def v(self, reg):
        return 'v%d' % reg

    def cb(self, buf, index):
        if not re.match(r'^\d+$', str(index)):
            raise NotImplementedError('a register-indexed constant buffer read (cb%d[%s])' % (buf, index))
        return 'cb%d_%s' % (buf, index)

    def tex(self, reg):
        return 't%d' % reg

    def samp(self, sreg, treg):
        return 's%d' % sreg

    def load3d(self, treg, arg):
        # the game's 64^3 blue noise: the engine's 128 x 128 x 64 spatiotemporal blue noise volume (the shader masks
        # the coordinates to 64)
        return None


SEMANTIC_V = {
    ('TEXCOORD', '0'): 'float4(UV0, UV1)',
    ('TEXCOORD', '1'): 'float4(UV2, UV3)',
    ('TEXCOORD', '6'): 'float4(Parameters.TangentToWorld[0], 0.0)',
    ('TEXCOORD', '7'): 'float4(Parameters.TangentToWorld[2], EMS_TangentSign)',
    ('COLOR', '0'): 'Parameters.VertexColor',
    ('COLOR', '1'): 'Parameters.VertexColor',
    ('VertexContextVector', '0'): 'float4(0.0, 0.0, 0.0, 0.0)',
    ('PixelPosition', '0'): 'float4(Parameters.WorldPosition_CamRelative, 1.0)',
}


def lift_node(name, shader_key, kind, inputs, notes):
    """one lifted shader as a Custom node: (code, outputs). kind 'base' (GBuffer outputs) or 'coverage' (the clip)"""
    asm_path = os.path.join(DIS, name, shader_key + '.asm')
    asm = open(asm_path, encoding='latin-1').read()
    bindings = json.load(open(os.path.join(DIS, name, 'bindings.json')))[shader_key]
    env = UEEnv(bindings)
    L = dxbc2hlsl.Lifter(asm, env)
    body = L.body_lines()
    decls = L.decls()
    uset = uniform_sets()[name]
    textures = list(uset['textures2d']) + list(uset['texturescube'])
    ub = UniformBuilder(inputs)

    # interpolants
    vset = []
    uses_uv = set()
    for sem, idx, mask, reg, sysv, fmt, used in L.input_sig:
        reg = int(reg)
        if sysv == 'POS':
            vset.append('E.v%d = asuint(Parameters.SvPosition);' % reg)
        elif sysv == 'FFACE':
            # the editor has already turned the normal of a back face round (two-sided materials)
            vset.append('E.v%d = uint4(0xffffffffu, 0u, 0u, 0u);' % reg)
        else:
            src = SEMANTIC_V.get((sem, idx))
            if src is None:
                notes.append('%s: interpolant %s%s is not mapped (0)' % (shader_key, sem, idx))
                src = 'float4(0.0, 0.0, 0.0, 0.0)'
            for u in re.findall(r'\bUV(\d)\b', src):
                uses_uv.add(int(u))
            vset.append('E.v%d = asuint(%s);' % (reg, src))
    for u in sorted(uses_uv | ({0, 1} if any('UV' in x for x in vset) else set())):
        inputs.add('UV%d' % u, 'uv', index=u)

    # uniform buffer slots
    cbset = []
    uvec = None
    for (buf, index) in sorted(L.cb_reads):
        bname = env.cbnames[buf] if buf < len(env.cbnames) else ''
        expr = None
        if bname == 'View':
            expr = VIEW.get(index)
        elif bname == 'Primitive':
            expr = PRIMITIVE.get(index)
        elif bname == 'Material':
            if uvec is None:
                vec = [ub.e(x) for x in uset['vectors']]
                sca = [ub.e(x) + '.x' for x in uset['scalars']]
                uvec = list(vec)
                for j in range(0, len(sca), 4):
                    part = (sca[j:j + 4] + ['0.0'] * 4)[:4]
                    uvec.append('float4(%s)' % ', '.join(part))
            expr = uvec[index] if index < len(uvec) else None
        elif bname == '':
            # the pass's own loose parameters ($Globals): [2].x is the dithered LOD fade (1 = fully there)
            expr = {2: 'float4(1.0, 1.0, 1.0, 1.0)'}.get(index, 'float4(0.0, 0.0, 0.0, 0.0)')

        elif bname == 'PrecomputedLightingBuffer':
            expr = 'float4(0.0, 0.0, 0.0, 0.0)'
        if expr is None:
            notes.append('%s: %s[%d] is not mapped (0)' % (shader_key, bname or 'cb%d' % buf, index))
            expr = 'float4(0.0, 0.0, 0.0, 0.0)'
        if expr.startswith('uint:'):
            cbset.append('E.cb%d_%d = %s;' % (buf, index, expr[5:]))
        else:
            cbset.append('E.cb%d_%d = asuint(%s);' % (buf, index, expr))

    # textures and samplers: the shader's resource table says which material texture each one is
    run_params, run_args = [], []
    for t, ty in sorted(L.res.items()):
        b = bindings['t'].get(str(t))
        hl = {'texture2d': 'Texture2D', 'texture3d': 'Texture3D', 'texturecube': 'TextureCube'}.get(ty, 'Texture2D')
        if b and b[0] == 'Material':
            k = b[1] // 2
            if k >= len(textures):
                raise ValueError('%s: t%d is the material\'s texture %d of %d' % (shader_key, t, k, len(textures)))
            tp = textures[k]
            arg = inputs.add('T_' + ident(tp['name']), 'texturecube' if ty == 'texturecube' else 'texture2d', param=tp['name'])
        elif b and b[0] == 'View' and ty == 'texture3d':
            arg = inputs.add('EMS_BlueNoise', 'bluenoise')
        else:
            raise ValueError('%s: t%d (%s) is %r' % (shader_key, t, ty, b))
        run_params.append('%s t%d' % (hl, t))
        run_args.append(arg)
    for s in sorted(L.samplers):
        b = bindings['s'].get(str(s))
        if b and b[0] == 'Material':
            k = (b[1] - 1) // 2
            tp = textures[k]
            arg = 'T_' + ident(tp['name']) + 'Sampler'
            if 'T_' + ident(tp['name']) not in inputs.names:
                inputs.add('T_' + ident(tp['name']), 'texture2d', param=tp['name'])
        else:
            arg = 'View.SharedBilinearWrappedSampler'
            notes.append('%s: sampler s%d is %r (the shared bilinear wrapped one here)' % (shader_key, s, b))
        run_params.append('SamplerState s%d' % s)
        run_args.append(arg)

    nouts = [int(r[3]) for r in L.output_sig]
    members = ['uint4 v%d;' % int(r[3]) for r in L.input_sig]
    members += ['uint4 cb%d_%d;' % (buf, index) for (buf, index) in sorted(L.cb_reads)]
    members += ['float4 o%d;' % o for o in nouts]
    members.append('bool Discarded;')
    sid = ident(name)
    lines = []
    lines.append('// FF7 Remake %s: the game\'s %s, lifted instruction by instruction (checked against it), fed by the editor.'
                 % (name, 'base pass pixel shader' if kind == 'base' else 'depth-only pixel shader (its coverage clip)'))
    lines.append('#if PIXELSHADER')
    lines.append('struct EMS_%s_%s' % (kind, sid))
    lines.append('{')
    lines.extend('    ' + m for m in members)
    if L.uses_bitfield:
        lines.extend('    ' + b for b in dxbc2hlsl.BITFIELD.strip().split('\n'))
    lines.append('    void Run(%s)' % ', '.join(run_params))
    lines.append('    {')
    lines.extend('        ' + d for d in decls)
    for b in body:
        b = b.replace('discard;', 'Discarded = true;')
        lines.append('    ' + b)
    lines.append('    }')
    lines.append('};')
    lines.append('FPrimitiveSceneData EMS_Prim = GetPrimitiveData(Parameters.PrimitiveId);' if any('EMS_Prim' in c for c in cbset) else '')
    lines.append('float EMS_TangentSign = dot(cross(Parameters.TangentToWorld[2], Parameters.TangentToWorld[0]), Parameters.TangentToWorld[1]) < 0.0 ? -1.0 : 1.0;')
    lines.extend(ub.tex_dims)
    lines.append('EMS_%s_%s E;' % (kind, sid))
    lines.extend(vset)
    lines.extend(cbset)
    lines.extend('E.o%d = float4(0.0, 0.0, 0.0, 0.0);' % o for o in nouts)
    lines.append('E.Discarded = false;')
    lines.append('E.Run(%s);' % ', '.join(run_args))
    if kind == 'base':
        outs = [('EMS_Metallic', 1, 'E.o2.x'), ('EMS_Specular', 1, 'E.o2.y'), ('EMS_Roughness', 1, 'E.o2.z'),
                ('EMS_Occlusion', 1, 'E.o3.w'), ('EMS_Normal', 3, 'normalize(E.o1.xyz * 2.0 - 1.0)'),
                ('EMS_Emissive', 3, 'E.o0.xyz'), ('EMS_ShadingModel', 1, 'float(uint(E.o2.w * 255.0 + 0.5) & 15u)'),
                ('EMS_CustomData', 4, 'E.o4' if 4 in nouts else 'float4(0.0, 0.0, 0.0, 0.0)'),
                ('EMS_Visible', 1, '(E.Discarded ? 0.0 : 1.0)')]
        for n, size, ex in outs:
            lines.append('%s = %s;' % (n, ex))
        lines.append('return E.o3.xyz;')
        lines.append('#else')
        for n, size, ex in outs:
            lines.append('%s = %s;' % (n, '0.0' if size == 1 else 'float%d(%s)' % (size, ', '.join(['0.0'] * size))))
        lines.append('return float3(0.0, 0.0, 0.0);')
        outputs = [{'name': n, 'size': size} for n, size, ex in outs]
        main = 3
    else:
        lines.append('return E.Discarded ? 0.0 : 1.0;')
        lines.append('#else')
        lines.append('return 1.0;')
        outputs = []
        main = 1
    lines.append('#endif')
    code = '\n'.join(l for l in lines if l is not None)
    return {'code': code, 'outputs': outputs, 'main_size': main, 'instructions': len(body),
            'textures': run_args, 'discards': L.discards}


def build(name):
    uset = uniform_sets()[name]
    info = parse_debug(uset.get('debug', ''))
    notes = []
    base_inputs = Inputs()
    base = lift_node(name, BASE_PS, 'base', base_inputs, notes)
    base['inputs'] = base_inputs.items
    cov = None
    if info['masked'] and os.path.exists(os.path.join(DIS, name, DEPTH_PS + '.asm')):
        cov_inputs = Inputs()
        cov = lift_node(name, DEPTH_PS, 'coverage', cov_inputs, notes)
        cov['inputs'] = cov_inputs.items
        if not cov['discards']:
            notes.append('%s: masked but its depth-only shader has no clip' % name)
    return {'name': name, 'master': uset.get('friendly', name), 'switches': info['switches'], 'shading_model': info['shading_model'],
            'blend_mode': info['blend_mode'], 'two_sided': info['twosided'], 'masked': info['masked'],
            'tangent_space_normal': info['tsnormal'], 'base': base, 'coverage': cov, 'notes': notes}


def main():
    os.makedirs(GEN, exist_ok=True)
    for name in sys.argv[1:]:
        r = build(name)
        json.dump(r, open(os.path.join(GEN, name + '.json'), 'w'), indent=1)
        print('%-70s base %d instr, %d inputs%s%s' % (name, r['base']['instructions'], len(r['base']['inputs']),
              ', coverage %d instr' % r['coverage']['instructions'] if r['coverage'] else '',
              ('; ' + '; '.join(r['notes'])) if r['notes'] else ''))


if __name__ == '__main__':
    main()
