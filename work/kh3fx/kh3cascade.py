"""KINGDOM HEARTS III Cascade particle systems -> UE 4.26 editor packages the End editor can open (and convert to Niagara).

KH3's cooked .uasset + .uexp keeps every object as tagged properties, the same format a 4.26 editor package uses, so
the objects are copied as they are into a new editor package (4.26 header, KH3's names), with:
  - KH3-only modules (ParticleModuleSQEX_*, TypeDataSQEX_*) taken out of the emitters (the End engine has none of
    them); an emitter driven by a TypeDataSQEX module is taken out whole;
  - references to KH3 content outside the package (its materials, meshes, sounds) cleared, unless `remap` gives an
    object of the project for them: {KH3 object path: (class package, class name[, project object path])}, the KH3
    path in any case; without a project path the reference keeps KH3's path;
  - ParticleModuleRequired's cooked tail (bCooked, derived data) cut back to what an editor package has.

    python3 kh3cascade.py <KH3 .uasset> <out .uasset> [package path]
"""
import os
import struct
import sys
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, '/work/kh3bnm/src/rebirth_fx']
import edpkg          # noqa: E402
import kh3bonamik as k  # noqa: E402
import tagged         # noqa: E402

PARTICLE_SYSTEM_CUSTOM_VERSION = (struct.pack('<IIII', 0x4A56EB40, 0x10F511DC, 0x92D3347E, 0xB2C96AE7), 2)
RF_PUBLIC, RF_STANDALONE, RF_TRANSACTIONAL = 0x1, 0x2, 0x8


def _is_kh3_only(class_name):
    return class_name.startswith('ParticleModuleSQEX_') or class_name.startswith('ParticleModuleTypeDataSQEX')


def split_name(s):
    """An FName's text and number the way the engine splits a string: a trailing _<digits> (no leading 0 unless it is
    the only digit, not the first character, at most MAX_int32) is the number + 1."""
    i = len(s)
    while i > 1 and s[i - 1].isdigit():
        i -= 1
    if i == len(s) or i < 2 or s[i - 1] != '_':
        return s, 0
    digits = s[i:]
    if digits[0] == '0' and len(digits) > 1:
        return s, 0
    v = int(digits)
    if v > 0x7FFFFFFF:
        return s, 0
    return s[:i - 1], v + 1


def import_path(pk, idx):
    parts = []
    while idx < 0:
        imp = pk.imports[-idx - 1]
        parts.append(imp['name'])
        idx = imp['outer']
    parts.reverse()
    return parts[0] + ('.' + ':'.join(parts[1:]) if len(parts) > 1 else '')


