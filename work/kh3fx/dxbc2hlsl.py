"""KH3 material pixel shader (DXBC) -> HLSL for an End material's Custom node.

The material's own code (everything before KH3's debug-view block) is translated instruction by instruction; the
engine's inputs are mapped to what a 4.26 material sees:
  interpolants  -> Parameters.TexCoords / VertexColor / Particle.Color / Particle.DynamicParameter / SvPosition ...
  View (cb0)    -> View.ViewRectMin, ViewSizeAndInvSize, ScreenPositionScaleBias, InvDeviceZToWorldZTransform ...
  Material (cb2)-> float4s built from the parameters (from the material's uniform expression set)
  textures      -> the material's textures (Custom node inputs), the scene depth texture -> LookupDeviceZ
The Custom node returns float4(emissive, opacity).
"""
import struct

import dxbcir
import kh3uniform

F = 'xyzw'

# KH3 (4.17 + SQEX) View uniform buffer rows -> 4.26 View members, found from how the engine's code uses them
VIEW = {
    36: 'View.SVPositionToTranslatedWorld[0]', 37: 'View.SVPositionToTranslatedWorld[1]',
    38: 'View.SVPositionToTranslatedWorld[2]', 39: 'View.SVPositionToTranslatedWorld[3]',
    53: 'View.InvDeviceZToWorldZTransform', 54: 'View.ScreenPositionScaleBias',
    117: 'View.ViewRectMin', 118: 'View.ViewSizeAndInvSize', 119: 'View.BufferSizeAndInvSize',
    124: 'View.NormalOverrideParameter', 127: 'float4(0, 0, 0, View.CullingSign)',
    161: 'float4(0, 0, KH3_TIME, 0)',
}
PRIMITIVE = {9: 'GetPrimitiveData(Parameters.PrimitiveId).InvNonUniformScaleAndDeterminantSign'}

