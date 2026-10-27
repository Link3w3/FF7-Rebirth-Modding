"""Reader/writer for UE 4.26 unversioned property data (cooked packages), driven by schema.py."""
import struct
from schema import parse_headers, NATIVE_STRUCTS

STRUCTS, ENUMS = parse_headers()
PRIM_SIZE = {'bool': 1, 'uint8': 1, 'int8': 1, 'uint16': 2, 'int16': 2, 'uint32': 4, 'int32': 4, 'uint64': 8, 'int64': 8,
             'float': 4, 'double': 8}
PRIM_FMT = {'bool': '<B', 'uint8': '<B', 'int8': '<b', 'uint16': '<H', 'int16': '<h', 'uint32': '<I', 'int32': '<i',
            'uint64': '<Q', 'int64': '<q', 'float': '<f', 'double': '<d'}

def schema(sname):
    """Flat slot list (name, type, arrayindex) in serialization order: own properties, then the base's."""
    out = []
    s = STRUCTS[sname]
    for name, ptype, dim in s['props']:
        for k in range(dim):
            out.append((name, ptype, k if dim > 1 else None))
    base = s.get('base')
    if base in STRUCTS:
        out += schema(base)
    return out

class Reader:
    def __init__(self, data, names, pos=0):
        self.d = data; self.p = pos; self.names = names
    def take(self, n):
        v = self.d[self.p:self.p + n]
        if len(v) != n: raise EOFError('read past end at %d' % self.p)
        self.p += n; return v
    def unpack(self, fmt):
        v = struct.unpack_from(fmt, self.d, self.p)[0]; self.p += struct.calcsize(fmt); return v
    def fstring(self):
        n = self.unpack('<i')
        if n == 0: return ''
        if n < 0:
            raw = self.take(-n * 2); return raw.decode('utf-16-le').rstrip('\0')
        raw = self.take(n); return raw.decode('latin-1').rstrip('\0')
    def fname(self):
        i = self.unpack('<i'); num = self.unpack('<i')
        s = self.names[i] if 0 <= i < len(self.names) else '?%d' % i
        return s if num == 0 else '%s_%d' % (s, num - 1)

def zero_value(ptype):
    t = ptype
    if t in PRIM_SIZE: return False if t == 'bool' else (0.0 if t in ('float', 'double') else 0)
    if t.startswith('TEnumAsByte<') or t in ENUMS: return 0
    if t in ('FString', 'FText'): return ''
    if t == 'FName': return 'None'
    if t.startswith('TArray<'): return []
    if t.endswith('*') or t.startswith('TSubclassOf<') or t.startswith('TSoftObjectPtr<'): return 0
    if t in NATIVE_STRUCTS: return [0.0] * (NATIVE_STRUCTS[t] // 4)
    if t in STRUCTS: return {'__zero__': True}
    raise KeyError(t)

def read_value(r, ptype):
    t = ptype
    if t in PRIM_FMT:
        v = r.unpack(PRIM_FMT[t]); return bool(v) if t == 'bool' else v
    if t.startswith('TEnumAsByte<'): return r.unpack('<B')
    if t in ENUMS: return r.unpack(PRIM_FMT[ENUMS[t]])
    if t == 'FString': return r.fstring()
    if t == 'FName': return r.fname()
    if t.endswith('*') or t.startswith('TSubclassOf<'): return r.unpack('<i')
    if t.startswith('TArray<'):
        inner = t[len('TArray<'):-1].strip()
        n = r.unpack('<i')
        if n < 0 or n > 1_000_000: raise ValueError('bad array count %d for %s at %d' % (n, t, r.p - 4))
        return [read_value(r, inner) for _ in range(n)]
    if t in NATIVE_STRUCTS:
        return list(struct.unpack_from('<%df' % (NATIVE_STRUCTS[t] // 4), r.take(NATIVE_STRUCTS[t])))
    if t in STRUCTS:
        return read_struct(r, t)
    raise KeyError('unknown type ' + t)

def read_struct(r, sname):
    slots = schema(sname)
    frags = []
    while True:
        packed = r.unpack('<H')
        f = dict(skip=packed & 0x7F, zeroes=bool(packed & 0x80), last=bool(packed & 0x100), values=packed >> 9)
        frags.append(f)
        if f['last']: break
    zero_bits = sum(f['values'] for f in frags if f['zeroes'])
    mask = []
    if zero_bits:
        if zero_bits <= 8: words = [r.unpack('<B')]; wbits = 8
        elif zero_bits <= 16: words = [r.unpack('<H')]; wbits = 16
        else: words = [r.unpack('<I') for _ in range((zero_bits + 31) // 32)]; wbits = 32
        for b in range(zero_bits):
            mask.append(bool((words[b // wbits] >> (b % wbits)) & 1))
    out = {'__present__': [], '__zeroed__': []}
    idx = 0; zi = 0
    for f in frags:
        idx += f['skip']
        for _ in range(f['values']):
            if idx >= len(slots): raise ValueError('%s: slot %d beyond schema (%d) at %d' % (sname, idx, len(slots), r.p))
            name, ptype, ai = slots[idx]
            key = name if ai is None else '%s[%d]' % (name, ai)
            is_zero = False
            if f['zeroes']:
                is_zero = mask[zi]; zi += 1
            if is_zero:
                out[key] = zero_value(ptype); out['__zeroed__'].append(key)
            else:
                out[key] = read_value(r, ptype); out['__present__'].append(key)
            idx += 1
    out['__frags__'] = [(f['skip'], f['zeroes'], f['last'], f['values']) for f in frags]
    out['__mask__'] = mask
    return out
