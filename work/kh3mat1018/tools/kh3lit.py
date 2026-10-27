"""KH3 (UE 4.17 + SQEX) material pixel shaders -> HLSL for End (UE 4.26) Custom nodes.

A lit material's base pass pixel shader writes KH3's GBuffer; its depth-only pixel shader does the opacity-mask
clip. Each is translated instruction by instruction (dxbcir) after dead-code removal from the outputs that are
wanted, so the engine's own code after the material (GBuffer flags, dither, debug views, precomputed shadowing)
falls away by itself. The engine's inputs are mapped by the uniform buffer names the shader itself records:
  View        -> 4.26 View members (KH3_VIEW rows)
  Primitive   -> GetPrimitiveData(Parameters.PrimitiveId) members
  Material    -> float4 rows rebuilt from the material's uniform expressions (parameters, constants)
  MaterialCollectionN -> the material's N-th parameter collection, through Custom node inputs
  textures    -> the Material buffer's Texture2D_i (bind slots from the shader's resource table); a standalone
                 texture read with ld at (0, 0) is the eye adaptation value (K_EA input)
The outputs come back as KH3's GBuffer said them: BaseColor (GBufferC.rgb), Metallic/Specular/Roughness
(GBufferB.xyz), world normal (GBufferA.rgb * 2 - 1), Emissive (scene color with the unlit view mode off),
subsurface colour (GBufferD.rgb squared) and opacity (GBufferD.a); a depth pass gives the opacity mask (1, or 0
where the material clips)."""
import struct
import sys

sys.path[:0] = ['/work/kh3fx', '/work/kh3bnm/src/rebirth_fx']
import dxbcir             # noqa: E402
import dxbc2hlsl as D     # noqa: E402

F = 'xyzw'


class TranslateError(Exception):
    pass


# ---- KH3's View uniform buffer rows -> 4.26 ------------------------------------------------------------------------
def _m(name, base):
    return {base + i: '%s[%d]' % (name, i) for i in range(4)}


KH3_VIEW = {}
for _name, _base in (('View.TranslatedWorldToClip', 0), ('View.WorldToClip', 4), ('View.TranslatedWorldToView', 8),
                     ('View.ViewToTranslatedWorld', 12), ('View.TranslatedWorldToCameraView', 16),
                     ('View.CameraViewToTranslatedWorld', 20), ('View.ViewToClip', 24), ('View.ViewToClipNoAA', 28),
                     ('View.ClipToView', 32), ('View.SVPositionToTranslatedWorld', 36), ('View.ScreenToWorld', 40),
                     ('View.ScreenToTranslatedWorld', 44), ('View.PrevProjection', 59), ('View.PrevViewProj', 63),
                     ('View.PrevViewRotationProj', 67), ('View.PrevViewToClip', 71), ('View.PrevClipToView', 75),
                     ('View.PrevTranslatedWorldToClip', 79), ('View.PrevTranslatedWorldToView', 83),
                     ('View.PrevViewToTranslatedWorld', 87), ('View.PrevTranslatedWorldToCameraView', 91),
                     ('View.PrevCameraViewToTranslatedWorld', 95), ('View.PrevInvViewProj', 102),
                     ('View.PrevScreenToTranslatedWorld', 106), ('View.ClipToPrevClip', 110)):
    KH3_VIEW.update(_m(_name, _base))
