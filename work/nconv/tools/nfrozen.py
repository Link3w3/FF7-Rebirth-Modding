"""Frozen memory images (UE FMemoryImage, as Square Enix uses them in Rebirth's Niagara data) — writer and the KHCV
system block codec.

FMemoryImage layout: every frozen pointer (TMemoryImagePtr / TMemoryImageArray data) points to its own section; sections
are laid out in creation order (depth first), each aligned to its own alignment, identical sections merged into the
first one; a pointer is stored as ((target - pointer position) << 1) | 1, an int64. FNames inside an image are written
as 8 zero bytes and listed in the image's name tables (minimal names: name -> image offsets).

KHCV (start of every cooked NiagaraSystem export): a frozen struct of four arrays
    SystemDataSetLayouts        FNiagaraVariableLayoutInfo per SystemCompiledData.DataSetCompiledData variable
    SpawnInstanceParamsLayouts  .. per SpawnInstanceParamsDataSetCompiledData variable
    UpdateInstanceParamsLayouts .. per UpdateInstanceParamsDataSetCompiledData variable
    Emitters                    per emitter: { TArray<FName> SpawnAttributes, TArray<FNiagaraVariableLayoutInfo> Layouts }
FNiagaraVariableLayoutInfo (104 bytes): u16 FloatComponentStart, Int32ComponentStart, HalfComponentStart, u16 0, then
TArray<u16> Float/Int32/Half ComponentByteOffsets and ComponentRegisterOffsets, interleaved (FloatByte, FloatReg,
IntByte, IntReg, HalfByte, HalfReg).
"""
import struct


class Section:
    __slots__ = ('data', 'align', 'ptrs', 'names')

    def __init__(self, align):
        self.data = bytearray()
        self.align = align
        self.ptrs = []      # (offset in this section, target section index)
        self.names = []     # (offset in this section, name)


class Image:
    def __init__(self):
        self.sections = []

    def section(self, align):
        self.sections.append(Section(align))
        return len(self.sections) - 1

    # --- writing helpers into a section
    def raw(self, s, b):
        self.sections[s].data += b

    def pad_to(self, s, align):
        d = self.sections[s].data
        while len(d) % align:
            d.append(0)

    def array(self, s, target, num):
        """a TMemoryImageArray field in section s pointing at section `target` (None: empty)"""
        sec = self.sections[s]
        self.pad_to(s, 8)
        if target is None or num == 0:
            sec.data += struct.pack('<qii', 0, 0, 0)
        else:
            sec.ptrs.append((len(sec.data), target))
            sec.data += struct.pack('<qii', 0, num, num)

    def name(self, s, name):
        sec = self.sections[s]
        sec.names.append((len(sec.data), name))
        sec.data += b'\0' * 8

    # --- flattening
    def flatten(self, merge=True):
        """-> (image bytes, alignment, minimal names {name: [offsets]}). Identical sections (same bytes, alignment, names
        and, recursively, the same pointed-to content) are merged into the first one created."""
        import hashlib
        n = len(self.sections)
        remap = list(range(n))
        if merge:
            skey = [None] * n
            for i in range(n - 1, -1, -1):          # children are created after their parents
                sec = self.sections[i]
                h = hashlib.sha1()
                h.update(struct.pack('<II', sec.align, len(sec.data)))
                h.update(bytes(sec.data))
                for o, t in sec.ptrs:            # by the target section itself (not its content): only sections
                    h.update(struct.pack('<II', o, t))  # with no pointers, or the very same targets, merge
                for o, nm in sec.names:
                    h.update(struct.pack('<I', o)); h.update(str(nm).encode('utf-8') + b'\0')
                skey[i] = h.digest()
            first = {}
            for i in range(n):
                k = skey[i]
                if k in first:
                    remap[i] = first[k]
                else:
                    first[k] = i
        # a merged section's own children are unreachable unless referenced elsewhere: lay out only reachable ones
        reach = set()
        stack = [0]
        while stack:
            i = remap[stack.pop()]
            if i in reach:
                continue
            reach.add(i)
            for o, t in self.sections[i].ptrs:
                stack.append(t)
        live = [i for i in range(n) if remap[i] == i and i in reach]
        offs = {}
        at = 0
        align = 1
        for i in live:
            sec = self.sections[i]
            a = max(sec.align, 1)
            align = max(align, a)
            at = (at + a - 1) // a * a
            offs[i] = at
            at += len(sec.data)
        at = (at + align - 1) // align * align      # the image size is a multiple of its alignment
        out = bytearray(at)
        names = {}
        for i in live:
            sec = self.sections[i]
            o = offs[i]
            out[o:o + len(sec.data)] = sec.data
            for po, t in sec.ptrs:
                rel = offs[remap[t]] - (o + po)
                struct.pack_into('<q', out, o + po, (rel << 1) | 1)
            for no, nm in sec.names:
                names.setdefault(nm, []).append(o + no)
        return bytes(out), align, names


