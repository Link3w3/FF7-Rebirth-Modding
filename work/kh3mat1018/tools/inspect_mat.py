import os, sys, json, collections, struct
sys.path[:0] = ['/work/kh3fx', '/work/kh3bnm/src/rebirth_fx']
import kh3bonamik as k, tagged, kh3mat
base = sys.argv[1]
pk = k.Package(open(base + '.uasset', 'rb').read(), open(base + '.uexp', 'rb').read())
print('names', len(pk.names), 'imports', len(pk.imports), 'exports', len(pk.exports), 'data', len(pk.data))
cnt = collections.Counter(pk.class_name(e) for e in pk.exports)
for c, n in cnt.most_common():
    print('  %4d %s' % (n, c))
info = kh3mat.read_material(open(base + '.uasset', 'rb').read(), open(base + '.uexp', 'rb').read())
print(json.dumps({kk: v for kk, v in info.items() if kk != 'imports'}, indent=1)[:6000])
print(json.dumps(info['imports'], indent=1)[:4000])