KH3_VIEW.update({
    48: 'float4(View.ViewForward, 0)', 49: 'float4(View.ViewUp, 0)', 50: 'float4(View.ViewRight, 0)',
    51: 'float4(View.HMDViewNoRollUp, 0)', 52: 'float4(View.HMDViewNoRollRight, 0)',
    53: 'View.InvDeviceZToWorldZTransform', 54: 'View.ScreenPositionScaleBias',
    55: 'float4(View.WorldCameraOrigin, 0)', 56: 'float4(View.TranslatedWorldCameraOrigin, 0)',
    57: 'float4(View.WorldViewOrigin, 0)', 58: 'float4(View.PreViewTranslation, 0)',
    99: 'float4(View.PrevWorldCameraOrigin, 0)', 100: 'float4(View.PrevWorldViewOrigin, 0)',
    101: 'float4(View.PrevPreViewTranslation, 0)', 114: 'View.TemporalAAJitter', 115: 'View.GlobalClippingPlane',
    116: 'float4(View.FieldOfViewWideAngles, View.PrevFieldOfViewWideAngles)', 117: 'View.ViewRectMin',
    118: 'View.ViewSizeAndInvSize', 119: 'View.BufferSizeAndInvSize', 120: 'View.BufferBilinearUVMinMax',
    # debug view modes: the identity values a normal view has
    122: 'float4(0, 0, 0, 1)', 123: 'float4(0, 0, 0, 1)', 124: 'float4(0, 0, 0, 1)',
    125: 'float4(0, 1, View.PrevFrameGameTime, View.PrevFrameRealTime)',
    126: 'float4(0, View.WorldCameraMovementSinceLastFrame)',
    127: 'float4(View.WorldCameraMovementSinceLastFrame, View.CullingSign)',
    128: 'float4(View.NearPlane, View.AdaptiveTessellationFactor, View.GameTime, View.RealTime)',
    129: 'float4(View.MaterialTextureMipBias, View.MaterialTextureDerivativeMultiply, View.Random, View.FrameNumber)',
    130: 'float4(0, 0, 0, 0)', 141: 'float4(0, 0, 0, 0)', 172: 'float4(0, 0, 0, 0)',
    137: 'View.TemporalAAParams',
    # SQEX: x = exposure fixed (else the eye adaptation texture), y = that exposure, z = time (wrapped hourly)
    161: 'float4(0, K_EA, KH3_TIME, KH3_TIME)',
})

KH3_PRIMITIVE = {
    0: 'GetPrimitiveData(Parameters.PrimitiveId).LocalToWorld[0]',
    1: 'GetPrimitiveData(Parameters.PrimitiveId).LocalToWorld[1]',
    2: 'GetPrimitiveData(Parameters.PrimitiveId).LocalToWorld[2]',
    3: 'GetPrimitiveData(Parameters.PrimitiveId).LocalToWorld[3]',
    4: 'GetPrimitiveData(Parameters.PrimitiveId).WorldToLocal[0]',
    5: 'GetPrimitiveData(Parameters.PrimitiveId).WorldToLocal[1]',
    6: 'GetPrimitiveData(Parameters.PrimitiveId).WorldToLocal[2]',
    7: 'GetPrimitiveData(Parameters.PrimitiveId).WorldToLocal[3]',
    8: 'GetPrimitiveData(Parameters.PrimitiveId).ObjectWorldPositionAndRadius',
    9: 'float4(GetPrimitiveData(Parameters.PrimitiveId).ObjectBounds, '
       'GetPrimitiveData(Parameters.PrimitiveId).InvNonUniformScaleAndDeterminantSign.w)',
    10: 'float4(GetPrimitiveData(Parameters.PrimitiveId).ActorWorldPosition, '
        'GetPrimitiveData(Parameters.PrimitiveId).DecalReceiverMask)',
    11: 'float4(GetPrimitiveData(Parameters.PrimitiveId).PerObjectGBufferData, '
        'GetPrimitiveData(Parameters.PrimitiveId).UseSingleSampleShadowFromStationaryLights, '
        'GetPrimitiveData(Parameters.PrimitiveId).UseVolumetricLightmapShadowFromStationaryLights, 0)',
    12: 'GetPrimitiveData(Parameters.PrimitiveId).ObjectOrientation',
    13: 'GetPrimitiveData(Parameters.PrimitiveId).NonUniformScale',
    14: 'float4(GetPrimitiveData(Parameters.PrimitiveId).InvNonUniformScaleAndDeterminantSign.xyz, 0)',
    15: 'float4(GetPrimitiveData(Parameters.PrimitiveId).LocalObjectBoundsMin, 0)',
    16: 'float4(GetPrimitiveData(Parameters.PrimitiveId).LocalObjectBoundsMax, 0)',
    # SQEX per-object flags (only the GBuffer's flag bits read them)
    17: 'float4(0, 0, 0, 0)', 18: 'float4(0, 0, 0, 0)',
}

COMPONENTWISE = {'mov', 'add', 'mul', 'div', 'min', 'max', 'mad', 'frc', 'round_ni', 'round_pi', 'round_z', 'round_ne',
                 'exp', 'log', 'rsq', 'sqrt', 'rcp', 'deriv_rtx', 'deriv_rty', 'deriv_rtx_coarse', 'deriv_rty_coarse',
                 'deriv_rtx_fine', 'deriv_rty_fine', 'itof', 'utof', 'ftoi', 'ftou', 'movc', 'lt', 'ge', 'eq', 'ne',
                 'ilt', 'ige', 'ieq', 'ine', 'ult', 'uge', 'and', 'or', 'not', 'xor', 'iadd', 'imul', 'ineg', 'imax',
                 'imin', 'umax', 'umin', 'ishl', 'ishr', 'ushr', 'imad', 'umad', 'f32tof16', 'f16tof32'}
