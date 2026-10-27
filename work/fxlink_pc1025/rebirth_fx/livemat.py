"""Rebirth Materials' live edits of your own materials (the ones Game Materials made for the game) and of textures the game
does not have yet, and the queue of link commands the live edits go through.

Your own material in the game is a game material instance on a copy of one of the game's surface carriers (Game
Materials): its textures are on the carrier's texture parameters (Color, Normal, Roughness...), not under the names your
material gives them, and its values (scalars, colours) are compiled into its shader code. So a live edit of it goes to
the game translated:

  a texture       onto the carrier parameter(s) Game Materials put that texture on (made info 'inputs', or worked out from
                  the material's last export for one made before that was kept)
  a value         the material is exported again (its constants evaluated by the editor, as Game Materials does) and the
                  constants go to the game as a small texture on the material's live values parameter (made info 'live':
                  materials made by Game Materials with live values read their constants through it; a material made
                  before needs Make Game Materials once more)

A texture the game does not have (a new one, not cooked into a mod yet) goes to the game as a preview: an uncompressed
copy (16-bit PNG, linear) that the game imports (KismetRenderingLibrary.ImportFileAsTexture2D) and puts on the slot.
"""
import hashlib
import json
import os
import struct
import time
import zlib

import unreal

from . import livelink

# a Lua chunk (RebirthLiveLink's op "lua"): the textures in args.files (PNG files) imported and put on every slot of the
# controlled character (and what it holds) that wears a live copy (a dynamic instance the link made) of material args.path
LUA_SET_FILES = r'''
local args = ...
local want = link.objPath(args.path):lower()
local pawn, why = link.player()
if not pawn then return { ok = false, error = why } end
local krl = StaticFindObject("/Script/Engine.Default__KismetRenderingLibrary")
if not link.valid(krl) then return { ok = false, error = "the game has no KismetRenderingLibrary" } end
local texs = {}
for _, f in ipairs(args.files or {}) do
    local okI, t = pcall(function() return krl:ImportFileAsTexture2D(pawn, f.file) end)
    if not okI or not link.valid(t) then return { ok = false, error = "the game could not read " .. tostring(f.file) } end
    texs[#texs + 1] = { slot = f.slot, tex = t }
end
local function pathOf(o)
    local n = link.fullName(o)
    return n and (n:match("^%S+ (.+)$") or n):lower() or ""
end
local function mine(comp)
    local okO, owner = pcall(function() return comp:GetOwner() end)
    if not okO or not link.valid(owner) then return false end
    if owner:GetAddress() == pawn:GetAddress() then return true end
    local okP, parent = pcall(function() return owner:GetAttachParentActor() end)
    return okP and link.valid(parent) and parent:GetAddress() == pawn:GetAddress()
end
local slots = {}
for _, cls in ipairs({ "SkeletalMeshComponent", "StaticMeshComponent" }) do
    for _, comp in ipairs(FindAllOf(cls) or {}) do
        if mine(comp) then
            local okN, n = pcall(function() return comp:GetNumMaterials() end)
            for slot = 0, (okN and n or 0) - 1 do
                local okM, m = pcall(function() return comp:GetMaterial(slot, 0) end)
                if okM and link.valid(m) then
                    local name = link.fullName(m) or ""
                    if name:find("MaterialInstanceDynamic", 1, true) then
                        local okP, p = pcall(function() return m.Parent end)
                        if okP and link.valid(p) and pathOf(p) == want then
                            for _, x in ipairs(texs) do
                                pcall(function() m:SetTextureParameterValue(FName(x.slot), x.tex) end)
                            end
                            slots[#slots + 1] = string.format("%s #%d", name, slot)
                        end
                    end
                end
            end
        end
    end
end
if #slots == 0 then return { ok = false, error = "nothing the character wears is a live copy of " .. tostring(args.path) } end
return { ok = true, slots = slots, textures = #texs }
'''


def _saved(*parts):
    return os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), *parts)


# ---------------------------------------------------------------------------------------------------------------------
# what Game Materials made
# ---------------------------------------------------------------------------------------------------------------------

_made = {'stamp': None, 'manifest': {}}


def made_manifest():
    """Game Materials' made/manifest.json ({material package: info}), read again when it changes."""
    path = _saved('RebirthGameMaterials', 'made', 'manifest.json')
    try:
        stamp = os.path.getmtime(path)
    except OSError:
        return {}
    if _made['stamp'] != stamp:
        try:
            with open(path, encoding='utf-8') as f:
                _made['manifest'] = json.load(f)
            _made['stamp'] = stamp
        except (IOError, OSError, ValueError):
            pass
    return _made['manifest']


def made_info(package):
    package = package.split('.', 1)[0]
    m = made_manifest()
    if package in m:
        return m[package]
    low = package.lower()
    for k, v in m.items():
        if k.lower() == low:
            return v
    return None


def _export_folder(package):
    """Where Game Materials exported the material when it last made it (convert.Converter.convert)."""
    import re
    safe = re.sub(r'[^A-Za-z0-9_]+', '_', package.split('.', 1)[0]).strip('_')
    return _saved('RebirthGameMaterials', 'exports', safe)


