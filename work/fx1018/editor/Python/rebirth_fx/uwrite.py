"""Unversioned property writing for UE 4.26 cooked zen packages (the inverse of uprops): FUnversionedHeader encoding and the
value encodings a material instance needs, so a property block can be rebuilt with values added or changed.

Unchanged values are copied byte for byte from the original package; only what changes is encoded here.
"""
import struct


def schema(usmap, sname):
    """[(schema index, Prop, element)] of a class/struct in serialization order (its own properties first, then its super's)."""
    out, base = [], 0
    for s in usmap.chain(sname):
        for p in sorted(s.props, key=lambda x: x.index):
            for k in range(p.array_dim):
                out.append((base + p.index + k, p, k))
        base += s.count
    out.sort(key=lambda x: x[0])
    return out


def schema_index(usmap, sname, prop_name, elem=0):
    for idx, p, k in schema(usmap, sname):
        if p.name == prop_name and k == elem:
            return idx
    raise KeyError('%s has no property %s' % (sname, prop_name))


def header(present, total=0):
    """FUnversionedHeader for `present`: [(schema index, is_zero)] (any order). Mirrors FUnversionedHeaderBuilder; `total`
    (the number of schema properties) matters only for an empty header, which skips them all."""
    frags = [[0, False, 0]]           # [skip, has_zeroes, values]
    starts = [0]                      # where each fragment's zero bits start in `mask`
    mask = []

    def close():
        f = frags[-1]
        if not f[1]:
            del mask[starts[-1]:]

    def new_fragment():
        close()
        frags.append([0, False, 0])
        starts.append(len(mask))

    nxt = 0
    for idx, zero in sorted(present):
        if idx < nxt:
            raise ValueError('property index %d twice' % idx)
        for _ in range(idx - nxt):            # excluded properties before this one
            f = frags[-1]
            if f[2] or f[0] == 127:
                new_fragment()
            frags[-1][0] += 1
        if frags[-1][2] == 127:
            new_fragment()
        frags[-1][2] += 1
        frags[-1][1] = frags[-1][1] or bool(zero)
        mask.append(bool(zero))
        nxt = idx + 1
    if not present:
        frags[0][0] = min(total, 127)
    close()
    while len(frags) > 1 and frags[-1][2] == 0:
        frags.pop()
    out = bytearray()
    for k, (skip, hz, num) in enumerate(frags):
        out += struct.pack('<H', skip | (0x80 if hz else 0) | (0x100 if k == len(frags) - 1 else 0) | (num << 9))
    if mask:
        n = len(mask)
        bits = 0
        for i, z in enumerate(mask):
            if z:
                bits |= 1 << i
        if n <= 8:
            out += struct.pack('<B', bits)
        elif n <= 16:
            out += struct.pack('<H', bits)
        else:
            for w in range((n + 31) // 32):
                out += struct.pack('<I', (bits >> (32 * w)) & 0xffffffff)
    return bytes(out)


class Names:
    """A zen package's name map with names added at the end when a new value needs one."""

    def __init__(self, names):
        self.names = list(names)
        self.index = {}
        for i, n in enumerate(self.names):
            self.index.setdefault(n, i)
        self.added = []

    def encode(self, name):
        """8 bytes: name map index and number (an FName in a zen package's property data)."""
        base, num = name, 0
        if name not in self.index:
            # 'Name_3' is Name with number 4 when Name is in the map
            head, _, tail = name.rpartition('_')
            if head and tail.isdigit() and not (len(tail) > 1 and tail[0] == '0') and head in self.index:
                base, num = head, int(tail) + 1
        if base not in self.index:
            self.index[base] = len(self.names)
            self.names.append(base)
            self.added.append(base)
        return struct.pack('<II', self.index[base], num)


def struct_bytes(usmap, sname, fields):
    """A struct (or class) property stream: fields = {property name: encoded bytes, or None for a zero value}. Properties
    left out of `fields` are not serialized (equal to the defaults)."""
    by_name = {}
    for idx, p, k in schema(usmap, sname):
        key = p.name if p.array_dim == 1 else '%s[%d]' % (p.name, k)
        by_name[key] = idx
    for key in fields:
        if key not in by_name:
            raise KeyError('%s has no property %s' % (sname, key))
    order = sorted((by_name[key], key) for key in fields)
    out = bytearray(header([(i, fields[key] is None) for i, key in order], usmap.total(sname)))
    for i, key in order:
        if fields[key] is not None:
            out += fields[key]
    return bytes(out)


def f32(v):
    return struct.pack('<f', float(v))


def i32(v):
    return struct.pack('<i', int(v))


def zero_or(b):
    """None (a zero value) when every byte is 0, else the bytes."""
    return None if not any(b) else b


def linear_color(rgba):
    return struct.pack('<4f', *[float(x) for x in rgba])


def guid(words):
    return struct.pack('<4I', *[int(x) & 0xffffffff for x in words])