SAMPLES = {'sample', 'sample_l', 'sample_b', 'sample_d', 'sample_c', 'sample_c_lz', 'ld', 'gather4'}
CONTROL = {'if', 'else', 'endif', 'loop', 'endloop', 'break', 'breakc', 'continue', 'continuec', 'ret', 'retc',
           'discard', 'switch', 'case', 'default', 'endswitch'}


def _key(o):
    if o.file in ('r', 'o') and o.index and isinstance(o.index[0], int):
        return '%s%d' % (o.file, o.index[0])
    return None


def reads(ins, dcomps):
    """{(reg, comp)} an instruction reads to produce the destination components dcomps."""
    out = set()
    op = ins.op
    srcs = ins.ops[1:] if ins.ops else []
    if op in ('sincos', 'udiv'):
        srcs = ins.ops[2:]
    if op in ('dp2', 'dp3', 'dp4'):
        n = int(op[2])
        for s in srcs:
            k = _key(s)
            if k:
                out.update((k, s.comps[i]) for i in range(n))
        return out
    if op in SAMPLES:
        coord = srcs[0]
        k = _key(coord)
        if k:
            out.update((k, coord.comps[i]) for i in range(3))
        for s in srcs[3:]:
            k = _key(s)
            if k:
                out.update((k, c) for c in s.comps)
        return out
    for s in srcs:
        k = _key(s)
        if not k:
            continue
        if s.comps and len(s.comps) == 4:
            for c in dcomps:
                out.add((k, s.comps[F.index(c)]))
        else:
            out.update((k, c) for c in (s.comps or 'xyzw'))
    return out


ZERO_VIEW = {(126, 'x'), (130, 'x'), (141, 'x'), (172, 'w')}   # debug / platform switches that are 0 in a normal view


def drop_dead_blocks(code, view_slot):
    """Instruction indices to leave out: if-blocks whose condition is a comparison of a View switch that is always 0
    (out-of-bounds debug, unlit view mode, checkerboard subsurface), and the markers of the ones always taken."""
    zero = set()                                  # (reg, comp) known to be 0
    drop = set()
    stack = []                                    # (if index, kind) kind: 'dead', 'live', None
    for i, ins in enumerate(code):
        op = ins.op
        if op == 'if' and ins.ops:
            o = ins.ops[0]
            k = _key(o)
            known = k is not None and (k, o.comps[0]) in zero
            if known:
                kind = 'dead' if ins.test == 'nz' else 'live'
                stack.append([i, kind, False])
                drop.add(i)
            else:
                stack.append([i, None, False])
            continue
        if op == 'else':
            if stack and stack[-1][1]:
                stack[-1][2] = True
                stack[-1][1] = 'live' if stack[-1][1] == 'dead' else 'dead'
                drop.add(i)
            continue
        if op == 'endif':
            if stack:
                top = stack.pop()
                if top[1]:
                    drop.add(i)
            continue
        if any(f[1] == 'dead' for f in stack):
            drop.add(i)
            continue
        if not ins.ops:
            continue
        d = ins.ops[0]
        k = _key(d)
        if k is None:
            continue
        # a comparison of 0 with an always-0 View switch is 0; anything else written is unknown
        val_zero = False
        if op in ('lt', 'ne', 'ge', 'eq') and len(ins.ops) >= 3:
            a, b = ins.ops[1], ins.ops[2]
            def is_zero_imm(x):
                return x.file == 'l' and all(v == 0 for v in x.imm)
            def is_zero_view(x):
                return (x.file == 'cb' and x.index and x.index[0] == view_slot and isinstance(x.index[1], int)
                        and all((x.index[1], c) in ZERO_VIEW for c in set(x.comps)))
            if (is_zero_imm(a) and is_zero_view(b)) or (is_zero_view(a) and is_zero_imm(b)):
                val_zero = op in ('lt', 'ne')
        for c in d.comps:
            if val_zero:
                zero.add((k, c))
            else:
                zero.discard((k, c))
    return drop


