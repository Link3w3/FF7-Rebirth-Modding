"""Kismet bytecode of a cooked (zen, UE 4.26) function: decoded into expression trees.

Storage differs from memory (object pointers 4 bytes on disk, 8 in memory; names 8 on disk, 12 in memory; property
pointers as FFieldPaths on disk, 8 in memory), so the decoder keeps the memory offset of every expression: jump targets
are memory offsets.

    kismet.py <package> <function export name or index> ...
"""
import struct, sys
sys.path[:0] = ['/work/cacsabp/tools', '/work/fx1018/tools', '/work/iostore', '/work/cs']

T = {
    0x00: 'LocalVariable', 0x01: 'InstanceVariable', 0x02: 'DefaultVariable', 0x04: 'Return', 0x06: 'Jump', 0x07: 'JumpIfNot',
    0x09: 'Assert', 0x0B: 'Nothing', 0x0F: 'Let', 0x12: 'ClassContext', 0x13: 'MetaCast', 0x14: 'LetBool', 0x15: 'EndParmValue',
    0x16: 'EndFunctionParms', 0x17: 'Self', 0x18: 'Skip', 0x19: 'Context', 0x1A: 'Context_FailSilent', 0x1B: 'VirtualFunction',
    0x1C: 'FinalFunction', 0x1D: 'IntConst', 0x1E: 'FloatConst', 0x1F: 'StringConst', 0x20: 'ObjectConst', 0x21: 'NameConst',
    0x22: 'RotationConst', 0x23: 'VectorConst', 0x24: 'ByteConst', 0x25: 'IntZero', 0x26: 'IntOne', 0x27: 'True', 0x28: 'False',
    0x29: 'TextConst', 0x2A: 'NoObject', 0x2B: 'TransformConst', 0x2C: 'IntConstByte', 0x2D: 'NoInterface', 0x2E: 'DynamicCast',
    0x2F: 'StructConst', 0x30: 'EndStructConst', 0x31: 'SetArray', 0x32: 'EndArray', 0x33: 'PropertyConst', 0x34: 'UnicodeStringConst',
    0x35: 'Int64Const', 0x36: 'UInt64Const', 0x38: 'PrimitiveCast', 0x39: 'SetSet', 0x3A: 'EndSet', 0x3B: 'SetMap', 0x3C: 'EndMap',
    0x3D: 'SetConst', 0x3E: 'EndSetConst', 0x3F: 'MapConst', 0x40: 'EndMapConst', 0x42: 'StructMemberContext',
    0x43: 'LetMulticastDelegate', 0x44: 'LetDelegate', 0x45: 'LocalVirtualFunction', 0x46: 'LocalFinalFunction',
    0x48: 'LocalOutVariable', 0x4B: 'InstanceDelegate', 0x4C: 'PushExecutionFlow', 0x4D: 'PopExecutionFlow', 0x4E: 'ComputedJump',
    0x4F: 'PopExecutionFlowIfNot', 0x50: 'Breakpoint', 0x51: 'InterfaceContext', 0x52: 'ObjToInterfaceCast', 0x53: 'EndOfScript',
    0x54: 'CrossInterfaceCast', 0x55: 'InterfaceToObjCast', 0x5A: 'WireTracepoint', 0x5B: 'SkipOffsetConst',
    0x5C: 'AddMulticastDelegate', 0x5D: 'ClearMulticastDelegate', 0x5E: 'Tracepoint', 0x5F: 'LetObj', 0x60: 'LetWeakObjPtr',
    0x61: 'BindDelegate', 0x62: 'RemoveMulticastDelegate', 0x63: 'CallMulticastDelegate', 0x64: 'LetValueOnPersistentFrame',
    0x65: 'ArrayConst', 0x66: 'EndArrayConst', 0x67: 'SoftObjectConst', 0x68: 'CallMath', 0x69: 'SwitchValue',
    0x6A: 'InstrumentationEvent', 0x6B: 'ArrayGetByRef', 0x6C: 'ClassSparseDataVariable', 0x6D: 'FieldPathConst',
}


class E:
    __slots__ = ('op', 'mem', 'args')

    def __init__(self, op, mem, args):
        self.op, self.mem, self.args = op, mem, args

    def __repr__(self):
        return '%s@%d%r' % (self.op, self.mem, self.args)


