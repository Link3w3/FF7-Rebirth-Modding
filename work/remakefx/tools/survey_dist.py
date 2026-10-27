import sys, glob, collections, json, os
sys.path[:0] = ['/data/uploads/FF7R2UProj/Tools/RemakeImporter/rk418', os.path.dirname(os.path.abspath(__file__))]
import pkg418, uprops
from schema import Schema
S = Schema('/data/uploads/FF7R2UProj/Tools/RemakeImporter/rk418/remake_schema.json')
shapes = collections.Counter(); dist_cls = collections.Counter(); ex = {}
ops = collections.Counter()
def visit(p, V, path, cls):
    if V.kind == 'struct':
        if V.type in ('RawDistributionFloat', 'RawDistributionVector'):
            keys = tuple(sorted(V.value))
            d = V.value.get('Distribution')
            dc = None
            if d is not None and d.kind == 'obj' and isinstance(d.value, int) and d.value != 0:
                dc = p.classname(p.exports[d.value - 1]) if d.value > 0 else 'import:' + p.import_path(d.value)
            tab = V.value.get('Table')
            op = None
            if tab is not None:
                op = (tab.value.get('Op').value if tab.value.get('Op') is not None else None, tab.value.get('EntryCount').value if tab.value.get('EntryCount') is not None else None)
            k = (V.type, keys, dc)
            shapes[k] += 1
            ops[(V.type, dc, op)] += 1
            ex.setdefault(k, '%s %s %s' % (cls, path, os.path.basename(p.path) if hasattr(p, 'path') else ''))
        for k, x in V.value.items():
            visit(p, x, path + '.' + k, cls)
    elif V.kind in ('array', 'set'):
        for i, x in enumerate(V.value):
            visit(p, x, path + '[%d]' % i, cls)
    elif V.kind == 'native' and isinstance(V.value, dict):
        for k, x in V.value.items():
            if isinstance(x, uprops.V):
                visit(p, x, path + '.' + k, cls)
for f in sorted(glob.glob('rm/End/Content/**/*.uasset', recursive=True)):
    p = pkg418.Package(f)
    for i, e in enumerate(p.exports):
        cls, v, end = uprops.read_export(S, p, i)
        visit(p, v, cls, cls)
for k, n in shapes.most_common(40):
    print('%5d %s %s dist=%s   e.g. %s' % (n, k[0], k[1], k[2], ex[k]))
print()
for k, n in ops.most_common(40):
    print('%5d %s' % (n, k))