# the rest of KH3's View and Primitive rows (from kh3lit, the lit-material translator)
VIEW_MORE = {0: 'View.TranslatedWorldToClip[0]',
 1: 'View.TranslatedWorldToClip[1]',
 2: 'View.TranslatedWorldToClip[2]',
 3: 'View.TranslatedWorldToClip[3]',
 4: 'View.WorldToClip[0]',
 5: 'View.WorldToClip[1]',
 6: 'View.WorldToClip[2]',
 7: 'View.WorldToClip[3]',
 8: 'View.TranslatedWorldToView[0]',
 9: 'View.TranslatedWorldToView[1]',
 10: 'View.TranslatedWorldToView[2]',
 11: 'View.TranslatedWorldToView[3]',
 12: 'View.ViewToTranslatedWorld[0]',
 13: 'View.ViewToTranslatedWorld[1]',
 14: 'View.ViewToTranslatedWorld[2]',
 15: 'View.ViewToTranslatedWorld[3]',
 16: 'View.TranslatedWorldToCameraView[0]',
 17: 'View.TranslatedWorldToCameraView[1]',
 18: 'View.TranslatedWorldToCameraView[2]',
 19: 'View.TranslatedWorldToCameraView[3]',
 20: 'View.CameraViewToTranslatedWorld[0]',
 21: 'View.CameraViewToTranslatedWorld[1]',
 22: 'View.CameraViewToTranslatedWorld[2]',
 23: 'View.CameraViewToTranslatedWorld[3]',
 24: 'View.ViewToClip[0]',
 25: 'View.ViewToClip[1]',
 26: 'View.ViewToClip[2]',
 27: 'View.ViewToClip[3]',
 28: 'View.ViewToClipNoAA[0]',
 29: 'View.ViewToClipNoAA[1]',
 30: 'View.ViewToClipNoAA[2]',
 31: 'View.ViewToClipNoAA[3]',
 32: 'View.ClipToView[0]',
 33: 'View.ClipToView[1]',
 34: 'View.ClipToView[2]',
 35: 'View.ClipToView[3]',
 40: 'View.ScreenToWorld[0]',
 41: 'View.ScreenToWorld[1]',
 42: 'View.ScreenToWorld[2]',
 43: 'View.ScreenToWorld[3]',
 44: 'View.ScreenToTranslatedWorld[0]',
 45: 'View.ScreenToTranslatedWorld[1]',
 46: 'View.ScreenToTranslatedWorld[2]',
 47: 'View.ScreenToTranslatedWorld[3]',
 48: 'float4(View.ViewForward, 0)',
 49: 'float4(View.ViewUp, 0)',
 50: 'float4(View.ViewRight, 0)',
 51: 'float4(View.HMDViewNoRollUp, 0)',
 52: 'float4(View.HMDViewNoRollRight, 0)',
 55: 'float4(View.WorldCameraOrigin, 0)',
 56: 'float4(View.TranslatedWorldCameraOrigin, 0)',
 57: 'float4(View.WorldViewOrigin, 0)',
 58: 'float4(View.PreViewTranslation, 0)',
 59: 'View.PrevProjection[0]',
 60: 'View.PrevProjection[1]',
 61: 'View.PrevProjection[2]',
 62: 'View.PrevProjection[3]',
 63: 'View.PrevViewProj[0]',
 64: 'View.PrevViewProj[1]',
 65: 'View.PrevViewProj[2]',
 66: 'View.PrevViewProj[3]',
 67: 'View.PrevViewRotationProj[0]',
 68: 'View.PrevViewRotationProj[1]',
 69: 'View.PrevViewRotationProj[2]',
 70: 'View.PrevViewRotationProj[3]',
 71: 'View.PrevViewToClip[0]',
 72: 'View.PrevViewToClip[1]',
 73: 'View.PrevViewToClip[2]',
 74: 'View.PrevViewToClip[3]',
 75: 'View.PrevClipToView[0]',
 76: 'View.PrevClipToView[1]',
 77: 'View.PrevClipToView[2]',
 78: 'View.PrevClipToView[3]',
 79: 'View.PrevTranslatedWorldToClip[0]',
 80: 'View.PrevTranslatedWorldToClip[1]',
 81: 'View.PrevTranslatedWorldToClip[2]',
 82: 'View.PrevTranslatedWorldToClip[3]',
 83: 'View.PrevTranslatedWorldToView[0]',
 84: 'View.PrevTranslatedWorldToView[1]',
 85: 'View.PrevTranslatedWorldToView[2]',
 86: 'View.PrevTranslatedWorldToView[3]',
 87: 'View.PrevViewToTranslatedWorld[0]',
 88: 'View.PrevViewToTranslatedWorld[1]',
 89: 'View.PrevViewToTranslatedWorld[2]',
 90: 'View.PrevViewToTranslatedWorld[3]',
 91: 'View.PrevTranslatedWorldToCameraView[0]',
 92: 'View.PrevTranslatedWorldToCameraView[1]',
 93: 'View.PrevTranslatedWorldToCameraView[2]',
 94: 'View.PrevTranslatedWorldToCameraView[3]',
 95: 'View.PrevCameraViewToTranslatedWorld[0]',
 96: 'View.PrevCameraViewToTranslatedWorld[1]',
 97: 'View.PrevCameraViewToTranslatedWorld[2]',
 98: 'View.PrevCameraViewToTranslatedWorld[3]',
 99: 'float4(View.PrevWorldCameraOrigin, 0)',
 100: 'float4(View.PrevWorldViewOrigin, 0)',
 101: 'float4(View.PrevPreViewTranslation, 0)',
 102: 'View.PrevInvViewProj[0]',
 103: 'View.PrevInvViewProj[1]',
 104: 'View.PrevInvViewProj[2]',
 105: 'View.PrevInvViewProj[3]',
 106: 'View.PrevScreenToTranslatedWorld[0]',
 107: 'View.PrevScreenToTranslatedWorld[1]',
 108: 'View.PrevScreenToTranslatedWorld[2]',
 109: 'View.PrevScreenToTranslatedWorld[3]',
 110: 'View.ClipToPrevClip[0]',
 111: 'View.ClipToPrevClip[1]',
 112: 'View.ClipToPrevClip[2]',
 113: 'View.ClipToPrevClip[3]',
 114: 'View.TemporalAAJitter',
 115: 'View.GlobalClippingPlane',
 116: 'float4(View.FieldOfViewWideAngles, View.PrevFieldOfViewWideAngles)',
 120: 'View.BufferBilinearUVMinMax',
 122: 'float4(0, 0, 0, 1)',
 123: 'float4(0, 0, 0, 1)',
 125: 'float4(0, 1, View.PrevFrameGameTime, View.PrevFrameRealTime)',
 126: 'float4(0, View.WorldCameraMovementSinceLastFrame)',
 128: 'float4(View.NearPlane, View.AdaptiveTessellationFactor, View.GameTime, View.RealTime)',
 129: 'float4(View.MaterialTextureMipBias, View.MaterialTextureDerivativeMultiply, View.Random, View.FrameNumber)',
 130: 'float4(0, 0, 0, 0)',
 137: 'View.TemporalAAParams',
 141: 'float4(0, 0, 0, 0)',
 172: 'float4(0, 0, 0, 0)'}