def live_code(code, wanted):
    """Indices of the instructions the wanted outputs ({(reg, comp)}) need. One backward pass: a write inside a
    conditional block does not end a value's life; an if/else/endif is kept (with its condition) only when something
    inside it is; loops make the pass repeat until nothing changes."""
    has_loop = any(i.op == 'loop' for i in code)
    live_after = set(wanted)
    keep = set()
    for rnd in range(8 if has_loop else 1):
        live = set(live_after)
        frames = []                 # [(endif index, else index, keep count at endif)]
        before = len(keep)
        for idx in range(len(code) - 1, -1, -1):
            ins = code[idx]
            op = ins.op
            if op in ('endif', 'endloop', 'endswitch'):
                frames.append([idx, None, len(keep)])
                continue
            if op == 'else':
                if frames:
                    frames[-1][1] = idx
                continue
            if op in ('if', 'loop', 'switch'):
                end, els, n = frames.pop() if frames else (None, None, len(keep))
                if len(keep) > n or op == 'loop':
                    keep.add(idx)
                    if end is not None:
                        keep.add(end)
                    if els is not None:
                        keep.add(els)
                    if op in ('if', 'switch') and ins.ops:
                        o = ins.ops[0]
                        kk = _key(o)
                        if kk:
                            live.add((kk, o.comps[0]))
                continue
            if op in CONTROL:
                keep.add(idx)
                if ins.ops:
                    o = ins.ops[0]
                    kk = _key(o)
                    if kk:
                        live.add((kk, o.comps[0]))
                continue
            if not ins.ops:
                continue
            dests = [ins.ops[0]] if op not in ('sincos', 'udiv') else [ins.ops[0], ins.ops[1]]
            hit = []
            for d in dests:
                kk = _key(d)
                if kk is None:
                    continue
                dc = [c for c in d.comps if (kk, c) in live]
                if dc:
                    hit.append((d, kk, dc))
            if not hit:
                continue
            keep.add(idx)
            conditional = bool(frames)
            for d, kk, dc in hit:
                if not conditional:
                    for c in d.comps:
                        live.discard((kk, c))
            for d, kk, dc in hit:
                live |= reads(ins, dc)
        if rnd > 0 and len(keep) == before:
            break
        live_after |= live
    return keep


_orig_uexpr = D.uexpr


import math as _math


def _fold(e):
    """The four values of a uniform expression made only of constants, else None."""
    k0 = e[0]
    try:
        if k0 == 'const':
            return [float(v) for v in e[1]]
        if k0 == 'math':
            a, b = _fold(e[2]), _fold(e[3])
            if a is None or b is None:
                return None
            if e[1] == 'dot':
                v = sum(x * y for x, y in zip(a, b))
                return [v] * 4
            op = {'+': lambda x, y: x + y, '-': lambda x, y: x - y, '*': lambda x, y: x * y,
                  '/': lambda x, y: x / y if y != 0 else float('nan')}[e[1]]
            return [op(x, y) for x, y in zip(a, b)]
        if k0 == 'append':
            a, b = _fold(e[1]), _fold(e[2])
            if a is None or b is None:
                return None
            return (a[:e[3]] + b)[:4]
        if k0 == 'swizzle':
            a = _fold(e[1])
            if a is None:
                return None
            sw = e[2] + e[2][-1] * (4 - len(e[2]))
            return [a['xyzw'.index(c)] for c in sw]
        if k0 in ('max', 'min'):
            a, b = _fold(e[1]), _fold(e[2])
            if a is None or b is None:
                return None
            f = max if k0 == 'max' else min
            return [f(x, y) for x, y in zip(a, b)]
        if k0 == 'clamp':
            a, lo, hi = _fold(e[1]), _fold(e[2]), _fold(e[3])
            if a is None or lo is None or hi is None:
                return None
            return [min(max(x, l), h) for x, l, h in zip(a, lo, hi)]
        if k0 in ('floor', 'ceil', 'frac', 'abs', 'saturate', 'sqrt', 'squareroot', 'trunc', 'round'):
            a = _fold(e[1])
            if a is None:
                return None
            f = {'floor': _math.floor, 'ceil': _math.ceil, 'frac': lambda x: x - _math.floor(x), 'abs': abs,
                 'saturate': lambda x: min(max(x, 0.0), 1.0), 'sqrt': lambda x: _math.sqrt(x) if x >= 0 else float('nan'),
                 'squareroot': lambda x: _math.sqrt(x) if x >= 0 else float('nan'), 'trunc': _math.trunc,
                 'round': lambda x: float(round(x))}[k0]
            return [float(f(x)) for x in a]
    except (ArithmeticError, ValueError, IndexError):
        return None
    return None


