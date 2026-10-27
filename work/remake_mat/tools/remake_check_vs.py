"""The vertex side of the rebuilt Remake masters' check: each permutation's base pass vertex shader - the game's 4.18 local
vertex factory with its animation (the material's VertexTransformVector0..2 applied as the game's RigidBody / SoftBody
switches apply them) and the material's VertexContextVector0 - transcribed, the rebuilt graph's vertex code in it, compiled
with Microsoft's compiler and run against the game's own vertex shader on the same random vertices (dxbc2cpp.py).

    remake_check_vs.py <master> [-n cases] [permutation filters...]"""
import json
import os
import re
import subprocess
import sys
import tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dxbc2cpp
import dxbc2hlsl
import lift_check
import remake_check
import remake_graphs
import remake_ue
import ue_mat

ROOT = remake_ue.ROOT
DIS = remake_ue.DIS
VS = 'TBasePassVSFNoLightMapPolicy'
PINS = {'VertexTransformVector0': (4, 'float4(0.0, 0.0, 0.0, 1.0)'), 'VertexTransformVector1': (4, 'float4(0.0, 0.0, 0.0, 1.0)'),
        'VertexTransformVector2': (4, 'float4(0.0, 0.0, 0.0, 0.0)'), 'VertexContextVector0': (4, 'float4(0.0, 0.0, 0.0, 0.0)')}

HELPERS = r'''
''' + remake_check.PARTICLE_STRUCT + r'''
struct FMaterialPixelParameters { float4 SvPosition; float3x3 TangentToWorld; float3 CameraVector; float UnMirrored; uint PrimitiveId;
                                  FMaterialParticleParameters Particle; };
float3 QRotate(float3 V, float4 Q) { return V + 2.0 * cross(Q.xyz, cross(Q.xyz, V) + Q.w * V); }
'''

# the game's 4.18 local vertex factory (its tangent frame re-derived in world space, flipped where the frame mirrors) and
# its animation: RigidBody turns the vertex about the piece's pivot (VertexTransformVector2) by the piece's rotation
# (VertexTransformVector0), scales it (VertexTransformVector1.w) and moves it (VertexTransformVector1.xyz); SoftBody moves
# it (VertexTransformVector1.xyz) and turns only its tangent frame; both turn the tangent frame
VS_LOCAL = r'''
    float3 TX = A_TangentX * 2.0 - 1.0;
    float4 TZ = A_TangentZ * 2.0 - 1.0;
    float3 Pos = A_Position;
#if STATIC_SWITCH_RIGID_BODY || STATIC_SWITCH_SOFT_BODY
    TX = QRotate(TX, P_VertexTransformVector0);
    TZ.xyz = QRotate(TZ.xyz, P_VertexTransformVector0);
#endif
#if STATIC_SWITCH_RIGID_BODY
    Pos = P_VertexTransformVector1.xyz + (QRotate(Pos - P_VertexTransformVector2.xyz, P_VertexTransformVector0) * P_VertexTransformVector1.w + P_VertexTransformVector2.xyz);
#elif STATIC_SWITCH_SOFT_BODY
    Pos = P_VertexTransformVector1.xyz + Pos;
#endif
#if STATIC_SWITCH_FLUID_BODY
    // FluidBody: the vertex is its animation's alone: its position (VertexTransformVector0) and its normal
    // (VertexTransformVector1, 0..1), the tangent frame from the normal and the x axis
    Pos = P_VertexTransformVector0.xyz;
    TZ = float4(normalize(P_VertexTransformVector1.xyz * 2.0 - 1.0), 1.0);
    TX = float3(1.0, 0.0, 0.0);
#endif
    float3x3 L2W = float3x3(Prim[0].xyz, Prim[1].xyz, Prim[2].xyz);
    float3 TY = normalize(cross(TZ.xyz, TX)) * TZ.w;
    float3 YW = mul(TY, L2W);
    float3 ZW = mul(TZ.xyz, L2W);
    float3 XW2 = normalize(cross(YW, ZW));
    float3 TX2 = normalize(cross(TY, TZ.xyz)) * TZ.w;
    float Sign = TZ.w * Prim[9].w;
    float3 XW = mul(TX2, L2W);
    bool Flip = dot(XW, XW2) < 0.0;
    float3 ZW2 = normalize(cross(XW, YW));
    float3 ZN = Flip ? -ZW2 : ZW2;
    float3 XN = Flip ? -XW2 : XW2;
    float3 YN = normalize(cross(ZN, XN));
    bool Neg = Sign < 0.0;
    YN = Neg ? -YN : YN;
    float3 XF = normalize(cross(YN, ZN));
    O_T2W0 = float4(Neg ? -XF : XF, 0.0);
    O_T2W2 = float4(ZN, Sign);
    O_Context = P_VertexContextVector0;
    float3 WPW = mul(Pos, L2W) + Prim[3].xyz;
    float3 TWP = WPW + View[62].xyz;
    O_Position = mul(float4(TWP, 1.0), float4x4(View[0], View[1], View[2], View[3]));
'''

