"""Compiles an exported editor material (material.hlsl + material.json from ExportMaterialForGame) into a base pass pixel
shader for one of the game's carriers.

  stage()      the engine's shader sources (as the editor has them) with the game's View/Primitive declarations, the
               material's code and constants, and the game base pass main (basepass.py)
  preprocess() dxc -P, then UB.Member -> UB_Member (what the engine's D3D compiler does before compiling)
  compile()    dxc -T ps_6_6, then the bindings from its reflection
"""
import os
import re
import shutil

from . import env
from . import ub

# uniform buffers the material code may name; the game gives the base pass View (b0), Primitive (b1), Material (b2)
GAME_UBS = ('View', 'Primitive')
STUB_UBS = ('SceneTexturesStruct', 'MobileSceneTextures', 'OpaqueBasePass', 'PrimitiveDither', 'PrimitiveFade', 'InstanceVF',
            'InstancedView', 'DrawRectangleParameters', 'SpeedTreeData', 'TranslucentBasePass', 'ReflectionStruct', 'FogStruct',
            'PlanarReflectionStruct', 'ForwardLightData', 'IndirectLightingCache', 'PrecomputedLightingBuffer',
            'MobileBasePass', 'SkyAtmosphere', 'LocalVF', 'BasePass')
INCLUDE_RE = re.compile(r'(#\s*include\s+")/(Engine|Plugin)/')


def _copy_tree(src, dst, patch=None):
    for dp, dn, fn in os.walk(src):
        rel = os.path.relpath(dp, src)
        out = os.path.join(dst, rel)
        os.makedirs(out, exist_ok=True)
        for f in fn:
            if not f.endswith(('.ush', '.usf', '.h')):
                continue
            with open(os.path.join(dp, f), encoding='utf-8', errors='replace') as fh:
                text = fh.read()
            text = INCLUDE_RE.sub(r'\1\2/', text)
            if patch:
                text = patch(os.path.join(rel, f).replace(os.sep, '/'), text)
            with open(os.path.join(out, f), 'w', encoding='utf-8') as fh:
                fh.write(text)


def _engine_patch(rel, text):
    """Small changes to the staged engine sources (the originals stay as they are)."""
    if rel.endswith('EyeAdaptationCommon.ush'):
        # the game's base pass has no eye adaptation texture to give a material; its View buffer has the exposure the
        # scene was pre-exposed with (the eye adaptation of the frame before), so a material that divides its emissive
        # by the exposure (an anime / unlit look) stays exposure-independent once the base pass multiplies by it again
        # (GAMESH_EYE_ADAPTATION_CONST: a fixed exposure, the one the material is shown at as in the editor)
        text = text.replace('float EyeAdaptationLookup()\n{', 'float EyeAdaptationLookup()\n{\n#if defined(GAMESH_EYE_ADAPTATION_CONST)\n\treturn GAMESH_EYE_ADAPTATION_CONST;\n#elif GAMESH_EYE_ADAPTATION_ONE\n\treturn 1.0f;\n#elif GAMESH_EYE_ADAPTATION_PREEXPOSURE\n\treturn View.PreExposure;\n#endif', 1)
    return text


_STAGED = {}


def staged_engine():
    """The engine's shader sources with their includes made relative (and the small patches), staged once per session in
    the work folder: every compile's include path has them after its own generated files."""
    engine = env.engine_shaders()
    root = env.work('engine_shaders')
    if _STAGED.get(root) == engine:
        return root
    marker = os.path.join(root, 'staged_from.txt')
    stamp = '%s\n%d\n' % (engine, sum(len(fn) for _, _, fn in os.walk(engine)))
    try:
        with open(marker, encoding='utf-8') as f:
            same = f.read() == stamp
    except (IOError, OSError):
        same = False
    if not same:
        if os.path.isdir(root):
            shutil.rmtree(root)
        for part in ('Private', 'Public', 'Shared'):
            _copy_tree(os.path.join(engine, part), os.path.join(root, 'Engine', part), _engine_patch)
        with open(marker, 'w', encoding='utf-8') as f:
            f.write(stamp)
    _STAGED[root] = engine
    return root