class Decoder:
    def __init__(self, z, data, start, storage, index_name):
        self.z, self.d, self.p, self.end = z, data, start, start + storage
        self.mem = 0
        self.index_name = index_name

    def take(self, fmt, mem=None):
        n = struct.calcsize(fmt)
        v = struct.unpack_from(fmt, self.d, self.p)
        self.p += n
        self.mem += n if mem is None else mem
        return v

    def u8(self): return self.take('<B')[0]
    def i32(self): return self.take('<i')[0]
    def u32(self): return self.take('<I')[0]
    def f32(self): return self.take('<f')[0]

    def name(self):
        idx, num = self.take('<II', 12)
        s = self.z.names[idx & 0x3fffffff]
        return s if num == 0 else '%s_%d' % (s, num - 1)

    def obj(self):
        return self.index_name(self.take('<i', 8)[0])

    def prop(self):
        """An FField pointer: on disk an FFieldPath (names, owner); 8 bytes in memory."""
        mem0 = self.mem
        n = self.take('<i', 0)[0]
        path = []
        for _ in range(n):
            idx, num = self.take('<II', 0)
            s = self.z.names[idx & 0x3fffffff]
            path.append(s if num == 0 else '%s_%d' % (s, num - 1))
        owner = self.index_name(self.take('<i', 0)[0]) if n else None
        self.mem = mem0 + 8
        return ('prop', '.'.join(path), owner)

    def string(self):
        mem0 = self.mem
        s = bytearray()
        while True:
            c = self.d[self.p]
            self.p += 1
            if c == 0:
                break
            s.append(c)
        self.mem = mem0 + len(s) + 1
        return s.decode('latin-1')

    def ustring(self):
        mem0 = self.mem
        s = bytearray()
        while True:
            c = self.d[self.p:self.p + 2]
            self.p += 2
            if c == b'\0\0':
                break
            s += c
        self.mem = mem0 + len(s) + 2
        return s.decode('utf-16-le')

    def expr(self):
        mem = self.mem
        tok = self.u8()
        op = T.get(tok)
        if op is None:
            raise ValueError('unknown token 0x%02x at %d (memory %d)' % (tok, self.p - 1, mem))
        a = []
        if op in ('LocalVariable', 'InstanceVariable', 'DefaultVariable', 'LocalOutVariable', 'ClassSparseDataVariable', 'PropertyConst'):
            a = [self.prop()]
        elif op in ('Return', 'InterfaceContext', 'ComputedJump', 'PopExecutionFlowIfNot', 'Skip0'):
            a = [self.expr()]
        elif op == 'Jump':
            a = [self.u32()]
        elif op == 'JumpIfNot':
            a = [self.u32(), self.expr()]
        elif op == 'Assert':
            a = [self.take('<H')[0], self.u8(), self.expr()]
        elif op in ('Nothing', 'EndParmValue', 'EndFunctionParms', 'Self', 'IntZero', 'IntOne', 'True', 'False', 'NoObject',
                    'NoInterface', 'EndStructConst', 'EndArray', 'EndSet', 'EndMap', 'EndSetConst', 'EndMapConst', 'EndArrayConst',
                    'PopExecutionFlow', 'Breakpoint', 'EndOfScript', 'WireTracepoint', 'Tracepoint', 'DeprecatedOp4A'):
            a = []
        elif op == 'Let':
            a = [self.prop(), self.expr(), self.expr()]
        elif op in ('LetBool', 'LetObj', 'LetWeakObjPtr', 'LetMulticastDelegate', 'LetDelegate'):
            a = [self.expr(), self.expr()]
        elif op in ('ClassContext', 'Context', 'Context_FailSilent'):
            a = [self.expr(), self.u32(), self.prop(), self.expr()]
        elif op in ('MetaCast', 'DynamicCast', 'ObjToInterfaceCast', 'CrossInterfaceCast', 'InterfaceToObjCast'):
            a = [self.obj(), self.expr()]
        elif op in ('VirtualFunction', 'LocalVirtualFunction'):
            a = [self.name(), self.params()]
        elif op in ('FinalFunction', 'LocalFinalFunction', 'CallMath', 'CallMulticastDelegate'):
            a = [self.obj(), self.params()]
        elif op == 'IntConst':
            a = [self.i32()]
        elif op == 'FloatConst':
            a = [self.f32()]
        elif op == 'StringConst':
            a = [self.string()]
        elif op == 'UnicodeStringConst':
            a = [self.ustring()]
        elif op == 'ObjectConst':
            a = [self.obj()]
        elif op == 'NameConst':
            a = [self.name()]
        elif op == 'RotationConst' or op == 'VectorConst':
            a = [self.take('<3f')]
        elif op == 'TransformConst':
            a = [self.take('<10f')]
        elif op == 'ByteConst' or op == 'IntConstByte':
            a = [self.u8()]
        elif op == 'Int64Const':
            a = [self.take('<q')[0]]
        elif op == 'UInt64Const':
            a = [self.take('<Q')[0]]
        elif op == 'TextConst':
            kind = self.u8()
            a = [kind]
            if kind == 0:      # empty
                pass
            elif kind == 1:    # localized: source, key, namespace
                a += [self.expr(), self.expr(), self.expr()]
            elif kind in (2, 3):  # invariant / literal string
                a += [self.expr()]
            elif kind == 4:    # string table: table id (object), key
                a += [self.obj(), self.expr()]
        elif op == 'StructConst':
            st = self.obj()
            size = self.i32()
            items = []
            while True:
                e = self.expr()
                if e.op == 'EndStructConst':
                    break
                items.append(e)
            a = [st, size, items]
        elif op == 'SetArray':
            target = self.expr()
            items = []
            while True:
                e = self.expr()
                if e.op == 'EndArray':
                    break
                items.append(e)
            a = [target, items]
        elif op in ('SetSet', 'SetMap'):
            target = self.expr()
            n = self.i32()
            items = []
            while True:
                e = self.expr()
                if e.op in ('EndSet', 'EndMap'):
                    break
                items.append(e)
            a = [target, n, items]
        elif op in ('SetConst', 'ArrayConst'):
            inner = self.prop()
            n = self.i32()
            items = []
            while True:
                e = self.expr()
                if e.op in ('EndSetConst', 'EndArrayConst'):
                    break
                items.append(e)
            a = [inner, n, items]
        elif op == 'MapConst':
            k, v = self.prop(), self.prop()
            n = self.i32()
            items = []
            while True:
                e = self.expr()
                if e.op == 'EndMapConst':
                    break
                items.append(e)
            a = [k, v, n, items]
        elif op == 'PrimitiveCast':
            a = [self.u8(), self.expr()]
        elif op == 'StructMemberContext':
            a = [self.prop(), self.expr()]
        elif op == 'InstanceDelegate':
            a = [self.name()]
        elif op == 'PushExecutionFlow':
            a = [self.u32()]
        elif op == 'SkipOffsetConst':
            a = [self.u32()]
        elif op in ('AddMulticastDelegate', 'RemoveMulticastDelegate'):
            a = [self.expr(), self.expr()]
        elif op == 'ClearMulticastDelegate':
            a = [self.expr()]
        elif op == 'BindDelegate':
            a = [self.name(), self.expr(), self.expr()]
        elif op == 'LetValueOnPersistentFrame':
            a = [self.prop(), self.expr()]
        elif op == 'SoftObjectConst':
            a = [self.expr()]
        elif op == 'SwitchValue':
            n = self.take('<H')[0]
            end = self.u32()
            index = self.expr()
            cases = []
            for _ in range(n):
                term = self.expr()
                next_off = self.u32()
                cases.append((term, next_off, self.expr()))
            a = [end, index, cases, self.expr()]
        elif op == 'InstrumentationEvent':
            kind = self.u8()
            a = [kind] + ([self.name()] if kind == 4 else [])
        elif op == 'ArrayGetByRef':
            a = [self.expr(), self.expr()]
        elif op == 'FieldPathConst':
            a = [self.expr()]
        else:
            raise ValueError('token %s not handled' % op)
        return E(op, mem, a)

    def params(self):
        out = []
        while True:
            e = self.expr()
            if e.op == 'EndFunctionParms':
                return out
            out.append(e)

    def all(self):
        out = []
        while self.p < self.end:
            out.append(self.expr())
        return out