PRIMITIVE_MORE = {0: 'GetPrimitiveData(Parameters.PrimitiveId).LocalToWorld[0]',
 1: 'GetPrimitiveData(Parameters.PrimitiveId).LocalToWorld[1]',
 2: 'GetPrimitiveData(Parameters.PrimitiveId).LocalToWorld[2]',
 3: 'GetPrimitiveData(Parameters.PrimitiveId).LocalToWorld[3]',
 4: 'GetPrimitiveData(Parameters.PrimitiveId).WorldToLocal[0]',
 5: 'GetPrimitiveData(Parameters.PrimitiveId).WorldToLocal[1]',
 6: 'GetPrimitiveData(Parameters.PrimitiveId).WorldToLocal[2]',
 7: 'GetPrimitiveData(Parameters.PrimitiveId).WorldToLocal[3]',
 8: 'GetPrimitiveData(Parameters.PrimitiveId).ObjectWorldPositionAndRadius',
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
 17: 'float4(0, 0, 0, 0)',
 18: 'float4(0, 0, 0, 0)'}
for _r, _v in VIEW_MORE.items():
    VIEW.setdefault(_r, _v)
for _r, _v in PRIMITIVE_MORE.items():
    PRIMITIVE.setdefault(_r, _v)


class TranslateError(Exception):
    pass


def fnum(u):
    f = struct.unpack('<f', struct.pack('<I', u))[0]
    if f != f or abs(f) == float('inf'):
        return 'asfloat(0x%08xu)' % u
    s = repr(float(f))
    if 'e' in s or 'E' in s:
        s = '%.9g' % f
        if 'e' in s and '.' not in s.split('e')[0]:
            s = s.replace('e', '.0e')
    return s


