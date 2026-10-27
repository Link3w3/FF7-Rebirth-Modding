"""Decode/encode the FF7 Rebirth EndDataObject memory image (frozen content)."""
import struct
from cityhash import CityHash64

# type code -> (size, align, struct fmt)
POD = {1: (1, 1, '?'), 2: (1, 1, 'B'), 3: (1, 1, 'b'), 4: (2, 2, 'H'), 5: (2, 2, 'h'), 6: (4, 4, 'I'), 7: (4, 4, 'i'), 8: (8, 8, 'q'), 9: (4, 4, 'f')}
STR, NAME = 10, 11

def align(x, a): return (x + a - 1) & ~(a - 1)

def elem_size_align(code):
    if code == STR: return 16, 8
    if code == NAME: return 8, 4
    s, a, f = POD[code]; return s, a

def field_size_align(code, is_array):
    if is_array: return 16, 8
    return elem_size_align(code)

def compute_layout(fields):
    """fields: list of (name, code, is_array) in game order -> (offsets, row_size, row_align)"""
    off = 0; offs = []; ra = 1
    for name, code, is_array in fields:
        s, a = field_size_align(code, is_array)
        off = align(off, a); offs.append(off); off += s; ra = max(ra, a)
    return offs, align(off, ra), ra

def hash_buckets(n):
    if n >= 4:
        v = n // 2 + 8
        p = 1
        while p < v: p <<= 1
        return p
    return 1

def name_bytes_lower(base):
    if all(ord(ch) < 128 for ch in base):
        return base.lower().encode('ascii')
    return base.lower().encode('utf-16-le')

def name_hash(name):
    base, num = name
    return (CityHash64(name_bytes_lower(base)) + num) & 0xffffffff

class Decoded:
    pass

def decode(content, name_at, is_array_fn=None):
    """name_at: dict offset -> (base, num). Returns Decoded with keys, fields, rows."""
    c = content
    def i32(o): return struct.unpack_from('<i', c, o)[0]
    def ptr(o):
        v = struct.unpack_from('<q', c, o)[0]
        if v == 0: return None
        assert v & 1, ('unfrozen pointer', o, v)
        return o + (v >> 1)
    def arr(o): return ptr(o), i32(o + 8), i32(o + 12)
    d = Decoded()
    el_ptr, el_num, el_max = arr(0)
    d.bits = arr(16); d.free = struct.unpack_from('<ii', c, 32)
    d.hash_ptr = ptr(40); d.hash_size = i32(48); d.hash_pad = i32(52)
    sd_ptr, sd_num, _ = arr(56)
    rows_ptr, rows_num, _ = arr(72)
    d.keys = []
    for i in range(el_num):
        o = el_ptr + i * 20
        val, nxt, hidx = struct.unpack_from('<iii', c, o + 8)
        d.keys.append((name_at.get(o), val, nxt, hidx))
    d.fields = []
    for i in range(sd_num):
        o = sd_ptr + i * 12
        nm = name_at.get(o)
        code = i32(o + 8)
        isarr = is_array_fn(nm[0] if nm else None, code) if is_array_fn else (nm is not None and nm[0].endswith('_Array'))
        d.fields.append((nm, code, isarr))
    offs, rsize, ralign = compute_layout(d.fields)
    d.row_size = rsize
    def read_elem(code, o):
        if code == STR:
            p, n, mx = arr(o)
            assert n == mx, ('str num!=max', o, n, mx)
            if n == 0: assert p is None; return None
            return c[p:p + n * 2]
        if code == NAME:
            return name_at.get(o)
        s, a, f = POD[code]
        return c[o:o + s]
    d.rows = []
    for r in range(rows_num):
        base = rows_ptr + r * rsize
        row = []
        for (nm, code, isarr), fo in zip(d.fields, offs):
            o = base + fo
            if isarr:
                p, n, mx = arr(o)
                assert n == mx, ('arr num!=max', r, nm, n, mx)
                if n == 0:
                    assert p is None; row.append([]); continue
                es, ea = elem_size_align(code)
                row.append([read_elem(code, p + i * es) for i in range(n)])
            else:
                row.append(read_elem(code, o))
        d.rows.append(row)
    d.rows_ptr = rows_ptr
    return d

class Section:
    __slots__ = ('data', 'align', 'ptrs', 'names', 'idx')
    def __init__(self, a):
        self.data = bytearray(); self.align = a; self.ptrs = []; self.names = []
    def pad_to(self, a):
        while len(self.data) % a: self.data.append(0)

