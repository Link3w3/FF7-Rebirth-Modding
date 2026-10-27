"""UE 4.26 legacy package reader (the End editor's uncooked .uasset: FPackageFileSummary, name/import/export maps) with a
tagged-property reader (FPropertyTag streams) and the native struct serializers the editor's Niagara (UnrealEngine-CE
4.26 + its SQEX stubs) writes.

    legacy.py <file.uasset>                  summary, imports, exports
    legacy.py <file.uasset> <export name>    that export's properties
"""
import struct, sys

TAG = 0x9E2A83C1


class P:
    """A tagged value: kind ('prim', 'name', 'str', 'obj', 'enum', 'struct', 'array', 'set', 'map', 'native', 'text',
    'soft', 'raw'), type (property type or struct name), value."""
    __slots__ = ('kind', 'type', 'value', 'tag')

    def __init__(self, kind, typ, value, tag=None):
        self.kind, self.type, self.value, self.tag = kind, typ, value, tag

    def __repr__(self):
        if self.kind == 'struct':
            return 'P(struct %s {%s})' % (self.type, ', '.join(self.value.keys()))
        if self.kind in ('array', 'set'):
            return 'P(%s %s x%d)' % (self.kind, self.type, len(self.value))
        return 'P(%s %s %r)' % (self.kind, self.type, self.value)

    def get(self, key, default=None):
        if self.kind != 'struct':
            raise TypeError('not a struct: %r' % self)
        x = self.value.get(key)
        return default if x is None else x

    def __getitem__(self, key):
        return self.value[key]


