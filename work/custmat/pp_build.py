"""A custom post-process material for the game: the engine's DefaultPostProcessMaterial (a cooked PostProcess-domain
material every game has, never drawn unless something adds it as a blendable) carrying our own pixel shader, inline.

The carrier's FPostProcessMaterialPS reads the scene colour only. Ours also reads the scene depth: the shader's
resource table gets the SceneTexturesStruct uniform buffer (layout 0x900F88, SceneDepthTexture = resource 1, as the
game's capsule shadow shaders use it) at buffer index 3, and the frozen FShader's parameter bindings get a graph
uniform buffer entry {BufferIndex 3, ByteOffset 8}: FPostProcessMaterialParameters' SceneTextures member, which the
post-process material pass always fills (the same entry the game's FApplyFogPS has, at its own buffer index).
"""
import hashlib, json, os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lz4.block
import psinfo
from custom_mi import find_frozen, parse_shader_map_tail, inline_code
from dxbc import container, signature
from bundle import read_bundle
sys.path.insert(0, '/work/fx1018/editor/Python')
from rebirth_fx import matcore
from rebirth_fx.zen import Zen
from rebirth_fx import iostore_write as W

CARRIER = '/work/anime/pkgs/Engine__EngineMaterials__DefaultPostProcessMaterial.uasset'
BUNDLE = '/data/uploads/FF7R2UProj/Saved/ModExtract/shlib/anime/DefaultPostProcessMaterial.bundle'
PS_RESOURCE = 69
PS_SHADER_AT = 912                     # the FPostProcessMaterialPS object in the frozen image
GRAPH_UNIFORM_BUFFERS = 0x30           # FShaderParameterBindings::GraphUniformBuffers (SQEX: 5 arrays, UE5 order)
SCENE_TEXTURES_LAYOUT = 9441160        # 0x900F88
VIEW_LAYOUT, MATERIAL_LAYOUT = 287775303, 86509815
END = 0xFFFFFFFF

HLSL = r'''// %(title)s
// FINAL FANTASY VII REBIRTH post-process material (after tonemapping), written for the game's FPostProcessMaterialPS slot:
// scene colour from PostProcessInput0, scene depth from SceneTexturesStruct.
cbuffer _Globals : register(b0)
{
    uint2 PostProcessOutput_ViewportMin : packoffset(c37);
    float2 PostProcessOutput_ViewportSizeInverse : packoffset(c38.z);
};
cbuffer View : register(b1)
{
    float4 View_InvDeviceZToWorldZTransform : packoffset(c73);
    float4 View_ViewRectMin : packoffset(c158);
    float4 View_ViewSizeAndInvSize : packoffset(c159);
    float4 View_BufferSizeAndInvSize : packoffset(c161);
    float View_GameTime : packoffset(c172.z);
};
Texture2D PostProcessInput_0_Texture : register(t1);
SamplerState PostProcessInput_0_Sampler : register(s1);
Texture2D<float> SceneTexturesStruct_SceneDepthTexture : register(t2);

%(params)s

float3 SceneColorAt(float2 Pixel)
{
    return PostProcessInput_0_Texture.SampleLevel(PostProcessInput_0_Sampler, Pixel * View_BufferSizeAndInvSize.zw, 0).rgb;
}

float SceneDepthAt(float2 Pixel)
{
    const float DeviceZ = SceneTexturesStruct_SceneDepthTexture.Load(int3(int2(Pixel), 0));
    const float Depth = DeviceZ * View_InvDeviceZToWorldZTransform[0] + View_InvDeviceZToWorldZTransform[1]
        + 1.0 / (DeviceZ * View_InvDeviceZToWorldZTransform[2] - View_InvDeviceZToWorldZTransform[3]);
    return min(abs(Depth), 1.0e7);
}

float Luma(float3 C) { return dot(C, float3(0.299, 0.587, 0.114)); }

%(body)s
'''