class Converter(object):
    def __init__(self, uasset, uexp, remap=None):
        self.pk = pk = k.Package(uasset, uexp)
        self.remap_paths = {p.lower(): tuple(v) for p, v in (remap or {}).items()}
        self.props = {}
        for i, e in enumerate(pk.exports):
            self.props[i + 1] = tagged.parse(pk.data, e['offset'], e['offset'] + e['size'], pk.names)
        self.cls = {i + 1: pk.class_name(e) for i, e in enumerate(pk.exports)}
        self.notes = []

    # -- what goes ------------------------------------------------------------------------------------------------
    def _children(self):
        ch = {}
        for i, e in enumerate(self.pk.exports):
            ch.setdefault(e['outer'], []).append(i + 1)
        return ch

    def _subtree(self, idx, children):
        out = [idx]
        for c in children.get(idx, []):
            out.extend(self._subtree(c, children))
        return out

    def _refs_of(self, idx, prop_name):
        t = tagged.find(self.props[idx], prop_name)
        if t is None:
            return []
        return [struct.unpack_from('<i', self.pk.data, r)[0] for r in t.refs]

    def dropped(self):
        children = self._children()
        drop = set()
        for idx, c in self.cls.items():
            if _is_kh3_only(c):
                drop.update(self._subtree(idx, children))
        # an emitter whose type data is KH3's own goes whole
        for idx, c in self.cls.items():
            if c in ('ParticleSpriteEmitter', 'ParticleEmitter'):
                for lod in self._refs_of(idx, 'LODLevels'):
                    if lod > 0 and any(t > 0 and _is_kh3_only(self.cls[t]) for t in self._refs_of(lod, 'TypeDataModule')):
                        drop.update(self._subtree(idx, children))
                        self.notes.append('emitter %s left out (KH3 type data %s)' % (self.pk.exports[idx - 1]['name'],
                                          [self.cls[t] for t in self._refs_of(lod, 'TypeDataModule')]))
                        break
        # a sprite emitter without a material of its own in KH3 draws nothing there (KH3's helper emitters: they carry
        # KH3's own modules, forces, parents, takeovers); here it would draw the default material, so it goes too
        for idx, c in self.cls.items():
            if c in ('ParticleSpriteEmitter', 'ParticleEmitter') and idx not in drop:
                lods = [l for l in self._refs_of(idx, 'LODLevels') if l > 0]
                if not lods:
                    continue
                req = [r for r in self._refs_of(lods[0], 'RequiredModule') if r > 0]
                td = [t for t in self._refs_of(lods[0], 'TypeDataModule') if t > 0]
                mat = self._refs_of(req[0], 'Material') if req else []
                if req and not td and (not mat or mat[0] == 0):
                    drop.update(self._subtree(idx, children))
                    self.notes.append('emitter %s left out (no material: a KH3 helper emitter)' % self.pk.exports[idx - 1]['name'])
        return drop

    # -- the new tables --------------------------------------------------------------------------------------------
    def build(self, package_path):
        pk = self.pk
        drop = self.dropped()
        kept = [i for i in range(1, len(pk.exports) + 1) if i not in drop]
        export_map = {old: new for new, old in enumerate(kept, 1)}

        # imports: what kept exports use (classes, objects they reference); KH3 content outside the package is cleared
        used_imports = set()
        for old in kept:
            e = pk.exports[old - 1]
            used_imports.add(e['cls'])
            for t in self.props[old]:
                for r in t.refs:
                    v = struct.unpack_from('<i', pk.data, r)[0]
                    if v < 0:
                        used_imports.add(v)
        keep_imports = set()
        cleared = set()
        remapped, as_written = {}, {}
        for v in used_imports:
            if v >= 0:
                continue
            path = import_path(pk, v)
            imp = pk.imports[-v - 1]
            if imp['class_name'] not in ('Class', 'Package') and path.startswith('/Game/'):
                if path.lower() in self.remap_paths:
                    remapped[v] = path.lower()
                    as_written[path.lower()] = path
                else:
                    cleared.add(v)
                continue
            x = v
            while x < 0:
                keep_imports.add(x)
                x = pk.imports[-x - 1]['outer']
        for v in sorted(cleared):
            self.notes.append('cleared %s %s' % (pk.imports[-v - 1]['class_name'], import_path(pk, v)))
        names = list(pk.names)
        name_index = {}
        for i, n in enumerate(names):
            name_index.setdefault(n, i)

        def fname(s):
            base, num = split_name(s)
            if base not in name_index:
                name_index[base] = len(names)
                names.append(base)
            return name_index[base], num

        imports = []
        import_map = {}
        # remapped content: a fresh package import + object import per path
        for old in sorted(keep_imports, reverse=True):          # -1, -2, ... in KH3's order
            imports.append(dict(old=old))
        for new_i, imp in enumerate(imports):
            import_map[imp['old']] = -(new_i + 1)
        extra = {}
        for v in sorted(used_imports):
            if v < 0 and v not in keep_imports and v not in cleared:
                pass
        for path in sorted(set(remapped.values())):
            spec = self.remap_paths[path]
            cls_package, cls_name = spec[0], spec[1]
            target = spec[2] if len(spec) > 2 else as_written[path]
            self.notes.append('remapped %s -> %s' % (as_written[path], target))
            pkg_path, obj = target.split('.', 1)
            pidx = -(len(imports) + 1)
            imports.append(dict(new=dict(class_package='/Script/CoreUObject', class_name='Package', outer=0, name=pkg_path)))
            oidx = -(len(imports) + 1)
            imports.append(dict(new=dict(class_package=cls_package, class_name=cls_name, outer=pidx, name=obj)))
            extra[path] = oidx

        def remap(v):
            if v == 0:
                return 0
            if v > 0:
                return export_map.get(v, 0)
            if v in cleared:
                return 0
            if v in remapped:
                return extra[remapped[v]]
            if v in import_map:
                return import_map[v]
            return extra.get(import_path(pk, v).lower(), 0)

        # exports
        exports = []
        for old in kept:
            e = pk.exports[old - 1]
            data = self._export_data(old, remap)
            is_asset = self.cls[old] == 'ParticleSystem' and e['outer'] == 0
            flags = (RF_PUBLIC | RF_STANDALONE | RF_TRANSACTIONAL) if is_asset else (RF_TRANSACTIONAL | (e['flags'] & RF_PUBLIC))
            exports.append(dict(cls=remap(e['cls']), sup=0, template=0, outer=remap(e['outer']) if e['outer'] else 0,
                                name=e['name'], flags=flags, data=data, is_asset=1 if is_asset else 0))
        return self._write(package_path, names, fname, imports, exports, export_map)

    def _export_data(self, old, remap):
        pk = self.pk
        e = pk.exports[old - 1]
        start = e['offset']
        props = self.props[old]
        body = bytearray(pk.data[start:props.end])
        # every reference, in place
        for t in props:
            for r in t.refs:
                v = struct.unpack_from('<i', pk.data, r)[0]
                struct.pack_into('<i', body, r - start, remap(v))
        # arrays of objects that lose entries (modules, emitters): rebuilt without the gaps, last first
        for t in sorted(props, key=lambda x: -x.tag_start):
            if t.type == 'ArrayProperty' and t.inner == 'ObjectProperty' and t.name in ('Modules', 'Emitters', 'LODLevels'):
                vals = [struct.unpack_from('<i', pk.data, a)[0] for a, _, _ in t.elements]
                new = [remap(v) for v in vals]
                kept_vals = [v for v, o in zip(new, vals) if v != 0 or o == 0]
                if len(kept_vals) == len(new):
                    continue
                value = struct.pack('<i', len(kept_vals)) + b''.join(struct.pack('<i', v) for v in kept_vals)
                tag = bytearray(body[t.tag_start - start:t.value_start - start])
                struct.pack_into('<i', tag, t.size_at - t.tag_start, len(value))
                body[t.tag_start - start:t.value_end - start] = bytes(tag) + value
        tail = pk.data[props.end:e['offset'] + e['size']]
        # UObject's "has a GUID" flag (0) only: ParticleModuleRequired's cooked bCooked + derived data go
        return bytes(body) + tail[:4]

    # -- the file --------------------------------------------------------------------------------------------------
    def _write(self, package_path, names, fname, imports, exports, export_map):
        pk = self.pk
        asset_name = package_path.rsplit('/', 1)[-1]
        # the asset itself takes the package's name
        for ex in exports:
            if ex['is_asset']:
                ex['name'] = asset_name
        # import records
        imp_records = []
        for imp in imports:
            if 'old' in imp:
                o = pk.imports[-imp['old'] - 1]
                rec = dict(class_package=o['class_package'], class_name=o['class_name'], outer=o['outer'], name=o['name'])
                rec['outer'] = 0 if o['outer'] == 0 else next(-(j + 1) for j, x in enumerate(imports) if x.get('old') == o['outer'])
            else:
                rec = dict(imp['new'])
            imp_records.append(rec)
        # names needed by the header
        for rec in imp_records:
            for key in ('class_package', 'class_name', 'name'):
                fname(rec[key])
        for ex in exports:
            fname(ex['name'])
        fname('None')
        s = edpkg.Summary()
        s.legacy, s.legacy_ue3, s.ue4, s.licensee = -7, 864, 522, 0
        s.custom_versions = [PARTICLE_SYSTEM_CUSTOM_VERSION]
        s.folder = 'None'
        s.flags = 0
        s.localization_id = uuid.uuid4().hex.upper()
        s.text_count = s.text_offset = 0
        s.soft_count = 0
        s.guid = uuid.uuid4().bytes
        s.persistent_guid = uuid.uuid4().bytes
        s.saved_by = ((0, 0, 0, 0), '')
        s.compatible_with = ((0, 0, 0, 0), '')
        s.compression_flags = 0
        s.package_source = 0
        s.additional_packages = []
        s.world_tile_offset = 0
        s.chunk_ids = []
        s.preload_count = -1
        s.name_count = len(names)
        s.import_count = len(imp_records)
        s.export_count = len(exports)
        s.generations = [(len(exports), len(names))]
        s.thumbnail_offset = 0
        s.total_header_size = s.name_offset = s.export_offset = s.import_offset = s.depends_offset = 0
        s.soft_offset = s.searchable_offset = s.asset_registry_offset = s.preload_offset = 0
        s.bulk_data_start_offset = 0

        def nm(sv):
            i, n = fname(sv)
            return struct.pack('<ii', i, n)

        def layout():
            out = bytearray(s.bytes())
            s.name_offset = len(out)
            for n in names:
                out += edpkg.fstring_bytes(n) + struct.pack('<HH', *edpkg.name_hashes(n))
            s.import_offset = len(out)
            for rec in imp_records:
                out += nm(rec['class_package']) + nm(rec['class_name']) + struct.pack('<i', rec['outer']) + nm(rec['name']) + nm('None')
            s.export_offset = len(out)
            offsets_at = []
            for ex in exports:
                out += struct.pack('<iiii', ex['cls'], ex['sup'], ex['template'], ex['outer']) + nm(ex['name']) + struct.pack('<I', ex['flags'])
                offsets_at.append(len(out))
                out += struct.pack('<qq', len(ex['data']), 0)
                out += struct.pack('<iii', 0, 0, 0) + b'\0' * 16 + struct.pack('<I', 0)
                out += struct.pack('<ii', 1, ex['is_asset']) + struct.pack('<iiiii', -1, 0, 0, 0, 0)
            s.depends_offset = len(out)
            for ex in exports:
                deps = sorted(set(d for d in ex.get('deps', []) if d))
                out += struct.pack('<i', len(deps)) + b''.join(struct.pack('<i', d) for d in deps)
            s.soft_offset = len(out)
            s.searchable_offset = len(out)
            out += struct.pack('<i', 0)                          # searchable names: none
            s.asset_registry_offset = len(out)
            asset = [ex for ex in exports if ex['is_asset']]
            ar = bytearray()
            ar += struct.pack('<q', 0)                           # dependency data offset (filled below)
            ar += struct.pack('<i', len(asset))
            for ex in asset:
                ar += edpkg.fstring_bytes(asset_name) + edpkg.fstring_bytes('ParticleSystem') + struct.pack('<i', 0)
            dep_at = s.asset_registry_offset + len(ar)
            struct.pack_into('<q', ar, 0, dep_at)
            nimp = len(imp_records)
            words = (nimp + 31) // 32
            bits = [0] * words
            for i in range(nimp):
                bits[i // 32] |= 1 << (i % 32)
            ar += struct.pack('<i', nimp) + b''.join(struct.pack('<I', w) for w in bits) + struct.pack('<i', 0)
            out += ar
            s.total_header_size = len(out)
            s.preload_offset = len(out)
            pos = len(out)
            for ex, at in zip(exports, offsets_at):
                struct.pack_into('<q', out, at + 8, pos)
                pos += len(ex['data'])
            s.bulk_data_start_offset = pos
            return out

        # dependencies: what each export's class and properties reference, its outer
        for ex in exports:
            ex['deps'] = [ex['cls'], ex['outer']]
        head = layout()
        head = layout()                                         # second pass: the summary's own offsets settled
        body = b''.join(ex['data'] for ex in exports)
        data = bytes(head) + body + struct.pack('<I', edpkg.TAG)
        return data


def convert_file(src, dst, package_path, remap=None):
    c = Converter(open(src, 'rb').read(), open(src[:-7] + '.uexp', 'rb').read(), remap)
    data = c.build(package_path)
    with open(dst, 'wb') as f:
        f.write(data)
    return c, data


if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    pkg = sys.argv[3] if len(sys.argv) > 3 else '/Game/KH3/w_so010/Cascade/' + os.path.basename(src)[:-7]
    c, data = convert_file(src, dst, pkg)
    print(dst, len(data))
    for n in c.notes:
        print('  ', n)
