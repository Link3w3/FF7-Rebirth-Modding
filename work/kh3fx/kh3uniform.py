"""The uniform expression set of a KH3 cooked material (what each slot of its Material uniform buffer holds), read
from the inline shader map that follows the material's properties.

    python3 kh3uniform.py <material .uasset>
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, '/work/kh3bnm/src/rebirth_fx']
import kh3bonamik as k   # noqa: E402
import tagged            # noqa: E402

FOLD_OPS = {0: '+', 1: '-', 2: '*', 3: '/', 4: 'dot'}


class Reader(object):
    def __init__(self, pk, p):
        self.pk, self.d, self.p = pk, pk.data, p

    def i32(self):
        v = struct.unpack_from('<i', self.d, self.p)[0]
        self.p += 4
        return v

    def f32(self):
        v = struct.unpack_from('<f', self.d, self.p)[0]
        self.p += 4
        return v

    def u8(self):
        v = self.d[self.p]
        self.p += 1
        return v

    def i8(self):
        v = struct.unpack_from('<b', self.d, self.p)[0]
        self.p += 1
        return v

    def name(self):
        i, n = struct.unpack_from('<ii', self.d, self.p)
        self.p += 8
        s = self.pk.names[i]
        return s if n == 0 else '%s_%d' % (s, n - 1)

    def color(self):
        v = struct.unpack_from('<4f', self.d, self.p)
        self.p += 16
        return v

    def expr(self):
        t = self.name()
        short = t[len('FMaterialUniformExpression'):]
        if short == 'Constant':
            c = self.color()
            vt = self.u8()
            return ('const', c, vt)
        if short == 'VectorParameter':
            return ('vparam', self.name(), self.color())
        if short == 'ScalarParameter':
            return ('sparam', self.name(), self.f32())
        if short == 'Texture':
            return ('tex', self.i32(), self.i32())
        if short == 'TextureParameter':
            n = self.name()
            return ('texparam', n, self.i32(), self.i32())
        if short == 'FlipBookTextureParameter':
            n = self.name()
            return ('texparam', n, self.i32(), self.i32())
        if short == 'AppendVector':
            a, b = self.expr(), self.expr()
            return ('append', a, b, self.i32())
        if short == 'ComponentSwizzle':
            x = self.expr()
            r, g, b, a, n = self.i8(), self.i8(), self.i8(), self.i8(), self.i8()
            return ('swizzle', x, ''.join('xyzw'[i] for i in (r, g, b, a)[:n]))
        if short in ('Max', 'Min', 'Fmod'):
            return (short.lower(), self.expr(), self.expr())
        if short == 'Clamp':
            return ('clamp', self.expr(), self.expr(), self.expr())
        if short == 'FoldedMath':
            a, b = self.expr(), self.expr()
            op = FOLD_OPS.get(self.u8(), '?')
            self.i32()                             # the result's value type
            return ('math', op, a, b)
        if short in ('Time', 'RealTime'):
            return (short.lower(),)
        if short == 'Sine':
            x = self.expr()
            return ('cos' if self.i32() else 'sin', x)
        if short in ('SquareRoot', 'Length', 'Frac', 'Floor', 'Ceil', 'Abs', 'Logarithm2', 'Logarithm10', 'Saturate',
                     'Round', 'Trunc', 'Sign', 'Periodic'):
            return (short.lower(), self.expr())
        if short == 'TrigMath':
            x, y = self.expr(), self.expr()
            op = self.u8()
            return ('trig', {0: 'sin', 1: 'cos', 2: 'tan', 3: 'asin', 4: 'acos', 5: 'atan', 6: 'atan2'}.get(op, '?%d' % op), x, y)
        if short == 'TextureProperty':
            x = self.expr()
            return ('texprop', x, self.u8())
        raise ValueError('uniform expression %s at %d not known' % (t, self.p - 8))


def show(e):
    k0 = e[0]
    if k0 == 'const':
        c = e[1]
        return '(%s)' % ', '.join('%g' % v for v in c[:max(1, e[2])])
    if k0 == 'vparam':
        return '"%s"' % e[1]
    if k0 == 'sparam':
        return '"%s"' % e[1]
    if k0 == 'tex':
        return 'texture#%d' % e[1]
    if k0 == 'texparam':
        return '"%s"(#%d)' % (e[1], e[2])
    if k0 == 'append':
        return 'append(%s, %s)' % (show(e[1]), show(e[2]))
    if k0 == 'swizzle':
        return '%s.%s' % (show(e[1]), e[2])
    if k0 == 'math':
        return '(%s %s %s)' % (show(e[2]), e[1], show(e[3]))
    if k0 in ('time', 'realtime'):
        return k0
    return '%s(%s)' % (k0, ', '.join(show(x) for x in e[1:] if isinstance(x, tuple)))


def find_set(pk, start, end):
    """Position of the vector expression count: an int32 followed by a uniform expression type name."""
    names = {i for i, n in enumerate(pk.names) if n.startswith('FMaterialUniformExpression')}
    d = pk.data
    for q in range(start, end - 12):
        i, n = struct.unpack_from('<ii', d, q + 4)
        if i in names and n == 0:
            cnt = struct.unpack_from('<i', d, q)[0]
            if 0 < cnt < 256:
                return q
    return None


def read_set(pk, export):
    props = tagged.parse(pk.data, export['offset'], export['offset'] + export['size'], pk.names)
    q = find_set(pk, props.end, export['offset'] + export['size'])
    if q is None:
        return None
    r = Reader(pk, q)
    out = {}
    for key in ('vectors', 'scalars', 'textures2d', 'texturescube'):
        n = r.i32()
        if not 0 <= n < 512:
            raise ValueError('%s count %d' % (key, n))
        out[key] = [r.expr() for _ in range(n)]
    out['end'] = r.p
    # then (KH3) an int32, the parameter collections' StateId GUIDs (MaterialCollectionN = the N-th)
    try:
        r.i32()
        n = r.i32()
        if 0 <= n <= 8:
            out['collections'] = [pk.data[r.p + 16 * i:r.p + 16 * i + 16].hex() for i in range(n)]
    except struct.error:
        pass
    return out


def material_set(path):
    base = path[:-7] if path.endswith('.uasset') else path
    pk = k.Package(open(base + '.uasset', 'rb').read(), open(base + '.uexp', 'rb').read())
    e = [x for x in pk.exports if pk.class_name(x) == 'Material' and x['outer'] == 0][0]
    return pk, e, read_set(pk, e)


def layout(s):
    """Material uniform buffer: vectors at [0..nv-1], scalars packed four per float4 after them."""
    lines = []
    nv = len(s['vectors'])
    for i, e in enumerate(s['vectors']):
        lines.append('cb[%d]      = %s' % (i, show(e)))
    for j, e in enumerate(s['scalars']):
        lines.append('cb[%d].%s    = %s' % (nv + j // 4, 'xyzw'[j % 4], show(e)))
    for j, e in enumerate(s['textures2d']):
        lines.append('Texture2D_%d = %s' % (j, show(e)))
    for j, e in enumerate(s['texturescube']):
        lines.append('TextureCube_%d = %s' % (j, show(e)))
    return lines


if __name__ == '__main__':
    pk, e, s = material_set(sys.argv[1])
    print('\n'.join(layout(s)))