def fmt(e, depth=0):
    """A readable line for an expression tree."""
    if not isinstance(e, E):
        if isinstance(e, tuple) and e and e[0] == 'prop':
            return e[1]
        if isinstance(e, tuple) and len(e) == 3 and e[0] in ('export', 'import'):
            return str(e[2]).rsplit('.', 1)[-1]
        return repr(e)
    a = e.args
    op = e.op
    if op in ('LocalVariable', 'InstanceVariable', 'LocalOutVariable', 'DefaultVariable'):
        return ('self.' if op == 'InstanceVariable' else '') + fmt(a[0])
    if op in ('CallMath', 'FinalFunction', 'LocalFinalFunction'):
        return '%s(%s)' % (fmt(a[0]), ', '.join(fmt(x, depth + 1) for x in a[1]))
    if op in ('VirtualFunction', 'LocalVirtualFunction'):
        return '%s(%s)' % (a[0], ', '.join(fmt(x, depth + 1) for x in a[1]))
    if op in ('Context', 'Context_FailSilent', 'ClassContext'):
        return '%s.%s' % (fmt(a[0]), fmt(a[3]))
    if op == 'LetBool' or op == 'LetObj':
        return '%s = %s' % (fmt(a[0]), fmt(a[1]))
    if op == 'Let':
        return '%s = %s' % (fmt(a[1]), fmt(a[2]))
    if op == 'LetValueOnPersistentFrame':
        return 'frame.%s = %s' % (fmt(a[0]), fmt(a[1]))
    if op == 'StructMemberContext':
        return '%s.%s' % (fmt(a[1]), fmt(a[0]))
    if op in ('IntConst', 'FloatConst', 'ByteConst', 'IntConstByte', 'NameConst', 'StringConst', 'Int64Const'):
        return repr(a[0])
    if op == 'True':
        return 'true'
    if op == 'False':
        return 'false'
    if op == 'IntZero':
        return '0'
    if op == 'IntOne':
        return '1'
    if op == 'Self':
        return 'self'
    if op == 'Jump':
        return 'goto %d' % a[0]
    if op == 'JumpIfNot':
        return 'if not (%s) goto %d' % (fmt(a[1]), a[0])
    if op == 'PushExecutionFlow':
        return 'push %d' % a[0]
    if op == 'PopExecutionFlowIfNot':
        return 'pop if not (%s)' % fmt(a[0])
    if op == 'ComputedJump':
        return 'goto [%s]' % fmt(a[0])
    if op == 'Return':
        return 'return %s' % fmt(a[0])
    if op == 'PrimitiveCast':
        return 'cast%d(%s)' % (a[0], fmt(a[1]))
    if op == 'ObjectConst':
        return fmt(a[0])
    if op == 'SwitchValue':
        return 'switch(%s){%s; default %s}' % (fmt(a[1]), '; '.join('%s: %s' % (fmt(t), fmt(v)) for t, _, v in a[2]), fmt(a[3]))
    return '%s(%s)' % (op, ', '.join(fmt(x) for x in a) if a else '')