def _uexpr(e, params):
    """dxbc2hlsl.uexpr, constants folded, with the engine's own parameters ('__SubsurfaceProfile') as their value."""
    if e[0] not in ('const',):
        v = _fold(e)
        if v is not None and all(x == x and abs(x) != float('inf') for x in v):
            return 'float4(%s)' % ', '.join(repr(float(x)) for x in v)
    if e[0] == 'vparam' and e[1] == 'SelectionColor':
        return 'float4(0, 0, 0, 0)'
    if e[0] == 'sparam' and e[1].startswith('__'):
        return 'float4(%s, %s, %s, %s)' % ((repr(float(e[2])),) * 4)
    if e[0] == 'vparam' and e[1].startswith('__'):
        return 'float4(%s)' % ', '.join(repr(float(v)) for v in e[2])
    return _orig_uexpr(e, params)


class _CSE(object):
    """Shared sub-expressions of the uniform rows as float4 temporaries (U_n), each written once."""

    def __init__(self):
        self.memo, self.decls = {}, []

    def __call__(self, e, params):
        s_ = _uexpr(e, params)
        if len(s_) > 40 and e[0] not in ('const', 'sparam', 'vparam'):
            if s_ in self.memo:
                return self.memo[s_]
            name = 'U_%d' % len(self.decls)
            self.decls.append('float4 %s = %s;' % (name, s_))
            self.memo[s_] = name
            return name
        return s_


def cb2_lines_cse(uset, used):
    cse = _CSE()
    D.uexpr = cse
    try:
        rows = D.cb2_lines(uset, used)
    finally:
        D.uexpr = _uexpr
    return cse.decls + rows


def _const_internal():
    D.uexpr = _uexpr


_const_internal()