# the game's 4.18 translucent vertex fog (a translucent material without per-pixel fog): the height fog's line integral as
# the pixel's, with the inscattering (the fog's cubemap toward the camera, the directional inscattering by a Cornette-Shanks
# phase, g = -0.6) and the volumetric fog
VS_VERTEX_FOG = r'''
    float3 FogC = TWP - View[60].xyz;
    float FogLen = sqrt(dot(FogC, FogC));
    float Ex = max(FogLen * View[187].w / dot(FogC, View[52].xyz), 0.0);
    float FogInv = 1.0 / FogLen;
    float3 FogDir = -FogC * FogInv;
    float CosT = dot(Globals[12].xyz, FogDir);
    float HG = -CosT * -1.2 + 1.36;
    float Phase = (CosT * CosT + 1.0) * (HG < 0.000001 ? 0.0 : pow(abs(HG), -1.5)) * 0.03237049;
    float3 Inscat = FogCube.SampleLevel(FogCubeSampler, FogDir, 0.0).xyz + Globals[13].xyz * Phase;
    Ex = max(Ex, Globals[7].w);
    bool Excl = 0.0 < Ex;
    float ExT = FogInv * Ex;
    float ExZ = ExT * FogC.z + View[59].z;
    float ExToZ = -ExT * FogC.z + FogC.z;
    float ExLen = FogLen * (-Ex * FogInv + 1.0);
    float Expo = max((ExZ - Globals[9].y) * Globals[7].y, -127.0);
    float RayOrigin = Excl ? exp2(-Expo) * Globals[9].x : Globals[7].x;
    float RayLen = Excl ? ExLen : FogLen;
    float RayZ = Excl ? ExToZ : FogC.z;
    float Fall = max(RayZ * Globals[7].y, -127.0);
    float Shared = (0.01 < abs(Fall)) ? (1.0 - exp2(-Fall)) / Fall : (0.6931472 - 0.2402265 * Fall);
    float Fog = min(exp2(Shared * (RayOrigin * -RayLen)), 1.0);
    float3 FogColor = Inscat * Globals[8].xyz * (1.0 - Fog);
    if (0.0 < Globals[14].y)
    {
        float3 FCl = WPW.y * View[5].xyw + WPW.x * View[4].xyw + WPW.z * View[6].xyw + View[7].xyw;
        float2 FUV = FCl.xy * (1.0 / FCl.z) * float2(0.5, -0.5) + 0.5;
        float FZ = log2(FCl.z * View[187].x + View[187].y) * View[187].z;
        float2 FG = min(max(FUV * View[183].xy, 0.5), View[183].xy - 0.5);
        float4 VF = VolumetricFog.SampleLevel(VolumetricFogSampler, float3(FG * View[186].xy, FZ * View[185].z), 0.0);
        FogColor = FogColor * VF.w + VF.xyz * View[128].y;
        Fog *= VF.w;
    }
    O_VertexFog = float4(FogColor * Globals[9].w, Globals[9].w * (Fog - 1.0) + 1.0);
'''

