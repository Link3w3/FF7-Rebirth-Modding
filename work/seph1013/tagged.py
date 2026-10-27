"""Tagged-property reader for FF7 Rebirth zen packages (UE 4.26 FPropertyTag)."""
import struct, sys
sys.path.insert(0, '/work/cs')
from zen import Zen

class Reader:
    def __init__(self, z, data):
        self.z, self.d, self.p = z, data, 0
    def u8(self): v = self.d[self.p]; self.p += 1; return v
    def i32(self): v = struct.unpack_from('<i', self.d, self.p)[0]; self.p += 4; return v
    def u32(self): v = struct.unpack_from('<I', self.d, self.p)[0]; self.p += 4; return v
    def f32(self): v = struct.unpack_from('<f', self.d, self.p)[0]; self.p += 4; return v
    def name(self):
        i, n = struct.unpack_from('<II', self.d, self.p); self.p += 8
        s = self.z.names[i] if i < len(self.z.names) else '?%d' % i
        return s if n == 0 else '%s_%d' % (s, n - 1)
    def fstring(self):
        n = self.i32()
        if n == 0: return ''
        if n > 0: s = self.d[self.p:self.p + n - 1].decode('latin-1'); self.p += n; return s
        n = -n; s = self.d[self.p:self.p + 2 * n - 2].decode('utf-16-le'); self.p += 2 * n; return s

def read_tag(r):
    name = r.name()
    if name == 'None': return None
    t = dict(name=name, type=r.name(), size=r.i32(), index=r.i32())
    ty = t['type']
    if ty == 'StructProperty': t['struct'] = r.name(); r.p += 16
    elif ty == 'BoolProperty': t['bool'] = r.u8()
    elif ty in ('ByteProperty', 'EnumProperty'): t['enum'] = r.name()
    elif ty in ('ArrayProperty', 'SetProperty'): t['inner'] = r.name()
    elif ty == 'MapProperty': t['inner'] = r.name(); t['value_type'] = r.name()
    if r.u8(): r.p += 16
    return t

NATIVE_STRUCTS = {'Vector': 12, 'Rotator': 12, 'Quat': 16, 'Guid': 16, 'LinearColor': 16, 'Color': 4, 'Vector2D': 8, 'IntPoint': 8}

def read_value(r, t, ty=None, struct_name=None, size=None):
    ty = ty or t['type']
    if ty == 'FloatProperty': return r.f32()
    if ty == 'IntProperty': return r.i32()
    if ty == 'UInt32Property': return r.u32()
    if ty == 'BoolProperty': return t.get('bool') if t else r.u8()
    if ty in ('NameProperty',): return r.name()
    if ty in ('EnumProperty',): return r.name()
    if ty == 'ByteProperty':
        if t and t.get('enum') not in (None, 'None'): return r.name()
        return r.u8()
    if ty == 'StrProperty': return r.fstring()
    if ty in ('ObjectProperty', 'ClassProperty', 'WeakObjectProperty'): return ('obj', r.i32())
    if ty in ('SoftObjectProperty', 'SoftClassProperty'): return ('soft', r.name(), r.fstring())
    if ty == 'StructProperty':
        sn = struct_name or t['struct']
        if sn in NATIVE_STRUCTS:
            v = r.d[r.p:r.p + NATIVE_STRUCTS[sn]]; r.p += NATIVE_STRUCTS[sn]; return (sn, v)
        if sn == 'SoftObjectPath': return ('soft', r.name(), r.fstring())
        return read_props(r)
    if ty == 'ArrayProperty':
        n = r.i32(); inner = t['inner']
        if inner == 'StructProperty':
            it = read_tag(r)  # inner tag describing the struct type
            return [read_value(r, it, 'StructProperty', it['struct']) for _ in range(n)]
        return [read_value(r, {'type': inner}, inner) for _ in range(n)]
    # unknown: skip
    if size is None and t: size = t['size']
    r.p += size or 0
    return ('skipped', ty)

def read_props(r):
    out = {}
    while True:
        t = read_tag(r)
        if t is None: break
        start = r.p
        try:
            v = read_value(r, t)
        except Exception as ex:
            v = ('error', str(ex))
        r.p = start + t['size']
        key = t['name'] if t['index'] == 0 else '%s[%d]' % (t['name'], t['index'])
        out[key] = v
    return out

def export_props(z, i):
    r = Reader(z, z.export_data(i))
    return read_props(r)

def export_layout(z):
    """Positions of export data in a zen package, in export bundle order."""
    size = z.graph_off - z.eb_off
    n = len(z.exports)
    bundles = (size - 16 * n) // 8
    entries_off = z.eb_off + 8 * bundles
    pos = z.header_end
    out = {}
    for k in range(2 * n):
        idx, cmd = struct.unpack_from('<II', z.d, entries_off + 8 * k)
        if cmd == 1:
            out[idx] = pos
            pos += z.exports[idx]['serial_size']
    return out

def export_bytes(z, i, layout=None):
    layout = layout or export_layout(z)
    p = layout[i]
    return z.d[p:p + z.exports[i]['serial_size']]
