"""Unversioned property data (UE 4.26 cooked, IoStore/Zen packages) read with layouts from ueschema.

    r = Reader(zen, export_index); obj = r.object(class_name)
Values: ints/floats, FName -> str, object refs -> ('export', i) / ('import', hash) / None, structs -> dict."""
import struct, sys
sys.path[:0] = ['/work/bizcut1015/tools', '/work/cs']
import ueschema

SCHEMA, ENUMS = ueschema.load()
PRIM = {'bool': '<B', 'uint8': '<B', 'int8': '<b', 'uint16': '<H', 'int16': '<h', 'uint32': '<I', 'int32': '<i',
        'uint64': '<Q', 'int64': '<q', 'float': '<f', 'double': '<d'}
FIXED = {'FVector': '<3f', 'FRotator': '<3f', 'FQuat': '<4f', 'FVector2D': '<2f', 'FLinearColor': '<4f', 'FVector4': '<4f',
         'FIntPoint': '<2i', 'FIntVector': '<3i', 'FColor': '<4B', 'FGuid': '<4I', 'FBox2D': '<4fB', 'FBox': '<6fB',
         'FPlane': '<4f', 'FMatrix': '<16f', 'FSphere': '<4f'}
UNDER = {'uint8': 'uint8', 'int8': 'int8', 'uint16': 'uint16', 'int16': 'int16', 'uint32': 'uint32', 'int32': 'int32',
         'uint64': 'uint64', 'int64': 'int64', 'int': 'int32'}


class DecodeError(Exception):
    pass


def schema_of(name, _cache={}):
    """Flat slots [(prop name, type, array index)] in serialization order: own properties, then the base's."""
    if name in _cache:
        return _cache[name]
    s = SCHEMA.get(name)
    if s is None:
        raise DecodeError('no layout for ' + name)
    out = []
    for ptype, pname, dim in s["props"]:
        if not isinstance(dim, int):
            raise DecodeError('%s.%s: array dimension %r' % (name, pname, dim))
        for k in range(dim):
            out.append((pname, ptype, k if dim > 1 else None))
    base = s.get('base')
    if base:
        base = base.split('::')[-1]
        if base in SCHEMA:
            out += schema_of(base)
        elif base not in ('UObject', 'UInterface'):
            raise DecodeError('%s: base %s has no layout' % (name, base))
    _cache[name] = out
    return out


def split_args(inner):
    out, depth, cur = [], 0, ''
    for c in inner:
        if c == '<':
            depth += 1
        elif c == '>':
            depth -= 1
        if c == ',' and depth == 0:
            out.append(cur.strip())
            cur = ''
        else:
            cur += c
    if cur.strip():
        out.append(cur.strip())
    return out


