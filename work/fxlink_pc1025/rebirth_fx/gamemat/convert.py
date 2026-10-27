"""Game Materials (keep the look): editor materials made into game packages, with their own shader code.

For every material (a Material or Material Instance in the project):
  1. the editor exports it (its translated HLSL and evaluated constants: RebirthFxLinkLibrary.ExportMaterialForGame);
  2. it is compiled with the game's base pass around it (dxc) for each skinned variant of a game carrier: one of the
     game's own surface material instances (RMI_Surface_*), whose shader map the game knows how to draw;
  3. the carrier is copied under a new name (/Game/RebirthCustom/...) with those pixel shaders inline, and a game material
     instance is made at the material's own path, parented to that copy, with the material's textures on the carrier's
     texture parameters;
  4. the material's textures are cooked by the editor (Create a Character System's Cook For Game) and converted to the
     game's IoStore format;
  5. every material made so far goes into one mod, RebirthGameMaterials_P, installed in the game's ~mods folder.

A model whose material slots point at these materials (by their editor paths) wears them in the game.

Opaque materials go on RMI_Surface_Standard_Wide_Detail (drawn solid), masked ones on
RMI_Surface_Fabric_Coverage_Wide_Detail (cut out in the base pass, the depth pass and the shadows exactly as the
material cuts out, against the blue noise as the game's coverage materials cut out), or, when they read UV3, on its
identifier twin RMI_Surface_Fabric_Identifier_Coverage_Wide_Detail (the same pixel shaders and texture parameters; its
vertex shaders pass on UV3 as well). Remake's hair and skin masters go on
the game's own hair and skin carriers and write those families' GBuffer (the game's hair and skin lighting: basepass), with
their own shader code. Translucent materials (Translucent, AlphaComposite, Additive: Remake's EndMaterial_Glass, _Tear,
_Thin, _Jewel, _Water, _Hologram, _InvisibleBody, _Particle, _Directional) go on the game's translucent character
carriers, drawn in its translucency pass: lit ones on RMI_Surface_Glass_Thin_Wide_Character, unlit ones on
RMI_Surface_Unlit_Hologram_Wide_Character (gamemat/translucent.py; REBIRTHFX_TRANSLUCENT=0: refused as before).

REBIRTHFX_FUSED_HAIR=1: Remake hair materials become instances of the game's own hair material instead (fused hair, no
shader of their own); REBIRTHFX_GAME_FAMILIES=0: every material is drawn as a standard one; REBIRTHFX_DITHERED_MASK=0:
masks are cut out at their clip value.

Live edits (Rebirth Materials): a material's info keeps 'inputs' (each texture parameter of the material: the carrier
texture parameters it is on) and, when its constants are read through a live values texture (material.Exported.
enable_live: one more free carrier texture parameter, the game's plain white by default so the baked constants stand),
'live' (that parameter, the constants' layout, the code they belong to). REBIRTHFX_LIVE_VALUES=0: constants baked only.
"""
import hashlib
import json
import os
import re
import shutil
import struct
import time
import traceback

from . import env
from . import carrier_build as cb
from . import packages
from . import translucent as tl
from . import pack
from . import zentex
from .material import Exported
from .pak import Pak
from .shaderlib import library_from_pak
from .. import iostore_write as W
from ..hdr import parse_header