def encode(keys, fields, rows, cross_type_merge=False):
    """keys: list of (base,num) per row (row i <-> key i). fields: list of ((base,num), code, isarr). rows: list of lists.
    Returns (content bytes, names: dict (base,num)->sorted offsets)."""
    sections = []
    def new_section(a):
        s = Section(a); s.idx = len(sections); sections.append(s); return s
    def w_ptr(sec, target):
        sec.ptrs.append((len(sec.data), target.idx)); sec.data += b'\0' * 8
    def w_name(sec, nm):
        if nm is not None and nm[0] is not None and not (nm[0] == 'None' and nm[1] == 0):
            sec.names.append((len(sec.data), nm))
        sec.data += b'\0' * 8
    def w_i32(sec, v): sec.data += struct.pack('<i', v)
    n = len(rows)
    offs, rsize, ralign = compute_layout(fields)
    root = new_section(8)
    # --- RowMap: TSparseArray Data
    if n:
        el = new_section(4)
        hs = hash_buckets(n)
        buckets = [-1] * hs
        nexts = [-1] * n; hidx = [0] * n
        for i in range(n):
            h = name_hash(keys[i]) & (hs - 1)
            hidx[i] = h; nexts[i] = buckets[h]; buckets[h] = i
        for i in range(n):
            w_name(el, keys[i]); w_i32(el, i); w_i32(el, nexts[i]); w_i32(el, hidx[i])
        w_ptr(root, el); w_i32(root, n); w_i32(root, n)
        bits = new_section(4)
        nw = (n + 31) // 32
        for wi in range(nw):
            cnt = min(32, n - wi * 32)
            bits.data += struct.pack('<I', (1 << cnt) - 1 if cnt < 32 else 0xffffffff)
        w_ptr(root, bits); w_i32(root, n); w_i32(root, n)
        w_i32(root, -1); w_i32(root, 0)
        hsec = new_section(4)
        for b in buckets: w_i32(hsec, b)
        w_ptr(root, hsec); w_i32(root, hs); w_i32(root, 0)
    else:
        root.data += b'\0' * 16 + b'\0' * 16 + struct.pack('<ii', -1, 0) + b'\0' * 16
    # --- struct definition
    if fields:
        sd = new_section(4)
        for nm, code, isarr in fields:
            w_name(sd, nm); w_i32(sd, code)
        w_ptr(root, sd); w_i32(root, len(fields)); w_i32(root, len(fields))
    else:
        root.data += b'\0' * 16
    # --- rows
    def write_elem(sec, code, v):
        if code == STR:
            if v is None or len(v) == 0:
                sec.data += b'\0' * 16
            else:
                s = new_section(2); s.data += v
                w_ptr(sec, s); w_i32(sec, len(v) // 2); w_i32(sec, len(v) // 2)
        elif code == NAME:
            w_name(sec, v)
        else:
            sec.data += v
    if n:
        rs = new_section(ralign)
        w_ptr(root, rs); w_i32(root, n); w_i32(root, n)
        for row in rows:
            base = len(rs.data)
            for (nm, code, isarr), fo, v in zip(fields, offs, row):
                rs.pad_to(1)
                while len(rs.data) < base + fo: rs.data.append(0)
                if isarr:
                    if not v:
                        rs.data += b'\0' * 16
                    else:
                        es, ea = elem_size_align(code)
                        a = new_section(ea)
                        w_ptr(rs, a); w_i32(rs, len(v)); w_i32(rs, len(v))
                        for e in v:
                            write_elem(a, code, e)
                else:
                    write_elem(rs, code, v)
            while len(rs.data) < base + rsize: rs.data.append(0)
    else:
        root.data += b'\0' * 16
    # --- flatten with merge of pointer-free sections (keep first)
    seen = {}; remap = {}; out = bytearray(); offsets = {}
    for s in sections:
        if not s.ptrs:
            key = (bytes(s.data), tuple(s.names))
            if key in seen:
                remap[s.idx] = seen[key]; continue
            seen[key] = s.idx
        remap[s.idx] = s.idx
        o = align(len(out), s.align)
        out += b'\0' * (o - len(out))
        offsets[s.idx] = o
        out += s.data
    total = align(len(out), 16)
    out += b'\0' * (total - len(out))
    names = {}
    for s in sections:
        if remap[s.idx] != s.idx: continue
        base = offsets[s.idx]
        for (po, tidx) in s.ptrs:
            t = offsets[remap[tidx]]
            loc = base + po
            struct.pack_into('<q', out, loc, ((t - loc) << 1) | 1)
        for (no, nm) in s.names:
            names.setdefault(nm, []).append(base + no)
    return bytes(out), names