class Package:
    def __init__(self, data):
        self.d = data
        self.p = 0
        self._summary()
        self._names()
        self._imports()
        self._exports()

    # --- primitives
    def u8(self):
        v = self.d[self.p]; self.p += 1; return v

    def unpack(self, fmt):
        v = struct.unpack_from(fmt, self.d, self.p); self.p += struct.calcsize(fmt); return v

    def i32(self): return self.unpack('<i')[0]
    def u32(self): return self.unpack('<I')[0]
    def i64(self): return self.unpack('<q')[0]

    def fstring(self):
        n = self.i32()
        if n == 0:
            return ''
        if n < 0:
            s = self.d[self.p:self.p - 2 * n].decode('utf-16-le'); self.p += -2 * n
        else:
            s = self.d[self.p:self.p + n].decode('latin-1'); self.p += n
        return s[:-1]

    def guid(self):
        g = self.d[self.p:self.p + 16]; self.p += 16; return g

    def engine_version(self):
        major, minor, patch, cl = self.unpack('<HHHI')
        return (major, minor, patch, cl, self.fstring())

    # --- header
    def _summary(self):
        tag = self.u32()
        assert tag == TAG, 'not a package'
        self.legacy_ver = self.i32()
        if self.legacy_ver != -4:
            self.ue3_ver = self.i32()
        self.ue4_ver = self.i32()
        self.licensee_ver = self.i32()
        self.custom_versions = {}
        if self.legacy_ver <= -2:
            for _ in range(self.i32()):
                g = self.guid(); v = self.i32()
                self.custom_versions[g] = v
        self.total_header_size = self.i32()
        self.folder = self.fstring()
        self.package_flags = self.u32()
        self.name_count, self.name_offset = self.unpack('<ii')
        if not (self.package_flags & 0x80000000):     # PKG_FilterEditorOnly
            self.localization_id = self.fstring()
        self.gatherable_count, self.gatherable_offset = self.unpack('<ii')
        self.export_count, self.export_offset, self.import_count, self.import_offset, self.depends_offset = self.unpack('<5i')
        self.soft_refs_count, self.soft_refs_offset = self.unpack('<ii')
        self.searchable_names_offset = self.i32()
        self.thumbnail_offset = self.i32()
        self.package_guid = self.guid()
        if not (self.package_flags & 0x80000000):
            self.persistent_guid = self.guid()
        self.generations = [self.unpack('<ii') for _ in range(self.i32())]
        self.saved_by = self.engine_version()
        self.compatible_with = self.engine_version()
        self.compression_flags = self.u32()
        n = self.i32()
        assert n == 0, 'compressed package'
        self.package_source = self.u32()
        self.additional_to_cook = [self.fstring() for _ in range(self.i32())]
        if self.legacy_ver > -7:
            self.num_texture_allocations = self.i32()
        self.asset_registry_offset = self.i32()
        self.bulk_data_start = self.i64()
        self.world_tile_info_offset = self.i32()
        self.chunk_ids = [self.i32() for _ in range(self.i32())]
        self.preload_count, self.preload_offset = self.unpack('<ii')

    def _names(self):
        self.p = self.name_offset
        self.names = []
        for _ in range(self.name_count):
            s = self.fstring()
            self.p += 4    # non-case-preserving and case-preserving hashes
            self.names.append(s)

    def name(self):
        idx, num = self.unpack('<ii')
        s = self.names[idx]
        return s if num == 0 else '%s_%d' % (s, num - 1)

    def _imports(self):
        self.p = self.import_offset
        self.imports = []
        for _ in range(self.import_count):
            cp = self.name(); cn = self.name(); outer = self.i32(); on = self.name()
            pn = self.name() if not (self.package_flags & 0x80000000) else None
            self.imports.append({'class_package': cp, 'class': cn, 'outer': outer, 'name': on, 'package_name': pn})

    def _exports(self):
        self.p = self.export_offset
        self.exports = []
        for _ in range(self.export_count):
            cls, sup, tmpl, outer = self.unpack('<4i')
            on = self.name()
            flags = self.u32()
            size, off = self.unpack('<qq')
            forced, nfc, nfs = self.unpack('<3i')
            pguid = self.guid(); pflags = self.u32()
            nale, is_asset = self.unpack('<ii')
            deps = self.unpack('<5i')
            self.exports.append({'class': cls, 'super': sup, 'template': tmpl, 'outer': outer, 'name': on, 'flags': flags,
                                 'size': size, 'offset': off, 'is_asset': is_asset, 'deps': deps})

    # --- object references
    def ref(self, idx):
        """a package index as a path-ish string"""
        if idx == 0:
            return None
        if idx < 0:
            imp = self.imports[-idx - 1]
            o = self.ref(imp['outer'])
            return (o + ('.' if o and o.count('/') and '.' not in o else ':' if o else '') if o else '') + imp['name']
        e = self.exports[idx - 1]
        o = self.ref(e['outer'])
        return (o + '.' if o else '') + e['name']

    def class_name(self, i):
        c = self.exports[i]['class']
        if c < 0:
            return self.imports[-c - 1]['name']
        return self.exports[c - 1]['name']

    def export_name(self, i):
        return self.exports[i]['name']

    def outer_name(self, i):
        o = self.exports[i]['outer']
        return self.exports[o - 1]['name'] if o > 0 else None

    def export_data(self, i):
        e = self.exports[i]
        return self.d[e['offset']:e['offset'] + e['size']]

    def find(self, name, cls=None):
        for i, e in enumerate(self.exports):
            if e['name'] == name and (cls is None or self.class_name(i) == cls):
                return i
        return None


# ---------------------------------------------------------------------------------------------------------------
# tagged properties

BINARY = {   # structs written natively (immutable / custom binary) in tagged streams
    'Vector': '<3f', 'Vector2D': '<2f', 'Vector4': '<4f', 'IntPoint': '<2i', 'IntVector': '<3i', 'Color': '<4B',
    'LinearColor': '<4f', 'Quat': '<4f', 'Rotator': '<3f', 'Plane': '<4f', 'Matrix': '<16f', 'Box': '<6fB',
    'Box2D': '<4fB', 'BoxSphereBounds': '<7f', 'Sphere': '<4f', 'Guid': '<4I', 'TwoVectors': '<6f',
    'FrameNumber': '<i', 'DateTime': '<q', 'Timespan': '<q', 'RichCurveKey': '<3B6f', 'SimpleCurveKey': '<2f',
    'IntVector4': '<4i', 'FloatInterval': '<2f', 'Int32Interval': '<2i', 'PackedNormal': '<4B',
}


