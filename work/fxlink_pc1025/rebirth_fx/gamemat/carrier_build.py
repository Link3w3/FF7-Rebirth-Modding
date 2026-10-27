"""An exported editor material compiled onto a game carrier: one pixel shader per skinned base pass variant of the
carrier (its own interface: texture coordinates, dynamic coverage, coverage texture), checked against the carrier's
signatures, then wrapped as game shader blobs with their own resource tables (the material's textures on the carrier's
named texture parameters)."""
import os
import re

from . import env
from . import gbuild as build
from . import basepass
from . import depthpass
from . import psinfo
from . import shaderblob
from .carriers import Carrier, texture_parameters
from .verify import verify


def decompress(shader):
    """A library shader's code as the compiler wrote it (the library keeps it LZ4-compressed when that is smaller)."""
    if len(shader['code']) == shader['usize']:
        return shader['code']
    env.vendor()
    import lz4.block
    return lz4.block.decompress(shader['code'], uncompressed_size=shader['usize'])


def skin_base_pass_ps(c):
    """{resource index: [shader type names]} of the carrier's base pass pixel shaders for the skinned vertex factories."""
    out = {}
    for s in c.shaders:
        if s['vf'].startswith('TGPUSkin') and s['freq'] == 5 and ('BasePassPS' in s['type'] or s['type'] == 'fa99734846c7227e'):
            out.setdefault(s['res'], set()).add(s['type'])
    return {k: sorted(v) for k, v in out.items()}


def skin_depth_ps(c):
    """{resource index: (kind, [shader type names])} of the carrier's depth-only and shadow depth pixel shaders for the
    skinned vertex factories (kind: depthpass.kind_of)."""
    out = {}
    for s in c.shaders:
        if s['vf'].startswith('TGPUSkin') and s['freq'] == 5 and depthpass.kind_of([s['type']]):
            out.setdefault(s['res'], set()).add(s['type'])
    res = {}
    for k, types in out.items():
        kinds = set(depthpass.kind_of([t]) for t in types)
        if len(kinds) != 1:
            raise ValueError('resource %d is shared by %s' % (k, sorted(kinds)))
        res[k] = (kinds.pop(), sorted(types))
    return res


def vs_texcoords(blob):
    """The texture coordinates (0-3) a base pass vertex shader passes on to the pixel shader: TEXCOORD0.xy / .zw and
    TEXCOORD1.xy / .zw that it stores something other than a constant in (a carrier whose own material reads one
    texture coordinate writes zeros where the next one would be)."""
    text = psinfo.dump(blob[blob.find(b'DXBC'):])
    osg = text.split('; Output signature:', 1)[1].split('; shader', 1)[0]
    ids, k = {}, 0
    for line in osg.splitlines():
        m = re.match(r';\s+(\w+)\s+(\d+)\s+([xyzw]+)\s+(\d+)\s', line)
        if m:
            ids[(m.group(1), int(m.group(2)))] = k
            k += 1
    stored = {}
    for sid, col, val in re.findall(r'storeOutput\.f32\(i32 5, i32 (\d+), i32 0, i8 (\d), float ([^)]+?)\)', text):
        stored[(int(sid), int(col))] = val.strip()

    def live(row, cols):
        sid = ids.get(('TEXCOORD', row))
        return sid is not None and all(stored.get((sid, c), '').startswith('%') for c in cols)
    out = set()
    for uv, (row, cols) in enumerate(((0, (0, 1)), (0, (2, 3)), (1, (0, 1)), (1, (2, 3)))):
        if live(row, cols):
            out.add(uv)
    return out


def material_texcoords(code):
    """The texture coordinates a material's pixel code reads (Parameters.TexCoords[k] in its own expressions: from its
    uniform expressions on, without the vertex shader's customized UVs; the engine's template code before them reads
    others under #if), below its NUM_MATERIAL_TEXCOORDS."""
    at = code.find('// Uniform material expressions.')
    own = code[at:] if at >= 0 else code
    for fn in ('GetMaterialCustomizedUVs', 'GetCustomInterpolators'):
        m = re.search(r'void %s\([^)]*\)\s*\{' % fn, own)
        if m:
            end = own.find('\n}', m.end())
            own = own[:m.start()] + own[end + 2:] if end >= 0 else own[:m.start()]
    used = set(int(k) for k in re.findall(r'Parameters\.TexCoords\[(\d+)\]', own))
    n = re.search(r'#define NUM_MATERIAL_TEXCOORDS (\d+)', code)
    if n:
        used = set(k for k in used if k < int(n.group(1)))
    return used


