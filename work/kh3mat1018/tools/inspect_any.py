import os, sys, json, collections, struct
sys.path[:0] = ['/work/kh3fx', '/work/kh3bnm/src/rebirth_fx']
import kh3bonamik as k, tagged, kh3mat
base = sys.argv[1]
pk = k.Package(open(base + '.uasset', 'rb').read(), open(base + '.uexp', 'rb').read())
print('names', len(pk.names), 'imports', len(pk.imports), 'exports', len(pk.exports), 'data', len(pk.data))
cnt = collections.Counter(pk.class_name(e) for e in pk.exports)
for c, n in cnt.most_common():
    print('  %4d %s' % (n, c))
top = [e for e in pk.exports if e['outer'] == 0][0]
props = tagged.parse(pk.data, top['offset'], top['offset'] + top['size'], pk.names)
for p in props:
    if p.type == 'ArrayProperty':
        print(' ', p.name, p.type, p.inner, len(p.elements))
    else:
        try:
            print(' ', p.name, p.type, kh3mat._value(pk, p))
        except Exception as e:
            print(' ', p.name, p.type, '?', e)