ANIME_PARAMS = dict(
    OutlineThickness=1.0,          # pixels at 1080p (scales with resolution)
    OutlineDepthThreshold=0.06,    # relative depth jump that starts a line
    OutlineStrength=0.9,
    OutlineColor=(0.03, 0.025, 0.04),
    OutlineFadeStart=1500.0,       # cm: lines fade out with distance
    OutlineFadeEnd=9000.0,
    ColorEdgeStrength=0.35,        # thin lines on strong colour edges too
    ColorEdgeLow=0.12,
    ColorEdgeHigh=0.35,
    Bands=4.0,                     # cel bands on the image's brightness
    BandSoftness=0.12,
    BandMix=0.5,
    Saturation=1.2,
    Vignette=0.2,
)

ANIME_BODY = r'''float4 MainPS(float4 SvPosition : SV_Position) : SV_Target0
{
    const float2 ViewportUV = (SvPosition.xy - float2(PostProcessOutput_ViewportMin)) * PostProcessOutput_ViewportSizeInverse;
    const float2 Pixel = ViewportUV * View_ViewSizeAndInvSize.xy + View_ViewRectMin.xy;
    float3 Color = SceneColorAt(Pixel);

    // outlines where the depth jumps (silhouettes): this pixel is in front of a neighbour that is much farther away
    const float R = P_OutlineThickness * max(1.0, View_ViewSizeAndInvSize.y / 1080.0);
    const float Depth = SceneDepthAt(Pixel);
    const float Far = max(max(SceneDepthAt(Pixel + float2(R, 0)), SceneDepthAt(Pixel - float2(R, 0))),
                          max(SceneDepthAt(Pixel + float2(0, R)), SceneDepthAt(Pixel - float2(0, R))));
    const float Jump = (Far - Depth) / max(Depth, 1.0);
    float DepthEdge = saturate((Jump - P_OutlineDepthThreshold) / P_OutlineDepthThreshold);
    DepthEdge *= 1.0 - smoothstep(P_OutlineFadeStart, P_OutlineFadeEnd, Depth);

    // thin lines on strong brightness edges (Sobel)
    float L[9];
    [unroll] for (int y = -1; y <= 1; y++)
        [unroll] for (int x = -1; x <= 1; x++)
            L[(y + 1) * 3 + (x + 1)] = Luma(SceneColorAt(Pixel + float2(x, y) * R));
    const float Gx = (L[2] + 2.0 * L[5] + L[8]) - (L[0] + 2.0 * L[3] + L[6]);
    const float Gy = (L[6] + 2.0 * L[7] + L[8]) - (L[0] + 2.0 * L[1] + L[2]);
    float ColorEdge = smoothstep(P_ColorEdgeLow, P_ColorEdgeHigh, sqrt(Gx * Gx + Gy * Gy));
    ColorEdge *= 1.0 - smoothstep(P_OutlineFadeStart, P_OutlineFadeEnd, Depth);

    // cel bands
    const float Y = Luma(Color);
    const float X = Y * P_Bands;
    const float F = floor(X);
    const float Banded = (F + smoothstep(0.5 - P_BandSoftness, 0.5 + P_BandSoftness, X - F)) / P_Bands;
    Color = lerp(Color, Color * (Banded / max(Y, 1.0e-4)), P_BandMix);

    // colour punch
    const float Y2 = Luma(Color);
    Color = max(0.0, lerp(Y2.xxx, Color, P_Saturation));

    // lines
    const float Edge = max(DepthEdge, ColorEdge * P_ColorEdgeStrength);
    Color = lerp(Color, P_OutlineColor, saturate(Edge * P_OutlineStrength));

    // vignette
    const float2 V = ViewportUV * 2.0 - 1.0;
    Color *= 1.0 - P_Vignette * saturate(dot(V, V) * 0.5);
    return float4(Color, 1.0);
}
'''


def params_hlsl(p):
    out = []
    for k, v in sorted(p.items()):
        if isinstance(v, tuple):
            out.append('static const float3 P_%s = float3(%s);' % (k, ', '.join(repr(float(x)) for x in v)))
        else:
            out.append('static const float P_%s = %r;' % (k, float(v)))
    return '\n'.join(out)


def compile_ps(src, out_path):
    import subprocess, tempfile
    with tempfile.NamedTemporaryFile('w', suffix='.hlsl', delete=False) as f:
        f.write(src)
        path = f.name
    try:
        r = subprocess.run([psinfo.DXC, '-T', 'ps_6_6', '-E', 'MainPS', '-O3', '-HV', '2018', path, '-Fo', out_path],
                           capture_output=True, text=True, env=psinfo.ENV)
        if r.returncode:
            raise RuntimeError(r.stderr)
        return open(out_path, 'rb').read()
    finally:
        os.unlink(path)