def function_script(z, i):
    """(storage start, storage size, memory size, data) of a function export's bytecode (after its UStruct header)."""
    import abpread, fxlib, uprops, tagged
    u = fxlib.usmap()
    # (an editor-cooked package keeps its tagged properties: read as such)
    read = tagged.read_export if tagged.is_versioned(z) else uprops.read_export
    cls, v, end, data = read(u, z, i, abpread.PATHS)
    r = abpread.R(z.names, data, end)
    if r.i32():
        r.p += 16
    r.i32()                                       # super
    for _ in range(r.i32()):
        r.i32()                                   # children
    props = [abpread.read_field(r, z) for _ in range(r.i32())]
    mem, storage = r.i32(), r.i32()
    return r.p, storage, mem, data, props


def decode_function(z, i):
    import abpread
    start, storage, mem, data, props = function_script(z, i)
    dec = Decoder(z, data, start, storage, lambda v: abpread.index_name(z, v))
    exprs = dec.all()
    assert dec.p == start + storage, (dec.p, start + storage)
    return exprs, mem, props


if __name__ == '__main__':
    from zen import Zen
    z = Zen(open(sys.argv[1], 'rb').read())
    for arg in sys.argv[2:]:
        i = int(arg) if arg.isdigit() else [k for k, e in enumerate(z.exports) if e['name'] == arg][0]
        exprs, mem, props = decode_function(z, i)
        print('== %s (%d bytes in memory; %d locals/params: %s)' % (z.exports[i]['name'], mem, len(props), ', '.join(p['name'] for p in props)))
        for e in exprs:
            print('  %5d  %s' % (e.mem, fmt(e)))
