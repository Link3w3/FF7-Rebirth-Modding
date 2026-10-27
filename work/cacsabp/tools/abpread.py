"""Reads a cooked (zen, UE 4.26) AnimBlueprint: its generated class's own properties (the anim nodes and variables:
UStruct::SerializeProperties after the class's unversioned properties), its UClass data, and its class default object
(the nodes' settings) read with a schema made from those properties.

    abpread.py <AnimBlueprint .uasset> [--nodes] [--machines] [--handlers] [--cdo NAME ...] [--json out.json]
"""
import json, struct, sys
sys.path[:0] = ['/work/fx1018/tools', '/work/iostore', '/work/cs', '/work/weap1012/tools',
                '/work/swap1012/tools']
import fxlib, uprops
sys.path.insert(0, '/work/cacsabp/tools')
import tagged
from usmap import Prop, PropType, Struct
from zen import Zen
import scriptobjs

NULL = 0xFFFFFFFFFFFFFFFF
PATHS, _ = scriptobjs.load()


class R:
    def __init__(self, names, d, p):
        self.names, self.d, self.p = names, d, p

    def take(self, fmt):
        v = struct.unpack_from(fmt, self.d, self.p)
        self.p += struct.calcsize(fmt)
        return v

    def i32(self): return self.take('<i')[0]
    def u32(self): return self.take('<I')[0]
    def u64(self): return self.take('<Q')[0]
    def u16(self): return self.take('<H')[0]
    def u8(self): return self.take('<B')[0]

    def name(self):
        idx, num = self.take('<II')
        s = self.names[idx & 0x3fffffff]
        return s if num == 0 else '%s_%d' % (s, num - 1)


def index_name(z, v):
    """An FPackageIndex: an export's name, an import's script path (or its hash), None."""
    if v == 0:
        return None
    if v > 0:
        return ('export', v - 1, z.exports[v - 1]['name'])
    h = z.imports[-v - 1]
    return ('import', -v - 1, PATHS.get(h) or '%016x' % h)


def short(path):
    return path.rsplit('.', 1)[-1].rsplit(':', 1)[-1] if isinstance(path, str) else path


def read_field(r, z, tname=None):
    """One FField (FProperty) as a dict: type, name, flags, array dim, size, property flags and the type's extras."""
    if tname is None:
        tname = r.name()
    if tname == 'None':
        return None
    f = dict(type=tname, name=r.name(), flags=r.u32())
    f['array_dim'] = r.i32()
    f['element_size'] = r.i32()
    f['property_flags'] = r.u64()
    f['rep_index'] = r.u16()
    f['rep_notify'] = r.name()
    f['rep_condition'] = r.u8()
    t = tname
    if t == 'StructProperty':
        f['struct'] = index_name(z, r.i32())
    elif t in ('ObjectProperty', 'WeakObjectProperty', 'LazyObjectProperty', 'SoftObjectProperty', 'ObjectPtrProperty'):
        f['class'] = index_name(z, r.i32())
    elif t in ('ClassProperty', 'SoftClassProperty'):
        f['class'] = index_name(z, r.i32())
        f['meta_class'] = index_name(z, r.i32())
    elif t == 'InterfaceProperty':
        f['class'] = index_name(z, r.i32())
    elif t in ('ArrayProperty', 'SetProperty'):
        f['inner'] = read_field(r, z)
    elif t == 'MapProperty':
        f['key'] = read_field(r, z)
        f['value'] = read_field(r, z)
    elif t == 'ByteProperty':
        f['enum'] = index_name(z, r.i32())
    elif t == 'EnumProperty':
        f['enum'] = index_name(z, r.i32())
        f['underlying'] = read_field(r, z)
    elif t == 'BoolProperty':
        f['field_size'], f['byte_offset'], f['byte_mask'], f['field_mask'], f['bool_size'], f['native_bool'] = r.take('<6B')
    elif t in ('DelegateProperty', 'MulticastDelegateProperty', 'MulticastInlineDelegateProperty', 'MulticastSparseDelegateProperty'):
        f['signature'] = index_name(z, r.i32())
    elif t == 'FieldPathProperty':
        f['field_class'] = r.name()
    elif t in ('IntProperty', 'FloatProperty', 'DoubleProperty', 'NameProperty', 'StrProperty', 'TextProperty', 'Int8Property',
               'Int16Property', 'Int64Property', 'UInt16Property', 'UInt32Property', 'UInt64Property'):
        pass
    else:
        raise ValueError('FField type %s not known (at %d)' % (t, r.p))
    return f