class LitTranslator(D.Translator):
    """dxbc2hlsl's translator for any material pixel shader: output registers, named uniform buffers, resource
    tables, ld, discard, loops and integer ops."""

    def __init__(self, ir, vf, uset, ntex, name, ubs, texmap, mpcs):
        D.Translator.__init__(self, ir, vf, uset, ntex, name)
        self.ubs = ubs
        self.mat_slot = ubs.index('Material') if 'Material' in ubs else None
        self.texslot = {}                       # t slot -> material Texture2D index
        for (ub, res), t in texmap.items():
            if ub == self.mat_slot and res % 2 == 0 and res // 2 < ntex:
                self.texslot[t] = res // 2
        self.mpcs = mpcs                        # [(path, scalar names, vector names)]
        self.used_mpc = set()                   # (collection index, row)
        self.used_view = set()
        self.unmapped = set()
        self.discards = 0

    # interpolants of the lit vertex factories
    def vreg(self, idx):
        sem, i = self.vsem.get(idx, ('?', 0))
        key = '%s%d' % (sem, i)
        skin = bool(self.vf) and self.vf.startswith('TGPUSkin')
        if key == 'SV_Position0':
            return 'Parameters.SvPosition'
        if key == 'SV_IsFrontFace0':
            self.used_inputs.add('FRONT')
            return 'KH3_FRONT'
        if key == 'TEXCOORD10':
            self.used_inputs.add('TANGENT')
            return 'float4(Parameters.TangentToWorld[0], 0)'
        if key == 'TEXCOORD11':
            self.used_inputs.add('TANGENT')
            return 'float4(Parameters.TangentToWorld[2], Parameters.UnMirrored)'
        if key == 'COLOR0':
            self.used_inputs.add('VC')
            return 'Parameters.VertexColor'
        if key == 'TEXCOORD9':
            self.used_inputs.add('WPNO')
            return 'float4(K_WPNO, 0)'
        if key == 'TEXCOORD7' and not self.vf.startswith('FParticle'):
            # translucency's vertex fog (the engine fogs translucent materials itself)
            return 'float4(0, 0, 0, 1)'
        if sem == 'TEXCOORD' and i < 8:
            if skin:
                self.used_inputs.add('UV%d' % i)
                return 'float4(UV%d, 0, 0)' % i
            self.used_inputs.add('UV%d' % (2 * i))
            self.used_inputs.add('UV%d' % (2 * i + 1))
            return 'float4(UV%d, UV%d)' % (2 * i, 2 * i + 1)
        raise TranslateError('%s: interpolant %s of %s not mapped' % (self.name, key, self.vf))

    def base(self, o):
        f = o.file
        if f in ('r', 'o'):
            return '%s%d' % (f, o.index[0])
        if f == 'v':
            return self.vreg(o.index[0])
        if f == 'cb':
            buf, row = o.index[0], o.index[1]
            if not isinstance(row, int):
                raise TranslateError('%s: dynamically indexed cb%d' % (self.name, buf))
            ub = self.ubs[buf] if buf < len(self.ubs) else '?'
            if ub == 'Material':
                self.used_cb2.add(row)
                return 'CB2_%d' % row
            if ub == 'View':
                self.used_view.add(row)
                if row in KH3_VIEW:
                    if row == 161:
                        self.used_inputs.update(('TIME', 'EA'))
                    return KH3_VIEW[row]
                self.unmapped.add('View[%d]' % row)
                return 'float4(0, 0, 0, 0)'
            if ub == 'Primitive':
                if row in KH3_PRIMITIVE:
                    return KH3_PRIMITIVE[row]
                self.unmapped.add('Primitive[%d]' % row)
                return 'float4(0, 0, 0, 0)'
            if ub.startswith('MaterialCollection'):
                n = int(ub[len('MaterialCollection'):])
                self.used_mpc.add((n, row))
                return 'MPC%d_%d' % (n, row)
            if ub in ('PrecomputedLightingBuffer', 'IndirectLightingCache'):
                return 'float4(0, 0, 0, 1)'
            self.unmapped.add('%s[%d]' % (ub, row))
            return 'float4(0, 0, 0, 0)'
        raise TranslateError('%s: operand file %s' % (self.name, f))

    @staticmethod
    def dest(o):
        if o.file == 'null':
            return None, ''
        if o.file not in ('r', 'o'):
            raise TranslateError('destination %s' % o.file)
        return '%s%d' % (o.file, o.index[0]), o.comps

    def logic(self, ins):
        """and with a low-bit mask on a small integer (held as a float): its remainder."""
        if ins.op == 'and':
            a, b = ins.ops[1], ins.ops[2]
            d, mask = self.dest(ins.ops[0])
            for o, other in ((b, a), (a, b)):
                if o.file == 'l' and not any(self._isbool(other, c) for c in mask):
                    vals = [o.imm[F.index(c)] for c in mask]
                    if all(v and (v & (v + 1)) == 0 and v < 0x10000 for v in vals):
                        for c, v in zip(mask, vals):
                            self.lines.append('%s.%s = fmod(floor(%s), %d.0);' % (d, c, self.src(other, c), v + 1))
                        self._clear_bools(ins)
                        return
        D.Translator.logic(self, ins)

    def texname(self, t):
        if t in self.texslot:
            i = self.texslot[t]
            self.used_tex.add(i)
            return 'Tex%d' % i
        return None

    def sample(self, ins, kind):
        if kind == 'ld':
            d, mask = self.dest(ins.ops[0])
            res = ins.ops[2]
            t = res.index[0]
            if self.texname(t) is None:
                # a standalone texture read at texel (0, 0): the eye adaptation value
                self.used_inputs.add('EA')
                self.emit(d, mask, 'K_EA.%s' % ('x' * len(mask)), ins.sat)
                return
            raise TranslateError('%s: ld from a material texture' % self.name)
        D.Translator.sample(self, ins, kind)

    def run(self, code, keep=None):
        self.bools = set()
        for idx, ins in enumerate(code):
            if keep is not None and idx not in keep:
                continue
            if self.step(ins) == 'ret':
                break

    def step(self, ins):
        op = ins.op
        if op == 'nop':
            return
        if op == 'discard':
            c = self.src(ins.ops[0], 'x')
            self.lines.append('KH3_MASK = (%s %s 0) ? 0 : KH3_MASK;' % (c, '!=' if ins.test == 'nz' else '=='))
            self.discards += 1
            return
        if op == 'loop':
            self.lines.append('[loop] for (int kh3_it = 0; kh3_it < 256; kh3_it++) {')
            return
        if op == 'endloop':
            self.lines.append('}')
            return
        if op == 'break':
            self.lines.append('break;')
            return
        if op == 'breakc':
            c = self.src(ins.ops[0], 'x')
            self.lines.append('if (%s %s 0) break;' % (c, '!=' if ins.test == 'nz' else '=='))
            return
        if op == 'ret':
            return 'ret'
        if op in ('iadd', 'imul'):
            d, mask = self.dest(ins.ops[0])
            sym = '+' if op == 'iadd' else '*'
            self.emit(d, mask, '(%s %s %s)' % (self.src(ins.ops[1], mask), sym, self.src(ins.ops[2], mask)), False)
            self._clear_bools(ins)
            return
        if op == 'ineg':
            d, mask = self.dest(ins.ops[0])
            self.emit(d, mask, '(-%s)' % self.src(ins.ops[1], mask), False)
            self._clear_bools(ins)
            return
        if op in ('ishl', 'ushr', 'ishr'):
            d, mask = self.dest(ins.ops[0])
            a, b = ins.ops[1], ins.ops[2]
            if b.file != 'l':
                raise TranslateError('%s: %s by a register' % (self.name, op))
            outs = []
            for c in mask:
                sh = b.imm[F.index(c)] & 31
                sa = self.src(a, c)
                outs.append(('(%s * %d.0)' % (sa, 1 << sh)) if op == 'ishl' else ('floor(%s / %d.0)' % (sa, 1 << sh)))
            for c, e in zip(mask, outs):
                self.lines.append('%s.%s = %s;' % (d, c, e))
            self._clear_bools(ins)
            return
        if op == 'udiv':
            q, r = ins.ops[0], ins.ops[1]
            a, b = ins.ops[2], ins.ops[3]
            for dest, kind in ((q, 'q'), (r, 'r')):
                dd, mask = self.dest(dest)
                if dd is None:
                    continue
                sa, sb = self.src(a, mask), self.src(b, mask)
                if kind == 'q':
                    self.emit(dd, mask, 'floor(%s / %s)' % (sa, sb), False)
                else:
                    self.emit(dd, mask, '(%s - floor(%s / %s) * %s)' % (sa, sa, sb, sb), False)
            return
        if op in ('imax', 'umax', 'imin', 'umin'):
            d, mask = self.dest(ins.ops[0])
            fn = 'max' if 'max' in op else 'min'
            self.emit(d, mask, '%s(%s, %s)' % (fn, self.src(ins.ops[1], mask), self.src(ins.ops[2], mask)), False)
            self._clear_bools(ins)
            return
        if op in ('sample', 'sample_l', 'sample_b', 'sample_d', 'ld'):
            self.sample(ins, op)
            self._clear_bools(ins)
            return
        if op in self.UN:
            d, mask = self.dest(ins.ops[0])
            self.emit(d, mask, self.UN[op] % self.src(ins.ops[1], mask), ins.sat)
            self._copy_bools(ins, op == 'mov')
            return
        if op in self.BIN:
            d, mask = self.dest(ins.ops[0])
            self.emit(d, mask, self.BIN[op] % (self.src(ins.ops[1], mask), self.src(ins.ops[2], mask)), ins.sat)
            self._clear_bools(ins)
            return
        if op == 'mad':
            d, mask = self.dest(ins.ops[0])
            self.emit(d, mask, '(%s * %s + %s)' % tuple(self.src(o, mask) for o in ins.ops[1:4]), ins.sat)
            self._clear_bools(ins)
            return
        if op in ('dp2', 'dp3', 'dp4'):
            n = int(op[2])
            d, mask = self.dest(ins.ops[0])
            self.emit(d, mask, 'dot(%s, %s)' % (self.srcn(ins.ops[1], n), self.srcn(ins.ops[2], n)), ins.sat)
            self._clear_bools(ins)
            return
        if op in self.CMP:
            d, mask = self.dest(ins.ops[0])
            a, b = self.src(ins.ops[1], mask), self.src(ins.ops[2], mask)
            ty = 'float%d' % len(mask) if len(mask) > 1 else 'float'
            self.emit(d, mask, '%s(%s %s %s)' % (ty, a, self.CMP[op], b), False)
            for c in mask:
                self.bools.add((d, c))
            return
        if op == 'movc':
            d, mask = self.dest(ins.ops[0])
            c, a, b = (self.src(o, mask) for o in ins.ops[1:4])
            self.emit(d, mask, '((%s != 0) ? %s : %s)' % (c, a, b), ins.sat)
            self._clear_bools(ins)
            return
        if op in ('and', 'or', 'not'):
            self.logic(ins)
            return
        if op == 'sincos':
            src = ins.ops[2]
            for o, fn in ((ins.ops[0], 'sin'), (ins.ops[1], 'cos')):
                d, mask = self.dest(o)
                if d:
                    self.emit(d, mask, '%s(%s)' % (fn, self.src(src, mask)), ins.sat)
            return
        if op == 'if':
            c = self.src(ins.ops[0], 'x')
            self.lines.append('if (%s %s 0) {' % (c, '!=' if ins.test == 'nz' else '=='))
            return
        if op == 'else':
            self.lines.append('} else {')
            return
        if op == 'endif':
            self.lines.append('}')
            return
        raise TranslateError('%s: instruction %s not translated' % (self.name, op))