class Tagged:
    def __init__(self, pkg, data, pos=0, end=None):
        self.pkg = pkg
        self.d = data
        self.p = pos
        self.end = len(data) if end is None else end
        self.natives = dict(NATIVES)
        self.lenient = True
        self.skipped = []

    def unpack(self, fmt):
        v = struct.unpack_from(fmt, self.d, self.p); self.p += struct.calcsize(fmt); return v

    def u8(self): v = self.d[self.p]; self.p += 1; return v
    def i32(self): return self.unpack('<i')[0]
    def u32(self): return self.unpack('<I')[0]

    def name(self):
        idx, num = self.unpack('<ii')
        s = self.pkg.names[idx]
        return s if num == 0 else '%s_%d' % (s, num - 1)

    def fstring(self):
        n = self.i32()
        if n == 0:
            return ''
        if n < 0:
            s = self.d[self.p:self.p - 2 * n].decode('utf-16-le'); self.p += -2 * n
        else:
            s = self.d[self.p:self.p + n].decode('latin-1'); self.p += n
        return s[:-1]

    def raw(self, n):
        b = self.d[self.p:self.p + n]; self.p += n; return b

    # --- tags
    def tag(self):
        name = self.name()
        if name == 'None':
            return None
        t = {'name': name, 'type': self.name()}
        t['size'], t['index'] = self.unpack('<ii')
        ty = t['type']
        if ty == 'StructProperty':
            t['struct'] = self.name(); t['guid'] = self.raw(16)
        elif ty == 'BoolProperty':
            t['bool'] = self.u8()
        elif ty in ('ByteProperty', 'EnumProperty'):
            t['enum'] = self.name()
        elif ty in ('ArrayProperty', 'SetProperty'):
            t['inner'] = self.name()
        elif ty == 'MapProperty':
            t['inner'] = self.name(); t['value'] = self.name()
        if self.u8():
            t['prop_guid'] = self.raw(16)
        return t

    def props(self, struct_name=None):
        """a tagged property stream up to None -> P('struct')"""
        out = {}
        while True:
            t = self.tag()
            if t is None:
                break
            start = self.p
            key = t['name'] if t['index'] == 0 else '%s[%d]' % (t['name'], t['index'])
            try:
                v = self.value(t, t['type'], t['size'], top=True)
                if self.p != start + t['size'] and t['type'] != 'BoolProperty':
                    raise ValueError('read %d of %d bytes' % (self.p - start, t['size']))
            except Exception as ex:
                if not self.lenient or t['type'] == 'BoolProperty':
                    raise ValueError('%s.%s (%s, %d bytes at %d): %s' % (struct_name, key, t['type'], t['size'], start, ex))
                # a value this reader cannot decode (editor-only maps with struct keys, ...): keep its bytes
                self.p = start + t['size']
                v = P('raw', t['type'], self.d[start:self.p])
                self.skipped.append('%s.%s' % (struct_name, key))
            v.tag = t
            out[key] = v
        return P('struct', struct_name, out)

    def value(self, t, ty, size, top=False, inner_struct=None):
        if ty == 'BoolProperty':
            return P('prim', ty, bool(t['bool']) if top else bool(self.u8()))
        if ty == 'ByteProperty':
            enum = t.get('enum') if top else None
            if enum and enum != 'None' and (size == 8 or not top):
                if top:
                    return P('enum', enum, self.name())
            if top and size == 8:
                return P('enum', enum, self.name())
            return P('prim', ty, self.u8())
        if ty == 'EnumProperty':
            return P('enum', t.get('enum') if top else None, self.name())
        if ty == 'Int8Property':
            return P('prim', ty, self.unpack('<b')[0])
        if ty == 'Int16Property':
            return P('prim', ty, self.unpack('<h')[0])
        if ty == 'UInt16Property':
            return P('prim', ty, self.unpack('<H')[0])
        if ty == 'IntProperty':
            return P('prim', ty, self.i32())
        if ty == 'UInt32Property':
            return P('prim', ty, self.u32())
        if ty == 'Int64Property':
            return P('prim', ty, self.unpack('<q')[0])
        if ty == 'UInt64Property':
            return P('prim', ty, self.unpack('<Q')[0])
        if ty == 'FloatProperty':
            return P('prim', ty, self.unpack('<f')[0])
        if ty == 'DoubleProperty':
            return P('prim', ty, self.unpack('<d')[0])
        if ty == 'NameProperty':
            return P('name', ty, self.name())
        if ty == 'StrProperty':
            return P('str', ty, self.fstring())
        if ty in ('ObjectProperty', 'ClassProperty', 'WeakObjectProperty', 'InterfaceProperty'):
            return P('obj', ty, self.i32())
        if ty in ('SoftObjectProperty', 'SoftClassProperty'):
            return P('soft', ty, (self.name(), self.fstring()))
        if ty == 'TextProperty':
            return P('text', ty, self.text())
        if ty == 'StructProperty':
            sname = t['struct'] if top else inner_struct
            return self.struct(sname, size if top else None)
        if ty in ('ArrayProperty', 'SetProperty'):
            inner = t['inner']
            if ty == 'SetProperty':
                removed = self.i32()
                assert removed == 0
            n = self.i32()
            items = []
            if inner == 'StructProperty':
                it = self.tag()          # the inner tag: element struct name
                sname = it['struct']
                for _ in range(n):
                    items.append(self.struct(sname, None))
                return P('array' if ty == 'ArrayProperty' else 'set', sname, items)
            if inner == 'BoolProperty':
                return P('array', inner, [bool(self.u8()) for _ in range(n)])
            if inner == 'ByteProperty' and n and size - 4 == n:
                return P('array', inner, list(self.raw(n)))
            for _ in range(n):
                items.append(self.value({'enum': None}, inner, None))
            return P('array' if ty == 'ArrayProperty' else 'set', inner, items)
        if ty == 'MapProperty':
            removed = self.i32()
            assert removed == 0, 'map with removed keys'
            n = self.i32()
            kt, vt = t['inner'], t['value']
            items = []
            for _ in range(n):
                k = self.value({}, kt, None, inner_struct=None) if kt != 'StructProperty' else P('raw', 'struct-key', None)
                v = self.value({}, vt, None) if vt != 'StructProperty' else self.struct(None, None)
                items.append((k, v))
            return P('map', '%s,%s' % (kt, vt), items)
        raise ValueError('cannot read %s' % ty)

    def struct(self, sname, size):
        nat = self.natives.get(sname)
        if nat is not None:
            return P('native', sname, nat(self, sname))
        if sname in BINARY:
            return P('native', sname, list(self.unpack(BINARY[sname])))
        return self.props(sname)

    def text(self):
        flags = self.u32()
        hist = self.unpack('<b')[0]
        if hist == -1:
            has = self.i32()
            return ('none', self.fstring() if has else None)
        if hist == 0:
            return ('base', self.fstring(), self.fstring(), self.fstring())
        raise ValueError('FText history %d' % hist)