MOD_NAME = 'RebirthGameMaterials_P'
ROOT = '/Game/RebirthCustom/'
SURFACE = '/Game/Renderer/MaterialInstance/Surface/'
SEPH = '/Game/Character/Player/PC0010_00_Sephiroth_Standard/Material/'
WHITE = '/Game/Renderer/Texture/FFFFFFFF_BC4.FFFFFFFF_BC4'
WHITE_SRGB = '/Game/Renderer/Texture/FFFFFFFF_sRGB.FFFFFFFF_sRGB'
WHITE_LINEAR = '/Game/Renderer/Texture/FFFFFFFF_HDR.FFFFFFFF_HDR'
FLAT_NORMAL = '/Game/Renderer/Texture/8080FFFF_BC5.8080FFFF_BC5'
# what a material's live values texture parameter has until a live edit puts the values there (not the marker: the
# constants compiled in stand)
LIVE_DEFAULT = WHITE_LINEAR
TEXTURE_ORDER = 580000
CARRIERS = {
    'standard': dict(rmi='RMI_Surface_Standard_Wide_Detail', template=SEPH + 'PC0010_00_BodyA', short='Standard', solid=True,
                     family='standard',
                     prefer=('Color', 'Metallic', 'Roughness', 'Normal', 'Detail', 'WideOcclusion', 'DetailNormal'), fixed={}),
    'coverage': dict(rmi='RMI_Surface_Fabric_Coverage_Wide_Detail', template=SEPH + 'PC0010_00_Hair', short='Coverage',
                     solid=False, family='standard', dithered=True,
                     prefer=('Color', 'Normal', 'Roughness', 'Occlusion', 'Detail', 'Diffusion', 'WideOcclusion',
                             'DetailNormal'),
                     fixed={'Coverage': WHITE, 'DetailCoverage': WHITE}),
    # Remake's hair with its own shader code on a copy of the game's hair carrier: its pixel shaders write the game's hair
    # GBuffer (the hair lighting, the bent normal of its Rebirth Hair Data), its coverage cut out the game's way
    'hair_shader': dict(rmi='RMI_Surface_Hair_Wide', template=SEPH + 'PC0010_00_Hair', short='Hair', solid=False,
                        family='hair', dithered=True,
                        prefer=('Color', 'Normal', 'Roughness', 'Occlusion', 'WideOcclusion', 'WideBentNormal'),
                        fixed={'Coverage': WHITE}),
    # Remake's eye with its own shader code, its Recovered Rebirth Eye Surface written as the game's eye GBuffer (the game's
    # eye lighting), on a copy of the game's eye carrier (UV0 and UV1); one that reads more texture coordinates goes on the
    # standard carrier, which passes on four ('eye_any')
    'eye': dict(rmi='RMI_Surface_Eye_Wide', template=SEPH + 'PC0010_00_Eye', short='Eye', solid=True, family='eye',
                prefer=('Color', 'Normal', 'Occlusion', 'ScrelaNormal', 'GazeNormal', 'IrisColor', 'IrisNormal', 'WideOcclusion'),
                fixed={}, fallback='eye_any'),
    'eye_any': dict(rmi='RMI_Surface_Standard_Wide_Detail', template=SEPH + 'PC0010_00_BodyA', short='Eye', solid=True,
                    family='eye',
                    prefer=('Color', 'Metallic', 'Roughness', 'Normal', 'Detail', 'WideOcclusion', 'DetailNormal'), fixed={}),
    # Remake's skin with its own shader code on a copy of the game's skin carrier: the game's skin lighting
    'skin': dict(rmi='RMI_Surface_Skin_Wide_Detail', template=SEPH + 'PC0010_00_Head', short='Skin', solid=False,
                 family='skin',
                 prefer=('Color', 'Normal', 'Roughness', 'Occlusion', 'Detail', 'Pores', 'WideOcclusion', 'DetailNormal',
                         'DetailRoughness'),
                 fixed={}, fallback='skin_any'),
    'skin_any': dict(rmi='RMI_Surface_Standard_Wide_Detail', template=SEPH + 'PC0010_00_BodyA', short='Skin', solid=False,
                     family='skin',
                     prefer=('Color', 'Metallic', 'Roughness', 'Normal', 'Detail', 'WideOcclusion', 'DetailNormal'), fixed={}),
    # Remake's cloth and subsurface masters: the game's fabric (on its fabric carriers) and subsurface lighting
    'fabric': dict(rmi='RMI_Surface_Fabric_Wide_Detail', template=SEPH + 'PC0010_00_BodyA', short='Fabric', solid=True,
                   family='fabric',
                   prefer=('Color', 'Normal', 'Roughness', 'Occlusion', 'Detail', 'Diffusion', 'WideOcclusion', 'DetailNormal',
                           'DetailRoughness'), fixed={}),
    'fabric_coverage': dict(rmi='RMI_Surface_Fabric_Coverage_Wide_Detail', template=SEPH + 'PC0010_00_Hair', short='Fabric',
                            solid=False, family='fabric', dithered=True,
                            prefer=('Color', 'Normal', 'Roughness', 'Occlusion', 'Detail', 'Diffusion', 'WideOcclusion',
                                    'DetailNormal'),
                            fixed={'Coverage': WHITE, 'DetailCoverage': WHITE}),
    'subsurface': dict(rmi='RMI_Surface_Subsurface_Wide', template=SEPH + 'PC0010_00_BodyA', short='Subsurface', solid=True,
                       family='subsurface',
                       prefer=('Color', 'Metallic', 'Normal', 'Roughness', 'Occlusion', 'Distribution', 'WideOcclusion'),
                       fixed={}, fallback='subsurface_any'),
    'subsurface_any': dict(rmi='RMI_Surface_Standard_Wide_Detail', template=SEPH + 'PC0010_00_BodyA', short='Subsurface',
                           solid=True, family='subsurface',
                           prefer=('Color', 'Metallic', 'Roughness', 'Normal', 'Detail', 'WideOcclusion', 'DetailNormal'),
                           fixed={}),
}
CARRIERS['subsurface_coverage'] = dict(CARRIERS['fabric_coverage'], short='Subsurface', family='subsurface')
# a kind for masked materials of a family drawn solid otherwise
MASKED_KINDS = {'fabric': 'fabric_coverage', 'subsurface': 'subsurface_coverage'}
# a masked material that reads a fourth texture coordinate (UV3): the coverage carrier's vertex shaders pass on UV0-UV2
# only, so it goes on the game's identifier twin of that carrier, whose pixel shaders and texture parameters are the
# plain carrier's own and whose vertex shaders pass on UV3 as well (the fallback of each coverage kind)
UV3_COVERAGE = 'RMI_Surface_Fabric_Identifier_Coverage_Wide_Detail'
for _kind in ('coverage', 'fabric_coverage', 'subsurface_coverage'):
    CARRIERS[_kind + '_uv3'] = dict(CARRIERS[_kind], rmi=UV3_COVERAGE)
    CARRIERS[_kind]['fallback'] = _kind + '_uv3'