def ub_names(blob):
    """The uniform buffer names of a game shader blob by slot (its optional data 'u')."""
    table, at, total, data = shaderblob.parse(blob)
    return shaderblob._ub_names(data)


class CarrierShaders(object):
    """A carrier (RMI_Surface_*): its package, its shaders out of the game's shader library, named texture parameters
    and skinned base pass variants. raw_shaders: [dict(index, hash, code, usize, freq)] in the shader map's order (as
    stored in the library); omitted, they are read from `library`."""

    def __init__(self, name, carrier_data, library=None, raw_shaders=None):
        self.name = name
        self.carrier = Carrier(carrier_data, library)
        if raw_shaders is None:
            raw_shaders = [library.shader(si) for si in self.carrier.order]
        if self.carrier.order is not None and [s['index'] for s in raw_shaders] != self.carrier.order:
            raise ValueError('%s: the shaders given are not the shader map\'s' % name)
        self.raw = raw_shaders
        self.shaders = [dict(index=s['index'], freq=s['freq'], hash=s['hash'], code=decompress(s)) for s in raw_shaders]
        self.params = texture_parameters(self.carrier)          # [(k, name or None, texture index)]
        self.named = [(k, n) for k, n, _ in self.params if n]
        self.variants = {}
        for res, types in sorted(skin_base_pass_ps(self.carrier).items()):
            info = psinfo.info(self.shaders[res]['code'])
            self.variants[res] = dict(kind='base', types=types, info=info,
                                      has_tc1=any(e[0] == 'TEXCOORD' and e[1] == 1 for e in info['isg']),
                                      dynamic_coverage=any('WithDynamicCoverage' in t for t in types),
                                      coverage_texture=self._coverage_texture(info, self.shaders[res]['code']),
                                      registers=self._registers(self.shaders[res]['code']))
        # the depth-only and shadow depth shaders: replaced for masked materials only (depthpass)
        self.depth_variants = {}
        for res, (kind, types) in sorted(skin_depth_ps(self.carrier).items()):
            info = psinfo.info(self.shaders[res]['code'])
            if not info['discard']:
                continue    # a shader that cuts nothing out (an opaque carrier's): the material's cut-outs can't be there
            self.depth_variants[res] = dict(kind=kind, types=types, info=info,
                                            has_tc1=any(e[0] == 'TEXCOORD' and e[1] == 1 for e in info['isg']),
                                            dynamic_coverage=True,
                                            coverage_texture=self._coverage_texture(info, self.shaders[res]['code']),
                                            registers=self._registers(self.shaders[res]['code']))

    def texcoords(self):
        """The texture coordinates the carrier's GPU skin base pass vertex shaders pass on (all of them do the same)."""
        if getattr(self, '_texcoords', None) is None:
            got = None
            for s in self.carrier.shaders:
                if s['vf'].startswith('TGPUSkin') and s['freq'] == 0 and 'BasePassVS' in s['type']:
                    uvs = vs_texcoords(self.shaders[s['res']]['code'])
                    got = uvs if got is None else (got & uvs)
            self._texcoords = got if got is not None else set(range(4))
        return self._texcoords

    def missing_texcoords(self, exported):
        """The texture coordinates the material reads that the carrier does not pass on (sorted)."""
        return sorted(material_texcoords(exported.code) - self.texcoords())

    @staticmethod
    def _registers(blob):
        names = ub_names(blob)
        return {n: names.index(n) for n in ('View', 'Primitive', 'ShadowDepthPass') if n in names}

    def _coverage_texture(self, info, blob=None):
        """The Material texture slot k the carrier's own coverage test samples (its 'Coverage' parameter), or None."""
        material_slot = 2
        if blob is not None:
            names = ub_names(blob)
            if 'Material' in names:
                material_slot = names.index('Material')
        for k, n in self.named:
            if n == 'Coverage' and info['discard']:
                for ub_slot, res, bind in info['tex']:
                    if ub_slot == material_slot and res == 2 * k:
                        return k
        return None

    def all_variants(self, depth=False):
        out = dict(self.variants)
        if depth:
            out.update(self.depth_variants)
        return out