def inputs_of(info, package):
    """{the material's texture parameter: [the game material's texture parameters it is on]} (a fused hair material's
    by the short name: 'Color' for '0:0:Color')."""
    if info.get('inputs'):
        return info['inputs']
    out = {}
    slots = info.get('textures', {})
    if info.get('native'):
        try:
            from .gamemat.convert import FUSED_HAIR_INPUTS
        except Exception:
            FUSED_HAIR_INPUTS = {}
        for param, slot in FUSED_HAIR_INPUTS.items():
            out.setdefault(param, []).append(slot)
        return out
    try:
        with open(os.path.join(_export_folder(package), 'material.json'), encoding='utf-8') as f:
            exported = json.load(f)
    except (IOError, OSError, ValueError):
        return out
    by_texture = {}
    for slot, tex in slots.items():
        by_texture.setdefault(tex, []).append(slot)
    for t in exported.get('textures', []):
        if t.get('type') != 'Texture2D' or not t.get('texture'):
            continue
        for slot in by_texture.get(t['texture'], []):
            if slot not in out.setdefault(t['parameter'], []):
                out[t['parameter']].append(slot)
    return {k: v for k, v in out.items() if v}


def slots_for(inputs, param):
    """The game material's texture parameters a texture parameter of the material is on ([] when its shader code does not
    sample it)."""
    if param in inputs:
        return inputs[param]
    parts = param.split(':')
    if len(parts) >= 3 and parts[2] in inputs:
        return inputs[parts[2]]
    return []


# ---------------------------------------------------------------------------------------------------------------------
# what the game can load
# ---------------------------------------------------------------------------------------------------------------------

_ids = {'game': None, 'mods': None, 'mods_stamp': None}


def _toc_ids(folder, cache_name):
    from .gamemat import convert
    from .gamemat import env
    if not os.path.isdir(folder):
        return set()
    return convert.game_package_ids(folder, env.work('cache', cache_name))


def game_has(object_path, paks=None):
    """Whether the running game can load this package: the game's own containers, or a mod in ~mods."""
    from .iostore_write import package_id
    paks = paks or unreal.RebirthFxLibrary.get_game_paks_directory()
    if not paks:
        return False
    if _ids['game'] is None:
        _ids['game'] = _toc_ids(paks, 'game_ids')
    mods = os.path.join(paks, '~mods')
    try:
        stamp = sorted((f, int(os.path.getmtime(os.path.join(mods, f)))) for f in os.listdir(mods) if f.lower().endswith('.utoc'))
    except OSError:
        stamp = []
    if _ids['mods'] is None or _ids['mods_stamp'] != stamp:
        _ids['mods'] = _toc_ids(mods, 'mods_ids')
        _ids['mods_stamp'] = stamp
    pid = package_id(object_path.split('.', 1)[0])
    return pid in _ids['game'] or pid in _ids['mods']


def game_texture_path(path):
    """'/Game/A/B.B' (the object path the game knows)."""
    pkg = path.split('.', 1)[0]
    return pkg + '.' + pkg.rsplit('/', 1)[-1]


# ---------------------------------------------------------------------------------------------------------------------
# files for the game: 16-bit PNGs (the game imports them as half-float textures, values as written)
# ---------------------------------------------------------------------------------------------------------------------

def live_dir(paks=None):
    paks = paks or unreal.RebirthFxLibrary.get_game_paks_directory()
    d = os.path.join(livelink.link_dir(paks), 'live')
    os.makedirs(d, exist_ok=True)
    return d


def write_png16(path, width, height, samples):
    """samples: bytes of big-endian 16-bit RGBA, row by row (PNG's own order)."""
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
    row = width * 8
    raw = b''.join(b'\x00' + samples[y * row:(y + 1) * row] for y in range(height))
    data = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 16, 6, 0, 0, 0)) +
            chunk(b'IDAT', zlib.compress(raw, 1)) + chunk(b'IEND', b''))
    tmp = path + '.tmp'
    with open(tmp, 'wb') as f:
        f.write(data)
    os.replace(tmp, path)
    return path


def _half(v):
    return struct.pack('>e', float(v))


MARKER = (1.0, 2.0, 3.0, 4.0)


def _pixel(r, g, b, a):
    """One 16-bit pixel as the game's import takes it: its ImageUtils reads a 16-bit PNG as B, G, R, A into a half-float
    RGBA texture, so red and blue are written swapped (and come out right)."""
    return _half(b) + _half(g) + _half(r) + _half(a)


def constants_png(path, floats):
    """The live values texture: pixel 0 the marker, then pixel 1 + i value i (its float bits in 11-bit pieces in r, g, b;
    a = 1)."""
    px = [_pixel(*MARKER)]
    for v in floats:
        bits = struct.unpack('<I', struct.pack('<f', float(v)))[0]
        px.append(_pixel(bits & 0x7FF, (bits >> 11) & 0x7FF, bits >> 22, 1.0))
    return write_png16(path, len(px), 1, b''.join(px))