def read_class(z, i):
    """The generated class export: its properties (V; unversioned, or tagged in a versioned package), then its UStruct
    and UClass data."""
    u = fxlib.usmap()
    if tagged.is_versioned(z):
        cls, v, end, data = tagged.read_export(u, z, i, PATHS)
    else:
        cls, v, end, data = uprops.read_export(u, z, i, PATHS)
    r = R(z.names, data, end)
    out = dict(cls=cls, props=v)
    out['has_guid'] = r.i32()   # (UObject::Serialize: FLazyObjectPtr::PossiblySerializeObjectGuid's bool)
    if out['has_guid']:
        r.p += 16
    out['super'] = index_name(z, r.i32())
    out['children'] = [index_name(z, r.i32()) for _ in range(r.i32())]
    out['properties'] = [read_field(r, z) for _ in range(r.i32())]
    out['script_size'], out['script_storage'] = r.i32(), r.i32()
    out['script_at'] = r.p
    r.p += out['script_storage']
    funcs = []
    for _ in range(r.i32()):
        funcs.append((r.name(), index_name(z, r.i32())))
    out['func_map'] = funcs
    out['class_flags'] = r.u32()
    out['within'] = index_name(z, r.i32())
    out['config_name'] = r.name()
    out['interfaces'] = []
    for _ in range(r.i32()):
        out['interfaces'].append((index_name(z, r.i32()), r.i32(), r.i32()))
    out['deprecated_force_script_order'] = r.i32()
    out['dummy'] = r.name()
    out['cooked'] = r.i32()
    out['cdo'] = index_name(z, r.i32())
    out['end'], out['size'] = r.p, len(data)
    return out


def ptype_of(f):
    t = f['type']
    if t == 'StructProperty':
        return PropType(t, struct=short(f['struct'][2]))
    if t == 'EnumProperty':
        return PropType(t, inner=ptype_of(f['underlying']), enum=short(f['enum'][2]) if f['enum'] else None)
    if t in ('ArrayProperty', 'SetProperty'):
        return PropType(t, inner=ptype_of(f['inner']))
    if t == 'MapProperty':
        return PropType(t, inner=ptype_of(f['key']), value=ptype_of(f['value']))
    if t == 'ByteProperty':
        return PropType(t, enum=short(f['enum'][2]) if f.get('enum') else None)
    if t in ('ClassProperty',):
        return PropType('ObjectProperty')
    if t in ('SoftClassProperty',):
        return PropType('SoftObjectProperty')
    if t in ('MulticastInlineDelegateProperty', 'MulticastSparseDelegateProperty'):
        return PropType('MulticastDelegateProperty')
    return PropType(t)


def register_class(info, name):
    """The class's own properties as a usmap struct (its super: the native parent's), so its CDO reads."""
    u = fxlib.usmap()
    props, idx = [], 0
    for f in info['properties']:
        props.append(Prop(idx, f['array_dim'], f['name'], ptype_of(f)))
        idx += f['array_dim']
    sup = info['super'][2] if info['super'] else None
    u.structs[name] = Struct(name, short(sup) if sup else None, idx, props)
    return u.structs[name]


def load(path):
    d = open(path, 'rb').read()
    z = Zen(d)
    ci = [k for k, e in enumerate(z.exports) if PATHS.get(e['cls'], '').endswith('AnimBlueprintGeneratedClass')]
    assert len(ci) == 1, ci
    info = read_class(z, ci[0])
    cname = z.exports[ci[0]]['name']
    register_class(info, cname)
    cdo = [k for k, e in enumerate(z.exports) if e['name'] == 'Default__' + cname]
    assert len(cdo) == 1
    u = fxlib.usmap()
    data = z.export_bytes(cdo[0])
    rr = (tagged.TaggedReader if tagged.is_versioned(z) else uprops.Reader)(u, z.names, data, 0, len(data))
    cdo_v = rr.props(cname)
    return dict(z=z, d=d, cls_index=ci[0], cls_name=cname, info=info, cdo=cdo_v, cdo_end=rr.p, cdo_size=len(data))


def plain(v):
    if v is None:
        return None
    if isinstance(v, uprops.V):
        if v.kind == 'struct':
            return {k: plain(x) for k, x in v.value.items()}
        if v.kind in ('array', 'set'):
            return [plain(x) for x in v.value]
        if v.kind == 'map':
            return [[plain(a), plain(b)] for a, b in v.value]
        if v.kind == 'native':
            return {k: plain(x) for k, x in v.value.items()} if isinstance(v.value, dict) else repr(v.value)
        if v.kind == 'enum' and isinstance(v.value, str):
            return v.value.split('::')[-1]          # (a versioned package's enum: by its full name)
        return v.value
    return v


if __name__ == '__main__':
    a = load(sys.argv[1])
    info = a['info']
    print('class %s: super %s, %d children, %d properties, script %d (storage %d), class data %d of %d bytes; CDO %d of %d bytes' % (
        a['cls_name'], info['super'], len(info['children']), len(info['properties']), info['script_size'], info['script_storage'],
        info['end'], info['size'], a['cdo_end'], a['cdo_size']))
    if '--nodes' in sys.argv:
        for f in info['properties']:
            print('  %-60s %s %s' % (f['name'], f['type'], short(f['struct'][2]) if f.get('struct') else (short(f['class'][2]) if f.get('class') else '')))
    if '--json' in sys.argv:
        out = sys.argv[sys.argv.index('--json') + 1]
        json.dump(dict(cls=a['cls_name'], props=plain(info['props']), properties=info['properties'], cdo=plain(a['cdo'])), open(out, 'w'), indent=1, default=str)
        print('wrote', out)