def live_textures(bindings):
    """The Material_Texture2D_k indices a compiled shader binds."""
    out = set()
    for name, typ, dim, bind in bindings:
        if name.startswith('Material_Texture2D_') and not name.endswith('Sampler'):
            out.add(int(name[len('Material_Texture2D_'):]))
    return sorted(out)


def slot_plan(exported, carrier, live, keep=('Coverage',), prefer=(), roles=None):
    """{material texture index: carrier slot k} for the `live` texture indices, textures that are the same asset sharing
    one slot, on the carrier's named texture parameters (`keep` ones stay the character's own). `roles` {material
    texture index: parameter name}: those textures are the character's own texture of that parameter (its Color, its
    Normal...), kept as the character's material has it. Raises when there are not enough slots."""
    roles = dict(roles or {})
    by_name = dict((n, k) for k, n in carrier.named)
    plan = {}
    for k, pname in roles.items():
        if k in live:
            if pname not in by_name:
                raise ValueError('%s has no %s parameter' % (carrier.name, pname))
            plan[k] = by_name[pname]
    keep = tuple(keep) + tuple(roles.values())
    live = [k for k in live if k not in plan]
    by_index = {t['index']: t for t in exported.textures if t['type'] == 'Texture2D'}
    free = [k for k, n in carrier.named if n not in keep]
    order = [k for k, n in carrier.named if n in prefer and n not in keep] + [k for k in free if k not in [kk for kk, nn in carrier.named if nn in prefer]]
    asset_slot = {}
    for k in live:
        asset = by_index[k]['texture']
        own = by_index[k].get('live')       # (the live values texture: a slot of its own, whatever its default texture)
        if asset in asset_slot and not own:
            plan[k] = asset_slot[asset]
            continue
        if not order:
            raise ValueError('%s uses %d different textures; %s has %d named texture parameters free' % (
                exported.name, len(set(by_index[x]['texture'] for x in live)), carrier.name, len(free)))
        plan[k] = order.pop(0)
        if not own:
            asset_slot[asset] = plan[k]
    return plan


def game_material_code(code):
    """The material's code as the game samples textures: the game's surface shaders bias their material textures by
    View.TemporalSamplerBias.y (the temporal AA's sharpening bias), not View.MaterialTextureMipBias, which the game leaves
    alone (REBIRTHFX_GAME_MIP_BIAS=0: as the editor wrote it)."""
    if os.environ.get('REBIRTHFX_GAME_MIP_BIAS', '1') == '0':
        return code
    return code.replace('View.MaterialTextureMipBias', 'View.TemporalSamplerBias.y')


def compile_variant(exported, carrier, res, work, title=None, ignore_mask=False, exposure='auto', editor_exposure=1.0,
                    family='standard', dithered=False):
    """(dxbc bytes, bindings, problems) of the material compiled for carrier variant `res` (ignore_mask: a masked
    material drawn solid, its cut-outs left to the carrier's coverage; exposure: basepass.exposure_defines; family: the
    game surface family whose GBuffer it writes, basepass.FAMILIES; dithered: its mask cut out against the blue noise)."""
    v = carrier.variants.get(res) or carrier.depth_variants[res]
    variant = '/'.join(t for t in v['types'] if t != 'fa99734846c7227e')
    title = title or ('%s on %s' % (exported.name, carrier.name))
    if v['kind'] == 'base':
        src = basepass.source(title, carrier.name, variant, v['has_tc1'], v['dynamic_coverage'], v['coverage_texture'] is not None,
                              family=family, dithered=dithered)
    else:
        src = depthpass.source(v['kind'], title, carrier.name, variant, v['has_tc1'], v['coverage_texture'] is not None,
                               v['registers'], dithered=dithered)
    os.makedirs(work, exist_ok=True)
    usf = build.stage(work, game_material_code(exported.code), exported.material_ub(), src, registers=v['registers'])
    defines = dict(basepass.BASE_DEFINES)
    defines.update(exported.defines())
    defines.update(basepass.exposure_defines(exported.code, exposure, editor_exposure)[1])
    # (an End engine input of the material: Distribution, the subsurface family's scattering distribution)
    defines['GAME_MATERIAL_HAS_DISTRIBUTION'] = 1 if 'PixelMaterialInputs.Distribution =' in exported.code else 0
    if ignore_mask and defines.pop('MATERIALBLENDING_MASKED', None):
        defines['MATERIALBLENDING_SOLID'] = 1
    pre = build.preprocess(work, usf, defines)
    names = set(build.GAME_UBS) | set(exported.uniform_buffer_names()) | set(build.STUB_UBS)
    final = build.rewrite_uniform_buffers(pre, names)
    dxbc, dump, warnings = build.compile_ps(work, final)
    problems, _ = verify(v['info'], dxbc)
    # (verify also lists bindings the carrier's own shader does not use: this shader has its own resource table)
    problems = [p for p in problems if not p.startswith('binding ')]
    return dxbc, build.bindings(dump), problems


