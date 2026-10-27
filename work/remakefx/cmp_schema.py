"""Remake's (remake_schema.json) and Rebirth's (Rebirth.usmap) layouts of the classes Remake Sephiroth's effects use,
and every struct inside them: what differs (missing properties, other types)."""
import sys, json, collections
sys.path[:0] = ['/data/uploads/FF7R2UProj/Tools/RemakeImporter/rk418', '/work/fx1018/tools']
from schema import Schema
from usmap import Usmap
RM = Schema('/data/uploads/FF7R2UProj/Tools/RemakeImporter/rk418/remake_schema.json')
RB = Usmap('/work/fx1018/Rebirth.usmap')
CLASSES = sys.argv[1].split(',')

def rb_props(name):
    out = {}
    try:
        chain = RB.chain(name)
    except Exception:
        return None
    for s in chain:
        for p in s.props:
            out[p.name] = (p.ptype, p.array_dim, s.name)
    return out

def rm_props(name):
    out = {}
    try:
        chain = RM.chain(name)
    except Exception:
        return None
    for s in chain:
        for p in s.props:
            out[p.name] = (p.ptype, p.array_dim, s.name)
    return out

def tstr(t):
    return repr(t)

def structs_in(t, acc):
    if t is None:
        return
    if t.type == 'StructProperty':
        acc.add(t.struct)
    for sub in (getattr(t, 'inner', None), getattr(t, 'value', None)):
        if sub is not None and not isinstance(sub, str):
            structs_in(sub, acc)

todo, done = list(CLASSES), set()
report = []
while todo:
    n = todo.pop()
    if n in done:
        continue
    done.add(n)
    a, b = rm_props(n), rb_props(n)
    if a is None:
        report.append('%-40s not in the Remake schema' % n); continue
    if b is None:
        report.append('%-40s NOT IN REBIRTH' % n); continue
    for k, (t, dim, owner) in a.items():
        acc = set(); structs_in(t, acc); todo.extend(acc)
        if k not in b:
            report.append('%-40s %-34s %-30s missing in Rebirth (Remake %s)' % (n, k, tstr(t), owner))
        elif tstr(b[k][0]).replace('AssetObject', 'SoftObject') != tstr(t).replace('AssetObject', 'SoftObject') or b[k][1] != dim:
            report.append('%-40s %-34s Remake %s[%d] / Rebirth %s[%d]' % (n, k, tstr(t), dim, tstr(b[k][0]), b[k][1]))
    for k in b:
        if k not in a:
            report.append('%-40s %-34s only in Rebirth (%s)' % (n, k, tstr(b[k][0])))
print('\n'.join(report))
print(len(done), 'classes and structs compared')