class Translator(object):
    def __init__(self, ir, vf, uset, ntex, name='', ubs=None, texmap=None):
        self.ir, self.vf, self.uset, self.ntex, self.name = ir, vf, uset, ntex, name
        # the uniform buffer bound at each constant buffer slot and the material textures' t slots, as the shader
        # records them (kh3shaders); without them: View b0, Primitive b1, Material b2, material texture k at t k
        self.ubs = list(ubs) if ubs else None
        self.texslot = None
        if ubs and texmap is not None:
            mat = self.ubs.index('Material') if 'Material' in self.ubs else None
            self.texslot = {}
            for (ub, res), t in texmap.items():
                if ub == mat and res % 2 == 0 and res // 2 < ntex:
                    self.texslot[t] = res // 2
        self.used_mpc = set()          # (collection index, row)
        self.skipped_outputs = 0
        self.vsem = {s.reg: (s.name, s.index) for s in ir['inputs']}
        self.used_inputs = set()      # 'UV0', 'UV1', 'VC', 'PC', 'DP', 'TIME', 'DEPTH', 'NORMAL', ...
        self.used_cb2 = set()
        self.used_tex = set()
        self.notes = []
        self.lines = []

    # -- operands ----------------------------------------------------------------------------------------------
    def vreg(self, idx):
        sem, i = self.vsem.get(idx, ('?', 0))
        key = '%s%d' % (sem, i)
        mesh = self.vf in ('FMeshParticleVertexFactory', 'FLocalVertexFactory')
        sprite = self.vf == 'FParticleSpriteVertexFactory'
        if key == 'SV_Position0':
            return 'Parameters.SvPosition'
        if key == 'SV_IsFrontFace0':
            self.used_inputs.add('FRONT')
            return 'KH3_FRONT'
        if mesh and key == 'TEXCOORD0':
            self.used_inputs.add('UV0')
            return 'KH3_UV'
        if mesh and key == 'COLOR0':
            self.used_inputs.add('VC')
            return 'Parameters.VertexColor'
        if self.vf == 'FMeshParticleVertexFactory' and key == 'COLOR1':
            self.used_inputs.add('PC')
            return 'Parameters.Particle.Color'
        if self.vf == 'FMeshParticleVertexFactory' and key == 'COLOR2':
            self.used_inputs.add('DP')
            return 'Parameters.Particle.DynamicParameter'
        if self.vf == 'FMeshParticleVertexFactory' and key == 'COLOR3':
            self.used_inputs.add('TIME')
            return 'float4(0, 0, KH3_TIME, 0)'
        if self.vf == 'FMeshParticleVertexFactory' and key == 'PARTICLE_TIME0':
            # the particle's relative time (a ParticleRelativeTime input makes the engine pass it)
            self.used_inputs.add('PT')
            return 'float4(K_PT, K_PT, K_PT, K_PT)'
        if self.vf == 'FMeshParticleVertexFactory' and key == 'PARTICLE_POSITION0':
            # translated world position and size, as 4.17 passes it (a ParticlePositionWS input makes 4.26 pass it)
            self.used_inputs.add('PPOS')
            return 'Parameters.Particle.TranslatedWorldPositionAndSize'
        if mesh and key == 'TEXCOORD9':
            # the base pass's world position without the material's offsets (translated world)
            return 'float4(Parameters.WorldPosition_NoOffsets_CamRelative, 0)'
        if key == 'TEXCOORD10':
            self.used_inputs.add('TANGENT')
            return 'float4(Parameters.TangentToWorld[0], 0)'
        if key == 'TEXCOORD11':
            self.used_inputs.add('TANGENT')
            return 'float4(Parameters.TangentToWorld[2], Parameters.UnMirrored)'
        if sprite and key == 'TEXCOORD2':
            self.used_inputs.add('PC')
            return 'Parameters.Particle.Color'
        if sprite and key == 'TEXCOORD3':
            self.used_inputs.add('UV0')
            return 'KH3_UV'
        if sprite and key == 'TEXCOORD1':
            self.used_inputs.add('DP')
            return 'Parameters.Particle.DynamicParameter'
        raise TranslateError('%s: interpolant %s of %s not mapped' % (self.name, key, self.vf))

    def base(self, o):
        f = o.file
        if f == 'r':
            return 'r%d' % o.index[0]
        if f == 'v':
            return self.vreg(o.index[0])
        if f == 'cb':
            buf, row = o.index[0], o.index[1]
            if not isinstance(row, int):
                raise TranslateError('%s: dynamically indexed cb%d' % (self.name, buf))
            if self.ubs is not None:
                ub = self.ubs[buf] if buf < len(self.ubs) else '?'
                buf = {'View': 0, 'Primitive': 1, 'Material': 2}.get(ub, buf)
                if ub.startswith('MaterialCollection'):
                    n = int(ub[len('MaterialCollection'):])
                    self.used_mpc.add((n, row))
                    return 'MPC%d_%d' % (n, row)
                if ub in ('PrecomputedLightingBuffer', 'IndirectLightingCache'):
                    return 'float4(0, 0, 0, 1)'
                if ub not in ('View', 'Primitive', 'Material'):
                    raise TranslateError('%s: %s[%d] (cb%d) not mapped' % (self.name, ub, row, o.index[0]))
            if buf == 2:
                self.used_cb2.add(row)
                return 'CB2_%d' % row
            if buf == 0 and row in VIEW:
                if row == 161:
                    self.used_inputs.add('TIME')
                return VIEW[row]
            if buf == 1 and row in PRIMITIVE:
                return PRIMITIVE[row]
            raise TranslateError('%s: cb%d[%d] not mapped' % (self.name, buf, row))
        raise TranslateError('%s: operand file %s' % (self.name, f))

    def src(self, o, mask):
        """Source operand o read for the destination components in mask (a string of xyzw)."""
        if o.file == 'l':
            vals = [fnum(o.imm[F.index(c)]) for c in mask]
            s = vals[0] if len(vals) == 1 else 'float%d(%s)' % (len(vals), ', '.join(vals))
        else:
            comps = ''.join(o.comps[F.index(c)] for c in mask)
            b = self.base(o)
            if b == 'KH3_UV' and ('z' in comps or 'w' in comps):
                self.used_inputs.add('UV1')
            s = '%s.%s' % (b, comps)
        if o.mod == 'abs':
            s = 'abs(%s)' % s
        elif o.mod == 'neg':
            s = '(-%s)' % s
        elif o.mod == 'negabs':
            s = '(-abs(%s))' % s
        return s

    def srcn(self, o, n):
        """The first n components of a source (dot products, texture coordinates)."""
        return self.src(o, F[:n])

    def dest(self, o):
        if o.file == 'null':
            return None, ''
        if o.file == 'o':
            # an output written inside the material's code: the engine's own GBuffer values of a lit material (its
            # roughness override and the like), not the emissive this translation takes
            self.skipped_outputs += 1
            return None, ''
        if o.file != 'r':
            raise TranslateError('destination %s' % o.file)
        return 'r%d' % o.index[0], o.comps

    def emit(self, d, mask, expr, sat):
        if d is None:
            return
        if sat:
            expr = 'saturate(%s)' % expr
        self.lines.append('%s.%s = %s;' % (d, mask, expr))

    # -- textures ----------------------------------------------------------------------------------------------
    def texname(self, t):
        if self.texslot is not None:
            k = self.texslot.get(t)
            if k is None:
                return None
            self.used_tex.add(k)
            return 'Tex%d' % k
        if t < self.ntex:
            self.used_tex.add(t)
            return 'Tex%d' % t
        return None

    def sample(self, ins, kind):
        d, mask = self.dest(ins.ops[0])
        coord, res = ins.ops[1], ins.ops[2]
        t = res.index[0]
        name = self.texname(t)
        uv = self.srcn(coord, 2)
        if ins.offsets and any(ins.offsets):
            raise TranslateError('%s: sample with texel offsets' % self.name)
        if name is None:
            # the scene depth texture (soft particles): device Z at the screen UV
            if kind != 'sample_l':
                raise TranslateError('%s: %s from texture t%d (not a material texture)' % (self.name, kind, t))
            self.used_inputs.add('DEPTH')
            expr = 'LookupDeviceZ(%s).xxxx' % uv
        else:
            samp = name + 'Sampler'
            if kind == 'sample':
                expr = 'Texture2DSample(%s, %s, %s)' % (name, samp, uv)
            elif kind == 'sample_l':
                expr = 'Texture2DSampleLevel(%s, %s, %s, %s)' % (name, samp, uv, self.src(ins.ops[4], 'x'))
            elif kind == 'sample_b':
                expr = 'Texture2DSampleBias(%s, %s, %s, %s)' % (name, samp, uv, self.src(ins.ops[4], 'x'))
            elif kind == 'sample_d':
                expr = 'Texture2DSampleGrad(%s, %s, %s, %s, %s)' % (name, samp, uv, self.srcn(ins.ops[4], 2),
                                                                   self.srcn(ins.ops[5], 2))
            else:
                raise TranslateError(kind)
        comps = ''.join(res.comps[F.index(c)] for c in mask)
        self.emit(d, mask, '(%s).%s' % (expr, comps), ins.sat)

    # -- instructions ------------------------------------------------------------------------------------------
    UN = {'mov': '%s', 'frc': 'frac(%s)', 'round_ni': 'floor(%s)', 'round_pi': 'ceil(%s)', 'round_z': 'trunc(%s)',
          'round_ne': 'round(%s)', 'exp': 'exp2(%s)', 'log': 'log2(%s)', 'rsq': 'rsqrt(%s)', 'sqrt': 'sqrt(%s)',
          'rcp': 'rcp(%s)', 'deriv_rtx': 'ddx(%s)', 'deriv_rty': 'ddy(%s)', 'deriv_rtx_coarse': 'ddx(%s)',
          'deriv_rty_coarse': 'ddy(%s)', 'deriv_rtx_fine': 'ddx_fine(%s)', 'deriv_rty_fine': 'ddy_fine(%s)',
          'itof': '%s', 'utof': '%s', 'ftoi': 'trunc(%s)', 'ftou': 'trunc(%s)'}
    BIN = {'add': '(%s + %s)', 'mul': '(%s * %s)', 'div': '(%s / %s)', 'min': 'min(%s, %s)', 'max': 'max(%s, %s)'}
    CMP = {'lt': '<', 'ge': '>=', 'eq': '==', 'ne': '!=', 'ilt': '<', 'ige': '>=', 'ieq': '==', 'ine': '!=',
           'ult': '<', 'uge': '>='}

    def run(self, code):
        self.bools = set()            # (reg, comp) holding a comparison result (1 or 0)
        for ins in code:
            op = ins.op
            if op in ('sample', 'sample_l', 'sample_b', 'sample_d'):
                self.sample(ins, op)
                self._clear_bools(ins)
                continue
            if op in self.UN:
                d, mask = self.dest(ins.ops[0])
                self.emit(d, mask, self.UN[op] % self.src(ins.ops[1], mask), ins.sat)
                self._copy_bools(ins, op == 'mov')
                continue
            if op in self.BIN:
                d, mask = self.dest(ins.ops[0])
                self.emit(d, mask, self.BIN[op] % (self.src(ins.ops[1], mask), self.src(ins.ops[2], mask)), ins.sat)
                self._clear_bools(ins)
                continue
            if op == 'mad':
                d, mask = self.dest(ins.ops[0])
                self.emit(d, mask, '(%s * %s + %s)' % tuple(self.src(o, mask) for o in ins.ops[1:4]), ins.sat)
                self._clear_bools(ins)
                continue
            if op in ('dp2', 'dp3', 'dp4'):
                n = int(op[2])
                d, mask = self.dest(ins.ops[0])
                self.emit(d, mask, 'dot(%s, %s)' % (self.srcn(ins.ops[1], n), self.srcn(ins.ops[2], n)), ins.sat)
                self._clear_bools(ins)
                continue
            if op in self.CMP:
                d, mask = self.dest(ins.ops[0])
                a, b = self.src(ins.ops[1], mask), self.src(ins.ops[2], mask)
                ty = 'float%d' % len(mask) if len(mask) > 1 else 'float'
                self.emit(d, mask, '%s(%s %s %s)' % (ty, a, self.CMP[op], b), False)
                for c in mask:
                    self.bools.add((d, c))
                continue
            if op == 'movc':
                d, mask = self.dest(ins.ops[0])
                c, a, b = (self.src(o, mask) for o in ins.ops[1:4])
                self.emit(d, mask, '((%s != 0) ? %s : %s)' % (c, a, b), ins.sat)
                self._clear_bools(ins)
                continue
            if op in ('and', 'or', 'not'):
                self.logic(ins)
                continue
            if op == 'sincos':
                src = ins.ops[2]
                for o, fn in ((ins.ops[0], 'sin'), (ins.ops[1], 'cos')):
                    d, mask = self.dest(o)
                    if d:
                        self.emit(d, mask, '%s(%s)' % (fn, self.src(src, mask)), ins.sat)
                continue
            if op in ('if',):
                c = self.src(ins.ops[0], 'x')
                self.lines.append('if (%s %s 0) {' % (c, '!=' if ins.test == 'nz' else '=='))
                continue
            if op == 'else':
                self.lines.append('} else {')
                continue
            if op == 'endif':
                self.lines.append('}')
                continue
            if op in ('discard',):
                self.notes.append('discard ignored')
                continue
            if op == 'ret':
                break
            raise TranslateError('%s: instruction %s not translated' % (self.name, op))

    def _clear_bools(self, ins):
        d, mask = self.dest(ins.ops[0])
        for c in mask:
            self.bools.discard((d, c))

    def _copy_bools(self, ins, is_mov):
        d, mask = self.dest(ins.ops[0])
        s = ins.ops[1]
        for c in mask:
            self.bools.discard((d, c))
            if is_mov and s.file == 'r' and not s.mod and ('r%d' % s.index[0], s.comps[F.index(c)]) in self.bools:
                self.bools.add((d, c))

    def _isbool(self, o, c):
        return o.file == 'r' and not o.mod and ('r%d' % o.index[0], o.comps[F.index(c)]) in self.bools

    def logic(self, ins):
        d, mask = self.dest(ins.ops[0])
        if ins.op == 'not':
            o = ins.ops[1]
            if not all(self._isbool(o, c) for c in mask):
                raise TranslateError('%s: bitwise not' % self.name)
            self.emit(d, mask, '(1 - %s)' % self.src(o, mask), False)
            for c in mask:
                self.bools.add((d, c))
            return
        a, b = ins.ops[1], ins.ops[2]
        out = []
        for c in mask:
            ab, bb = self._isbool(a, c), self._isbool(b, c)
            sa, sb = self.src(a, c), self.src(b, c)
            if ab and bb:
                out.append(('(%s * %s)' if ins.op == 'and' else 'max(%s, %s)') % (sa, sb))
                self.bools.add((d, c))
            elif ins.op == 'and' and (ab or bb):
                cond, other = (sa, b) if ab else (sb, a)
                val = self.src(other, c)
                out.append('((%s != 0) ? %s : 0)' % (cond, val))
                self.bools.discard((d, c))
            else:
                raise TranslateError('%s: bitwise %s on values' % (self.name, ins.op))
        for c, e in zip(mask, out):
            self.lines.append('%s.%s = %s;' % (d, c, e))