def material_resource_fn(plan, carrier_variant):
    """'Material_Texture2D_3' / 'Material_Texture2D_3Sampler' / 'GameCoverageTexture' -> the carrier's Material uniform
    buffer resource index (texture k at 2k, its sampler at 2k + 1)."""
    def fn(binding):
        if binding == 'GameCoverageTexture':
            k = carrier_variant['coverage_texture']
            if k is None:
                raise KeyError('the carrier has no coverage texture')
            return 2 * k
        name = binding[len('Material_'):]
        sampler = name.endswith('Sampler')
        if sampler:
            name = name[:-len('Sampler')]
        kind, _, index = name.rpartition('_')
        if kind != 'Texture2D':
            raise KeyError('%s: only 2D textures go on carrier slots' % binding)
        k = int(index)
        if k not in plan:
            raise KeyError('%s has no carrier slot' % binding)
        return 2 * plan[k] + (1 if sampler else 0)
    return fn


def wants_depth_passes(exported, carrier, ignore_mask=False):
    """True when the material cuts out by itself on this carrier: its cut-outs then go in the carrier's depth-only and
    shadow depth shaders too (depthpass), or the depth pre-pass and the shadows keep the whole surface."""
    masked = exported.defines().get('MATERIALBLENDING_MASKED') == 1
    return bool(masked and not ignore_mask and carrier.depth_variants)


def build_blobs(exported, carrier, work_root, prefer=(), keep=('Coverage',), roles=None, ignore_mask=False, exposure='auto',
                editor_exposure=1.0, depth='auto', family='standard', dithered=False):
    """({resource index: dict(blob, dxbc, bindings, problems, types, kind)}, slot plan) for every skinned base pass
    variant of the carrier (and, depth True / 'auto' for a material that cuts out by itself, its depth-only and shadow
    depth variants): all variants compiled first, one slot plan for the textures any of them binds, then the blobs."""
    if depth == 'auto':
        depth = wants_depth_passes(exported, carrier, ignore_mask)
    variants = carrier.all_variants(depth)
    compiled = {}
    for res in sorted(variants):
        compiled[res] = compile_variant(exported, carrier, res, os.path.join(work_root, '%s_%d' % (carrier.name, res)),
                                        ignore_mask=ignore_mask, exposure=exposure, editor_exposure=editor_exposure,
                                        family=family, dithered=dithered)
    live = sorted(set(k for dxbc, binds, problems in compiled.values() for k in live_textures(binds)))
    plan = slot_plan(exported, carrier, live, keep=keep, prefer=prefer, roles=roles)
    out = {}
    for res, (dxbc, binds, problems) in sorted(compiled.items()):
        v = variants[res]
        blob, blob_problems = (None, [])
        if not problems:
            blob, blob_problems = shaderblob.build(carrier.shaders[res]['code'], dxbc, binds, material_resource_fn(plan, v),
                                                   '%s_%s_%d' % (exported.name, carrier.name, res))
        out[res] = dict(blob=blob, dxbc=dxbc, bindings=binds, problems=problems + blob_problems, types=v['types'],
                        kind=v['kind'])
    return out, plan