def stage(work, material_hlsl, material_ub, basepass_usf, extra_generated=None, registers=None):
    """The compile's own files in work/: Engine/Generated/... and GameBasePass.usf (the engine's sources: staged_engine).
    registers: {'View': b, 'Primitive': b} where the pass binds them (the base pass: View b0, Primitive b1; the shadow
    passes put Primitive first)."""
    registers = dict({'View': 0, 'Primitive': 1}, **(registers or {}))
    if os.path.isdir(work):
        shutil.rmtree(work)
    os.makedirs(work)
    gen = os.path.join(work, 'Engine', 'Generated')
    os.makedirs(os.path.join(gen, 'UniformBuffers'), exist_ok=True)
    lay = ub.layouts()
    files = {
        'UniformBuffers/View.ush': ub.declaration('View', lay['View'], registers['View']),
        'UniformBuffers/Primitive.ush': ub.declaration('Primitive', lay['Primitive'], registers['Primitive']),
        'UniformBuffers/Material.ush': material_ub,
        'Material.ush': INCLUDE_RE.sub(r'\1\2/', material_hlsl),
        'GeneratedUniformBuffers.ush': '\n'.join('#include "Engine/Generated/UniformBuffers/%s.ush"' % n
                                                 for n in ('View', 'Primitive', 'Material') + STUB_UBS) + '\n',
        'GeneratedInstancedStereo.ush': ub.instanced_stereo('View'),
        'VertexFactory.ush': '',
    }
    for name in STUB_UBS:
        files['UniformBuffers/%s.ush' % name] = stub_declaration(name)
    files.update(extra_generated or {})
    for name, text in files.items():
        path = os.path.join(gen, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)
    with open(os.path.join(work, 'GameBasePass.usf'), 'w', encoding='utf-8') as f:
        f.write(basepass_usf)
    return os.path.join(work, 'GameBasePass.usf')


# Members of buffers the game's base pass does not bind. Declared so that the editor's material code (which has helpers
# for every pass) compiles; a material whose live code reads one gets a binding the carrier doesn't have, and the build
# says so.
STUB_MEMBERS = {
    'SceneTexturesStruct': [
        ('Texture2D', 'SceneColorTexture'), ('SamplerState', 'SceneColorTextureSampler'), ('Texture2D', 'SceneDepthTexture'),
        ('SamplerState', 'SceneDepthTextureSampler'), ('Texture2D<float>', 'SceneDepthTextureNonMS'),
        ('Texture2D', 'GBufferATexture'), ('Texture2D', 'GBufferBTexture'), ('Texture2D', 'GBufferCTexture'),
        ('Texture2D', 'GBufferDTexture'), ('Texture2D', 'GBufferETexture'), ('Texture2D', 'GBufferFTexture'),
        ('Texture2D', 'GBufferVelocityTexture'), ('Texture2D<float4>', 'GBufferATextureNonMS'),
        ('Texture2D<float4>', 'GBufferBTextureNonMS'), ('Texture2D<float4>', 'GBufferCTextureNonMS'),
        ('Texture2D<float4>', 'GBufferDTextureNonMS'), ('Texture2D<float4>', 'GBufferETextureNonMS'),
        ('Texture2D<float4>', 'GBufferFTextureNonMS'), ('Texture2D<float4>', 'GBufferVelocityTextureNonMS'),
        ('SamplerState', 'GBufferATextureSampler'), ('SamplerState', 'GBufferBTextureSampler'),
        ('SamplerState', 'GBufferCTextureSampler'), ('SamplerState', 'GBufferDTextureSampler'),
        ('SamplerState', 'GBufferETextureSampler'), ('SamplerState', 'GBufferFTextureSampler'),
        ('SamplerState', 'GBufferVelocityTextureSampler'), ('Texture2D', 'ScreenSpaceAOTexture'),
        ('SamplerState', 'ScreenSpaceAOTextureSampler'), ('Texture2D<float>', 'CustomDepthTextureNonMS'),
        ('Texture2D', 'CustomDepthTexture'), ('SamplerState', 'CustomDepthTextureSampler'),
        ('Texture2D<uint2>', 'CustomStencilTexture'), ('Texture2D<uint2>', 'SceneStencilTexture'),
        ('Texture2D', 'EyeAdaptationTexture'), ('Texture2D', 'SceneColorCopyTexture'),
        ('SamplerState', 'SceneColorCopyTextureSampler'), ('SamplerState', 'PointClampSampler'),
    ],
    'DrawRectangleParameters': [('float4', 'PosScaleBias'), ('float4', 'UVScaleBias'), ('float4', 'InvTargetSizeAndTextureSize')],
    'PrimitiveFade': [('float2', 'FadeTimeScaleBias')],
    'PrimitiveDither': [('float', 'LODFactor')],
    'InstancedView': [('uint', 'StereoPassIndex')],
}


