"""Compile the generated Remake Custom nodes (gen/<name>.json) with Microsoft's compiler under Wine inside a stand-in
for the editor's material shader (the function the material translator makes of a Custom node). Catches syntax and type
errors before the editor sees the code.   test_remake_fxc.py <name> [...]"""
import json, os, subprocess, sys
ROOT = '/work/remake_mat'
WINE = '/usr/lib/wine/wine64'
FXCW = '/work/fxcw/fxcw.exe'
FXCDLL = 'Z:\\work\\fxcw\\d3dcompiler_47.dll'
PRELUDE = r'''
#define PIXELSHADER 1
struct FMaterialPixelParameters
{
    float3x3 TangentToWorld;
    float4 SvPosition;
    float3 WorldPosition_CamRelative;
    float4 VertexColor;
    uint PrimitiveId;
};
struct FPrimitiveSceneData
{
    float4x4 LocalToWorld;
    float4 InvNonUniformScaleAndDeterminantSign;
    float4 ObjectWorldPositionAndRadius;
    float4x4 WorldToLocal;
    float3 ActorWorldPosition;
    float3 ObjectBounds;
    float DecalReceiverMask;
};
StructuredBuffer<FPrimitiveSceneData> GPrims;
FPrimitiveSceneData GetPrimitiveData(uint Id) { return GPrims[Id]; }
SamplerState View_SharedBilinearWrappedSampler;
cbuffer ViewCB
{
    float4x4 View_TranslatedWorldToClip;
    float4x4 View_SVPositionToTranslatedWorld;
    float3 View_PreViewTranslation;
    uint View_StateFrameIndexMod8;
};
'''


def ue_flavour(code):
    return code.replace('View.', 'View_')


def ftype(k):
    return 'float' if k == 1 else 'float%d' % k


def node_src(node, fname):
    params, args, globs = ['FMaterialPixelParameters Parameters'], ['P'], []
    for i in node['inputs']:
        n, k = i['name'], i['kind']
        if k == 'uv':
            params.append('float2 %s' % n); args.append('uv%d' % (i['index'] % 2 * 2) and ('uvs[%d]' % i['index']))
        elif k in ('texture2d', 'texturecube', 'bluenoise'):
            ty = {'texture2d': 'Texture2D', 'texturecube': 'TextureCube', 'bluenoise': 'Texture3D'}[k]
            params += ['%s %s' % (ty, n), 'SamplerState %sSampler' % n]
            args += ['G%s' % n, 'G%sSampler' % n]
            globs += ['%s G%s;' % (ty, n), 'SamplerState G%sSampler;' % n]
        elif k == 'scalar':
            params.append('float %s' % n); args.append('G%s.x' % n); globs.append('float4 G%s;' % n)
        else:
            params.append('float4 %s' % n); args.append('G%s' % n); globs.append('float4 G%s;' % n)
    for o in node['outputs']:
        params.append('inout %s %s' % (ftype(o['size']), o['name']))
        args.append(o['name'])
    decl = '\n'.join('    %s %s = (%s)0;' % (ftype(o['size']), o['name'], ftype(o['size'])) for o in node['outputs'])
    keep = ' + '.join(['0.0'] + ['dot(%s, %s)' % (o['name'], o['name']) for o in node['outputs']])
    rt = ftype(node['main_size'])
    src = PRELUDE + 'cbuffer Inputs\n{\n' + '\n'.join('    ' + g for g in globs if g.startswith('float4')) + '\n};\n'
    src += '\n'.join(g for g in globs if not g.startswith('float4')) + '\n'
    src += '%s %s(%s)\n{\n%s\n}\n' % (rt, fname, ', '.join(params), ue_flavour(node['code']))
    src += '''float4 main(float4 pos : SV_Position, float4 uv01 : TEXCOORD0, float4 uv23 : TEXCOORD1, float3 t0 : TEXCOORD2, float3 t2 : TEXCOORD3, float3 wp : TEXCOORD4, nointerpolation uint pid : TEXCOORD5) : SV_Target
{
    FMaterialPixelParameters P = (FMaterialPixelParameters)0;
    P.SvPosition = pos;
    P.TangentToWorld = float3x3(t0, cross(t2, t0), t2);
    P.WorldPosition_CamRelative = wp;
    P.PrimitiveId = pid;
    float2 uvs[4] = { uv01.xy, uv01.zw, uv23.xy, uv23.zw };
%s
    %s m = %s(%s);
    return float4(dot(m, m), %s, 0.0, 1.0);
}
''' % (decl, rt, fname, ', '.join(args), keep)
    return src


def compile_one(src, path):
    open(path, 'w').write(src)
    env = dict(os.environ, WINEPREFIX='/tmp/wpfx', WINEDEBUG='-all', WINEDLLOVERRIDES='d3dcompiler_47=n')
    p = subprocess.run([WINE, FXCW, FXCDLL, 'Z:' + path.replace('/', '\\'), 'ps_5_0', 'main', 'Z:' + (path + '.dxbc').replace('/', '\\'), '9000'],
                       capture_output=True, text=True, env=env)
    out = (p.stdout or '') + (p.stderr or '')
    return 'FXC OK' in out, out


def main():
    d = os.path.join(ROOT, 'gen', 'fxc')
    os.makedirs(d, exist_ok=True)
    bad = 0
    perms = []
    for m in sys.argv[1:]:
        spec = json.load(open(os.path.join(ROOT, 'gen', 'masters', m + '.json')))
        perms += spec['permutations']
    for r in perms:
        name = r['name']
        for kind in ('base', 'coverage'):
            node = r.get(kind)
            if not node:
                continue
            ok, msg = compile_one(node_src(node, 'CustomExpression0'), os.path.join(d, '%s_%s.hlsl' % (name, kind)))
            print('%-60s %-9s %s' % (name, kind, 'ok' if ok else 'FAILED'))
            if not ok:
                bad += 1
                print('\n'.join(l for l in msg.splitlines() if 'error' in l.lower())[:3000])
    print(bad, 'failed')


if __name__ == '__main__':
    main()
