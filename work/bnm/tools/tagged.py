"""Reader for UE 4.26 tagged (versioned) property data, as in the game's legacy cooked Bonamik packages."""
import struct

NATIVE = {'Vector': '<3f', 'Quat': '<4f', 'Rotator': '<3f', 'Vector2D': '<2f', 'LinearColor': '<4f', 'Color': '<4B',
          'Guid': '<16s', 'IntPoint': '<2i', 'Vector4': '<4f'}

class Reader:
    def __init__(self, data, names, pos=0):
        self.d = data; self.p = pos; self.names = names
    def take(self, n):
        v = self.d[self.p:self.p + n]
        if len(v) != n: raise EOFError('read past end at %d' % self.p)
        self.p += n; return v
    def unpack(self, fmt):
        v = struct.unpack_from(fmt, self.d, self.p); self.p += struct.calcsize(fmt)
        return v[0] if len(v) == 1 else v
    def fstring(self):
        n = self.unpack('<i')
        if n == 0: return ''
        if n < 0: return self.take(-n * 2).decode('utf-16-le').rstrip('\0')
        return self.take(n).decode('latin-1').rstrip('\0')
    def fname(self):
        i = self.unpack('<i'); num = self.unpack('<i')
        s = self.names[i] if 0 <= i < len(self.names) else '?%d' % i
        return s if num == 0 else '%s_%d' % (s, num - 1)

def read_tag(r):
    tag = {'name': r.fname()}
    if tag['name'] == 'None': return tag
    tag['type'] = r.fname(); tag['size'] = r.unpack('<i'); tag['index'] = r.unpack('<i')
    t = tag['type']
    if t == 'StructProperty': tag['struct'] = r.fname(); tag['guid'] = r.take(16)
    elif t == 'BoolProperty': tag['bool'] = r.unpack('<B')
    elif t in ('ByteProperty', 'EnumProperty'): tag['enum'] = r.fname()
    elif t in ('ArrayProperty', 'SetProperty'): tag['inner'] = r.fname()
    elif t == 'MapProperty': tag['inner'] = r.fname(); tag['value'] = r.fname()
    if r.unpack('<B'): tag['propguid'] = r.take(16)
    return tag

def read_scalar(r, t, tag=None, size=None):
    if t == 'IntProperty': return r.unpack('<i')
    if t == 'UInt32Property': return r.unpack('<I')
    if t == 'Int64Property': return r.unpack('<q')
    if t == 'UInt64Property': return r.unpack('<Q')
    if t == 'Int16Property': return r.unpack('<h')
    if t == 'UInt16Property': return r.unpack('<H')
    if t == 'Int8Property': return r.unpack('<b')
    if t == 'FloatProperty': return r.unpack('<f')
    if t == 'DoubleProperty': return r.unpack('<d')
    if t == 'StrProperty': return r.fstring()
    if t == 'NameProperty': return r.fname()
    if t in ('ObjectProperty', 'ClassProperty', 'WeakObjectProperty', 'InterfaceProperty'): return ('obj', r.unpack('<i'))
    if t == 'SoftObjectProperty': return ('soft', r.fname(), r.fstring())
    if t == 'ByteProperty':
        if tag is not None and tag.get('enum', 'None') != 'None': return r.fname()   # enum byte by name
        if size == 8: return r.fname()
        return r.unpack('<B')
    if t == 'EnumProperty': return r.fname()
    if t == 'BoolProperty': return bool(r.unpack('<B'))
    raise KeyError('scalar type ' + t)

def read_struct_value(r, struct_name, size=None):
    if struct_name in NATIVE:
        v = r.unpack(NATIVE[struct_name]); return list(v) if isinstance(v, tuple) else v
    return read_props(r)

def read_props(r):
    out = {}
    order = []
    while True:
        tag = read_tag(r)
        if tag['name'] == 'None': break
        start = r.p
        t = tag['type']
        if t == 'BoolProperty':
            val = bool(tag['bool'])
        elif t == 'StructProperty':
            val = read_struct_value(r, tag['struct'], tag['size'])
        elif t == 'ArrayProperty':
            n = r.unpack('<i'); inner = tag['inner']
            if inner == 'StructProperty':
                itag = read_tag(r)
                val = [read_struct_value(r, itag['struct']) for _ in range(n)]
            elif inner == 'BoolProperty':
                val = [bool(r.unpack('<B')) for _ in range(n)]
            elif inner == 'ByteProperty':
                per = (tag['size'] - 4) // n if n else 1
                val = [read_scalar(r, inner, None, per) for _ in range(n)]
            else:
                val = [read_scalar(r, inner) for _ in range(n)]
        elif t == 'MapProperty' or t == 'SetProperty':
            val = ('raw', r.take(tag['size']))
        else:
            val = read_scalar(r, t, tag, tag['size'])
        if r.p - start != tag['size']:
            raise ValueError('%s (%s) size mismatch: read %d, tag says %d at %d' % (tag['name'], t, r.p - start, tag['size'], start))
        key = tag['name'] if tag['index'] == 0 and tag['name'] not in out else '%s[%d]' % (tag['name'], tag['index'])
        out[key] = val; order.append(key)
    out['__order__'] = order
    return out