def stub_declaration(name):
    members = STUB_MEMBERS.get(name, [])
    lines = ['#ifndef __UniformBuffer_%s_Definition__' % name, '#define __UniformBuffer_%s_Definition__' % name]
    # constants go in a cbuffer of their own: a material that reads one gets a buffer the carrier doesn't bind
    constants = [(t, m) for t, m in members if not t.startswith(('Texture', 'SamplerState', 'StructuredBuffer', 'Buffer'))]
    if constants:
        lines.append('cbuffer %s\n{' % name)
        for typ, member in constants:
            lines.append('    %s %s_%s;' % (typ, name, member))
        lines.append('};')
    for typ, member in members:
        if (typ, member) not in constants:
            lines.append('%s %s_%s;' % (typ, name, member))
    lines.append('#endif')
    return '\n'.join(lines) + '\n'


def run_dxc(args, cwd):
    return env.run_dxc(args, cwd)


def preprocess(work, usf, defines):
    out = os.path.join(work, 'preprocessed.hlsl')
    args = ['-P', '-Fi', out, '-I', work, '-I', staged_engine(), '-HV', '2018'] + ['-D%s=%s' % kv for kv in sorted(defines.items())] + [usf]
    code, so, se = run_dxc(args, work)
    if code != 0 or not os.path.isfile(out):
        raise RuntimeError('preprocessing failed:\n' + se[-6000:])
    with open(out, encoding='utf-8', errors='replace') as f:
        return f.read()


def rewrite_uniform_buffers(text, names):
    """UB.Member -> UB_Member for every uniform buffer name (as RemoveUniformBuffersFromSource does)."""
    pattern = re.compile(r'(?<![\w.])(%s)\s*\.\s*([A-Za-z_]\w*)' % '|'.join(sorted(names, key=len, reverse=True)))
    return pattern.sub(r'\1_\2', text)


def compile_ps(work, source, entry='MainPS', profile='ps_6_6', extra=()):
    src = os.path.join(work, 'final.hlsl')
    with open(src, 'w', encoding='utf-8') as f:
        f.write(source)
    obj = os.path.join(work, 'final.dxbc')
    args = ['-T', profile, '-E', entry, '-HV', '2018', '-Zpr', '-O3', '-Qstrip_debug', src, '-Fo', obj] + list(extra)
    code, so, se = run_dxc(args, work)
    if code != 0:
        raise RuntimeError('compile failed:\n' + se[-8000:])
    with open(obj, 'rb') as f:
        dxbc = f.read()
    code, text, se2 = run_dxc(['-dumpbin', obj], work)
    return dxbc, text, se


def bindings(dump_text):
    """[(name, type, dim, bind like 't3')] from dxc -dumpbin."""
    out = []
    sec = dump_text.split('; Resource Bindings:', 1)
    if len(sec) < 2:
        return out
    for line in sec[1].splitlines()[4:]:
        if not line.startswith('; ') or line.strip() == ';':
            break
        parts = line[2:].split()
        if len(parts) >= 7:
            out.append((parts[0], parts[1], parts[3], parts[-2]))
    return out
