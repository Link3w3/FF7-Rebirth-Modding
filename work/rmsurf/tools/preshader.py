"""The uniform expressions of an RMI's shader map: Material_VectorExpressions[i] / ScalarExpressions as expressions of
its parameters (the frozen FUniformExpressionSet: +112 vector preshader headers, +128 scalar headers, +160 numeric
parameters, +304 opcode bytes)."""
import sys, struct, glob, json
sys.path[:0] = ['/work/custmat']
import carriers

OPS = {0: 'Nop', 1: 'ConstantZero', 2: 'Constant', 3: 'ScalarParameter', 4: 'VectorParameter', 5: 'Add', 6: 'Sub', 7: 'Mul',
       8: 'Div', 9: 'Fmod', 10: 'Min', 11: 'Max', 12: 'Clamp', 13: 'Dot', 14: 'Cross', 15: 'Neg', 16: 'Abs', 17: 'Saturate',
       18: 'Floor', 19: 'Ceil', 20: 'Round', 21: 'Trunc', 22: 'Sign', 23: 'Frac', 24: 'Fractional', 25: 'Sqrt', 26: 'Length',
       27: 'Normalize', 28: 'Sin', 29: 'Cos', 30: 'Tan', 31: 'Asin', 32: 'Acos', 33: 'Atan', 34: 'Atan2', 35: 'ComponentSwizzle',
       36: 'AppendVector'}


def arr(fz, at):
    v, n, m = struct.unpack_from('<qii', fz, at)
    if not (v & 1) or n == 0:
        return None, 0
    return at + (v >> 1), n


def patched_names(c):
    ex, t = c.ex, c.tail
    names, _ = carriers._name_list(ex, c.mi.v.at + c.mi.v.size)
    p = t['frozen_at'] + t['frozen_size']
    nv, ns, nm_ = struct.unpack_from('<iii', ex, p); p += 12
    for _ in range(nv):
        h, n = struct.unpack_from('<QI', ex, p); p += 12 + 8 * n
    at_name = {}
    for _ in range(ns):
        idx, num, n = struct.unpack_from('<III', ex, p)
        for off in struct.unpack_from('<%dI' % n, ex, p + 12):
            at_name[off] = names[idx] + ('_%d' % (num - 1) if num else '')
        p += 12 + 4 * n
    return at_name


def numeric_parameters(c, at_name, at=160, size=36):
    """+144: scalar parameters (24-byte entries: name, association, index, ?, default); +160: vector parameters (36)."""
    base, n = arr(c.fz, at)
    out = []
    for k in range(n or 0):
        e = base + size * k
        assoc, index, typ = struct.unpack_from('<iii', c.fz, e + 8)
        dv = struct.unpack_from('<4f' if size == 36 else '<f', c.fz, e + 20)
        out.append(dict(name=at_name.get(e), type=typ, default=dv))
    return out


def decode(code, params, scalars=()):
    """opcode bytes -> an expression string (a little stack machine)."""
    st = []
    p = 0
    while p < len(code):
        op = code[p]; p += 1
        name = OPS.get(op, 'op%d' % op)
        if op == 1:
            st.append('0')
        elif op == 2:
            v = struct.unpack_from('<4f', code, p); p += 16
            st.append('float4(%s)' % ', '.join('%g' % x for x in v))
        elif op in (3, 4):
            i = struct.unpack_from('<H', code, p)[0]; p += 2
            tab = scalars if op == 3 else params
            st.append(tab[i]['name'] if i < len(tab) else 'param%d' % i)
        elif op == 35:
            n = code[p]; idx = code[p + 1:p + 5]; p += 5
            a = st.pop()
            st.append('%s.%s' % (a, ''.join('xyzw'[i] for i in idx[:n])))
        elif op == 36:
            n = code[p]; p += 1
            b = st.pop(); a = st.pop()
            st.append('append(%s, %s)' % (a, b))
        elif op in (5, 6, 7, 8, 9, 10, 11, 13, 14, 34):
            b = st.pop(); a = st.pop()
            sym = {5: '+', 6: '-', 7: '*', 8: '/'}.get(op)
            st.append('(%s %s %s)' % (a, sym, b) if sym else '%s(%s, %s)' % (name, a, b))
        elif op == 12:
            c_ = st.pop(); b = st.pop(); a = st.pop()
            st.append('clamp(%s, %s, %s)' % (a, b, c_))
        elif 15 <= op <= 33:
            a = st.pop()
            st.append('%s(%s)' % (name, a))
        else:
            st.append('?%s@%d[%s]' % (name, p - 1, code[p:].hex()))
            break
    return ' ; '.join(st)


def uniform_expressions(c):
    fz = c.fz
    at_name = patched_names(c)
    params = numeric_parameters(c, at_name)
    scalars = numeric_parameters(c, at_name, 144, 24)
    dbase, dn = arr(fz, 304)
    data = fz[dbase:dbase + dn] if dbase else b''
    res = {}
    for key, at in (('vector', 112), ('scalar', 128)):
        base, n = arr(fz, at)
        lst = []
        for k in range(n or 0):
            off, size = struct.unpack_from('<II', fz, base + 8 * k)
            lst.append(decode(data[off:off + size], params, scalars))
        res[key] = lst
    res['params'] = params
    res['scalar_params'] = scalars
    return res


def load(name):
    path = glob.glob('/work/rmsurf/rmi/p*/pkgs/Renderer__MaterialInstance__Surface__%s.uasset' % name)[0]
    return carriers.Carrier(path)


if __name__ == '__main__':
    out = {}
    for path in sorted(glob.glob('/work/rmsurf/rmi/p*/pkgs/Renderer__MaterialInstance__Surface__RMI_Surface*.uasset')):
        name = path.rsplit('__', 1)[1][:-7]
        try:
            out[name] = uniform_expressions(carriers.Carrier(path))
        except Exception as e:
            out[name] = dict(error=repr(e))
    json.dump(out, open('/work/rmsurf/uniform_expressions.json', 'w'), indent=1)
    for n in sys.argv[1:]:
        print(n, json.dumps(out[n], indent=1))
    print(len(out), sum('error' in v for v in out.values()), 'errors')