def find_outputs(code, cut):
    """(emissive register, (opacity register, component)) as the engine's code after the material reads them:
    translucent  o0.rgb = (E / EyeAdaptation + debug) * fog.a + fog.rgb,   o0.a = opacity
    additive     o0.rgb = opacity * (E / EyeAdaptation + debug) * fog.a,     o0.a = 0"""
    post = code[cut:]

    def reg(o):
        return 'r%d' % o.index[0] if o.file == 'r' else None

    opacity = None
    chain = None
    for ins in post:
        if not ins.ops or ins.ops[0].file != 'o':
            continue
        d = ins.ops[0]
        if d.index[0] != 0:
            continue                                              # (a lit material's other GBuffer targets)
        if 'w' in d.comps and ins.op == 'mov' and ins.ops[1].file == 'r':
            opacity = (reg(ins.ops[1]), ins.ops[1].comps[3])
        if 'x' in d.comps:
            if ins.op == 'mad' and ins.ops[1].file == 'cb':       # opaque: debug * cb0[130].x + E / EyeAdaptation
                chain = reg(ins.ops[3])
                opacity = opacity or ('1', 'x')
            elif ins.op == 'mad':                                 # translucent: rA * fog.w + fog.rgb
                chain = reg(ins.ops[1])
            elif ins.op == 'mul':                                 # additive: opacity.w * rA
                a, b = ins.ops[1], ins.ops[2]
                if a.file == 'r' and a.comps == 'wwww':
                    opacity, chain = (reg(a), 'w'), reg(b)
                elif b.file == 'r' and b.comps == 'wwww':
                    opacity, chain = (reg(b), 'w'), reg(a)
    if chain is None:
        return None, opacity
    # walk the chain back to the material's emissive: through * fog.w, the debug colour mad and the eye adaptation div
    pos = len(post)
    while True:
        found = None
        for i in range(pos - 1, -1, -1):
            ins = post[i]
            if ins.ops and ins.ops[0].file == 'r' and reg(ins.ops[0]) == chain and 'x' in ins.ops[0].comps:
                found = i
                break
        if found is None:
            return chain, opacity
        ins = post[found]
        pos = found
        if ins.op == 'mul' and any(o.file == 'v' for o in ins.ops[1:]):
            chain = reg([o for o in ins.ops[1:] if o.file == 'r'][0])
        elif ins.op == 'mad' and ins.ops[1].file == 'cb':
            chain = reg(ins.ops[3])
        elif ins.op == 'div':
            chain = reg(ins.ops[1])
        elif ins.op == 'movc':
            continue                                              # the debug view's override
        else:
            return chain, opacity


