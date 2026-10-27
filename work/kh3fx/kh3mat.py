"""KH3 cooked materials and material instances -> what they are: parent, parameters (scalar, vector, texture), blend /
shading settings, and every texture the package refers to.

    python3 kh3mat.py <Effects root> <material path or .uasset> ...      (prints JSON)
"""
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, '/work/kh3bnm/src/rebirth_fx']
import kh3bonamik as k   # noqa: E402
import tagged            # noqa: E402

MATERIAL_CLASSES = ('MaterialInstanceConstant', 'Material', 'MaterialFunction')


def import_path(pk, idx):
    parts = []
    while idx < 0:
        imp = pk.imports[-idx - 1]
        parts.append(imp['name'])
        idx = imp['outer']
    parts.reverse()
    return parts[0] + ('.' + ':'.join(parts[1:]) if len(parts) > 1 else '')


def ref_name(pk, i):
    if i < 0:
        return import_path(pk, i)
    return pk.exports[i - 1]['name'] if i > 0 else None


def _value(pk, p):
    d = pk.data
    v = p.value_start
    if p.type == 'BoolProperty':
        return bool(p.bool)
    if p.type == 'FloatProperty':
        return struct.unpack_from('<f', d, v)[0]
    if p.type == 'IntProperty':
        return struct.unpack_from('<i', d, v)[0]
    if p.type in ('ByteProperty', 'EnumProperty'):
        return tagged._name(d, v, pk.names) if p.size == 8 else d[v]
    if p.type == 'NameProperty':
        return tagged._name(d, v, pk.names)
    if p.type == 'ObjectProperty':
        return ref_name(pk, struct.unpack_from('<i', d, v)[0])
    if p.type == 'StructProperty' and p.struct == 'LinearColor':
        return list(struct.unpack_from('<4f', d, v))
    if p.type == 'StructProperty' and p.children is not None:
        return {c.name: _value(pk, c) for c in p.children}
    return '<%s %s>' % (p.type, p.struct or '')


def _params(pk, prop):
    out = {}
    if prop is None:
        return out
    for (s, t, refs) in prop.elements:
        ch = tagged.parse(pk.data, s, t, pk.names)
        vals = {c.name: _value(pk, c) for c in ch}
        name = vals.get('ParameterName')
        if name is None and isinstance(vals.get('ParameterInfo'), dict):
            name = vals['ParameterInfo'].get('Name')
        out[name] = vals.get('ParameterValue')
    return out


def read_material(uasset, uexp):
    pk = k.Package(uasset, uexp)
    e = [x for x in pk.exports if pk.class_name(x) in MATERIAL_CLASSES and x['outer'] == 0][0]
    props = tagged.parse(pk.data, e['offset'], e['offset'] + e['size'], pk.names)
    info = dict(name=e['name'], cls=pk.class_name(e))
    simple = {}
    for p in props:
        if p.name in ('ScalarParameterValues', 'VectorParameterValues', 'TextureParameterValues', 'FontParameterValues',
                      'ExpressionGUID', 'StateId', 'LightingGuid', 'CachedExpressionData', 'ReferencedTextureGuids'):
            continue
        if p.type == 'ArrayProperty':
            if p.inner == 'ObjectProperty':
                simple[p.name] = [ref_name(pk, struct.unpack_from('<i', pk.data, a)[0]) for a, _, _ in p.elements]
            continue
        simple[p.name] = _value(pk, p)
    info['props'] = simple
    info['parent'] = simple.pop('Parent', None)
    info['scalars'] = _params(pk, tagged.find(props, 'ScalarParameterValues'))
    info['vectors'] = _params(pk, tagged.find(props, 'VectorParameterValues'))
    info['textures'] = _params(pk, tagged.find(props, 'TextureParameterValues'))
    refs = {}
    for i, im in enumerate(pk.imports):
        if im['class_name'] in ('Texture2D', 'TextureCube', 'MaterialInstanceConstant', 'Material', 'MaterialFunction',
                                'TextureRenderTarget2D', 'MaterialParameterCollection'):
            refs.setdefault(im['class_name'], []).append(import_path(pk, -i - 1))
    info['imports'] = refs
    return info


def file_of(root, path):
    """/Game/Effects/a/b.c -> <root>/a/b (no extension), the KH3 Effects folder as root."""
    pkg = path.split('.', 1)[0]
    assert pkg.startswith('/Game/Effects/'), path
    return os.path.join(root, *pkg[len('/Game/Effects/'):].split('/'))


def load(root, path):
    base = file_of(root, path) if path.startswith('/Game/') else (path[:-7] if path.endswith('.uasset') else path)
    return read_material(open(base + '.uasset', 'rb').read(), open(base + '.uexp', 'rb').read())


if __name__ == '__main__':
    root = sys.argv[1]
    out = {}
    for p in sys.argv[2:]:
        out[p] = load(root, p)
    print(json.dumps(out, indent=1))