# --- natives (UnrealEngine-CE 4.26 Niagara, saving side)

def _type_def(r, s):
    return r.props('NiagaraTypeDefinition')


def _var_base(r, s):
    return {'Name': r.name(), 'TypeDef': r.props('NiagaraTypeDefinition')}


def _var(r, s):
    """name, type definition (tagged), then (the End editor's SQEX stub as it saves) i32, i32, VarData, i32"""
    out = _var_base(r, s)
    out['sqex'] = r.unpack('<2i')
    n = r.i32()
    out['data'] = r.raw(n)
    out['sqex2'] = r.i32()
    return out


def _var_offset(r, s):
    out = _var_base(r, s)
    out['Offset'] = r.i32()
    return out


def _soft_path(r, s):
    return (r.name(), r.fstring())


def _ext_fn(r, s):
    return r.props('VMExternalFunctionBindingInfo')


def _per_platform(fmt):
    def f(r, s):
        cooked = r.u32()
        v = r.unpack(fmt)[0]
        per = []
        if not cooked:
            per = [(r.name(), r.unpack(fmt)[0]) for _ in range(r.i32())]
        return {'cooked': cooked, 'value': v, 'per_platform': per}
    return f


def _rich_curve_key(r, s):
    return list(r.unpack('<3B6f'))


