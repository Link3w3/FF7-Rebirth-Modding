"""Reads UHT reflection data (UE 4.26 UE4CodeGen_Private params) out of the game exe: function signatures, the
functions of a class (FClassFunctionLinkInfo arrays) and native registrations (FNameNativePtrPair)."""
import struct, sys
sys.path.insert(0, '/work/grab1014/refl')
from pe import PE

GEN = {0x00: 'Byte', 0x01: 'Int8', 0x02: 'Int16', 0x03: 'Int', 0x04: 'Int64', 0x05: 'UInt16', 0x06: 'UInt32', 0x07: 'UInt64',
       0x08: 'UnsizedInt', 0x09: 'UnsizedUInt', 0x0A: 'Float', 0x0B: 'Double', 0x0C: 'Bool', 0x0D: 'SoftClass',
       0x0E: 'WeakObject', 0x0F: 'LazyObject', 0x10: 'SoftObject', 0x11: 'Class', 0x12: 'Object', 0x13: 'Interface',
       0x14: 'Name', 0x15: 'Str', 0x16: 'Array', 0x17: 'Map', 0x18: 'Set', 0x19: 'Struct', 0x1A: 'Delegate',
       0x1B: 'InlineMulticastDelegate', 0x1C: 'SparseMulticastDelegate', 0x1D: 'Text', 0x1E: 'Enum', 0x1F: 'FieldPath'}
CPF = {0x1: 'Edit', 0x2: 'Const', 0x80: 'Parm', 0x100: 'Out', 0x400: 'Return', 0x8000000: 'Ref', 0x10: 'Zero'}
FUNC = {0x1: 'Final', 0x400: 'Native', 0x800: 'Event', 0x2000: 'Static', 0x20000: 'Public', 0x40000: 'Private',
        0x80000: 'Protected', 0x100000: 'Delegate', 0x10000: 'Multicast', 0x400000: 'HasOutParms', 0x4000000: 'BlueprintCallable',
        0x8000000: 'BlueprintEvent', 0x10000000: 'BlueprintPure', 0x40000000: 'Const', 0x200: 'Exec', 0x80000000: 'NetValidate'}


class Refl:
    def __init__(self, path):
        self.p = PE(path)
        self._ptr_index = None

    def strings(self, name):
        """VAs of NUL-terminated copies of `name` outside code."""
        out = []
        for o in self.p.find_all(b'\0' + name.encode() + b'\0'):
            va = self.p.va(o + 1)
            if va and self.p.is_data(va):
                out.append(va)
        return out

    def refs(self, va):
        """File offsets where the 8-byte pointer `va` is stored."""
        return self.p.find_all(struct.pack('<Q', va))

    def prop(self, va):
        p = self.p
        if not va or not p.is_data(va) or p.u64(va) is None or p.u32(va + 24) is None:
            return None
        name = p.cstr(p.u64(va))
        flags = p.u64(va + 16)
        gen = p.u32(va + 24)
        kind = GEN.get(gen & 0x1F, hex(gen))
        if gen & 0x20:
            kind += '(native bool)'
        arraydim = p.i32(va + 32)
        offset = p.i32(va + 36) if (gen & 0x1F) != 0x0C else None
        size = p.u32(va + 36) if (gen & 0x1F) == 0x0C else None
        fl = [n for b, n in CPF.items() if flags & b]
        return dict(name=name, kind=kind, flags=flags, flag_names=fl, offset=offset, bool_size=size, arraydim=arraydim,
                    func=p.u64(va + 40) if (gen & 0x1F) in (0x12, 0x11, 0x19, 0x1E, 0x00, 0x0E, 0x10, 0x13, 0x1A, 0x1B, 0x1C) else None)

    def function_params_at(self, base):
        """FFunctionParams at `base` (VA), or None if it does not look like one."""
        p = self.p
        outer, sup, name_ptr, owning, delegate, size, props, nprops = (p.u64(base), p.u64(base + 8), p.u64(base + 16),
            p.u64(base + 24), p.u64(base + 32), p.u64(base + 40), p.u64(base + 48), p.i32(base + 56))
        if outer is None or not p.is_code(outer):
            return None
        if sup and not p.is_code(sup):
            return None
        if owning and not p.is_data(owning) or delegate and not p.is_data(delegate):
            return None
        if size is None or size > 0x10000 or nprops is None or not (0 <= nprops < 200):
            return None
        if nprops and (not props or not p.is_data(props)):
            return None
        objflags, fflags = p.u32(base + 60), p.u32(base + 64)
        params = [self.prop(p.u64(props + 8 * i)) for i in range(nprops)]
        if any(x is None or not x['name'] for x in params):
            return None
        return dict(at=base, outer=outer, super=sup, name=p.cstr(name_ptr), owning=p.cstr(owning), delegate=p.cstr(delegate),
                    size=size, params=params, flags=fflags, flag_names=[n for b, n in FUNC.items() if fflags & b])

    def functions(self, name):
        out = []
        for s in self.strings(name):
            for o in self.refs(s):
                va = self.p.va(o)
                if va is None:
                    continue
                f = self.function_params_at(va - 16)
                if f:
                    out.append(f)
        return out

    def link_arrays(self, name):
        """FClassFunctionLinkInfo arrays ({CreateFuncPtr, FuncNameUTF8}) holding `name`: the class's function list."""
        p = self.p
        out = []
        for s in self.strings(name):
            for o in self.refs(s):
                va = p.va(o)
                if va is None or not p.is_code(p.u64(va - 8) or 0):
                    continue
                # walk to the array's ends
                def entry(at):
                    f, n = p.u64(at), p.u64(at + 8)
                    if f is None or not p.is_code(f) or not n or not p.is_data(n):
                        return None
                    t = p.cstr(n)
                    return (f, t) if t and t.isidentifier() else None
                start = va - 8
                while entry(start - 16):
                    start -= 16
                names = []
                at = start
                while entry(at):
                    names.append(entry(at))
                    at += 16
                out.append(dict(at=start, names=names))
        return out

    def native_arrays(self, name):
        """FNameNativePtrPair arrays ({NameUTF8, Pointer}) holding `name` (StaticRegisterNatives of a class)."""
        p = self.p
        out = []
        for s in self.strings(name):
            for o in self.refs(s):
                va = p.va(o)
                if va is None or not p.is_code(p.u64(va + 8) or 0):
                    continue
                def entry(at):
                    n, f = p.u64(at), p.u64(at + 8)
                    if f is None or not p.is_code(f) or not n or not p.is_data(n):
                        return None
                    t = p.cstr(n)
                    return (t, f) if t and t.isidentifier() else None
                start = va
                while entry(start - 16):
                    start -= 16
                names = []
                at = start
                while entry(at):
                    names.append(entry(at))
                    at += 16
                out.append(dict(at=start, names=names))
        return out


def signature(f):
    parts = []
    ret = None
    for prm in f['params']:
        if prm['flags'] & 0x400:
            ret = prm['kind']
            continue
        tags = [t for t in prm['flag_names'] if t in ('Out', 'Ref', 'Const')]
        parts.append('%s %s%s' % (prm['kind'], prm['name'], (' [' + ','.join(tags) + ']') if tags else ''))
    return '%s(%s) -> %s  {%s} size %d' % (f['name'], ', '.join(parts), ret or 'void', ' '.join(f['flag_names']), f['size'])