class Reader:
    def __init__(self, zen, data=None, pos=0):
        self.z = zen
        self.d = data
        self.p = pos
        self.names = zen.names
        self.trace = []

    def take(self, n):
        if self.p + n > len(self.d):
            raise DecodeError('read past the end (%d + %d > %d)' % (self.p, n, len(self.d)))
        v = self.d[self.p:self.p + n]
        self.p += n
        return v

    def unpack(self, fmt):
        n = struct.calcsize(fmt)
        v = struct.unpack_from(fmt, self.d, self.p)
        if self.p + n > len(self.d):
            raise DecodeError('read past the end')
        self.p += n
        return v if len(v) > 1 else v[0]

    def i32(self):
        return self.unpack('<i')

    def fstring(self):
        n = self.i32()
        if n == 0:
            return ''
        if n < 0:
            if -n > 1 << 20:
                raise DecodeError('bad string length %d at %d' % (n, self.p - 4))
            return self.take(-n * 2).decode('utf-16-le').rstrip('\0')
        if n > 1 << 20:
            raise DecodeError('bad string length %d at %d' % (n, self.p - 4))
        return self.take(n).decode('latin-1').rstrip('\0')

    def fname(self):
        i, num = self.unpack('<ii')
        if not (0 <= i < len(self.names)):
            raise DecodeError('name index %d out of range at %d' % (i, self.p - 8))
        s = self.names[i]
        return s if num == 0 else '%s_%d' % (s, num - 1)

    def objref(self):
        v = self.i32()
        if v == 0:
            return None
        if v > 0:
            return ('export', v - 1)
        idx = -v - 1
        imp = self.z.imports[idx] if idx < len(self.z.imports) else None
        return ('import', imp)

    def soft_path(self):
        return {'asset': self.fname(), 'sub': self.fstring()}

    # ---- natives
    def native(self, t):
        if t in FIXED:
            v = self.unpack(FIXED[t])
            return list(v)
        if t in ('FSoftObjectPath', 'FSoftClassPath'):
            return self.soft_path()
        if t == 'FMovieSceneFrameRange':
            lt, lv, ut, uv = self.unpack('<BiBi')
            return {'lower': (lt, lv), 'upper': (ut, uv)}
        if t == 'FMovieSceneFloatChannel':
            return self.float_channel()
        if t == 'FFrameNumber':
            return self.i32()
        if t == 'FMovieSceneSequenceID':
            return self.unpack('<I')
        if t == 'FText':
            return self.ftext()
        if t in ('FMovieSceneEndEventParameters', 'FMovieSceneEventParameters'):
            st = self.soft_path()
            n = self.i32()
            if n < 0 or n > 1 << 22:
                raise DecodeError('bad payload size %d at %d' % (n, self.p - 4))
            return {'struct': st, 'bytes': self.take(n)}
        return None

    def float_channel(self):
        pre, post = self.unpack('<BB')
        es, n = self.unpack('<ii')
        if es != 4 or n < 0 or n > 1 << 20:
            raise DecodeError('float channel times: element %d count %d at %d' % (es, n, self.p - 8))
        times = list(struct.unpack_from('<%di' % n, self.take(4 * n)))
        es, n2 = self.unpack('<ii')
        if es != 28 or n2 != n:
            raise DecodeError('float channel values: element %d count %d (times %d) at %d' % (es, n2, n, self.p - 8))
        raw = self.take(28 * n)
        values = []
        for k in range(n):
            v, at, lt, atw, ltw, wm, interp, tmode = struct.unpack_from('<5fBBB', raw, 28 * k)
            values.append(dict(v=v, arrive=at, leave=lt, aw=atw, lw=ltw, wmode=wm, interp=interp, tmode=tmode))
        default, hasdef = self.unpack('<fI')
        num, den = self.unpack('<ii')
        return dict(pre=pre, post=post, times=times, values=values, default=default, has_default=bool(hasdef), tick=(num, den))

    def ftext(self):
        flags = self.unpack('<I')
        kind = self.unpack('<b')
        if kind == -1:
            has = self.unpack('<I')
            return {'invariant': self.fstring()} if has else {'none': True}
        if kind == 0:
            return {'ns': self.fstring(), 'key': self.fstring(), 'src': self.fstring()}
        if kind == 11:   # StringTableEntry
            return {'table': self.fname(), 'key': self.fstring()}
        raise DecodeError('FText history %d not handled at %d' % (kind, self.p - 1))

    # ---- values
    def value(self, t):
        t = t.strip()
        if t in PRIM:
            v = self.unpack(PRIM[t])
            return bool(v) if t == 'bool' else v
        if t.startswith('TEnumAsByte<'):
            return self.unpack('<B')
        if t in ENUMS:
            return self.unpack(PRIM[UNDER.get(ENUMS[t], 'int32')])
        if t.endswith('::Type') and t[:-6] in ENUMS:
            return self.unpack(PRIM[UNDER.get(ENUMS[t[:-6]], 'uint8')])
        if t == 'FString':
            return self.fstring()
        if t == 'FName':
            return self.fname()
        if t.endswith('*') or t.startswith(('TSubclassOf<', 'TWeakObjectPtr<', 'TObjectPtr<')) or t == 'FWeakObjectPtr':
            return self.objref()
        if t.startswith(('TSoftObjectPtr<', 'TSoftClassPtr<')):
            return self.soft_path()
        if t.startswith('TLazyObjectPtr<'):
            return self.unpack('<4I')
        if t.startswith('TScriptInterface<'):
            return self.objref()
        if t.startswith(('TArray<', 'TSet<')):
            inner = t[t.index('<') + 1:-1].strip()
            if t.startswith('TSet<'):
                removed = self.i32()
                if removed:
                    raise DecodeError('set with removed keys')
            n = self.i32()
            if n < 0 or n > 1 << 20:
                raise DecodeError('bad array count %d for %s at %d' % (n, t, self.p - 4))
            return [self.value(inner) for _ in range(n)]
        if t.startswith('TMap<'):
            k, v = split_args(t[5:-1])
            removed = self.i32()
            if removed:
                raise DecodeError('map with removed keys')
            n = self.i32()
            if n < 0 or n > 1 << 20:
                raise DecodeError('bad map count %d at %d' % (n, self.p - 4))
            return [(self.value(k), self.value(v)) for _ in range(n)]
        nat = self.native(t)
        if nat is not None:
            return nat
        if t in SCHEMA:
            return self.struct(t)
        raise DecodeError('unknown type %s at %d' % (t, self.p))

    def header(self):
        frags = []
        while True:
            packed = self.unpack('<H')
            frags.append((packed & 0x7f, bool(packed & 0x80), bool(packed & 0x100), packed >> 9))
            if packed & 0x100:
                break
        zero_bits = sum(f[3] for f in frags if f[1])
        mask = []
        if zero_bits:
            if zero_bits <= 8:
                words, wb = [self.unpack('<B')], 8
            elif zero_bits <= 16:
                words, wb = [self.unpack('<H')], 16
            else:
                words, wb = [self.unpack('<I') for _ in range((zero_bits + 31) // 32)], 32
            mask = [bool((words[b // wb] >> (b % wb)) & 1) for b in range(zero_bits)]
        return frags, mask

    def struct(self, name):
        slots = schema_of(name)
        frags, mask = self.header()
        out = {'__type__': name}
        idx = zi = 0
        for skip, zeroes, last, count in frags:
            idx += skip
            for _ in range(count):
                if idx >= len(slots):
                    raise DecodeError('%s: slot %d beyond its %d properties' % (name, idx, len(slots)))
                pname, ptype, ai = slots[idx]
                key = pname if ai is None else '%s[%d]' % (pname, ai)
                z = False
                if zeroes:
                    z = mask[zi]
                    zi += 1
                if z:
                    out[key] = 0
                else:
                    start = self.p
                    try:
                        out[key] = self.value(ptype)
                    except DecodeError as e:
                        raise DecodeError('%s.%s (%s) at %d: %s' % (name, key, ptype, start, e))
                idx += 1
        return out

    def object(self, cls):
        obj = self.struct(cls)
        return obj


def export_object(z, i, cls):
    """Properties of export i (its class name without the /Script path) and the bytes left after them."""
    data = z.export_bytes(i)
    r = Reader(z, data, 0)
    obj = r.object(cls)
    return obj, data[r.p:]