NATIVES = {
    'NiagaraTypeDefinition': _type_def, 'NiagaraVariableBase': _var_base, 'NiagaraVariable': _var,
    'NiagaraVariableWithOffset': _var_offset, 'SoftObjectPath': _soft_path, 'SoftClassPath': _soft_path,
    'VMExternalFunctionBindingInfo': _ext_fn, 'PerPlatformFloat': _per_platform('<f'), 'PerPlatformInt': _per_platform('<i'),
    'PerPlatformBool': _per_platform('<I'), 'RichCurveKey': _rich_curve_key,
}


def read_export(pkg, i):
    """(class, P struct of the tagged properties, tail bytes)"""
    data = pkg.export_data(i)
    r = Tagged(pkg, data)
    v = r.props(pkg.class_name(i))
    return pkg.class_name(i), v, data[r.p:]


def dump(v, indent='', out=None, depth=0, maxdepth=8, limit=12):
    out = out or sys.stdout
    w = out.write
    if v.kind == 'struct':
        w('{%s}\n' % v.type)
        for k, x in v.value.items():
            w('%s  %s: ' % (indent, k))
            if depth >= maxdepth:
                w('...\n'); continue
            dump(x, indent + '  ', out, depth + 1, maxdepth, limit)
    elif v.kind in ('array', 'set'):
        w('[%s x%d]\n' % (v.type, len(v.value)))
        for j, x in enumerate(v.value[:limit]):
            w('%s  [%d] ' % (indent, j))
            dump(x, indent + '  ', out, depth + 1, maxdepth, limit)
        if len(v.value) > limit:
            w('%s  ...\n' % indent)
    elif v.kind == 'native' and isinstance(v.value, dict):
        w('<%s>\n' % v.type)
        for k, x in v.value.items():
            w('%s  %s: ' % (indent, k))
            if isinstance(x, P):
                dump(x, indent + '  ', out, depth + 1, maxdepth, limit)
            elif isinstance(x, (bytes, bytearray)):
                w('%s\n' % (x.hex() if len(x) <= 48 else x[:48].hex() + '...(%d)' % len(x)))
            else:
                w('%r\n' % (x,))
    elif v.kind == 'map':
        w('{map x%d}\n' % len(v.value))
        for a, b in v.value[:limit]:
            w('%s  ' % indent); dump(a, indent + '  ', out, depth + 1, maxdepth, limit)
            w('%s   -> ' % indent); dump(b, indent + '    ', out, depth + 1, maxdepth, limit)
    else:
        val = v.value
        if isinstance(val, float):
            val = round(val, 6)
        w('%r\n' % (val,))


if __name__ == '__main__':
    pkg = Package(open(sys.argv[1], 'rb').read())
    if len(sys.argv) == 2:
        print('ue4 %d licensee %d flags %08x names %d imports %d exports %d saved by %s' % (
            pkg.ue4_ver, pkg.licensee_ver, pkg.package_flags, len(pkg.names), len(pkg.imports), len(pkg.exports), pkg.saved_by))
        for k, imp in enumerate(pkg.imports):
            print('  import %3d %-28s %s (outer %d)' % (-k - 1, imp['class'], imp['name'], imp['outer']))
        for k, e in enumerate(pkg.exports):
            print('  export %3d %-44s %-40s outer %-4d size %d' % (k + 1, pkg.class_name(k), e['name'], e['outer'], e['size']))
    else:
        for nm in sys.argv[2:]:
            i = pkg.find(nm)
            cls, v, tail = read_export(pkg, i)
            print('==', nm, cls, 'tail', len(tail))
            dump(v)
