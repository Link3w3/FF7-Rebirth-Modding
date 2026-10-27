"""Tagged (versioned) property streams written by a memory archive (FNames as strings), as in the cut events' payloads
(FMovieSceneEndEventParameters: magic A1B2C3D4, size, then the struct's tagged properties)."""
import struct


class T:
    def __init__(self, d, p=0):
        self.d = d
        self.p = p

    def u8(self):
        v = self.d[self.p]
        self.p += 1
        return v

    def i32(self):
        v = struct.unpack_from('<i', self.d, self.p)[0]
        self.p += 4
        return v

    def f32(self):
        v = struct.unpack_from('<f', self.d, self.p)[0]
        self.p += 4
        return v

    def fstr(self):
        n = self.i32()
        if n == 0:
            return ''
        if n < 0:
            s = self.d[self.p:self.p - 2 * n].decode('utf-16-le')
            self.p -= 2 * n
        else:
            s = self.d[self.p:self.p + n].decode('latin-1')
            self.p += n
        return s.rstrip('\0')


def short(name):
    """'VoiceName_35_AE6F64...' -> 'VoiceName' (a user struct's property names carry an index and a GUID)."""
    parts = name.split('_')
    if len(parts) >= 3 and len(parts[-1]) == 32 and parts[-2].isdigit():
        return '_'.join(parts[:-2])
    return name


def read_value(r, typ, size, extra, end):
    if typ == 'IntProperty':
        return r.i32()
    if typ == 'FloatProperty':
        return r.f32()
    if typ == 'BoolProperty':
        return extra
    if typ in ('NameProperty', 'StrProperty'):
        return r.fstr()
    if typ == 'ByteProperty':
        if extra and extra != 'None':
            return r.fstr()
        return r.u8()
    if typ == 'EnumProperty':
        return r.fstr()
    if typ == 'ObjectProperty' or typ == 'SoftObjectProperty':
        if typ == 'SoftObjectProperty':
            return (r.fstr(), r.fstr())
        return r.i32()
    if typ == 'TextProperty':
        raw = r.d[r.p:r.p + size]
        r.p += size
        return ('text', raw.hex())
    if typ == 'StructProperty':
        sname = extra
        if sname in ('Vector', 'Rotator'):
            v = struct.unpack_from('<3f', r.d, r.p)
            r.p += 12
            return list(v)
        if sname in ('LinearColor', 'Quat'):
            v = struct.unpack_from('<4f', r.d, r.p)
            r.p += 16
            return list(v)
        if sname == 'Vector2D':
            v = struct.unpack_from('<2f', r.d, r.p)
            r.p += 8
            return list(v)
        if sname == 'Guid':
            v = r.d[r.p:r.p + 16].hex()
            r.p += 16
            return v
        if sname in ('SoftObjectPath', 'SoftClassPath'):
            return (r.fstr(), r.fstr())
        return props(r, r.p + size)
    if typ == 'ArrayProperty':
        n = r.i32()
        inner = extra
        if inner == 'StructProperty':
            # inner tag then n structs
            tag = read_tag(r)
            return [props(r, end) if tag['extra'] not in ('Vector', 'Rotator', 'LinearColor', 'Guid') else read_value(r, 'StructProperty', 0, tag['extra'], end)
                    for _ in range(n)]
        return [read_value(r, inner, 0, None, end) for _ in range(n)]
    raw = r.d[r.p:r.p + size]
    r.p += size
    return ('raw', typ, raw.hex())


def read_tag(r):
    name = r.fstr()
    if name == 'None':
        return None
    typ = r.fstr()
    size, aidx = r.i32(), r.i32()
    extra = None
    if typ == 'StructProperty':
        extra = r.fstr()
        r.p += 16
    elif typ == 'BoolProperty':
        extra = bool(r.u8())
    elif typ in ('ByteProperty', 'EnumProperty', 'ArrayProperty', 'SetProperty'):
        extra = r.fstr()
    elif typ == 'MapProperty':
        extra = (r.fstr(), r.fstr())
    if r.u8():
        r.p += 16
    return dict(name=name, type=typ, size=size, index=aidx, extra=extra)


def props(r, end):
    out = {}
    while r.p < end:
        tag = read_tag(r)
        if tag is None:
            break
        start = r.p
        try:
            v = read_value(r, tag['type'], tag['size'], tag['extra'], start + tag['size'])
        except Exception as e:
            v = ('error', str(e))
        if tag['type'] != 'BoolProperty':
            r.p = start + tag['size']
        key = short(tag['name'])
        if tag['index']:
            key = '%s[%d]' % (key, tag['index'])
        out[key] = v
    return out


def payload(raw):
    r = T(raw)
    magic = struct.unpack_from('<I', raw, 0)[0]
    if magic == 0xA1B2C3D4:
        r.p = 4
        size = r.i32()
        return props(r, len(raw))
    return props(r, len(raw))
