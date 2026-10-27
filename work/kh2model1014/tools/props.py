"""Tagged (versioned) property dump of a Zen package's exports.  props.py <pkg> [export index]"""
import struct, sys, uuid
sys.path.insert(0, '/work/aura1014/tools')
import zx

class R:
    def __init__(s, b, z): s.b = b; s.o = 0; s.z = z
    def i32(s): v = struct.unpack_from('<i', s.b, s.o)[0]; s.o += 4; return v
    def u8(s): v = s.b[s.o]; s.o += 1; return v
    def f32(s): v = struct.unpack_from('<f', s.b, s.o)[0]; s.o += 4; return v
    def name(s):
        i, n = struct.unpack_from('<ii', s.b, s.o); s.o += 8
        t = s.z.names[i] if 0 <= i < len(s.z.names) else '?%d' % i
        return t if n == 0 else '%s_%d' % (t, n - 1)
    def guid(s): s.o += 16

def tag(r):
    name = r.name()
    if name == 'None':
        return None
    typ = r.name(); size = r.i32(); idx = r.i32()
    extra = {}
    if typ == 'StructProperty':
        extra['struct'] = r.name(); r.guid()
    elif typ == 'BoolProperty':
        extra['bool'] = r.u8()
    elif typ in ('ByteProperty', 'EnumProperty'):
        extra['enum'] = r.name()
    elif typ in ('ArrayProperty', 'SetProperty'):
        extra['inner'] = r.name()
    elif typ == 'MapProperty':
        extra['inner'] = r.name(); extra['value'] = r.name()
    if r.u8():
        r.guid()
    return name, typ, size, idx, extra

def value(r, typ, size, extra, depth):
    start = r.o
    pad = '  ' * depth
    out = None
    if typ == 'FloatProperty':
        out = '%.4f' % r.f32()
    elif typ == 'IntProperty':
        out = str(r.i32())
    elif typ == 'BoolProperty':
        out = str(extra['bool'])
    elif typ == 'NameProperty':
        out = r.name()
    elif typ in ('ByteProperty', 'EnumProperty'):
        if size == 8:
            out = r.name()
        else:
            out = str(r.u8())
    elif typ == 'ObjectProperty':
        v = r.i32()
        out = 'obj %d%s' % (v, (' (import %d)' % (-v - 1)) if v < 0 else '')
    elif typ == 'StructProperty':
        st = extra['struct']
        if st == 'LinearColor':
            out = 'RGBA(%.3f, %.3f, %.3f, %.3f)' % struct.unpack_from('<4f', r.b, r.o)
        elif st == 'Guid':
            out = 'guid'
        elif st in ('Vector', 'Vector2D', 'Rotator', 'Color', 'IntPoint'):
            out = st
        else:
            print(pad + '{')
            props(r, depth + 1)
            print(pad + '}')
            out = ''
    elif typ == 'ArrayProperty':
        n = r.i32()
        inner = extra['inner']
        if inner == 'StructProperty':
            t = tag(r)
            print(pad + '[%d x %s]' % (n, t[4].get('struct')))
            for k in range(n):
                print(pad + ' #%d' % k)
                props(r, depth + 1)
            out = ''
        elif inner == 'ObjectProperty':
            out = '[' + ', '.join(str(r.i32()) for _ in range(n)) + ']'
        else:
            out = '[%d x %s]' % (n, inner)
    r.o = start + size
    return out

def props(r, depth=0):
    pad = '  ' * depth
    while True:
        t = tag(r)
        if t is None:
            return
        name, typ, size, idx, extra = t
        hdr = pad + '%s%s (%s%s)' % (name, ('[%d]' % idx) if idx else '', typ, (' ' + str(list(extra.values()))) if extra else '')
        start = r.o
        try:
            v = value(r, typ, size, extra, depth)
        except Exception as e:
            v = 'ERR %s' % e
        r.o = start + size
        if v != '':
            print(hdr + ' = ' + str(v))
        else:
            print(hdr)

f = sys.argv[1]
z = zx.load(f)
idxs = [int(sys.argv[2])] if len(sys.argv) > 2 else z.order
for i in idxs:
    e = z.exports[i]
    print('== export', i, e['name'], e['serial_size'])
    b = z.exp(i)
    r = R(b, z)
    props(r)
    print('   (%d of %d bytes are properties)' % (r.o, len(b)))
