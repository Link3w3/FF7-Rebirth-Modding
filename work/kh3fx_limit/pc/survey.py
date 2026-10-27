"""Everything the effects of one KH3 par folder (default wep/limit/par) need from KH3's Effects folder: materials (instances, parents, functions they call),
textures and meshes, and which expression classes the materials use.

    python3 survey.py <Effects folder> <out.json> [par folder under Effects]
"""
import collections
import glob
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, 'tools')]
import kh3bonamik as k   # noqa: E402
import kh3mat            # noqa: E402

root = sys.argv[1]


def pkg_file(path):
    pkg = path.split('.', 1)[0]
    if not pkg.startswith('/Game/Effects/'):
        return None
    return os.path.join(root, *pkg[len('/Game/Effects/'):].split('/'))


def imports_of(base):
    pk = k.Package(open(base + '.uasset', 'rb').read(), open(base + '.uexp', 'rb').read())
    out = []
    for i, im in enumerate(pk.imports):
        if im['class_name'] in ('Class', 'Package'):
            continue
        out.append((im['class_name'], kh3mat.import_path(pk, -i - 1)))
    classes = collections.Counter(pk.class_name(e) for e in pk.exports)
    return out, classes


todo = collections.deque()
PAR = sys.argv[3] if len(sys.argv) > 3 else 'wep/limit/par'
for f in sorted(glob.glob(os.path.join(root, *PAR.split('/'), '*.uasset'))):
    todo.append(('ParticleSystem', '/Game/Effects/' + PAR + '/' + os.path.basename(f)[:-7]))
seen = {}
missing = []
expr_classes = collections.Counter()
while todo:
    cls, path = todo.popleft()
    if path in seen:
        continue
    base = pkg_file(path)
    if base is None:
        seen[path] = dict(cls=cls, external=True)
        continue
    if not os.path.isfile(base + '.uasset'):
        seen[path] = dict(cls=cls, missing=True)
        missing.append(path)
        continue
    entry = dict(cls=cls, file=os.path.relpath(base, root), size=os.path.getsize(base + '.uexp') if os.path.isfile(base + '.uexp') else 0,
                 ubulk=os.path.isfile(base + '.ubulk'))
    seen[path] = entry
    if cls in ('MaterialInstanceConstant', 'Material', 'MaterialFunction', 'ParticleSystem'):
        try:
            imps, classes = imports_of(base)
        except Exception as e:
            entry['error'] = str(e)
            continue
        if cls in ('Material', 'MaterialFunction'):
            for c, n in classes.items():
                if c.startswith('MaterialExpression'):
                    expr_classes[c] += n
            entry['expressions'] = sum(n for c, n in classes.items() if c.startswith('MaterialExpression'))
        for c, p in imps:
            if c in ('MaterialInstanceConstant', 'Material', 'MaterialFunction', 'Texture2D', 'TextureCube', 'StaticMesh',
                     'MaterialParameterCollection', 'TextureRenderTarget2D', 'SkeletalMesh', 'SubUVAnimation', 'VectorField',
                     'VectorFieldStatic', 'CurveFloat', 'CurveLinearColor'):
                if p.startswith('/Game/') and p not in seen:
                    todo.append((c, p))
            elif p.startswith('/Game/'):
                seen.setdefault(p, dict(cls=c, other=True))
by_cls = collections.Counter(v['cls'] for v in seen.values())
out = dict(by_class=by_cls, missing=missing, expression_classes=expr_classes, items=seen)
json.dump(out, open(sys.argv[2], 'w'), indent=1, default=str)
print('by class', dict(by_cls))
print('missing', len(missing), missing[:20])
print('expression classes', len(expr_classes))
for c, n in expr_classes.most_common():
    print('  %5d %s' % (n, c))