del _kind
# translucent materials (gamemat/translucent.py), drawn in the game's translucency pass with its own two-target blending
# (BLEND_AlphaCompositeColored): lit ones on the game's thin glass for characters (forward lit: its pass gives the
# translucency lighting volume and the directional light), unlit ones on its unlit glow for characters (its base pass
# gives the scene depth for depth fades), or on the glass when they need more than the glow's four texture parameters
TRANSLUCENT_BLENDS = ('BLEND_AlphaComposite', 'BLEND_Translucent', 'BLEND_Additive')
CARRIERS['translucent'] = dict(rmi='RMI_Surface_Glass_Thin_Wide_Character', template=SEPH + 'PC0010_00_BodyA', short='Glass',
                               solid=True, family='translucent', lit=True,
                               prefer=('Color', 'Metallic', 'Normal', 'Roughness', 'Occlusion', 'Opacity', 'WideOcclusion',
                                       'Thinness', 'Muddiness', 'Transparency', 'TransparencyCoefficient', 'Transmittance',
                                       'TransmittanceCoefficient'), fixed={})
CARRIERS['translucent_unlit_glass'] = dict(CARRIERS['translucent'], short='Unlit', lit=False)
CARRIERS['translucent_unlit'] = dict(rmi='RMI_Surface_Unlit_Hologram_Wide_Character', template=SEPH + 'PC0010_00_BodyA',
                                     short='Unlit', solid=True, family='translucent', lit=False,
                                     prefer=('Normal', 'Roughness', 'Occlusion', 'WideOcclusion'), fixed={},
                                     slot_fallback='translucent_unlit_glass')
# the Remake masters drawn as one of the game's surface families (their own shader code, the family's GBuffer)
GAME_FAMILY_MASTERS = {'EndMaterial_Hair': 'hair_shader', 'EndMaterial_Skin': 'skin', 'EndMaterial_Eye': 'eye',
                       'EndMaterial_Fabric': 'fabric', 'EndMaterial_Subsurface': 'subsurface'}
# what a material's exported code needs for its master's family (else it is drawn as a standard one)
FAMILY_NEEDS = {'eye': 'NUM_MATERIAL_OUTPUTS_REBIRTHEYEBRIDGE'}
# (fused hair, REBIRTHFX_FUSED_HAIR=1) A Remake hair material (on EndMaterial_Hair) becomes an instance of the game's own
# hair material: RM_Surface's RMI_Surface_Hair_Wide, which Rebirth's own hair wears (its hair shading, cylindrical normals,
# bent normals), with the material's textures on its inputs. No shader of it is the material's own: no carrier copy,
# nothing compiled. Otherwise (the default) they keep their own shader code on the game's hair carrier ('hair_shader').
CARRIERS['hair'] = dict(rmi='RMI_Surface_Hair_Wide', template=SEPH + 'PC0010_00_Hair', short='Hair', native=True, solid=False,
                        prefer=(), fixed={})
FUSED_HAIR_MASTERS = ('EndMaterial_Hair',)
# the material's texture parameters (Remake's "uv:slot:Name", by Name) -> the game hair's inputs
FUSED_HAIR_INPUTS = {'Color': 'Color', 'Coverage': 'Coverage', 'Normal': 'Normal', 'Occlusion': 'WideOcclusion',
                     'BentNormal': 'WideBentNormal'}
# a packed map split into the game's single-channel ones: (its channel, the game hair's input, the new texture's suffix)
FUSED_HAIR_SPLIT = {'Metallic/Roughness/Variant': (('r', 'Metallic', 'Mr'), ('g', 'Roughness', 'Mg'))}


class ConvertError(Exception):
    pass


def _package(object_path):
    return object_path.split('.', 1)[0]


def _safe(name):
    return re.sub(r'[^A-Za-z0-9_]+', '_', name).strip('_')


