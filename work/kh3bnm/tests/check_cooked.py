"""The cooked copy (unversioned properties, as the game loads them) against the converter's v2 data, value by value."""
import json, struct, sys
sys.path.insert(0, '/work/cs'); sys.path.insert(0, '/work/bnm/tools')
from legacy import Legacy
import unversioned as U

path = sys.argv[1] if len(sys.argv) > 1 else '/work/kh3bnm/cooked/p_ex011_Bonamik.uasset'
spec = json.load(open(sys.argv[2] if len(sys.argv) > 2 else '/work/kh3bnm/test/p_ex011_v2.json'))
d = open(path, 'rb').read()
L = Legacy(d, b'')
fails = []
def check(ok, what):
    if not ok: fails.append(what)
def ref(i):
    if i < 0: return 'import:' + L.imports[-i - 1][3]
    if i > 0: return 'export:' + L.exports[i - 1]['name']
    return 'null'
print('flags %08x (unversioned %s)' % (L.flags, bool(L.flags & 0x2000)))
for i, e in enumerate(L.exports):
    print('  export %d %-24s class %-30s outer %-26s flags %08x size %d' % (i + 1, e['name'], ref(e['cls']), ref(e['outer']), e['flags'], e['size']))
wrap_e, v2_e = L.exports[0], L.exports[1]
check(ref(wrap_e['cls']) == 'import:SQEX_BonamikAsset' and ref(v2_e['cls']) == 'import:SQEX_BonamikAsset_v2', 'export classes')
check(ref(v2_e['outer']) == 'export:' + wrap_e['name'] and v2_e['name'] == 'SQEX_BonamikAsset_v2_0', 'v2 object name and outer')

def obj(e, cls):
    r = U.Reader(L.d, L.names, e['offset'])
    v = U.read_struct(r, cls)
    tail = L.d[r.p:e['offset'] + e['size']]
    return v, tail
w, wtail = obj(wrap_e, 'USQEX_BonamikAsset')
v, vtail = obj(v2_e, 'USQEX_BonamikAsset_v2')
print('wrapper present', w['__present__'], 'zeroed', w['__zeroed__'], 'tail', wtail.hex())
print('v2 present', v['__present__'])
print('v2 zeroed', v['__zeroed__'], 'tail', vtail.hex())
check(w['__present__'] == ['m_VersionNo', 'v2'] and w['m_VersionNo'] == 2401 and ref(w['v2']) == 'export:SQEX_BonamikAsset_v2_0', 'wrapper: only m_VersionNo + v2')

f32 = lambda x: struct.unpack('<f', struct.pack('<f', x))[0]
ENUM_LISTS = {}
sys.path.insert(0, '/work/kh3bnm/src')
import rebirth_fx.kh3bonamik as K
count = [0]
def same(exp, got, ptype, where):
    count[0] += 1
    if ptype.startswith('TEnumAsByte<'):
        enum = ptype[12:-1]
        check(K.V2_ENUMS[enum][got] == exp, '%s: %r vs %r' % (where, K.V2_ENUMS[enum][got], exp)); return
    if ptype.startswith('TArray<'):
        inner = ptype[7:-1].strip()
        if not isinstance(got, list) or len(got) != len(exp): fails.append('%s: length %r vs %d' % (where, len(got) if isinstance(got, list) else got, len(exp))); return
        for i, (a, b) in enumerate(zip(exp, got)): same(a, b, inner, '%s[%d]' % (where, i))
        return
    if ptype.startswith('F') and ptype in U.STRUCTS:
        if isinstance(got, dict) and got.get('__zero__'):
            check(all(x in (0, 0.0, False, '', [], None) for x in exp.values()), '%s zeroed struct with values' % where); return
        for name, ptype2, dim in U.STRUCTS[ptype]['props']:
            keys = [name] if dim == 1 else ['%s[%d]' % (name, i) for i in range(dim)]
            exps = ([exp[name]] if dim == 1 else exp[name]) if name in exp else [None] * dim
            for key, e in zip(keys, exps):
                if name not in exp:
                    check(key not in got.get('__present__', []), '%s.%s written though the KH3 data has none' % (where, key)); continue
                if key not in got:   # left out of a delta-serialized struct: the default (zero) value
                    check(e in (0, 0.0, False, '') or e == [0.0] * len(e) if isinstance(e, list) else e in (0, 0.0, False, ''), '%s.%s missing, value %r' % (where, key, e)); continue
                same(e, got[key], ptype2, '%s.%s' % (where, key))
        return
    if ptype in ('FVector', 'FQuat'):
        check(len(got) == len(exp) and all(f32(a) == f32(b) and str(a)[0] == str(b)[0] for a, b in zip(exp, got)) or all(f32(a) == f32(b) for a, b in zip(exp, got)), '%s: %r vs %r' % (where, got, exp)); return
    if ptype == 'float':
        check(f32(exp) == f32(got), '%s: %r vs %r' % (where, got, exp)); return
    check(exp == got, '%s: %r vs %r' % (where, got, exp))

for name, ptype, dim in U.STRUCTS['USQEX_BonamikAsset_v2']['props']:
    if name in spec:
        if name not in v: fails.append('v2.%s not in the cooked data' % name); continue
        same(spec[name], v[name], ptype, 'v2.' + name)
    elif name in v['__present__']:
        fails.append('v2.%s is in the cooked data but not in the KH3 data' % name)
# negative zeros survive?
negz = sum(1 for l in v['m_Links'] if str(l['m_ConeOffsetZ']).startswith('-'))
print('links with -0.0 cone offset Z kept: %d of %d' % (negz, len(v['m_Links'])))
print('checked %d values: %s' % (count[0], 'ALL MATCH' if not fails else '%d FAIL' % len(fails)))
for f in fails[:25]: print('  ', f)
sys.exit(1 if fails else 0)