PREVIEW_SIZE = int(os.environ.get('REBIRTHMAT_PREVIEW_SIZE', '1024'))


def _texture_image(tex, name, work):
    """The texture's picture as the editor has it (exported from the asset), as a PIL image."""
    from PIL import Image
    for ext in ('.tga', '.png'):
        path = os.path.join(work, name + ext)
        task = unreal.AssetExportTask()
        for k, v in (('object', tex), ('filename', path), ('automated', True), ('replace_identical', True), ('prompt', False)):
            task.set_editor_property(k, v)
        try:
            ok = unreal.Exporter.run_asset_export_task(task)
        except Exception:
            ok = False
        if ok and os.path.isfile(path):
            img = Image.open(path)
            img.load()
            return img
    src = ''
    data = tex.get_editor_property('asset_import_data')
    if data is not None:
        try:
            src = data.get_first_filename()
        except Exception:
            src = ''
    if src and os.path.isfile(src):
        img = Image.open(src)
        img.load()
        return img
    raise RuntimeError('could not export %s' % name)


def preview_png(texture_path, paks=None):
    """A texture the game does not have, as a file the game can import (16-bit PNG, linear values: an sRGB texture's
    colours decoded as the game's sampler would): its path."""
    from .gamemat import env
    env.vendor()
    import numpy as np
    from PIL import Image
    pkg = texture_path.split('.', 1)[0]
    tex = unreal.load_asset(pkg)
    if tex is None or not isinstance(tex, unreal.Texture2D):
        raise RuntimeError('%s is not a 2D texture the editor has' % pkg)
    name = pkg.rsplit('/', 1)[-1]
    work = env.work('live', 'preview')
    os.makedirs(work, exist_ok=True)
    img = _texture_image(tex, name, work).convert('RGBA')
    w, h = img.size
    if max(w, h) > PREVIEW_SIZE:
        f = max(w, h) / float(PREVIEW_SIZE)
        img = img.resize((max(1, int(round(w / f))), max(1, int(round(h / f)))), Image.BILINEAR)
        w, h = img.size
    a = np.asarray(img, dtype=np.float32) / 255.0
    if tex.get_editor_property('srgb'):
        c = a[..., :3]
        a[..., :3] = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    a = a[..., [2, 1, 0, 3]]           # (the game's import swaps red and blue back: _pixel)
    samples = np.ascontiguousarray(a).astype(np.float16).view(np.uint16).astype('>u2').tobytes()
    key = hashlib.sha1(pkg.lower().encode('utf-8')).hexdigest()[:8]
    return write_png16(os.path.join(live_dir(paks), 'tex_%s_%s.png' % (name[:40], key)), w, h, samples)


# ---------------------------------------------------------------------------------------------------------------------
# a material's values, evaluated by the editor (as Game Materials exports them)
# ---------------------------------------------------------------------------------------------------------------------

def evaluated_constants(asset, package):
    """(the material's constants as Game Materials compiles them: [float4], vectors, scalars, code hash)."""
    from .gamemat import env
    from .gamemat.material import Exported, code_hash
    from . import gamematerials
    folder = env.work('live', 'exports', package.strip('/').replace('/', '_'))
    os.makedirs(folder, exist_ok=True)
    err = gamematerials._native().export_material_for_game(asset, folder)
    if err:
        raise RuntimeError(err)
    exported = Exported(folder)
    return exported.constants[:exported.vectors + exported.scalars], exported.vectors, exported.scalars, code_hash(exported.code)


# ---------------------------------------------------------------------------------------------------------------------
# the link commands of the live edits, one at a time (each waits for the game's answer, or a few seconds)
# ---------------------------------------------------------------------------------------------------------------------

class Queue(object):
    def __init__(self, wait=3.0):
        self.items = []
        self.sent = None        # (seq, at, item)
        self.wait = wait
        self.last_status = None

    def put(self, op, on_answer=None, **fields):
        self.items.append(dict(op=op, fields=fields, on_answer=on_answer))

    def busy(self):
        return bool(self.items) or self.sent is not None

    def tick(self, paks, now=None):
        """Sends the next command once the last one was answered. Returns the answered status (or None)."""
        now = now or time.time()
        answered = None
        if self.sent is not None:
            seq, at, item = self.sent
            s = livelink.status(paks)
            if s and s.get('seq', -1) >= seq:
                self.sent = None
                self.last_status = s
                answered = s
                if item.get('on_answer'):
                    try:
                        item['on_answer'](s if s.get('seq') == seq else None)
                    except Exception:
                        unreal.log_warning('[Rebirth Materials] ' + __import__('traceback').format_exc())
            elif now - at > self.wait:
                self.sent = None
                if item.get('on_answer'):
                    try:
                        item['on_answer'](None)
                    except Exception:
                        pass
            else:
                return None
        if self.items:
            item = self.items.pop(0)
            seq = livelink.send(paks, item['op'], **item['fields'])
            self.sent = (seq, now, item)
        return answered
