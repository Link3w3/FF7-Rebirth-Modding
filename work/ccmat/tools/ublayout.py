"""UE 4.26 uniform buffer layouts from the engine's own headers (shader parameter structs): every constant member's
byte offset, by the engine's packing (float 4-aligned, float2 8, float3 / float4 / matrices 16, array elements 16).
    ublayout.py view|primitive|opaquebasepass       prints  [float4 slot].comp  member"""
import re
import sys
import os

UE = '/work/ccmat/ue'
SIZES = {'float': (4, 4), 'int32': (4, 4), 'uint32': (4, 4), 'bool': (4, 4), 'FVector2D': (8, 8), 'FIntPoint': (8, 8),
         'FUintVector2': (8, 8), 'FVector': (12, 16), 'FIntVector': (12, 16), 'FVector4': (16, 16), 'FLinearColor': (16, 16),
         'FIntVector4': (16, 16), 'FUintVector4': (16, 16), 'FMatrix': (64, 16), 'FVector2f': (8, 8), 'FVector3f': (12, 16),
         'FVector4f': (16, 16), 'FMatrix44f': (64, 16), 'FIntRect': (16, 16)}
RESOURCE = ('TEXTURE', 'SAMPLER', 'SRV', 'UAV', 'RDG_', 'STRUCT_REF', 'INCLUDED_STRUCT')


def members_from_lines(lines):
    out = []
    for ln in lines:
        s = ln.strip().rstrip('\\').strip()
        m = re.match(r'(VIEW_UNIFORM_BUFFER_MEMBER(?:_EX)?|SHADER_PARAMETER(?:_EX)?)\(\s*([\w:<>]+)\s*,\s*(\w+)', s)
        if m:
            out.append((m.group(2), m.group(3), 1))
            continue
        m = re.match(r'(VIEW_UNIFORM_BUFFER_MEMBER_ARRAY|SHADER_PARAMETER_ARRAY(?:_EX)?)\(\s*([\w:<>]+)\s*,\s*(\w+)\s*,\s*\[\s*([\w:+*()\s]+)\s*\]', s)
        if m:
            n = m.group(4)
            out.append((m.group(2), m.group(3), n))
            continue
        if any(k in s for k in RESOURCE) and s.startswith(('SHADER_PARAMETER', 'VIEW_UNIFORM')):
            out.append(('RESOURCE', s, 0))
    return out


def layout(members, consts=None):
    consts = consts or {}
    off = 0
    rows = []
    for ty, name, n in members:
        if ty == 'RESOURCE':
            continue
        size, align = SIZES[ty]
        if n != 1:
            cnt = eval(str(n).replace('::', '_'), {}, dict(consts, FCustomPrimitiveData_NumCustomPrimitiveDataFloat4s=8))
            off = (off + 15) // 16 * 16
            for k in range(cnt):
                rows.append((off, size, '%s[%d]' % (name, k)))
                off += 16 if size <= 16 else size
            continue
        off = (off + align - 1) // align * align
        rows.append((off, size, name))
        off += size
    return rows


def view():
    src = open(os.path.join(UE, 'SceneView.h'), encoding='latin-1').read().split('\n')
    i = next(k for k, l in enumerate(src) if l.startswith('#define VIEW_UNIFORM_BUFFER_MEMBER_TABLE'))
    j = i + 1
    while src[j].rstrip().endswith('\\'):
        j += 1
    table = src[i + 1:j + 1]
    k = next(k for k, l in enumerate(src) if 'BEGIN_GLOBAL_SHADER_PARAMETER_STRUCT_WITH_CONSTRUCTOR(FViewUniformShaderParameters' in l)
    e = next(x for x in range(k, len(src)) if 'END_GLOBAL_SHADER_PARAMETER_STRUCT' in src[x])
    rest = [l for l in src[k + 1:e] if 'VIEW_UNIFORM_BUFFER_MEMBER_TABLE' not in l]
    consts = {'NUM_ATMOSPHERE_LIGHTS': 2, 'TVC_MAX': 2, 'GMaxGlobalDistanceFieldClipmaps': 4, 'MAX_MOBILE_SHADOWCASCADES': 4}
    return layout(members_from_lines(table) + members_from_lines(rest), consts)


def generic(fname, struct):
    src = open(os.path.join(UE, fname), encoding='latin-1').read().split('\n')
    k = next(k for k, l in enumerate(src) if struct in l and 'BEGIN_' in l)
    e = next(x for x in range(k, len(src)) if 'END_' in src[x] and 'STRUCT' in src[x])
    return layout(members_from_lines(src[k + 1:e]))


def slots(rows):
    """{(float4 index, component): member name}"""
    out = {}
    for off, size, name in rows:
        for b in range(0, size, 4):
            o = off + b
            sub = '' if size == 4 else ('.%s' % 'xyzw'[(b // 4) % 4] if size <= 16 else '[%d].%s' % (b // 16, 'xyzw'[(b // 4) % 4]))
            out[(o // 16, (o // 4) % 4)] = name + sub
    return out


if __name__ == '__main__':
    which = sys.argv[1]
    rows = {'view': view, 'primitive': lambda: generic('PrimitiveUniformShaderParameters.h', 'FPrimitiveUniformShaderParameters'),
            'opaquebasepass': lambda: generic('BasePassRendering.h', 'FOpaqueBasePassUniformParameters')}[which]()
    for off, size, name in rows:
        print('[%3d].%s  +%d  %s' % (off // 16, 'xyzw'[(off // 4) % 4], size, name))