def resource_table(bits, maps):
    out = struct.pack('<I', bits)
    for name in ('SRVMap', 'SamplerMap', 'UAVMap', 'LayoutHashes', 'TextureMap'):
        m = maps[name]
        out += struct.pack('<i', len(m)) + struct.pack('<%dI' % len(m), *m)
    return out


def optional_data(entries):
    body = b''.join(bytes([ord(k)]) + struct.pack('<I', len(v)) + v for k, v in entries)
    return body + struct.pack('<i', len(body) + 4)


def fstrings(names):
    out = struct.pack('<i', len(names))
    for n in names:
        out += struct.pack('<i', len(n) + 1 if n else 0) + (n.encode() + b'\0' if n else b'')
    return out


def custom_blob(carrier_blob, dxbc):
    """Our PS blob: the carrier's header extended with SceneTexturesStruct at uniform buffer index 3."""
    data, tail = psinfo.data_entries(carrier_blob)
    # (the carrier's own blob must round-trip through our writer)
    at = carrier_blob.find(b'DXBC')
    c = container(carrier_blob, at)
    assert optional_data(data) == carrier_blob[at + c['total']:], 'optional data does not round-trip'
    bits, maps, exact = psinfo.resource_table(carrier_blob)
    assert exact and maps['LayoutHashes'] == [0, VIEW_LAYOUT, MATERIAL_LAYOUT], maps
    new_maps = dict(
        SRVMap=[0, 0, 0, 0, END],
        SamplerMap=[0, 0, 4, 0, (2 << 24) | (1 << 8) | 0, END],             # Material_Texture2D_0Sampler -> s0
        UAVMap=[0, 0, 0, 0, END],
        LayoutHashes=[0, VIEW_LAYOUT, MATERIAL_LAYOUT, SCENE_TEXTURES_LAYOUT],
        TextureMap=[0, 0, 4, 5, (2 << 24) | (0 << 8) | 0,                   # Material_Texture2D_0 -> t0
                    (3 << 24) | (1 << 8) | 2, END],                         # SceneTexturesStruct_SceneDepthTexture -> t2
    )
    header = resource_table(bits | (1 << 3), new_maps)
    entries = []
    for k, v in data:
        if k == 'p':
            v = bytearray(v)
            assert v[:5] == b'\x01\x02\x02\x02\x00', v[:5].hex()
            v[2] = 3                    # SRVs t0..t2
            v = bytes(v)
        elif k == 'u':
            v = fstrings(['', 'View', 'Material', 'SceneTexturesStruct', ''])
        elif k == 'n':
            v = b'AnimeCelPP/FPostProcessMaterialPS/0:RebirthCustom\0'
        entries.append((k, v))
    return header + dxbc + optional_data(entries)


def with_graph_uniform_buffer(ex, buffer_index, byte_offset):
    """The export with a GraphUniformBuffers entry added to the PP pixel shader's frozen parameter bindings: the entry
    is appended to the frozen image (16-aligned) and the empty array at +0x30 of the FShader made to point at it."""
    q = find_frozen(ex, 0)
    t = parse_shader_map_tail(ex, q)
    fz = bytearray(ex[t['frozen_at']:t['frozen_at'] + t['frozen_size']])
    field = PS_SHADER_AT + GRAPH_UNIFORM_BUFFERS
    assert struct.unpack_from('<qii', fz, field) == (0, 0, 0), 'GraphUniformBuffers is not empty'
    # the FShader is the PS of resource 69
    assert struct.unpack_from('<Ii', fz, PS_SHADER_AT + 0xe8) == (0x15, PS_RESOURCE)
    pad = (-len(fz)) % 16
    new_at = len(fz) + pad
    fz += b'\0' * pad + struct.pack('<HH', buffer_index, byte_offset) + b'\0' * 12
    struct.pack_into('<qii', fz, field, ((new_at - field) << 1) | 1, 1, 1)
    out = ex[:q] + struct.pack('<I', len(fz)) + bytes(fz) + ex[t['frozen_at'] + t['frozen_size']:]
    t2 = parse_shader_map_tail(out, q)
    assert t2 and t2['frozen_size'] == len(fz)
    return out


