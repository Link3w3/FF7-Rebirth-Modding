"""The exported material (material.json + material.hlsl from ExportMaterialForGame) as the compile needs it: its Material
uniform buffer with the constants baked in (the game evaluates the carrier's own buffer, not ours) and its textures.

Live values (enable_live): the constants are read through one more texture on a free carrier slot, the live values
texture. The material's own texture there is one of the game's (not the live values marker), so the baked constants
stand; while Rebirth Materials live-edits the material in the game, the link puts a small texture there holding the
constants as the editor evaluates them now: pixel 0 the marker (1, 2, 3, 4), then pixel 1 + 4n + c component c of
constant n (constants: the vectors, then the scalar float4s), its float bits in 11-bit pieces in r, g, b and a = 1."""
import hashlib
import json
import os
import re

TEXTURE_TYPES = {'Texture2D': 'Texture2D', 'TextureCube': 'TextureCube', 'Texture2DArray': 'Texture2DArray',
                 'VolumeTexture': 'Texture3D', 'ExternalTexture': 'Texture2D', 'VirtualTexture': 'Texture2D'}
LIVE_PARAMETER = '(live values)'
VECTOR_RE = re.compile(r'Material\.VectorExpressions\[(\d+)\]')
SCALAR_RE = re.compile(r'Material\.ScalarExpressions\[(\d+)\]')


def code_hash(code):
    """What a material's live values need to stay the same: its exported code (its constants' layout)."""
    return hashlib.sha1(code.encode('utf-8', 'replace')).hexdigest()