# ------------------------------------------------------------------------------------------------------------------
# KHCV codec

LAYOUT_SIZE = 104


def _arr(im, o):
    ptr, num, mx = struct.unpack_from('<qii', im, o)
    if num == 0:
        return None, 0
    assert ptr & 1 and num == mx, (o, ptr, num, mx)
    return o + (ptr >> 1), num


def decode_layout(im, o):
    fs, is_, hs, pad = struct.unpack_from('<4H', im, o)
    arrays = []
    for j in range(6):
        t, n = _arr(im, o + 8 + 16 * j)
        arrays.append(list(struct.unpack_from('<%dH' % n, im, t)) if n else [])
    return {'starts': (fs, is_, hs), 'pad': pad, 'offsets': arrays}


def decode_khcv(im, names_at):
    """names_at: {image offset: name} from the minimal names table"""
    out = {}
    keys = ['system', 'spawn_params', 'update_params']
    for k, key in enumerate(keys):
        t, n = _arr(im, 16 * k)
        out[key] = [decode_layout(im, t + LAYOUT_SIZE * j) for j in range(n)]
    t, n = _arr(im, 48)
    ems = []
    for j in range(n):
        eo = t + 32 * j
        st, sn = _arr(im, eo)
        attrs = [names_at[st + 8 * q] for q in range(sn)] if sn else []
        lt, ln = _arr(im, eo + 16)
        ems.append({'spawn_attributes': attrs, 'layouts': [decode_layout(im, lt + LAYOUT_SIZE * q) for q in range(ln)]})
    out['emitters'] = ems
    return out


def _write_layouts(img, s, layouts):
    """the elements of a layouts array into section s, creating the offset-array sections after"""
    pend = []
    for L in layouts:
        img.pad_to(s, 8)
        img.raw(s, struct.pack('<4H', *L['starts'], L.get('pad', 0)))
        for arr in L['offsets']:
            if arr:
                t = img.section(2)
                img.raw(t, struct.pack('<%dH' % len(arr), *arr))
                img.array(s, t, len(arr))
            else:
                img.array(s, None, 0)


def encode_khcv(k):
    img = Image()
    root = img.section(8)
    # the root's four array headers are written first, their targets created in order
    targets = []
    for key in ('system', 'spawn_params', 'update_params'):
        lst = k[key]
        if lst:
            t = img.section(8)
            img.array(root, t, len(lst))
            _write_layouts(img, t, lst)
        else:
            img.array(root, None, 0)
    ems = k['emitters']
    if ems:
        t = img.section(8)
        img.array(root, t, len(ems))
        # element headers first (they live in section t), then their arrays depth first
        for e in ems:
            if e['spawn_attributes']:
                a = img.section(4)
                for nm in e['spawn_attributes']:
                    img.name(a, nm)
                img.array(t, a, len(e['spawn_attributes']))
            else:
                img.array(t, None, 0)
            if e['layouts']:
                L = img.section(8)
                img.array(t, L, len(e['layouts']))
                _write_layouts(img, L, e['layouts'])
            else:
                img.array(t, None, 0)
    else:
        img.array(root, None, 0)
    return img.flatten()