def mpc_lines(t, mpcs):
    """float4 MPCn_row from one Custom input per parameter of that row (mpcs: [(End path, scalar names, vector
    names)] in the material's collection order); a collection's scalars come first, four to a row."""
    lines, inputs = [], []
    for n, row in sorted(t.used_mpc):
        if mpcs is None or n >= len(mpcs):
            raise TranslateError('%s: MaterialCollection%d, the material has %d' % (t.name, n, len(mpcs or [])))
        path, scalars, vectors = mpcs[n]
        nsrows = (len(scalars) + 3) // 4
        if row < nsrows:
            comps = []
            for c in range(4):
                j = row * 4 + c
                if j < len(scalars):
                    nm = 'M%d_%s' % (n, pname(scalars[j])[2:])
                    inputs.append(dict(name=nm, kind='collection', collection=path, param=scalars[j], comps=1))
                    comps.append(nm + '.x')
                else:
                    comps.append('0')
            lines.append('float4 MPC%d_%d = float4(%s);' % (n, row, ', '.join(comps)))
        else:
            vi = row - nsrows
            if vi >= len(vectors):
                raise TranslateError('%s: MaterialCollection%d row %d past its parameters' % (t.name, n, row))
            nm = 'M%d_%s' % (n, pname(vectors[vi])[2:])
            inputs.append(dict(name=nm, kind='collection', collection=path, param=vectors[vi], comps=4))
            lines.append('float4 MPC%d_%d = %s;' % (n, row, nm))
    seen, uniq = set(), []
    for i in inputs:
        if i['name'] not in seen:
            seen.add(i['name'])
            uniq.append(i)
    return lines, uniq