# the game's 4.18 distortion pass's vertex side: where the surface moves to, along its tangent (or its normal, its binormal
# - the material's velocity switches)
VS_DISTORTION = r'''
    float3 Velocity = float3(0.0, 0.0, 0.0);
#if STATIC_SWITCH_VELOCITY_TANGENT
    Velocity = O_T2W0.xyz;
#elif STATIC_SWITCH_VELOCITY_NORMAL
    Velocity = O_T2W2.xyz;
#elif STATIC_SWITCH_VELOCITY_BINORMAL
    Velocity = cross(O_T2W2.xyz, O_T2W0.xyz) * O_T2W2.w;
#endif
    O_Destination = mul(float4(TWP + Velocity, 1.0), float4x4(View[0], View[1], View[2], View[3]));
'''
DISTORTION_VS = 'TDistortionMeshVS_FDistortMeshAccumulatePolicy_'

SEM_IN = {('ATTRIBUTE', '0'): ('float3', 'A_Position'), ('ATTRIBUTE', '1'): ('float3', 'A_TangentX'),
          ('ATTRIBUTE', '2'): ('float4', 'A_TangentZ'), ('ATTRIBUTE', '4'): ('float4', 'A_TexCoord01'),
          ('ATTRIBUTE', '5'): ('float4', 'A_TexCoord23'), ('ATTRIBUTE', '15'): ('float2', 'A_LightMap')}
SEM_OUT = {('TEXCOORD', '0'): 'A_TexCoord01', ('TEXCOORD', '1'): 'float4(A_TexCoord23.xy, 0.0, 0.0)',
           ('TEXCOORD', '6'): 'O_T2W0', ('TEXCOORD', '7'): 'O_T2W2', ('VertexContextVector', '0'): 'O_Context',
           ('SV_POSITION', '0'): 'O_Position', ('SV_Position', '0'): 'O_Position', ('SV_CullDistance', '0'): '0.0', ('PixelPosition', '0'): 'float4(TWP, 1.0)',
           # (the depth-only shaders of the vertex factory with the static lighting's: the lightmap coordinate, the position)
           ('TEXCOORD', '3'): 'float4(A_LightMap * PLB[16].xy + PLB[16].zw, 0.0, 0.0)', ('WorldPosition', '0'): 'float4(TWP, 1.0)',
           # (with PreSkinnedNormal: the vertex's own tangent frame, unskinned, in the mesh's space; the sign the world one's)
           ('PreSkinnedMatrix', '0'): 'float4(A_TangentX * 2.0 - 1.0, 0.0)', ('PreSkinnedMatrix', '2'): 'float4(A_TangentZ.xyz * 2.0 - 1.0, O_T2W2.w)',
           ('VertexFog', '0'): 'O_VertexFog',
           # (the distortion pass: the clip position and the moved one; the local vertex factory's sub-image coordinates, none)
           ('SourceClipPosition', '0'): 'O_Position', ('DestinationClipPosition', '0'): 'O_Destination',
           ('TEXCOORD', '2'): 'float4(0.0, 0.0, 0.0, 0.0)'}


