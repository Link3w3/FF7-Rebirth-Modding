"""Minimal FBX 7.x ASCII reader: geometry arrays, limb nodes, clusters and connections (for checking imports)."""
import re, numpy as np

def _arr(block, name, dtype=float):
    m = re.search(r'\b%s: \*(\d+) \{\s*a: ([^}]*)\}' % re.escape(name), block)
    if not m:
        return None
    return np.array([dtype(x) for x in m.group(2).replace('\n', '').split(',') if x.strip()])

def _objects(text, kind):
    """(id, name, subtype, body) of every 'kind: id, "X::name", "sub" {...}' object (brace matched)."""
    out = []
    for m in re.finditer(r'\n\t%s: (-?\d+), "([^"]*)", "([^"]*)" \{' % kind, text):
        i = m.end(); depth = 1
        while depth:
            j = text.find('{', i); k = text.find('}', i)
            if j != -1 and j < k:
                depth += 1; i = j + 1
            else:
                depth -= 1; i = k + 1
        out.append((int(m.group(1)), m.group(2).split('::', 1)[-1], m.group(3), text[m.end():i]))
    return out

def _layer(body, tag, arrname):
    m = re.search(r'%s: \d+ \{(.*?)\n\t\t\}' % tag, body, re.S)
    if not m:
        return None
    b = m.group(1)
    mapping = re.search(r'MappingInformationType: "(\w+)"', b).group(1)
    ref = re.search(r'ReferenceInformationType: "(\w+)"', b).group(1)
    data = _arr(b, arrname)
    idx = _arr(b, arrname.rstrip('s') + 'Index', int) if ref == 'IndexToDirect' else None
    if idx is None and arrname == 'UV':
        idx = _arr(b, 'UVIndex', int)
    return dict(mapping=mapping, ref=ref, data=data, index=idx)

def read(path):
    text = open(path, encoding='utf-8', errors='replace').read()
    geos = []
    for gid, name, sub, body in _objects(text, 'Geometry'):
        if sub != 'Mesh':
            continue
        g = dict(id=gid, name=name, verts=_arr(body, 'Vertices').reshape(-1, 3), pvi=_arr(body, 'PolygonVertexIndex', int))
        g['normals'] = _layer(body, 'LayerElementNormal', 'Normals')
        g['tangents'] = _layer(body, 'LayerElementTangent', 'Tangents')
        g['binormals'] = _layer(body, 'LayerElementBinormal', 'Binormals')
        uvs = []
        for m in re.finditer(r'LayerElementUV: (\d+) \{(.*?)\n\t\t\}', body, re.S):
            b = m.group(2)
            uvs.append(dict(mapping=re.search(r'MappingInformationType: "(\w+)"', b).group(1), data=_arr(b, 'UV').reshape(-1, 2), index=_arr(b, 'UVIndex', int)))
        g['uvs'] = uvs
        mm = re.search(r'LayerElementMaterial: \d+ \{(.*?)\n\t\t\}', body, re.S)
        g['materials'] = _arr(mm.group(1), 'Materials', int) if mm else None
        geos.append(g)
    models = {}
    for mid, name, sub, body in _objects(text, 'Model'):
        def prop(p):
            m = re.search(r'P: "%s", "[^"]*", "[^"]*", "[^"]*",([-\d.eE+]+),([-\d.eE+]+),([-\d.eE+]+)' % re.escape(p), body)
            return [float(m.group(i)) for i in (1, 2, 3)] if m else None
        models[mid] = dict(name=name, kind=sub, t=prop('Lcl Translation') or [0, 0, 0], r=prop('Lcl Rotation') or [0, 0, 0],
                           s=prop('Lcl Scaling') or [1, 1, 1], pre=prop('PreRotation') or [0, 0, 0], post=prop('PostRotation') or [0, 0, 0])
    clusters = {}
    for cid, name, sub, body in _objects(text, 'Deformer'):
        if sub != 'Cluster':
            continue
        clusters[cid] = dict(name=name, idx=_arr(body, 'Indexes', int), w=_arr(body, 'Weights'),
                             T=_arr(body, 'Transform').reshape(4, 4).T if _arr(body, 'Transform') is not None else None,
                             TL=_arr(body, 'TransformLink').reshape(4, 4).T if _arr(body, 'TransformLink') is not None else None)
    conns = [(int(a), int(b)) for a, b in re.findall(r'C: "OO",(-?\d+),(-?\d+)', text)]
    return dict(geos=geos, models=models, clusters=clusters, conns=conns)
