"""FF7 Remake (UE 4.18) material uniform expression sets: what fills each slot of a material's uniform buffer (the
"Material" cbuffer: its vector expressions first, then its scalar expressions four to a vector) and its textures.
    uniform418.py <package.uasset>"""
import struct, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shadermap418

OPS = {0: '+', 1: '-', 2: '*', 3: '/', 4: 'dot'}


class P:
    def __init__(self, pk, pos):
        self.pk, self.d, self.p = pk, pk.d, pos

    def i32(self):
        v = struct.unpack_from('<i', self.d, self.p)[0]; self.p += 4; return v

    def u8(self):
        v = self.d[self.p]; self.p += 1; return v

    def i8(self):
        v = struct.unpack_from('<b', self.d, self.p)[0]; self.p += 1; return v

    def f32(self):
        v = struct.unpack_from('<f', self.d, self.p)[0]; self.p += 4; return v

    def fname(self):
        i, n = struct.unpack_from('<ii', self.d, self.p); self.p += 8
        if not (0 <= i < len(self.pk.names)):
            raise ValueError('bad name %d at %d' % (i, self.p - 8))
        s = self.pk.names[i]
        return s if n == 0 else '%s_%d' % (s, n - 1)

    def color(self):
        return tuple(self.f32() for _ in range(4))

    def expr(self):
        t = self.fname()
        k = t.replace('FMaterialUniformExpression', '')
        if k == 'Constant':
            return {'op': 'const', 'value': self.color(), 'type': self.u8()}
        if k == 'VectorParameter':
            return {'op': 'vparam', 'name': self.fname(), 'default': self.color()}
        if k == 'ScalarParameter':
            return {'op': 'sparam', 'name': self.fname(), 'default': self.f32()}
        if k in ('TextureParameter',):
            return {'op': 'tparam', 'name': self.fname(), 'index': self.i32(), 'sampler': self.i32()}
        if k == 'Texture':
            return {'op': 'texture', 'index': self.i32(), 'sampler': self.i32()}
        if k == 'FlipBookTextureParameter':
            return {'op': 'flipbook', 'index': self.i32(), 'sampler': self.i32()}
        if k == 'ComponentSwizzle':
            x = self.expr()
            idx = [self.i8() for _ in range(4)]
            return {'op': 'swizzle', 'x': x, 'index': idx, 'n': self.i8()}
        if k == 'FoldedMath':
            a = self.expr()
            b = self.expr()
            op = self.u8()
            return {'op': 'math', 'a': a, 'b': b, 'math': OPS.get(op, op), 'type': self.i32()}
        if k == 'AppendVector':
            a = self.expr()
            b = self.expr()
            return {'op': 'append', 'a': a, 'b': b, 'na': self.u32()}
        if k in ('Clamp',):
            return {'op': 'clamp', 'x': self.expr(), 'lo': self.expr(), 'hi': self.expr()}
        if k in ('Min', 'Max'):
            return {'op': k.lower(), 'a': self.expr(), 'b': self.expr()}
        if k in ('Floor', 'Ceil', 'Frac', 'Abs', 'SquareRoot', 'Length', 'Logarithm2', 'Logarithm10', 'Saturate', 'Round', 'Truncate', 'Sign'):
            return {'op': k.lower(), 'x': self.expr()}
        if k == 'Sine':
            x = self.expr()
            return {'op': 'cos' if self.u32() else 'sin', 'x': x}
        if k == 'Trigonometry':
            x = self.expr()
            return {'op': 'trig', 'x': x, 'which': self.u8()}
        if k == 'Fmod':
            return {'op': 'fmod', 'a': self.expr(), 'b': self.expr()}
        if k == 'Power':
            return {'op': 'pow', 'a': self.expr(), 'b': self.expr()}
        if k == 'TextureProperty':
            t = self.expr()
            return {'op': 'texprop', 'texture': t, 'property': ('size', 'texelsize')[self.u8()] if True else None}
        if k == 'Time':
            return {'op': 'time'}
        if k == 'RealTime':
            return {'op': 'realtime'}
        if k == 'Exponential':
            return {'op': 'exp', 'x': self.expr()}
        if k == 'Exponential2':
            return {'op': 'exp2', 'x': self.expr()}
        raise ValueError('unknown uniform expression %s at %d' % (t, self.p))

    def u32(self):
        v = struct.unpack_from('<I', self.d, self.p)[0]; self.p += 4; return v

    def array(self):
        n = self.i32()
        if n < 0 or n > 512:
            raise ValueError('bad count %d at %d' % (n, self.p - 4))
        return [self.expr() for _ in range(n)]


def find_sets(pk, limit=None):
    """every shader map's uniform expression set: right after its FriendlyName FString, which comes shortly before its
    DebugDescription ("Compiling <name>: Platform=..., Usage=...")"""
    import re
    d = pk.d
    out = []
    for m in re.finditer(rb'Compiling ([A-Za-z0-9_]+): ([^\x00]*)', d):
        name = m.group(1)
        fs = struct.pack('<i', len(name) + 1) + name + b'\x00'
        q = d.rfind(fs, max(0, m.start() - 200000), m.start())
        if q < 0:
            continue
        try:
            pr = P(pk, q + len(fs))
            st = parse_set(pr)
        except Exception as ex:
            out.append({'friendly': name.decode(), 'error': str(ex), 'at': q})
            continue
        st['friendly'] = name.decode()
        st['at'] = q
        st['debug'] = m.group(2).decode('latin-1')
        out.append(st)
        if limit and len(out) >= limit:
            break
    return out


def parse_set(pr):
    s = {}
    s['vectors'] = pr.array()
    s['scalars'] = pr.array()
    s['textures2d'] = pr.array()
    s['texturescube'] = pr.array()
    s['end'] = pr.p
    return s


def show(e):
    o = e['op']
    if o == 'const':
        return 'const%r' % (tuple(round(v, 6) for v in e['value']),)
    if o == 'vparam':
        return 'V[%s]' % e['name']
    if o == 'sparam':
        return 'S[%s]' % e['name']
    if o == 'tparam':
        return 'T[%s]#%d' % (e['name'], e['index'])
    if o == 'swizzle':
        return '%s.%s' % (show(e['x']), ''.join('xyzw'[i] for i in e['index'][:e['n']]))
    if o == 'math':
        return '(%s %s %s)' % (show(e['a']), e['math'], show(e['b']))
    keys = [k for k in e if k not in ('op',)]
    return '%s(%s)' % (o, ', '.join(show(e[k]) if isinstance(e[k], dict) else repr(e[k]) for k in keys))


if __name__ == '__main__':
    pk = shadermap418.Lite(sys.argv[1])
    for s in find_sets(pk):
        if 'error' in s:
            print('set "%s" at %d: PARSE ERROR %s' % (s['friendly'], s['at'], s['error']))
            continue
        print(s['debug'][:400])
        print('set "%s" at %d: %d vectors, %d scalars, %d textures, %d cube' % (s['friendly'], s['at'], len(s['vectors']), len(s['scalars']), len(s['textures2d']), len(s['texturescube'])))
        for i, e in enumerate(s['vectors']):
            print('   CB[%d] = %s' % (i, show(e)))
        nv = len(s['vectors'])
        for j, e in enumerate(s['scalars']):
            print('   CB[%d].%s = %s' % (nv + j // 4, 'xyzw'[j % 4], show(e)))
        for e in s['textures2d'] + s['texturescube']:
            print('   ', show(e))