def translate(blob, vf, uset, name='', ubs=None, texmap=None, mpcs=None):
    import kh3pick
    ir = dxbcir.parse(blob)
    cut = kh3pick.cut(ir['code'])
    ntex = len(uset['textures2d'])
    t = Translator(ir, vf, uset, ntex, name, ubs, texmap)
    t.run(ir['code'][:cut])
    em, op = find_outputs(ir['code'], cut)
    if em is None or op is None:
        raise TranslateError('%s: outputs not found (emissive %s, opacity %s)' % (name, em, op))
    # an emissive the compiler set after the material's code (a constant: mov rE, cbN[row] on the normal path)
    tail_lines = []
    for ins in ir['code'][cut:]:
        if ins.op == 'mov' and ins.ops and ins.ops[0].file == 'r' and 'r%d' % ins.ops[0].index[0] == em \
                and 'x' in ins.ops[0].comps and ins.ops[1].file in ('cb', 'l'):
            tail_lines = ['%s.xyz = %s;' % (em, t.src(ins.ops[1], 'xyz'))]

    ntemps = 0
    for dcl in ir['decls']:
        if dcl.op == 'dcl_temps':
            ntemps = dcl.raw[0]
    body = ['float4 %s;' % ', '.join('r%d = 0' % i for i in range(max(ntemps, 1)))]
    if 'UV0' in t.used_inputs:
        body.append('float4 KH3_UV = float4(UV0, %s);' % ('UV1' if 'UV1' in t.used_inputs else '0, 0'))
    if 'TIME' in t.used_inputs:
        body.append('float KH3_TIME = View.GameTime;')
    if 'FRONT' in t.used_inputs:
        body.append('float4 KH3_FRONT = (Parameters.TwoSidedSign * View.CullingSign * '
                    'GetPrimitiveData(Parameters.PrimitiveId).InvNonUniformScaleAndDeterminantSign.w > 0) ? 1 : 0;')
    body += cb2_lines(uset, t.used_cb2)
    mlines, minputs = mpc_lines(t, mpcs)
    body += mlines
    body += t.lines
    base_color = None
    if any(o.index > 0 for o in ir['outputs'] if o.name == 'SV_Target'):
        # a lit material: KH3's GBuffer C (o3.rgb) holds its base colour; drawn unlit, the base colour is lit by a
        # fixed amount on top of its emissive (an approximation until lit particle materials are translated)
        for ins in ir['code'][cut:]:
            if ins.ops and ins.ops[0].file == 'o' and ins.ops[0].index[0] == 3 and 'x' in ins.ops[0].comps \
                    and ins.op == 'mov' and ins.ops[1].file == 'r':
                base_color = 'r%d' % ins.ops[1].index[0]
        if base_color:
            t.notes.append('lit: base colour %s drawn at 0.7 on top of the emissive' % base_color)
    body += tail_lines
    if base_color:
        body.append('return float4(%s.xyz + %s.xyz * 0.7, %s);' % (em, base_color, '1' if op[0] == '1' else '%s.%s' % op))
    else:
        body.append('return float4(%s.xyz, %s);' % (em, '1' if op[0] == '1' else '%s.%s' % op))
    notes = list(t.notes)
    if t.skipped_outputs:
        notes.append('lit: its GBuffer outputs are left out, its emissive is drawn unlit (%d output writes skipped)'
                     % t.skipped_outputs)
    return dict(code='\n'.join(body), inputs=t.used_inputs, cb2=t.used_cb2, textures=sorted(t.used_tex),
                notes=notes, emissive=em, opacity=op, ninstr=cut, mpc_inputs=minputs, lit=bool(t.skipped_outputs))