def build(out_dir, title='AnimeCelPP', params=None, body=ANIME_BODY, mod_name='AnimeCelPostProcess_P'):
    p = dict(ANIME_PARAMS)
    p.update(params or {})
    src = HLSL % dict(title=title, params=params_hlsl(p), body=body)
    os.makedirs(out_dir, exist_ok=True)
    open(os.path.join(out_dir, title + '.hlsl'), 'w').write(src)
    dxbc = compile_ps(src, os.path.join(out_dir, title + '.dxbc'))
    shaders = read_bundle(BUNDLE)
    carrier_blob = shaders[PS_RESOURCE]['code']
    cinfo = psinfo.info(carrier_blob)
    # interface: the same signature as the carrier's
    c = container(dxbc, 0)
    sigs = {f: signature(dxbc, o) for f, o, s in c['parts'] if f in ('ISG1', 'OSG1')}
    assert sigs['ISG1'] == cinfo['isg'] and sigs['OSG1'] == cinfo['osg'], (sigs, cinfo['isg'], cinfo['osg'])
    mine = psinfo.dump(dxbc)
    binds = sorted(b[3] for b in psinfo.bindings(mine) if b[3][:1] in 'cts')
    blob = custom_blob(carrier_blob, dxbc)
    # the package
    data = open(CARRIER, 'rb').read()
    z = Zen(data)
    s0, z0 = z.bundle_positions()[0]
    ex = data[s0:s0 + z0]
    q = find_frozen(ex, 0)
    t = parse_shader_map_tail(ex, q)
    ex = bytearray(ex)
    ex[t['id_hash_at']:t['id_hash_at'] + 20] = hashlib.sha1(('RebirthCustom/' + title).encode()).digest()
    ex = with_graph_uniform_buffer(bytes(ex), 3, 8)
    # inline code: every shader of the map as the game has it, ours in place of resource 69
    raw = open(BUNDLE, 'rb').read()
    pos, entries = 0, []
    while pos < len(raw):
        index, size, usize, freq = struct.unpack_from('<IIIB', raw, pos); pos += 13
        hsh = raw[pos:pos + 20]; pos += 20
        entries.append(dict(hash=hsh, code=raw[pos:pos + size], usize=usize, freq=freq)); pos += size
    entries[PS_RESOURCE] = dict(hash=hashlib.sha1(blob).digest(), code=blob, usize=len(blob), freq=5)
    t = parse_shader_map_tail(ex, find_frozen(ex, 0))
    ex = ex[:t['share_at']] + struct.pack('<I', 0) + inline_code(entries)
    pkg = matcore.rebuild(data, export_index=0, new_export=ex)
    assert Zen(pkg).exports[0]['name'] == 'DefaultPostProcessMaterial'
    # the container: the engine package at its own path
    hdr0 = open(os.path.join(HERE, 'pakchunk0_container_header.bin'), 'rb').read()
    from rebirth_fx.hdr import parse_header
    retail = parse_header(hdr0)[1]
    name = '/Engine/EngineMaterials/DefaultPostProcessMaterial'
    pid = W.package_id(name)
    e = retail[pid]
    chunks = [None, dict(id64=pid, type=2, data=pkg, path='EngineMaterials/DefaultPostProcessMaterial.uasset')]
    cid = W.container_id_from_name(mod_name)
    chunks[0] = dict(id64=cid, type=10, data=W.container_header(cid, [dict(
        id=pid, size=len(pkg), export_count=e['export_count'], export_bundle_count=e['export_bundle_count'],
        load_order=e['load_order'], imports=e['imports'])]), path=None)
    base = os.path.join(out_dir, mod_name)
    W.write_container(base, mod_name, chunks, mount='../../../Engine/Content/')
    import shutil
    shutil.copy('/work/fx1018/editor/Python/rebirth_fx/data/empty_P.pak', base + '.pak')
    return dict(files=[base + '.utoc', base + '.ucas', base + '.pak'], bindings=binds, dxbc=len(dxbc), blob=len(blob),
                package=len(pkg))


if __name__ == '__main__':
    r = build(os.path.join(HERE, 'anime', 'pp'))
    print(json.dumps(r, indent=1))