def _nop():
    n = dxbcir.Instr()
    n.op, n.sat, n.test, n.ops, n.dim, n.offsets, n.raw, n.controls = 'nop', False, '', [], None, None, None, 0
    return n


def mpc_lines(t, mpcs):
    """float4 MPCn_row from one Custom input per parameter of that row."""
    lines, inputs = [], []
    for n, row in sorted(t.used_mpc):
        if n >= len(mpcs):
            raise TranslateError('%s: MaterialCollection%d, the material has %d' % (t.name, n, len(mpcs)))
        path, scalars, vectors = mpcs[n]
        nsrows = (len(scalars) + 3) // 4
        if row < nsrows:
            comps = []
            for c in range(4):
                j = row * 4 + c
                if j < len(scalars):
                    nm = 'M%d_%s' % (n, D.pname(scalars[j])[2:])
                    inputs.append(dict(name=nm, kind='collection', collection=path, param=scalars[j], comps=1))
                    comps.append(nm + '.x')
                else:
                    comps.append('0')
            lines.append('float4 MPC%d_%d = float4(%s);' % (n, row, ', '.join(comps)))
        else:
            vi = row - nsrows
            if vi >= len(vectors):
                raise TranslateError('%s: MaterialCollection%d row %d past its parameters' % (t.name, n, row))
            nm = 'M%d_%s' % (n, D.pname(vectors[vi])[2:])
            inputs.append(dict(name=nm, kind='collection', collection=path, param=vectors[vi], comps=4))
            lines.append('float4 MPC%d_%d = %s;' % (n, row, nm))
    return lines, inputs