class Exported(object):
    def __init__(self, folder):
        self.folder = folder
        with open(os.path.join(folder, 'material.json'), encoding='utf-8') as f:
            self.info = json.load(f)
        with open(os.path.join(folder, 'material.hlsl'), encoding='utf-8', errors='replace') as f:
            self.code = f.read()
        self.name = self.info['material'].rsplit('.', 1)[-1]
        uniform = self.info.get('uniform', {})
        floats = uniform.get('constants', [])
        float4s = len(floats) // 4
        vmax = max([int(x) for x in re.findall(r'Material\.VectorExpressions\[(\d+)\]', self.code)] or [-1])
        smax = max([int(x) for x in re.findall(r'Material\.ScalarExpressions\[(\d+)\]', self.code)] or [-1])
        self.vectors = vmax + 1
        self.scalars = float4s - self.vectors
        self.problems = []
        if self.scalars < smax + 1:
            self.problems.append('the constants (%d float4s) do not hold %d vectors and %d scalar float4s' % (float4s, vmax + 1, smax + 1))
            self.scalars = smax + 1
        self.constants = [tuple(floats[4 * i:4 * i + 4]) + (0.0,) * (4 - len(floats[4 * i:4 * i + 4])) for i in range(float4s)]
        while len(self.constants) < self.vectors + self.scalars:
            self.constants.append((0.0, 0.0, 0.0, 0.0))
        self.textures = self.info.get('textures', [])
        self.code_hash = code_hash(self.code)
        self.live = None

    def has_constants(self):
        return bool(VECTOR_RE.search(self.code) or SCALAR_RE.search(self.code))

    def enable_live(self, default_texture):
        """The constants read through the live values texture (see the module's notes), on 2D texture index
        self.live['index'] (default_texture: the game texture it is bound to by default). False when the material reads
        no constants."""
        if self.live or not self.has_constants():
            return False
        index = 1 + max([t['index'] for t in self.textures if t['type'] == 'Texture2D'] or [-1])
        self.code = SCALAR_RE.sub(r'RebirthLiveS(\1)', VECTOR_RE.sub(r'RebirthLiveV(\1)', self.code))
        self.textures = list(self.textures) + [dict(type='Texture2D', index=index, parameter=LIVE_PARAMETER,
                                                    texture=default_texture, texture_class='Texture2D', srgb=False,
                                                    compression='TC_HDR', sampler_source='SSM_FromTextureAsset', live=True)]
        self.live = dict(index=index, texture=default_texture)
        return True

    def textures_of(self, kind):
        return [t for t in self.textures if t['type'] == kind]

    def used_textures(self):
        """[(type, index)] the code samples: Material.Texture2D_3 -> ('Texture2D', 3)."""
        out = set()
        for kind in TEXTURE_TYPES:
            for k in re.findall(r'Material\.%s_(\d+)\b(?!Sampler)' % kind, self.code):
                out.add((kind, int(k)))
        return sorted(out)

    def material_ub(self):
        """Engine/Generated/UniformBuffers/Material.ush: constants as static arrays, resources as plain declarations."""
        def f4(v):
            return 'float4(%s)' % ', '.join(repr(float(x)) for x in v)
        lines = ['#ifndef __UniformBuffer_Material_Definition__', '#define __UniformBuffer_Material_Definition__',
                 '// %s: constants evaluated in the editor (%s)' % (self.info['material'], 'with its parameters' if self.info.get('uniform', {}).get('evaluated') else 'not evaluated: zeros')]
        if self.vectors:
            lines.append('static const float4 Material_VectorExpressions[%d] = {%s};' % (
                self.vectors, ', '.join(f4(v) for v in self.constants[:self.vectors])))
        if self.scalars:
            lines.append('static const float4 Material_ScalarExpressions[%d] = {%s};' % (
                self.scalars, ', '.join(f4(v) for v in self.constants[self.vectors:self.vectors + self.scalars])))
        counts = {}
        for t in self.textures:
            counts[t['type']] = max(counts.get(t['type'], 0), t['index'] + 1)
        for kind, n in sorted(counts.items()):
            hlsl = TEXTURE_TYPES.get(kind, 'Texture2D')
            for k in range(n):
                lines.append('%s Material_%s_%d;' % (hlsl, kind, k))
                lines.append('SamplerState Material_%s_%dSampler;' % (kind, k))
        # every texture type the template can name, so unused helpers still compile
        for kind, hlsl in TEXTURE_TYPES.items():
            if kind not in counts:
                pass
        if self.live:
            t = 'Material_Texture2D_%d' % self.live['index']
            lines += [
                '// live values: the constants as Rebirth Materials puts them on %s while it edits the material in the game' % t,
                'bool RebirthLiveOn()',
                '{',
                '\tconst float4 m = %s.Load(int3(0, 0, 0));' % t,
                '\treturn all(abs(m - float4(1.0, 2.0, 3.0, 4.0)) < 0.01);',
                '}',
                'float RebirthLiveValue(uint i, float baked)',
                '{',
                '\tconst float4 p = %s.Load(int3(1 + (int)i, 0, 0));' % t,
                '\tconst uint bits = (uint)p.r | ((uint)p.g << 11) | ((uint)p.b << 22);',
                '\treturn p.a > 0.5 ? asfloat(bits) : baked;',
                '}',
                'float4 RebirthLiveFloat4(uint n, float4 baked)',
                '{',
                '\tif (!RebirthLiveOn())',
                '\t\treturn baked;',
                '\treturn float4(RebirthLiveValue(4 * n, baked.x), RebirthLiveValue(4 * n + 1, baked.y), '
                'RebirthLiveValue(4 * n + 2, baked.z), RebirthLiveValue(4 * n + 3, baked.w));',
                '}',
            ]
            if self.vectors:
                lines.append('#define RebirthLiveV(n) RebirthLiveFloat4((n), Material_VectorExpressions[(n)])')
            if self.scalars:
                lines.append('#define RebirthLiveS(n) RebirthLiveFloat4(%du + (n), Material_ScalarExpressions[(n)])' % self.vectors)
        # material parameter collections: their default values, packed as the engine packs them (scalars four to a float4,
        # then one float4 per vector)
        for c in self.collections():
            lines.append('static const float4 MaterialCollection%d_Vectors[%d] = {%s};   // %s' % (
                c['index'], len(c['data']), ', '.join(f4(v) for v in c['data']), c['collection']))
        lines.append('SamplerState Material_Wrap_WorldGroupSettings;')
        lines.append('SamplerState Material_Clamp_WorldGroupSettings;')
        lines.append('#endif')
        return '\n'.join(lines) + '\n'

    def collections(self):
        out = []
        for c in self.info.get('parameter_collections', []):
            data = []
            scalars = c.get('scalars', [])
            for i, sp in enumerate(scalars):
                if i % 4 == 0:
                    data.append([0.0, 0.0, 0.0, 0.0])
                data[-1][i % 4] = float(sp.get('value', 0.0))
            for vp in c.get('vectors', []):
                v = list(vp.get('value', [0, 0, 0, 0])) + [0.0] * 4
                data.append([float(x) for x in v[:4]])
            if not data:
                data.append([0.0, 0.0, 0.0, 0.0])
            out.append(dict(index=c.get('index', len(out)), collection=c.get('collection', '?'), data=data))
        return out

    def uniform_buffer_names(self):
        return ['Material'] + ['MaterialCollection%d' % c['index'] for c in self.collections()]

    def defines(self):
        """The material environment's defines (FMaterial::SetupMaterialEnvironment and the translator's), as far as the
        export tells them."""
        i = self.info
        d = {}
        blend = i.get('blend_mode', 'BLEND_Opaque')
        if blend in ('BLEND_Opaque', 'BLEND_Masked'):
            d['MATERIALBLENDING_MASKED' if i.get('masked') else 'MATERIALBLENDING_SOLID'] = 1
        elif blend == 'BLEND_Translucent':
            d['MATERIALBLENDING_TRANSLUCENT'] = 1
        elif blend == 'BLEND_Additive':
            d['MATERIALBLENDING_ADDITIVE'] = 1
        elif blend == 'BLEND_Modulate':
            d['MATERIALBLENDING_MODULATE'] = 1
        else:
            d['MATERIALBLENDING_SOLID'] = 1
        d['MATERIAL_TWOSIDED'] = 1 if i.get('two_sided') else 0
        d['MATERIAL_TANGENTSPACENORMAL'] = 1 if i.get('tangent_space_normal', True) else 0
        domain = i.get('domain', 'MD_Surface')
        d['MATERIAL_DOMAIN_' + domain[3:].upper()] = 1
        d['MATERIALDOMAIN_' + domain[3:].upper()] = 1
        models = i.get('shading_models', ['MSM_DefaultLit'])
        for m in models:
            d['MATERIAL_SHADINGMODEL_' + {'MSM_DefaultLit': 'DEFAULT_LIT', 'MSM_Unlit': 'UNLIT', 'MSM_Subsurface': 'SUBSURFACE',
                                          'MSM_PreintegratedSkin': 'PREINTEGRATED_SKIN', 'MSM_ClearCoat': 'CLEAR_COAT',
                                          'MSM_SubsurfaceProfile': 'SUBSURFACE_PROFILE', 'MSM_TwoSidedFoliage': 'TWOSIDED_FOLIAGE',
                                          'MSM_Hair': 'HAIR', 'MSM_Cloth': 'CLOTH', 'MSM_Eye': 'EYE',
                                          'MSM_SingleLayerWater': 'SINGLELAYERWATER', 'MSM_ThinTranslucent': 'THIN_TRANSLUCENT'}.get(m, 'DEFAULT_LIT')] = 1
        if len(models) == 1:
            d['MATERIAL_SINGLE_SHADINGMODEL'] = 1
        d['USING_TESSELLATION'] = 0
        d['MATERIALDECALRESPONSEMASK'] = 7
        d['REFRACTION_USE_INDEX_OF_REFRACTION'] = 1
        for name in ('USE_DITHERED_LOD_TRANSITION_FROM_MATERIAL', 'GENERATE_SPHERICAL_PARTICLE_NORMALS',
                     'MATERIAL_USES_SCENE_COLOR_COPY', 'MATERIAL_USE_PREINTEGRATED_GF', 'MATERIAL_HQ_FORWARD_REFLECTIONS',
                     'MATERIAL_PLANAR_FORWARD_REFLECTIONS', 'MATERIAL_NONMETAL', 'MATERIAL_USE_LM_DIRECTIONALITY',
                     'MATERIAL_INJECT_EMISSIVE_INTO_LPV', 'MATERIAL_SSR', 'MATERIAL_CONTACT_SHADOWS', 'MATERIAL_BLOCK_GI',
                     'MATERIAL_DITHER_OPACITY_MASK', 'MATERIAL_NORMAL_CURVATURE_TO_ROUGHNESS',
                     'MATERIAL_ALLOW_NEGATIVE_EMISSIVECOLOR', 'MATERIAL_OUTPUT_OPACITY_AS_ALPHA',
                     'TRANSLUCENT_SHADOW_WITH_MASKED_OPACITY', 'MATERIAL_USE_ALPHA_TO_COVERAGE'):
            d.setdefault(name, 0)
        d['USE_STENCIL_LOD_DITHER_DEFAULT'] = 0
        # the translator's: what the code needs, read from the code
        code = self.code
        d['USES_EYE_ADAPTATION'] = 1 if 'EyeAdaptationLookup' in code else 0
        return d
