"""HLSL declarations of the game's uniform buffers (View, Primitive) from the layouts read out of ff7rebirth_.exe.

The game's shaders read View at b0 and Primitive at b1 with these exact offsets (checked against the cbuffer reflection
of the game's own base pass shaders). The editor's generated material code names a few members the game's buffers don't
have; those become constants (STUBS), and using one in the material's live code is reported by the build.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))

# editor-side (engine 4.26 CE) members the game's buffers lack: name -> (HLSL type, array size)
STUBS = {
    'View': {
        'DepthOfFieldSensorWidth': ('float', 0), 'DepthOfFieldScale': ('float', 0), 'DepthOfFieldFocalLength': ('float', 0),
        'DepthOfFieldFocalRegion': ('float', 0), 'DepthOfFieldNearTransitionRegion': ('float', 0),
        'DepthOfFieldFarTransitionRegion': ('float', 0), 'VolumetricFogInvGridSize': ('float3', 0),
        'VolumetricFogGridZParams': ('float3', 0), 'VolumetricFogSVPosToVolumeUV': ('float2', 0),
    },
    'Primitive': {
        'CustomPrimitiveData': ('float4', 8),
    },
}

SCALAR = {'float': 'float', 'int': 'int', 'uint': 'uint', 'bool': 'bool'}


def layouts():
    with open(os.path.join(HERE, 'layouts.json')) as f:
        return json.load(f)


def hlsl_type(m):
    base = SCALAR[m['base_name']]
    rows, cols = m['rows'] or 1, m['columns'] or 1
    if rows > 1:
        return '%s%dx%d' % (base, rows, cols)
    return base if cols == 1 else '%s%d' % (base, cols)


def packoffset(offset):
    reg, byte = divmod(offset, 16)
    return 'c%d' % reg + ('.' + 'xyzw'[byte // 4] if byte else '')


def is_constant(m):
    return m['base_name'] in SCALAR


def declaration(name, members, register, resource_registers=None):
    """cbuffer <name> : register(b<register>) with every constant at its game offset, then the resources (pinned to
    the registers given in resource_registers {member: 't3' / 's0'}, otherwise left to the compiler), then stubs."""
    resource_registers = resource_registers or {}
    lines = ['#ifndef __UniformBuffer_%s_Definition__' % name, '#define __UniformBuffer_%s_Definition__' % name,
             'cbuffer %s : register(b%d)' % (name, register), '{']
    for m in members:
        if not is_constant(m):
            continue
        typ = hlsl_type(m)
        array = '[%d]' % m['elements'] if m['elements'] else ''
        major = 'row_major ' if (m['rows'] or 1) > 1 else ''
        lines.append('    %s%s %s_%s%s : packoffset(%s);' % (major, typ, name, m['name'], array, packoffset(m['offset'])))
    lines.append('};')
    for m in members:
        if is_constant(m):
            continue
        typ = m['type'] or ('SamplerState' if m['base_name'] == 'SAMPLER' else 'Texture2D')
        reg = resource_registers.get(m['name'])
        lines.append('%s %s_%s%s;' % (typ, name, m['name'], ' : register(%s)' % reg if reg else ''))
    for stub, (typ, n) in sorted(STUBS.get(name, {}).items()):
        if n:
            zero = '{' + ', '.join(['(%s)0' % typ] * n) + '}'
            lines.append('static const %s %s_%s[%d] = %s;   // not in the game\'s %s' % (typ, name, stub, n, zero, name))
        else:
            lines.append('static const %s %s_%s = (%s)0;   // not in the game\'s %s' % (typ, name, stub, typ, name))
    lines.append('#endif')
    return '\n'.join(lines) + '\n'


def member_names(name):
    """Every name the declaration gives (for the UB.Member -> UB_Member rewrite and the stub check)."""
    out = set(m['name'] for m in layouts()[name])
    return out | set(STUBS.get(name, {}))


def resource_index(name, member):
    """The member's index among the buffer's resources (the order the game's shader resource tables count them in)."""
    k = 0
    for m in layouts()[name]:
        if is_constant(m):
            continue
        if m['name'] == member:
            return k
        k += 1
    raise KeyError('%s has no resource %s' % (name, member))


def instanced_stereo(name='View'):
    """Engine/Generated/GeneratedInstancedStereo.ush (GenerateInstancedStereoCode): ViewState with the View constants,
    GetPrimaryView() reading them, GetInstancedView() the same (the game draws no instanced stereo)."""
    members = layouts()[name]
    fields, copies = [], []
    for m in members:
        if not is_constant(m):
            continue
        array = '[%d]' % m['elements'] if m['elements'] else ''
        major = 'row_major ' if (m['rows'] or 1) > 1 else ''
        fields.append('    %s%s %s%s;' % (major, hlsl_type(m), m['name'], array))
        copies.append('    Result.%s = %s_%s;' % (m['name'], name, m['name']))
    for stub, (typ, n) in sorted(STUBS.get(name, {}).items()):
        fields.append('    %s %s%s;' % (typ, stub, '[%d]' % n if n else ''))
        copies.append('    Result.%s = %s_%s;' % (stub, name, stub))
    return ('struct ViewState\n{\n' + '\n'.join(fields) + '\n};\n\n'
            'ViewState GetPrimaryView()\n{\n    ViewState Result;\n' + '\n'.join(copies) + '\n    return Result;\n}\n\n'
            'ViewState GetInstancedView()\n{\n    return GetPrimaryView();\n}\n')
