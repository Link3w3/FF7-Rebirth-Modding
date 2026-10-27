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
material cuts out). Translucent materials are not supported (the game's surface carriers are deferred).
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
TEXTURE_ORDER = 580000
CARRIERS = {
    'standard': dict(rmi='RMI_Surface_Standard_Wide_Detail', template=SEPH + 'PC0010_00_BodyA', short='Standard', solid=True,
                     prefer=('Color', 'Metallic', 'Roughness', 'Normal', 'Detail', 'WideOcclusion', 'DetailNormal'), fixed={}),
    'coverage': dict(rmi='RMI_Surface_Fabric_Coverage_Wide_Detail', template=SEPH + 'PC0010_00_Hair', short='Coverage',
                     solid=False, prefer=('Color', 'Normal', 'Roughness', 'Occlusion', 'Detail', 'Diffusion', 'WideOcclusion',
                                          'DetailNormal'),
                     fixed={'Coverage': WHITE, 'DetailCoverage': WHITE}),
}


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
        blend = i.get('blend_mode', 'BLEND_Opaque')
        if blend == 'BLEND_Masked' or (blend == 'BLEND_Opaque' and i.get('masked')):
            return 'coverage'
        if blend == 'BLEND_Opaque':
            return 'standard'
        raise ConvertError('%s materials are not supported: the game\'s surface carriers draw opaque and masked ones' % blend)

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
        c = CARRIERS[kind]
        cs, carrier_data = self.carrier(kind)
        if progress:
            progress('compiling %s on %s' % (short, c['rmi']))
        work = env.work('compile', _safe(package_name))
        built, plan = cb.build_blobs(exported, cs, work, prefer=c['prefer'], keep=('Coverage',) + tuple(c['fixed']),
                                     ignore_mask=c['solid'])
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
        # a texture the material names that is neither in the game nor in the project (a missing asset: the editor draws
        # it with its default texture) becomes the game's plain white of its kind
        srgb_of = {t['texture']: bool(t.get('srgb')) for t in exported.textures if t.get('texture')}
        missing = []
        for n, v in sorted(slot_textures.items()):
            if n in c['fixed'] or self.game.exists(v) or self.editor.asset_exists(v):
                continue
            slot_textures[n] = WHITE_SRGB if srgb_of.get(v) else WHITE_LINEAR
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
                    two_sided=two_sided, textures=slot_textures, cook=textures, game_textures=game_textures, missing=missing,
                    variants={res: dict(types=r['types'], kind=r['kind'], size=len(r['blob'])) for res, r in built.items()},
                    blend=exported.info.get('blend_mode'), shading_models=exported.info.get('shading_models'))
        return {carrier_name: carrier_pkg, package_name: mi_pkg}, info


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


def build_mod(store, game, cook, out_dir=None):
    """The mod of every material in the store: carrier copies, game material instances, cooked textures.
    cook(package names, content dir) -> report string. Returns (paths, entries, notes)."""
    out_dir = out_dir or env.work('mod')
    notes = []
    textures = sorted(set(t for info in store.manifest.values() for t in info.get('cook', []) if not game.exists(t)))
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
    for material, info in sorted(store.manifest.items()):
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