def game_package_ids(paks_dir, cache_dir=None):
    """The package ids of every package in the game's own containers (Paks/*.utoc, the optional chunks too): the ids of
    their export bundle chunks, read from the tables of contents (cached in cache_dir until a container changes)."""
    tocs = sorted(f for f in os.listdir(paks_dir) if f.lower().endswith('.utoc'))
    stamp = [[f, os.path.getsize(os.path.join(paks_dir, f)), int(os.path.getmtime(os.path.join(paks_dir, f)))] for f in tocs]
    if cache_dir:
        stamp_path, ids_path = os.path.join(cache_dir, 'game_package_ids.json'), os.path.join(cache_dir, 'game_package_ids.bin')
        try:
            with open(stamp_path, encoding='utf-8') as f:
                if json.load(f) == stamp:
                    with open(ids_path, 'rb') as g:
                        raw = g.read()
                    return set(struct.unpack('<%dQ' % (len(raw) // 8), raw))
        except (IOError, OSError, ValueError, struct.error):
            pass
    ids = set()
    for name in tocs:
        with open(os.path.join(paks_dir, name), 'rb') as f:
            head = f.read(64)
            if head[:16] != b'-==--==--==--==-':
                continue
            hdr_size, count = struct.unpack_from('<II', head, 20)
            f.seek(hdr_size)
            raw = f.read(12 * count)
        for i in range(len(raw) // 12):
            if raw[12 * i + 11] == 2:                       # EIoChunkType::ExportBundleData: one per package
                ids.add(struct.unpack_from('<Q', raw, 12 * i)[0])
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)
        with open(ids_path, 'wb') as g:
            g.write(struct.pack('<%dQ' % len(ids), *sorted(ids)))
        with open(stamp_path, 'w', encoding='utf-8') as f:
            json.dump(stamp, f)
    return ids


class GameData(object):
    """The game's packages, container headers and shader library, read through the editor plugin (cached in the work
    folder)."""

    def __init__(self, native, paks_dir=None):
        self.native = native
        self.paks_dir = paks_dir or native.get_game_paks_directory()
        if not self.paks_dir or not os.path.isdir(self.paks_dir):
            raise ConvertError('the game\'s Paks folder was not found (%r): set it in Rebirth FX first' % self.paks_dir)
        self._packages = {}
        self._entries = {}
        self._containers = set()
        self._library = None
        self._ids = None

    def package(self, name):
        name = _package(name)
        if name not in self._packages:
            path = env.work('cache', 'packages', name.strip('/').replace('/', '__') + '.uasset')
            if not os.path.isfile(path):
                os.makedirs(os.path.dirname(path), exist_ok=True)
                err = self.native.save_game_package_to_file(name, path)
                if err:
                    raise ConvertError('%s: %s' % (name, err))
            with open(path, 'rb') as f:
                self._packages[name] = f.read()
        return self._packages[name]

    def package_ids(self):
        if self._ids is None:
            self._ids = game_package_ids(self.paks_dir, env.work('cache'))
        return self._ids

    def exists(self, name):
        """Whether the game has this package (in any of its own containers)."""
        return W.package_id(_package(name)) in self.package_ids()

    def entries_for(self, name):
        """{package id: store entry} of the game container holding package `name` (merged into what was read so far)."""
        name = _package(name)
        pid = W.package_id(name)
        if pid not in self._entries:
            path = env.work('cache', 'headers', name.strip('/').replace('/', '__') + '.bin')
            os.makedirs(os.path.dirname(path), exist_ok=True)
            got = self.native.save_game_container_header_to_file(name, path)
            err = got[0] if isinstance(got, (tuple, list)) else got
            if err:
                raise ConvertError('%s: %s' % (name, err))
            with open(path, 'rb') as f:
                cid, entries = parse_header(f.read())
            self._entries.update(entries)
        return self._entries

    def library(self):
        if self._library is None:
            pak = Pak(os.path.join(self.paks_dir, 'pakchunk0-WindowsNoEditor.pak'))
            cache = env.work('cache', 'End_shader_library_header.bin')
            os.makedirs(os.path.dirname(cache), exist_ok=True)
            self._library = library_from_pak(pak, header_cache=cache)
        return self._library


class Converter(object):
    def __init__(self, game, editor):
        """editor: export(material path, folder) -> error string or ''; cook(package names, out content dir) -> report."""
        self.game = game
        self.editor = editor
        self._carriers = {}
        self.report = dict(materials={}, problems=[])

    def carrier(self, kind):
        if kind not in self._carriers:
            c = CARRIERS[kind]
            data = self.game.package(SURFACE + c['rmi'])
            self._carriers[kind] = (cb.CarrierShaders(c['rmi'], data, self.game.library()), data)
        return self._carriers[kind]

    def kind_of(self, exported):
        i = exported.info
        if i.get('domain', 'MD_Surface') != 'MD_Surface':
            raise ConvertError('only surface materials (its domain is %s)' % i.get('domain'))
        base = (i.get('base_material') or '').split('.')[0].rsplit('/', 1)[-1]
        if base in FUSED_HAIR_MASTERS and os.environ.get('REBIRTHFX_FUSED_HAIR', '0') == '1':
            return 'hair'
        blend = i.get('blend_mode', 'BLEND_Opaque')
        if base in GAME_FAMILY_MASTERS and blend in ('BLEND_Opaque', 'BLEND_Masked') and \
                os.environ.get('REBIRTHFX_GAME_FAMILIES', '1') != '0':
            kind = GAME_FAMILY_MASTERS[base]
            if blend == 'BLEND_Masked' or i.get('masked'):
                kind = MASKED_KINDS.get(kind, kind)
            need = FAMILY_NEEDS.get(kind)
            if not need or need in exported.code:
                return kind
        if blend == 'BLEND_Masked' or (blend == 'BLEND_Opaque' and i.get('masked')):
            return 'coverage'
        if blend == 'BLEND_Opaque':
            return 'standard'
        if blend in TRANSLUCENT_BLENDS and os.environ.get('REBIRTHFX_TRANSLUCENT', '1') != '0':
            models = list(i.get('shading_models') or ['MSM_DefaultLit'])
            return 'translucent_unlit' if models == ['MSM_Unlit'] else 'translucent'
        raise ConvertError('%s materials are not supported: the game\'s surface carriers draw opaque, masked and translucent '
                           '(Translucent, AlphaComposite, Additive) ones' % blend)

    def convert(self, material_path, progress=None):
        """One material -> {package name: bytes} (its carrier copy and its game material instance) and the textures it
        needs that the game does not have."""
        package_name = _package(material_path)
        short = package_name.rsplit('/', 1)[-1]
        if self.game.exists(package_name):
            raise ConvertError('%s is one of the game\'s own packages: make a copy of it under another name first' % package_name)
        folder = env.work('exports', _safe(package_name))
        if os.path.isdir(folder):
            shutil.rmtree(folder)
        os.makedirs(folder)
        err = self.editor.export(material_path, folder)
        if err:
            raise ConvertError('export: %s' % err)
        exported = Exported(folder)
        kind = self.kind_of(exported)
        if CARRIERS[kind].get('native'):
            return self.convert_native(material_path, package_name, exported, kind)
        # (a carrier whose vertex shaders do not pass on every texture coordinate the material reads: its fallback)
        while True:
            cs, carrier_data = self.carrier(kind)
            missing = cs.missing_texcoords(exported)
            if not missing or not CARRIERS[kind].get('fallback'):
                break
            kind = CARRIERS[kind]['fallback']
        # (a translucent carrier with fewer free texture parameters than the material needs: its fallback)
        while not missing and CARRIERS[kind].get('slot_fallback') and not self._textures_fit(
                exported, cs, ('Coverage',) + tuple(CARRIERS[kind]['fixed'])):
            kind = CARRIERS[kind]['slot_fallback']
            cs, carrier_data = self.carrier(kind)
            missing = cs.missing_texcoords(exported)
        if missing:
            raise ConvertError('the material reads texture coordinate(s) %s, which %s does not pass on' % (
                ', '.join('UV%d' % k for k in missing), CARRIERS[kind]['rmi']))
        c = CARRIERS[kind]
        if progress:
            progress('compiling %s on %s' % (short, c['rmi']))
        work = env.work('compile', _safe(package_name))
        dithered = bool(c.get('dithered')) and os.environ.get('REBIRTHFX_DITHERED_MASK', '1') != '0'
        keep = ('Coverage',) + tuple(c['fixed'])
        live_note = None
        if os.environ.get('REBIRTHFX_LIVE_VALUES', '1') != '0' and exported.has_constants():
            if self._live_fits(exported, cs, keep):
                exported.enable_live(LIVE_DEFAULT)
            else:
                live_note = 'no texture parameter of %s is left for its live values' % c['rmi']

        def build_blobs(exported):
            if c.get('family') == 'translucent':
                return tl.build_blobs(exported, cs, work, prefer=c['prefer'], keep=keep, lit=c.get('lit', True))
            return cb.build_blobs(exported, cs, work, prefer=c['prefer'], keep=keep,
                                  ignore_mask=c['solid'], family=c.get('family', 'standard'), dithered=dithered)
        try:
            built, plan = build_blobs(exported)
        except ValueError as e:
            if not exported.live or 'named texture parameters free' not in str(e):
                raise
            # (no carrier slot left for the live values after all: the constants compiled in only)
            live_note = str(e)
            exported = Exported(folder)
            built, plan = build_blobs(exported)
        problems = {res: r['problems'] for res, r in built.items() if r['problems']}
        if problems:
            lines = []
            for res, ps in sorted(problems.items()):
                lines += ['%s (variant %d): %s' % (', '.join(built[res]['types'])[:80], res, p) for p in ps[:3]]
            raise ConvertError('the shaders do not fit the game\'s %s:\n  %s' % (c['rmi'], '\n  '.join(lines[:8])))
        named = dict(cs.named)
        by_index = {t['index']: t for t in exported.textures if t['type'] == 'Texture2D'}
        slot_textures = {named[j]: by_index[k]['texture'] for k, j in sorted(plan.items())}
        slot_textures.update(c['fixed'])
        # (for live edits: where each texture parameter of the material is, and its live values)
        inputs, live = {}, None
        for k, j in sorted(plan.items()):
            t = by_index[k]
            if t.get('live'):
                live = dict(slot=named[j], vectors=exported.vectors, scalars=exported.scalars, code_hash=exported.code_hash,
                            baked=[list(v) for v in exported.constants[:exported.vectors + exported.scalars]])
                continue
            if named[j] not in inputs.setdefault(t['parameter'], []):
                inputs[t['parameter']].append(named[j])
        if exported.live and live is None:
            live_note = 'its shaders read none of its values'
        # a texture the material names that the game does not have and the mod cannot carry (missing from the project: the
        # editor draws it with its default texture; or an engine or plugin texture, outside /Game/, such as
        # /Engine/EngineMaterials/FlatNormal) becomes the game's own of its kind: its flat normal for a normal map, else
        # its plain white
        srgb_of = {t['texture']: bool(t.get('srgb')) for t in exported.textures if t.get('texture')}
        normal_of = {t['texture']: t.get('compression') == 'TC_Normalmap' for t in exported.textures if t.get('texture')}
        missing = []
        for n, v in sorted(slot_textures.items()):
            if n in c['fixed'] or self.game.exists(v):
                continue
            if _package(v).startswith('/Game/') and self.editor.asset_exists(v):
                continue
            slot_textures[n] = FLAT_NORMAL if normal_of.get(v) else (WHITE_SRGB if srgb_of.get(v) else WHITE_LINEAR)
            missing.append(v)
        tag = hashlib.sha1(package_name.encode('utf-8')).hexdigest()[:6]
        carrier_name = ROOT + '%s_%s/%s_%s' % (_safe(short), tag, _safe(short), c['short'])
        blobs = {res: r['blob'] for res, r in built.items()}
        report = {}
        carrier_pkg = packages.carrier_package(carrier_name, carrier_data, cs.raw, blobs, report)
        two_sided = bool(exported.info.get('two_sided'))
        if two_sided:
            carrier_pkg = packages.set_two_sided(carrier_pkg, carrier_name)
        template = self.game.package(c['template'])
        mi_pkg = packages.game_mi(package_name, template, carrier_name, slot_textures, report)
        own_textures = sorted(set(v for n, v in slot_textures.items() if n not in c['fixed']))
        game_textures = [t for t in own_textures if self.game.exists(t)]
        textures = [t for t in own_textures if t not in game_textures]
        info = dict(material=material_path, kind=kind, carrier=c['rmi'], carrier_copy=carrier_name, template=c['template'],
                    family=c.get('family', 'standard'), dithered=dithered, two_sided=two_sided, textures=slot_textures, cook=textures, game_textures=game_textures, missing=missing,
                    variants={res: dict(types=r['types'], kind=r['kind'], size=len(r['blob'])) for res, r in built.items()},
                    blend=exported.info.get('blend_mode'), shading_models=exported.info.get('shading_models'),
                    inputs=inputs, live=live, live_note=None if live else live_note)
        if c.get('family') == 'translucent':
            # (what each variant's shader takes from the game's translucency pass: translucent.features)
            info['translucent'] = dict(lit=bool(c.get('lit', True)), features={res: r.get('features') for res, r in built.items()})
        return {carrier_name: carrier_pkg, package_name: mi_pkg}, info

    @staticmethod
    def _live_fits(exported, cs, keep):
        """Whether the carrier has a named texture parameter left for the live values once the material's own textures
        are on (textures that are the same asset share one)."""
        by_index = {t['index']: t for t in exported.textures if t['type'] == 'Texture2D'}
        used = set(k for kind, k in exported.used_textures() if kind == 'Texture2D')
        assets = set(by_index[k]['texture'] for k in used if k in by_index)
        free = [k for k, n in cs.named if n not in keep]
        return len(assets) + 1 <= len(free)

    @staticmethod
    def _textures_fit(exported, cs, keep):
        """Whether the carrier has a named texture parameter for every texture the material uses (textures that are the
        same asset share one), and one more for its live values when it has constants and live values are on."""
        by_index = {t['index']: t for t in exported.textures if t['type'] == 'Texture2D'}
        used = set(k for kind, k in exported.used_textures() if kind == 'Texture2D')
        assets = set(by_index[k]['texture'] for k in used if k in by_index)
        live = 1 if (os.environ.get('REBIRTHFX_LIVE_VALUES', '1') != '0' and exported.has_constants()) else 0
        free = [k for k, n in cs.named if n not in keep]
        return len(assets) + live <= len(free)

    def convert_native(self, material_path, package_name, exported, kind):
        """(fused hair) The material as an instance of one of the game's own material instances (the kind's rmi), its
        textures on that one's inputs: {package name: bytes} (just the instance) and its info."""
        c = CARRIERS[kind]
        slots, inputs = {}, {}
        for t in exported.textures:
            if t.get('type') != 'Texture2D' or not t.get('texture'):
                continue
            parts = t['parameter'].split(':')
            name = parts[2] if len(parts) >= 3 else t['parameter']
            if name in FUSED_HAIR_INPUTS:
                slots.setdefault(FUSED_HAIR_INPUTS[name], t['texture'])
                inputs.setdefault(t['parameter'], []).append(FUSED_HAIR_INPUTS[name])
            elif name in FUSED_HAIR_SPLIT:
                made = self.editor.split_channels(t['texture'], [(ch, suffix) for ch, _, suffix in FUSED_HAIR_SPLIT[name]])
                for (ch, slot, suffix), path in zip(FUSED_HAIR_SPLIT[name], made):
                    slots.setdefault(slot, path)
        slots.setdefault('Coverage', WHITE)   # (an opaque one, such as the hair's core: covered all over)
        srgb_of = {t['texture']: bool(t.get('srgb')) for t in exported.textures if t.get('texture')}
        missing = []
        for n, v in sorted(slots.items()):
            if v == WHITE or self.game.exists(v):
                continue
            if _package(v).startswith('/Game/') and self.editor.asset_exists(v):
                continue
            slots[n] = FLAT_NORMAL if n in ('Normal', 'WideBentNormal') else (WHITE_SRGB if srgb_of.get(v) else WHITE_LINEAR)
            missing.append(v)
        parent = SURFACE + c['rmi']
        report = {}
        mi_pkg = packages.game_mi(package_name, self.game.package(c['template']), parent, slots, report)
        own = sorted(set(v for v in slots.values() if v != WHITE))
        game_textures = [t for t in own if self.game.exists(t)]
        textures = [t for t in own if t not in game_textures]
        info = dict(material=material_path, kind=kind, carrier=c['rmi'], carrier_copy=None, native=True, template=c['template'],
                    two_sided=False, textures=slots, cook=textures, game_textures=game_textures, missing=missing, variants={},
                    blend=exported.info.get('blend_mode'), shading_models=exported.info.get('shading_models'),
                    inputs=inputs, live=None, live_note='an instance of the game\'s own hair material: its values are the game\'s')
        return {package_name: mi_pkg}, info


class Store(object):
    """What has been made so far (work/made): each material's packages and info, so the mod always holds them all."""

    def __init__(self):
        self.root = env.work('made')
        self.manifest_path = os.path.join(self.root, 'manifest.json')
        try:
            with open(self.manifest_path, encoding='utf-8') as f:
                self.manifest = json.load(f)
        except (IOError, OSError, ValueError):
            self.manifest = {}

    def _file(self, package_name):
        return os.path.join(self.root, 'packages', package_name.strip('/').replace('/', '__') + '.uasset')

    def put(self, material_path, made, info):
        for name, data in made.items():
            path = self._file(name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'wb') as f:
                f.write(data)
        info = dict(info, packages=sorted(made), made=time.strftime('%Y-%m-%d %H:%M:%S'))
        self.manifest[_package(material_path)] = info
        self.save()

    def remove(self, material_package):
        self.manifest.pop(material_package, None)
        self.save()

    def save(self):
        os.makedirs(self.root, exist_ok=True)
        with open(self.manifest_path, 'w', encoding='utf-8') as f:
            json.dump(self.manifest, f, indent=1, sort_keys=True)

    def package(self, name):
        with open(self._file(name), 'rb') as f:
            return f.read()


# the engine's flat normals: not in the game; a material made before convert() swapped them for the game's own keeps them
ENGINE_FLAT_NORMALS = ('/Engine/EngineMaterials/FlatNormal', '/Engine/EngineMaterials/DefaultNormal')


def heal_engine_textures(store, game, notes):
    """Stored materials naming a texture outside /Game/ that the game does not have (made before convert() swapped those
    for the game's own): an engine flat normal becomes the game's flat normal and the material instance is made again from
    its stored parts; anything else leaves that material out of the mod (the rest still builds), with a note to make it
    again. Returns the materials left out."""
    dropped = set()
    for material, info in sorted(store.manifest.items()):
        named = set(info.get('textures', {}).values()) | set(info.get('cook', []))
        bad = sorted(v for v in named if not _package(v).startswith('/Game/') and not game.exists(v))
        if not bad:
            continue
        unknown = [v for v in bad if _package(v) not in ENGINE_FLAT_NORMALS]
        if unknown:
            dropped.add(material)
            notes.append('%s was left out of the mod: it uses %s, which the game does not have; make it a game material '
                         'again' % (material.rsplit('/', 1)[-1], ', '.join(u.rsplit('.', 1)[-1] for u in unknown)))
            continue
        slots = {n: (FLAT_NORMAL if _package(v) in ENGINE_FLAT_NORMALS else v) for n, v in info['textures'].items()}
        mi = packages.game_mi(material, game.package(info['template']), info['carrier_copy'] or SURFACE + info['carrier'], slots)
        made = {material: mi}
        if info['carrier_copy']:
            made[info['carrier_copy']] = store.package(info['carrier_copy'])
        store.put(info['material'], made, dict(info, textures=slots, cook=[t for t in info.get('cook', []) if t not in bad],
                                               missing=sorted(set(info.get('missing', [])) | set(bad))))
        notes.append('%s: the engine\'s FlatNormal swapped for the game\'s flat normal' % material.rsplit('/', 1)[-1])
    return dropped


def build_mod(store, game, cook, out_dir=None):
    """The mod of every material in the store: carrier copies, game material instances, cooked textures.
    cook(package names, content dir) -> report string. Returns (paths, entries, notes)."""
    out_dir = out_dir or env.work('mod')
    notes = []
    dropped = heal_engine_textures(store, game, notes)
    manifest = {m: i for m, i in store.manifest.items() if m not in dropped}
    textures = sorted(set(t for info in manifest.values() for t in info.get('cook', []) if not game.exists(t)))
    tex_items = []
    if textures:
        content = env.work('cook', 'End', 'Content')
        if os.path.isdir(env.work('cook')):
            shutil.rmtree(env.work('cook'))
        rep = cook([_package(t) for t in textures], content)
        notes.append(rep.strip())
        for t in textures:
            rel = _package(t)[len('/Game/'):]
            ua = os.path.join(content, rel + '.uasset')
            if not os.path.isfile(ua):
                raise ConvertError('%s was not cooked (%s)' % (t, rep.strip()[-300:]))
            with open(ua, 'rb') as f:
                ua_bytes = f.read()
            ub_path = os.path.join(content, rel + '.ubulk')
            ub_bytes = b''
            if os.path.isfile(ub_path):
                with open(ub_path, 'rb') as f:
                    ub_bytes = f.read()
            data, bulk, r = zentex.convert(ua_bytes, ub_bytes)
            tex_items.append(dict(data=data, bulk=bulk or None, like=None, load_order=TEXTURE_ORDER))
    retail = {}
    items = []
    for material, info in sorted(manifest.items()):
        if info.get('native'):
            # (fused hair) an instance of the game's own material instance: no carrier copy
            retail.update(game.entries_for(info['template']))
            template_order = retail[W.package_id(info['template'])]['load_order']
            items.append(dict(data=store.package(material), like=info['template'], load_order=max(template_order, TEXTURE_ORDER + 1)))
            continue
        carrier = info['carrier_copy']
        like_carrier = SURFACE + info['carrier']
        retail.update(game.entries_for(like_carrier))
        retail.update(game.entries_for(info['template']))
        carrier_order = retail[W.package_id(like_carrier)]['load_order']
        items.append(dict(data=store.package(carrier), like=like_carrier, load_order=carrier_order))
        template_order = retail[W.package_id(info['template'])]['load_order']
        items.append(dict(data=store.package(material), like=info['template'],
                          load_order=max(template_order, carrier_order + 1, TEXTURE_ORDER + 1)))
    items += tex_items
    for it in items:
        name = pack.package_name(it['data'])
        if game.exists(name) and not it.get('replace'):
            raise ConvertError('%s is one of the game\'s own packages: the mod must not replace it' % name)
    paths, entries = pack.build(items, out_dir, MOD_NAME, retail)
    back = pack.read_back(paths[0])
    for it in items:
        pid = W.package_id(pack.package_name(it['data']))
        if back.get((pid, 2)) != it['data'] or (it.get('bulk') and back.get((pid, 3)) != it['bulk']):
            raise ConvertError('%s does not read back from the mod' % pack.package_name(it['data']))
    return paths, entries, notes


def install(paths, paks_dir):
    """Copies the mod into the game's ~mods folder. Returns (installed paths, error or None)."""
    mods = os.path.join(paks_dir, '~mods')
    os.makedirs(mods, exist_ok=True)
    out = []
    try:
        for p in paths:
            dst = os.path.join(mods, os.path.basename(p))
            shutil.copyfile(p, dst)
            out.append(dst)
    except (IOError, OSError) as e:
        return out, 'could not write %s (%s): close the game, then use Install Game Materials' % (getattr(e, 'filename', '?'), e)
    return out, None
