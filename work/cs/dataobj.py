import struct
from mmimg import MMAsset

TYPE_SIZES = {2: (1, 1, 'B'), 3: (1, 1, 'b'), 7: (4, 4, 'i'), 9: (4, 4, 'f')}
def field_layout(name, code):
    is_array = name.endswith('_Array')
    if is_array: return ('array', code, 8, 16)
    if code == 10: return ('str', code, 8, 16)
    if code == 11: return ('name', code, 4, 8)
    a, s, f = TYPE_SIZES[code]
    return ('pod', code, a, s)

def align(x, a): return (x + a - 1) & ~(a - 1)

class DataObject:
    def __init__(self, m: MMAsset):
        self.m = m
        c = m.content
        # map
        self.el_ptr, self.el_num, self.el_max = m.arr(0)
        self.bits_ptr, self.bits_num, self.bits_max = m.arr(16)
        self.first_free, self.num_free = struct.unpack_from('<ii', c, 32)
        self.hash_ptr = m.ptr(40); self.hash_size = m.i32(48); self.hash_pad = m.i32(52)
        self.sd_ptr, self.sd_num, _ = m.arr(56)
        self.rows_ptr, self.rows_num, _ = m.arr(72)
        self.elements = []
        for i in range(self.el_num):
            o = self.el_ptr + i*20
            key = m.name_at.get(o)
            val, nxt, hidx = struct.unpack_from('<iii', c, o+8)
            self.elements.append((key, val, nxt, hidx))
        nwords = (self.bits_num + 31)//32
        self.bits = list(struct.unpack_from('<%dI' % nwords, c, self.bits_ptr)) if self.bits_ptr is not None else []
        self.hash = list(struct.unpack_from('<%di' % self.hash_size, c, self.hash_ptr)) if self.hash_ptr is not None else []
        self.fields = []
        off = 0
        for i in range(self.sd_num):
            o = self.sd_ptr + i*12
            nm = m.name_at.get(o); code = m.i32(o+8)
            kind, code, a, s = field_layout(nm, code)
            off = align(off, a)
            self.fields.append(dict(name=nm, code=code, kind=kind, offset=off, align=a, size=s))
            off += s
        self.row_align = max(f['align'] for f in self.fields)
        self.row_size = align(off, self.row_align)
        self.rows = [self.read_row(self.rows_ptr + r*self.row_size) for r in range(self.rows_num)]
    def read_scalar(self, code, o):
        m = self.m
        if code == 10:
            p, n, mx = m.arr(o)
            if p is None: return None if n == 0 else ('BAD', n)
            raw = m.content[p:p+n*2]
            s = raw.decode('utf-16-le')
            return s
        if code == 11:
            return m.name_at.get(o, '<none>' if m.content[o:o+8] == b'\0'*8 else '<unpatched %s>' % m.content[o:o+8].hex())
        a, s, f = TYPE_SIZES[code]
        return struct.unpack_from('<' + f, m.content, o)[0]
    def read_row(self, base):
        row = {}
        for f in self.fields:
            o = base + f['offset']
            if f['kind'] == 'array':
                p, n, mx = self.m.arr(o)
                esz = {10: 16, 11: 8, 7: 4, 9: 4, 2: 1}[f['code']]
                row[f['name']] = [self.read_scalar(f['code'], p + i*esz) for i in range(n)] if n else []
                row['__arr_' + f['name']] = (p, n, mx)
            else:
                row[f['name']] = self.read_scalar(f['code'], o)
                if f['kind'] == 'str': row['__str_' + f['name']] = self.m.arr(o)
        return row
