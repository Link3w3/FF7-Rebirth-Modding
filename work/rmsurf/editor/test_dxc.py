"""Compile the editor's RM_Surface Custom node code (out/RMS_Surface_Editor.hlsl) with DXC for every one of the game's 104
static permutations, inside a stand-in for the engine's material shader (the function the material translator makes of a
Custom node: its inputs as parameters, the static switches as the constants they become, the extra outputs as inout).
Also the "RMS Engine" and "RMS Noise" nodes. Catches syntax and type errors before the editor sees the code.
    test_dxc.py [-k]   (-k keeps the generated .hlsl files in out/dxc)"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.dirname(HERE)
OUT = os.path.join(HERE, 'out')
DXC = '/home/user/microsoft/dxc-build/bin/dxc'
SPEC = json.load(open(os.path.join(OUT, 'RM_SurfaceRebuilt.json')))
RMIS = json.load(open(os.path.join(R, 'rmi_surface.json')))

PRELUDE = r'''
#define PIXELSHADER 1
struct FMaterialPixelParameters
{
    float3x3 TangentToWorld;
    float3 CameraVector;
    float4 SvPosition;
    float3 WorldPosition_CamRelative;
    float TwoSidedSign;
    float4 VertexColor;
};
Texture3D View_PerlinNoise3DTexture;
SamplerState View_PerlinNoise3DTextureSampler;
SamplerState View_SharedBilinearWrappedSampler;
SamplerState View_SharedBilinearClampedSampler;
SamplerState Material_Wrap_WorldGroupSettings;
SamplerState Material_Clamp_WorldGroupSettings;
cbuffer ViewCB
{
    float4 View_InvDeviceZToWorldZTransform;
    float4 View_ViewRectMin;
    float4 View_ViewSizeAndInvSize;
    float View_OneOverPreExposure;
    float3 View_PreViewTranslation;
    uint View_FrameNumber;
};
float4 Texture2DSample(Texture2D Tex, SamplerState Sampler, float2 UV) { return Tex.Sample(Sampler, UV); }
float4 Texture2DSampleLevel(Texture2D Tex, SamplerState Sampler, float2 UV, float Mip) { return Tex.SampleLevel(Sampler, UV, Mip); }
float4 Texture3DSample(Texture3D Tex, SamplerState Sampler, float3 UV) { return Tex.Sample(Sampler, UV); }
'''


def ue_flavour(code):
    # the engine reaches its uniform buffers' members as View.X / Material.X; the stand-in declares them as View_X / Material_X
    return code.replace('View.', 'View_').replace('Material.', 'Material_')


def ftype(k):
    return 'float' if k == 1 else 'float%d' % k


def rms_test(switch_on):
    node = SPEC['node']
    code = ue_flavour(open(os.path.join(OUT, node['code_file'])).read())
    params, args, globs = ['FMaterialPixelParameters Parameters'], ['P'], []
    for name in node['inputs']:
        if name.startswith('T_'):
            params += ['Texture2D %s' % name, 'SamplerState %sSampler' % name]
            args += ['G%s' % name, 'G%sSampler' % name]
            globs += ['Texture2D G%s;' % name, 'SamplerState G%sSampler;' % name]
        elif name.startswith('S_'):
            params.append('float %s' % name)
            args.append('1.00000000' if name[2:] in switch_on else '0.00000000')
        elif name.startswith('UV'):
            params.append('float2 %s' % name)
            args.append({'UV0': 'uv01.xy', 'UV1': 'uv01.zw', 'UV2': 'uv23.xy', 'UV3': 'uv23.zw'}[name])
        elif name == 'RMS_DynamicCoverage':
            params.append('float %s' % name)
            args.append('1.0')
        else:
            params.append('float4 %s' % name)
            args.append('G%s' % name)
            globs.append('float4 G%s;' % name)
    for o in node['outputs']:
        params.append('inout %s %s' % (ftype(o['size']), o['name']))
        args.append(o['name'])
    decl = '\n'.join('    %s %s = (%s)0;' % (ftype(o['size']), o['name'], ftype(o['size'])) for o in node['outputs'])
    keep = ' + '.join('dot(%s, %s)' % (o['name'], o['name']) for o in node['outputs'])
    src = PRELUDE + 'cbuffer Inputs\n{\n' + '\n'.join('    ' + g for g in globs if g.startswith('float4')) + '\n};\n'
    src += '\n'.join(g for g in globs if not g.startswith('float4')) + '\n'
    src += 'float3 CustomExpression0(%s)\n{\n%s\n}\n' % (', '.join(params), code)
    src += '''float4 main(float4 pos : SV_Position, float4 uv01 : TEXCOORD0, float4 uv23 : TEXCOORD1, float3 t0 : TEXCOORD2, float3 t2 : TEXCOORD3, float3 wp : TEXCOORD4) : SV_Target
{
    FMaterialPixelParameters P = (FMaterialPixelParameters)0;
    P.SvPosition = pos;
    P.TangentToWorld = float3x3(t0, cross(t2, t0), t2);
    P.WorldPosition_CamRelative = wp;
    P.CameraVector = normalize(-wp);
    P.TwoSidedSign = 1.0;
%s
    float3 bc = CustomExpression0(%s);
    return float4(bc, %s);
}
''' % (decl, ', '.join(args), keep)
    return src


def engine_test():
    e = SPEC['engine']
    code = ue_flavour(open(os.path.join(OUT, e['code_file'])).read())
    sizes = {'RMS_N': 3, 'RMS_E': 3, 'RMS_W': 3, 'RMS_C': 4}
    params = ['FMaterialPixelParameters Parameters'] + ['%s %s' % (ftype(sizes.get(n, 1)), n) for n, _ in e['inputs']]
    params += ['inout %s %s' % (ftype(o['size']), o['name']) for o in e['outputs']]
    decl = '\n'.join('    %s %s = (%s)0;' % (ftype(o['size']), o['name'], ftype(o['size'])) for o in e['outputs'])
    keep = ' + '.join('dot(%s, %s)' % (o['name'], o['name']) for o in e['outputs'])
    args = ['P'] + ['G.%s' % n if False else ('float%d(1,0,0%s)' % (sizes[n], ',0' if sizes[n] == 4 else '') if n in sizes else '0.5') for n, _ in e['inputs']]
    args += [o['name'] for o in e['outputs']]
    return PRELUDE + 'float3 CustomExpression1(%s)\n{\n%s\n}\n' % (', '.join(params), code) + '''float4 main(float4 pos : SV_Position, float3 t0 : TEXCOORD2, float3 t2 : TEXCOORD3, float3 wp : TEXCOORD4) : SV_Target
{
    FMaterialPixelParameters P = (FMaterialPixelParameters)0;
    P.SvPosition = pos;
    P.TangentToWorld = float3x3(t0, cross(t2, t0), t2);
    P.CameraVector = normalize(-wp);
%s
    float3 n = CustomExpression1(%s);
    return float4(n, %s);
}
''' % (decl, ', '.join(args), keep)


def noise_test():
    code = ue_flavour(open(os.path.join(OUT, SPEC['noise']['code_file'])).read())
    return PRELUDE + 'Texture2D GSTBN; SamplerState GSTBNSampler;\nfloat4 CustomExpression2(FMaterialPixelParameters Parameters, Texture2D STBN, SamplerState STBNSampler)\n{\n%s\n}\n' % code + '''float4 main(float4 pos : SV_Position) : SV_Target
{
    FMaterialPixelParameters P = (FMaterialPixelParameters)0;
    P.SvPosition = pos;
    return CustomExpression2(P, GSTBN, GSTBNSampler);
}
'''


def compile_one(src, path):
    open(path, 'w').write(src)
    p = subprocess.run([DXC, '-T', 'ps_6_0', '-E', 'main', '-O3', '-Fo', path + '.dxil', path], capture_output=True, text=True)
    return p.returncode, (p.stderr or '') + (p.stdout or '')


def main():
    d = os.path.join(OUT, 'dxc')
    os.makedirs(d, exist_ok=True)
    bad = 0
    for name, src in (('engine', engine_test()), ('noise', noise_test())):
        rc, msg = compile_one(src, os.path.join(d, name + '.hlsl'))
        print('%-60s %s' % (name, 'ok' if rc == 0 else 'FAILED'))
        if rc:
            bad += 1
            print(msg[:3000])
    for e in RMIS:
        on = {s.rstrip('_') for s in e['switches']}
        rc, msg = compile_one(rms_test(on), os.path.join(d, e['name'] + '.hlsl'))
        size = os.path.getsize(os.path.join(d, e['name'] + '.hlsl.dxil')) if rc == 0 else 0
        print('%-60s %s' % (e['name'], 'ok (%d bytes)' % size if rc == 0 else 'FAILED'))
        if rc:
            bad += 1
            print(msg[:3000])
    print('%d failed' % bad)
    if '-k' not in sys.argv:
        for f in os.listdir(d):
            os.remove(os.path.join(d, f))


if __name__ == '__main__':
    main()