def translate(blob, shader, uset, mpcs, wanted, name='', extra_tail=None):
    """HLSL body for the code the wanted outputs need. wanted: {(reg, comp)}; returns the translator state and the
    lines (declarations, uniform rows, code)."""
    ir = dxbcir.parse(blob)
    code = ir['code']
    view_slot = shader.ubs.index('View') if 'View' in shader.ubs else -1
    drop = drop_dead_blocks(code, view_slot)
    code = [ins if i not in drop else _nop() for i, ins in enumerate(code)]
    keep = live_code(code, wanted)
    ntex = len(uset['textures2d'])
    t = LitTranslator(ir, shader.vf, uset, ntex, name, shader.ubs, shader.textures, mpcs)
    t.run(code, keep)
    ntemps = 0
    for dcl in ir['decls']:
        if dcl.op == 'dcl_temps':
            ntemps = dcl.raw[0]
    outs = sorted({k for k, _ in wanted if k.startswith('o')})
    body = ['float4 %s;' % ', '.join('r%d = 0' % i for i in range(max(ntemps, 1)))]
    if outs:
        body.append('float4 %s;' % ', '.join('%s = 0' % o for o in outs))
    body.append('float KH3_MASK = 1;')
    uvs = sorted(int(u[2:]) for u in t.used_inputs if u.startswith('UV'))
    if 'TIME' in t.used_inputs:
        body.append('float KH3_TIME = View.GameTime;')
    if 'FRONT' in t.used_inputs:
        body.append('float4 KH3_FRONT = (Parameters.TwoSidedSign * View.CullingSign * '
                    'GetPrimitiveData(Parameters.PrimitiveId).InvNonUniformScaleAndDeterminantSign.w > 0) ? 1 : 0;')
    body += cb2_lines_cse(uset, t.used_cb2)
    ml, minputs = mpc_lines(t, mpcs)
    body += ml
    body += t.lines
    return t, body, minputs, uvs, len(keep), len(code)