# -- the Material uniform buffer rows, rebuilt from parameters --------------------------------------------------
def pname(n):
    """An HLSL identifier for a parameter: its ASCII letters and digits, plus a short hash when it has others
    (KH3 names some parameters in Japanese)."""
    import zlib
    ascii_part = ''.join(ch if (ch.isascii() and ch.isalnum()) else '_' for ch in n)
    if all(ch.isascii() and (ch.isalnum() or ch in ' _') for ch in n):
        return 'P_' + ascii_part
    return 'P_%s_%08x' % (ascii_part.strip('_')[:24] or 'p', zlib.crc32(n.encode('utf-8')))


def uexpr(e, params):
    """HLSL float4 for a uniform expression; params collects (name, kind, default)."""
    k0 = e[0]
    if k0 == 'const':
        return 'float4(%s)' % ', '.join(repr(float(v)) for v in e[1])
    if k0 == 'vparam':
        params[e[1]] = ('vector', e[2])
        return pname(e[1])
    if k0 == 'sparam':
        params[e[1]] = ('scalar', e[2])
        return pname(e[1]) + '.xxxx'
    if k0 == 'append':
        a, b, na = uexpr(e[1], params), uexpr(e[2], params), e[3]
        comps = [('(%s).%s' % (a, F[i])) for i in range(na)] + [('(%s).%s' % (b, F[i])) for i in range(4 - na)]
        return 'float4(%s)' % ', '.join(comps)
    if k0 == 'swizzle':
        x = uexpr(e[1], params)
        sw = e[2] + e[2][-1] * (4 - len(e[2]))
        return '(%s).%s' % (x, sw)
    if k0 == 'math':
        a, b = uexpr(e[2], params), uexpr(e[3], params)
        if e[1] == 'dot':
            return 'dot(%s, %s).xxxx' % (a, b)
        return '(%s %s %s)' % (a, e[1], b)
    if k0 in ('max', 'min', 'fmod'):
        return '%s(%s, %s)' % (k0, uexpr(e[1], params), uexpr(e[2], params))
    if k0 == 'clamp':
        return 'clamp(%s, %s, %s)' % tuple(uexpr(x, params) for x in e[1:4])
    if k0 in ('time', 'realtime'):
        return 'View.%s.xxxx' % ('GameTime' if k0 == 'time' else 'RealTime')
    if k0 in ('sin', 'cos', 'sqrt', 'frac', 'floor', 'ceil', 'abs', 'saturate', 'round', 'trunc', 'sign'):
        fn = {'sqrt': 'sqrt'}.get(k0, k0)
        return '%s(%s)' % (fn, uexpr(e[1], params))
    if k0 == 'squareroot':
        return 'sqrt(%s)' % uexpr(e[1], params)
    if k0 == 'length':
        return 'length(%s).xxxx' % uexpr(e[1], params)
    if k0 == 'trig':
        if e[1] == 'atan2':
            return 'atan2(%s, %s)' % (uexpr(e[2], params), uexpr(e[3], params))
        return '%s(%s)' % (e[1], uexpr(e[2], params))
    if k0 == 'periodic':
        return 'frac(%s)' % uexpr(e[1], params)
    if k0 in ('logarithm2',):
        return 'log2(%s)' % uexpr(e[1], params)
    raise TranslateError('uniform expression %s' % k0)


def cb2_lines(uset, used):
    lines = []
    nv = len(uset['vectors'])
    params = {}
    for row in sorted(used):
        if row < nv:
            lines.append('float4 CB2_%d = %s;' % (row, uexpr(uset['vectors'][row], params)))
        else:
            j = (row - nv) * 4
            comps = []
            for c in range(4):
                if j + c < len(uset['scalars']):
                    comps.append('(%s).x' % uexpr(uset['scalars'][j + c], params))
                else:
                    comps.append('0')
            lines.append('float4 CB2_%d = float4(%s);' % (row, ', '.join(comps)))
    return lines


def params_of(uset, used):
    """Every parameter the used rows read: {name: (kind, default)}."""
    params = {}
    nv = len(uset['vectors'])
    for row in sorted(used):
        if row < nv:
            uexpr(uset['vectors'][row], params)
        else:
            j = (row - nv) * 4
            for c in range(4):
                if j + c < len(uset['scalars']):
                    uexpr(uset['scalars'][j + c], params)
    return params