def shader_source(perm, material, vs=VS):
    asm = open(os.path.join(DIS, perm, vs + '.asm'), encoding='latin-1').read()
    bind = json.load(open(os.path.join(DIS, perm, 'bindings.json')))[vs]
    uset = remake_ue.uniform_sets()[perm]
    info = remake_ue.parse_debug(uset['debug'])
    L = dxbc2hlsl.Lifter(asm)
    out = [HELPERS]
    cbnames = bind['cb']
    for b, n in sorted(L.cbs.items()):
        nm = remake_check.BUFFER_NAMES.get(cbnames[b] if b < len(cbnames) else '', 'CB%d' % b)
        out.append('cbuffer CB%d : register(b%d) { float4 %s[%d]; };' % (b, b, nm, max(n, 160) if nm == 'View' else max(n, 10) if nm == 'Prim' else n))
    raw = remake_check.raw_layout(uset, material)
    out.append('cbuffer CBRaw : register(b%d) { float4 Raw[%d]; };' % (remake_check.RAW_SLOT, max(1, len(raw))))
    textures = list(uset['textures2d']) + list(uset['texturescube'])
    tex_regs, smp_regs = {}, {}
    for t, (ub, res) in bind['t'].items():
        if ub == 'Material' and res // 2 < len(textures):
            tex_regs[textures[res // 2]['name']] = int(t)
    shared, view_t, view_s = {}, {}, {}
    for t, (ub, res) in bind['t'].items():
        if ub == 'View':
            view_t[res] = int(t)
    for s_, (ub, res) in bind['s'].items():
        if ub == 'Material' and res % 2 == 1 and (res - 1) // 2 < len(textures):
            smp_regs[textures[(res - 1) // 2]['name']] = int(s_)
        elif ub == 'Material' and res in (2 * len(textures), 2 * len(textures) + 1):
            shared['Wrap' if res == 2 * len(textures) else 'Clamp'] = int(s_)
        elif ub == 'View':
            view_s[res] = int(s_)
    texmap = {}
    for k, tp in enumerate(textures):
        nm = tp['name']
        if nm in tex_regs:
            ident = 'MT%d' % k
            out.append('%s %s : register(t%d);' % ('TextureCube' if k >= len(uset['textures2d']) else 'Texture2D', ident, tex_regs[nm]))
            sreg = smp_regs.get(nm)
            out.append('SamplerState %sSampler%s;' % (ident, '' if sreg is None else ' : register(s%d)' % sreg))
            texmap[nm] = (ident, ident + 'Sampler')

    out.extend(remake_check.shared_decls(shared, True))
    # the translucent vertex fog's cubemap and the volumetric fog (the textures of the shader's that are no one's else)
    for kind, name in (('texturecube', 'FogCube'), ('texture3d', 'VolumetricFog')):
        regs = [t for t in re.findall(r'dcl_resource_%s \(float,float,float,float\) t(\d+)' % kind, asm) if bind['t'].get(t, ['', 0])[0] != 'View']
        m = regs and re.search(r'sample\w*\(%s\)\([^)]*\) [^,]+, [^,]+, t%s\.\w+, s(\d+)' % (kind, regs[0]), asm)
        out.append('%s %s%s;' % ('TextureCube' if kind == 'texturecube' else 'Texture3D', name, ' : register(t%s)' % regs[0] if regs else ''))
        out.append('SamplerState %sSampler%s;' % (name, ' : register(s%s)' % m.group(1) if m else ''))
    # the game's 3D noise the directional tilt samples (the View's texture 31, its sampler 25)
    out.append('Texture3D TiltNoise3D%s;' % (' : register(t%d)' % view_t[31] if 31 in view_t else ''))
    out.append('SamplerState TiltNoise3DSampler%s;' % (' : register(s%d)' % view_s[25] if 25 in view_s else ''))
    extra_decl = []

    class Missing(dict):
        # a texture this vertex shader of the game's does not read (dead code here: the outputs it feeds are not this
        # shader's): declared without a register; if the rebuilt shader did read it, its made-up texture would differ
        def __missing__(self, k):
            ident = 'XT%d' % len(extra_decl)
            extra_decl.append('Texture2D %s; SamplerState %sSampler;' % (ident, ident))
            self[k] = (ident, ident + 'Sampler')
            return self[k]

    class Params(dict):
        def __missing__(self, k):
            raise KeyError('parameter %s is not in the uniform set of %s' % (k, perm))
    pv = Params()
    vnames = remake_check.vector_params(uset)
    for i, n in enumerate(raw):
        pv[n] = ('Raw[%d]' if n in vnames else 'Raw[%d].x') % i
    uvs = {0: 'A_TexCoord01.xy', 1: 'A_TexCoord01.zw', 2: 'A_TexCoord23.xy', 3: 'A_TexCoord23.zw'}
    lines, res, tr = ue_mat.translate(material, info['switches'], Missing(texmap), pv, uvs, PINS, vertex=True,
                                      extra={'TwoSidedSign': '1.0', 'TiltNoise': ('TiltNoise3D', 'TiltNoise3DSampler'),
                                             'NearPlane': 'View[138].x', 'PreViewTranslation': 'View[62].xyz', 'CameraPositionWS': 'View[59].xyz',
                                             **remake_check.SHARED_HOOKS})
    out.extend(extra_decl)
    for k, v in sorted(ue_mat.definitions(material, info['switches']).items()):
        out.append('#define %s %d' % (k, int(v)))
    out.extend(tr.custom_funcs)
    sprite = '__Sprite' in vs
    if sprite:
        # (a sprite vertex shader without the particle's colour - position only - has nothing of the material's to compare)
        return sprite_source(out, lines, res, tr, L, asm), raw, info
    params_sig, setup, have = [], [], set()
    for r in L.input_sig:
        sem, idx, reg, sysv = r[0], r[1], int(r[3]), r[4]
        if sysv == 'INSTID':
            params_sig.append('uint in_v%d : SV_InstanceID' % reg)
            continue
        t, nm = SEM_IN.get((sem, idx), ('float4', 'A_%s%s' % (sem, idx)))
        params_sig.append('%s %s : %s%s' % (t, nm, sem, idx))
        have.add(nm)
    for nm in ('A_TexCoord01', 'A_TexCoord23'):
        if nm not in have:
            setup.append('float4 %s = float4(0.0, 0.0, 0.0, 0.0);' % nm)
    outs = []
    for r in L.output_sig:
        sem, idx, reg, sysv = r[0], r[1], r[3], r[4]
        mask = r[2]
        if sysv == 'POS':
            params_sig.append('out float4 o%s : SV_Position' % reg)
        elif sysv == 'CULLDST':
            params_sig.append('out float o%s : SV_CullDistance%s' % (reg, idx))
        else:
            params_sig.append('out float4 o%s : %s%s' % (reg, sem, idx))
        outs.append((reg, SEM_OUT[(sem, idx)], sysv))
    body = ['void main(%s)' % ',\n          '.join(params_sig), '{']
    body.extend('    ' + s for s in setup)
    body.append('    FMaterialPixelParameters Parameters = (FMaterialPixelParameters)0;')
    body.append('    float4 O_T2W0, O_T2W2, O_Context, O_Position, O_VertexFog, O_Destination;')
    body.extend('    ' + l for l in lines)
    for pin, (t, d) in PINS.items():
        body.append('    %s P_%s = %s;' % (ue_mat.TYPE_NAMES[t], pin, res[pin].code))
    body.append(VS_LOCAL)
    if any(expr == 'O_VertexFog' for reg, expr, sysv in outs):
        body.append(VS_VERTEX_FOG)
    if any(expr == 'O_Destination' for reg, expr, sysv in outs):
        body.append(VS_DISTORTION)
    for reg, expr, sysv in outs:
        body.append('    o%s = %s;' % (reg, expr))
        # the texture coordinates the material does not use: the game's vertex factory writes zeros
        if expr.startswith('A_TexCoord') or expr.startswith('float4(A_TexCoord'):
            for m in re.finditer(r'^mov o%s\.([xyzw]+), l\(0x00000000(?:, ?0x00000000)*\)' % reg, asm, re.M):
                body.append('    o%s.%s = 0.0;' % (reg, m.group(1)))
    body.append('}')
    return '\n'.join(out + body), raw, info


# the game's sprite particle vertex factory's vertex attributes
SEM_IN_SPRITE = {('ATTRIBUTE', '0'): ('float4', 'A_Position'), ('ATTRIBUTE', '1'): ('float4', 'A_OldPosition'),
                 ('ATTRIBUTE', '2'): ('float4', 'A_SizeRotSubImage'), ('ATTRIBUTE', '3'): ('float4', 'A_Color'),
                 ('ATTRIBUTE', '4'): ('float2', 'A_TexCoord'), ('ATTRIBUTE', '5'): ('float4', 'A_DynamicParameter')}


def sprite_source(out, lines, res, tr, L, asm):
    """the material's part of the game's sprite vertex shader alone (the sprite vertex factory itself is not
    transcribed): the particle's colour, its alpha times the material's view modifier (VertexContextVector0.x) - the
    one output the check compares (COMPARE_ONLY)"""
    params_sig, color = [], None
    for r in L.input_sig:
        sem, idx, reg, sysv = r[0], r[1], int(r[3]), r[4]
        if sysv in ('INSTID', 'VERTID'):
            params_sig.append('uint in_v%d : %s' % (reg, 'SV_InstanceID' if sysv == 'INSTID' else 'SV_VertexID'))
            continue
        t, nm = SEM_IN_SPRITE.get((sem, idx), ('float4', 'A_%s%s' % (sem, idx)))
        params_sig.append('%s %s : %s%s' % (t, nm, sem, idx))
    regs = []
    for r in L.output_sig:
        sem, idx, reg, sysv = r[0], r[1], r[3], r[4]
        if sysv == 'POS':
            params_sig.append('out float4 o%s : SV_Position' % reg)
        elif sysv == 'CULLDST':
            params_sig.append('out float o%s : SV_CullDistance%s' % (reg, idx))
            regs.append((reg, '0.0'))
            continue
        else:
            params_sig.append('out float4 o%s : %s%s' % (reg, sem, idx))
        regs.append((reg, 'float4(0.0, 0.0, 0.0, 0.0)'))
        if (sem, idx) == ('TEXCOORD', '5'):
            color = reg
    if color is None:
        return None
    body = ['#define COMPARE_ONLY %s' % color, 'void main(%s)' % ',\n          '.join(params_sig), '{']
    body.append('    FMaterialPixelParameters Parameters = (FMaterialPixelParameters)0;')
    body.append('    Parameters.Particle.Color = A_Color;')
    body.append('    Parameters.Particle.TranslatedWorldPositionAndSize = float4(mul(float4(A_Position.xyz, 1.0), '
                'float4x4(Prim[0], Prim[1], Prim[2], Prim[3])).xyz + View[62].xyz, 0.0);')
    body.extend('    ' + l for l in lines)
    for pin, (t, d) in PINS.items():
        body.append('    %s P_%s = %s;' % (ue_mat.TYPE_NAMES[t], pin, res[pin].code))
    for reg, zero in regs:
        body.append('    o%s = %s;' % (reg, zero))
    body.append('    o%s = float4(A_Color.xyz, P_VertexContextVector0.x * A_Color.w);' % color)
    body.append('}')
    return '\n'.join(['#define PARTICLE_SPRITE_FACTORY 1'] + out + body)


DRIVER = r'''
#include <random>
#include <cstdio>
#include <cstring>
#include <cmath>
struct F4 { double c[4]; F4(double x = 0, double y = 0, double z = 0, double w = 0) { c[0] = x; c[1] = y; c[2] = z; c[3] = w; } };
static F4 operator+(F4 a, F4 b) { return F4(a.c[0] + b.c[0], a.c[1] + b.c[1], a.c[2] + b.c[2], a.c[3] + b.c[3]); }
static F4 operator-(F4 a, F4 b) { return F4(a.c[0] - b.c[0], a.c[1] - b.c[1], a.c[2] - b.c[2], a.c[3] - b.c[3]); }
static F4 operator*(F4 a, F4 b) { return F4(a.c[0] * b.c[0], a.c[1] * b.c[1], a.c[2] * b.c[2], a.c[3] * b.c[3]); }
static F4 operator/(F4 a, F4 b) { return F4(a.c[0] / b.c[0], a.c[1] / b.c[1], a.c[2] / b.c[2], a.c[3] / b.c[3]); }
static double dot4(F4 a, F4 b) { return a.c[0] * b.c[0] + a.c[1] * b.c[1] + a.c[2] * b.c[2] + a.c[3] * b.c[3]; }
static F4 BC(double x) { return F4(x, x, x, x); }
static F4 clamp4(F4 x, F4 lo, F4 hi) { F4 r; for (int i = 0; i < 4; ++i) r.c[i] = std::min(std::max(x.c[i], lo.c[i]), hi.c[i]); return r; }
static F4 max4(F4 a, F4 b) { F4 r; for (int i = 0; i < 4; ++i) r.c[i] = std::max(a.c[i], b.c[i]); return r; }
static F4 frac4(F4 a) { F4 r; for (int i = 0; i < 4; ++i) r.c[i] = a.c[i] - std::floor(a.c[i]); return r; }
static F4 sqrt4(F4 a) { F4 r; for (int i = 0; i < 4; ++i) r.c[i] = std::sqrt(a.c[i]); return r; }
static std::mt19937_64 rng;
static double U(double a, double b) { return a + (b - a) * std::uniform_real_distribution<double>(0, 1)(rng); }
static uint32_t fbits(float f) { uint32_t u; std::memcpy(&u, &f, 4); return u; }
static float bitsf(uint32_t u) { float f; std::memcpy(&f, &u, 4); return f; }
int main(int argc, char** argv)
{
    const int N = argc > 1 ? atoi(argv[1]) : 200;
    double maxd[10][4] = {};
    int nanmis[10][4] = {};
    for (int k = 0; k < N; ++k)
    {
        rng.seed(9000 + k);
        DXIO a;
        for (int r = 0; r < 40; ++r)
            for (int c = 0; c < 4; ++c)
                a.v[r][c] = LF(D(U(0.0, 1.0), 0, 0));
        // the position anywhere, the packed tangents (0..1, their sign 0 or 1), the texture coordinates in 0..1
        for (int c = 0; c < 3; ++c) a.v[0][c] = LF(D(U(-100.0, 100.0), 0, 0));
        a.v[2][3] = LF(D(U(0, 1) < 0.5 ? 0.0 : 1.0, 0, 0));
        for (int b = 0; b < 16; ++b)
        {
            a.cb[b].resize(256);
            for (auto& row : a.cb[b])
                for (int c = 0; c < 4; ++c)
                    row[c] = fbits((float)U(-2.0, 2.0));
        }
        // the primitive's determinant sign: +-1
        a.cb[PRIMSLOT][9][3] = fbits(U(0, 1) < 0.5 ? -1.0f : 1.0f);
        for (auto& row : a.cb[RAWSLOT])
            for (int c = 0; c < 4; ++c)
                row[c] = fbits((float)U(-0.2, 9.5));
        auto RAW = [&](int i) { return F4(bitsf(a.cb[RAWSLOT][i][0]), bitsf(a.cb[RAWSLOT][i][1]), bitsf(a.cb[RAWSLOT][i][2]), bitsf(a.cb[RAWSLOT][i][3])); };
        (void)RAW;
FILL_MATERIAL
        for (int t = 0; t < 128; ++t) a.tex[t] = 0x1234567ULL * (t + 1) + k * 7919ULL;
        for (int s = 0; s < 16; ++s) a.samp[s] = s + 1;
        DXIO b = a;
        shader_orig(a);
        shader_rebuilt(b);
        for (int o = 0; o < 10; ++o)
            for (int c = 0; c < 4; ++c)
            {
#ifdef COMPARE_ONLY
                if (o != COMPARE_ONLY) continue;
#endif
                const double x = a.o[o][c].f.v, y = b.o[o][c].f.v;
                if (std::isnan(x) || std::isnan(y)) { if (std::isnan(x) != std::isnan(y)) ++nanmis[o][c]; continue; }
                const double d = std::fabs(x - y) / std::max(1.0, std::fabs(x));
                if (d > maxd[o][c]) maxd[o][c] = d;
            }
    }
    double worst = 0;
    for (int o = 0; o < 10; ++o)
        for (int c = 0; c < 4; ++c)
            if (maxd[o][c] > worst) worst = maxd[o][c];
    printf("cases %d worst %.3g\n", N, worst);
    for (int o = 0; o < 10; ++o)
    {
        bool any = false;
        for (int c = 0; c < 4; ++c) any |= maxd[o][c] > 1e-4 || nanmis[o][c];
        if (any)
            printf("  o%d: %.3g %.3g %.3g %.3g  nan-mismatch %d %d %d %d\n", o, maxd[o][0], maxd[o][1], maxd[o][2], maxd[o][3],
                   nanmis[o][0], nanmis[o][1], nanmis[o][2], nanmis[o][3]);
    }
    return 0;
}
'''


def check(master, perm, n=200, keep=None, vs=VS):
    material = remake_graphs.MASTERS[master]()
    src, raw, info = shader_source(perm, material, vs)
    if src is None:
        return {'result': 'skipped (nothing of the material\'s to compare)', 'hlsl': None}
    work = keep or tempfile.mkdtemp(prefix='rchkvs_', dir='/tmp/scratch')
    hp = os.path.join(work, '%s_%s.hlsl' % (perm, vs))
    open(hp, 'w').write(src)
    asm_orig = open(os.path.join(DIS, perm, vs + '.asm'), encoding='latin-1').read()
    try:
        asm_new = lift_check.fxc(hp, 'vs_5_0', hp[:-5] + '.dxbc')
    except RuntimeError as ex:
        return {'error': str(ex)[-3000:], 'hlsl': hp}
    bind = json.load(open(os.path.join(DIS, perm, 'bindings.json')))[vs]
    cbn = bind['cb']
    mat_slot = cbn.index('Material') if 'Material' in cbn else 15
    prim_slot = cbn.index('Primitive') if 'Primitive' in cbn else 14
    uset = remake_ue.uniform_sets()[perm]
    fill = remake_check.uniform_cpp(uset, raw, mat_slot)
    only = re.search(r'#define COMPARE_ONLY (\d+)', src)
    cpp = ['#include "dxbc_cpu.hpp"', '#define PRIMSLOT %d' % prim_slot, '#define RAWSLOT %d' % remake_check.RAW_SLOT,
           '#define COMPARE_ONLY %s' % only.group(1) if only else '',
           dxbc2cpp.translate(asm_orig, 'shader_orig'), dxbc2cpp.translate(asm_new, 'shader_rebuilt'),
           DRIVER.replace('FILL_MATERIAL', fill)]
    cp = os.path.join(work, '%s_%s.cpp' % (perm, vs))
    open(cp, 'w').write('\n'.join(cpp))
    exe = cp[:-4]
    p = subprocess.run(['g++', '-std=c++17', '-O1', '-w', '-I' + lift_check.HERE, '-I' + lift_check.HARNESS, cp, '-o', exe],
                       capture_output=True, text=True)
    if p.returncode:
        return {'error': 'g++: ' + p.stderr[-3000:], 'hlsl': hp}
    p = subprocess.run([exe, str(n)], capture_output=True, text=True)
    if not keep:
        # (each check's files are megabytes: only a failed one's are kept, to look at)
        import shutil
        shutil.rmtree(work, ignore_errors=True)
    return {'result': p.stdout.strip(), 'hlsl': hp}


def main():
    args = sys.argv[1:]
    n = 200
    if '-n' in args:
        i = args.index('-n'); n = int(args[i + 1]); del args[i:i + 2]
    after = None
    if '--after' in args:
        i = args.index('--after'); after = args[i + 1]; del args[i:i + 2]
    master = args[0]
    flt = [f for f in args[1:] if not f.startswith('!')]
    excl = [f[1:] for f in args[1:] if f.startswith('!')]
    for p in remake_check.permutations(master):
        if flt and not any(f in p['name'] for f in flt) or any(f in p['name'] for f in excl) or (after and p['name'] <= after):
            continue
        # the base pass's and every depth-only one the package has (one per vertex factory variant)
        files = os.listdir(os.path.join(DIS, p['name']))
        base = sorted((f[:-4] for f in files if f.startswith(VS) and f.endswith('.asm')), key=lambda f: (len(f), f))
        depth = sorted((f[:-4] for f in files if f.startswith('TDepthOnlyVS_false_') and f.endswith('.asm')), key=lambda f: (len(f), f))
        distortion = [d for d in (DISTORTION_VS, DISTORTION_VS + '__Sprite') if d + '.asm' in files]
        for vs in base + depth + distortion:
            if not os.path.exists(os.path.join(DIS, p['name'], vs + '.asm')):
                continue
            try:
                r = check(master, p['name'], n, vs=vs)
            except Exception as ex:
                r = {'error': '%s: %s' % (type(ex).__name__, ex), 'hlsl': ''}
            tag = '%-70s %-8s' % (p['name'], 'vertex' + vs[len(VS):] if vs.startswith(VS) else 'distortion-vs' + vs[len(DISTORTION_VS):] if vs.startswith(DISTORTION_VS)
                                  else 'depth' + vs[len('TDepthOnlyVS_false_'):])
            if 'error' in r:
                print(tag, 'ERROR', r['error'].strip().splitlines()[-1][:300], '(%s)' % r['hlsl'])
            else:
                print(tag, r['result'].replace('\n', '\n' + ' ' * 80))


if __name__ == '__main__':
    main()
