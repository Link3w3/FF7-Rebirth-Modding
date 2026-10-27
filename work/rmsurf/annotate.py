"""The decompiled base pass pixel shaders with names: View / Primitive / Material members, texture parameters."""
import json, re, os
lay = json.load(open('cbuffer_layouts.json'))
texmap = json.load(open('texmap.json'))
recs = json.load(open('rmi_surface.json'))
os.makedirs('named', exist_ok=True)
UE = json.load(open('uniform_expressions.json'))
CUR = {}
def material_member(index, comp):
    """Material._m0[i]: vector expression i, or a scalar expression after the vectors (the decoded preshader)."""
    u = CUR.get('ue') or {}
    nv = len(u.get('vector', []))
    if index < nv:
        e = u['vector'][index]
        return 'Material_V%d.%s=%s' % (index, comp, e.replace('append(', '(').replace(' ', ''))
    k = (index - nv) * 4 + 'xyzw'.index(comp)
    sc = u.get('scalar', [])
    return 'Material_S%d=%s' % (k, sc[k] if k < len(sc) else '?')
def member(ub, index, comp):
    if ub == 'Material':
        return material_member(index, comp)
    d = lay.get(ub, {})
    off = index * 16 + 'xyzw'.index(comp) * 4
    # the member that holds this offset: the largest start <= off
    best = None
    for k, (typ, name) in d.items():
        s = int(k)
        if s <= off and (best is None or s > best[0]):
            best = (s, typ, name)
    if not best:
        return None
    s, typ, name = best
    rel = off - s
    size = {'float': 4, 'float2': 8, 'float3': 12, 'float4': 16, 'int': 4, 'uint': 4, 'int2': 8, 'uint2': 8, 'int3': 12, 'uint3': 12, 'int4': 16, 'uint4': 16, 'float4x4': 64, 'float3x4': 48}.get(re.sub(r'\[.*', '', typ), 16)
    if '[' in typ:
        n = int(re.search(r'\[(\d+)\]', typ).group(1))
        size = 16 * n
    if rel >= size:
        return None
    if typ.startswith('float4x4'):
        return '%s[%d].%s' % (name, rel // 16, 'xyzw'[(rel % 16) // 4])
    if '[' in typ:
        return '%s[%d].%s' % (name, rel // 16, 'xyzw'[(rel % 16) // 4])
    comps = 'xyzw'
    return name + ('' if size == 4 else '.' + comps[rel // 4])
def rename(text, names):
    def ub(m):
        u, i, c = m.group(1), int(m.group(2)), m.group(3)
        out = []
        for ch in c:
            r = member(u, i, ch)
            out.append(r or '%s[%d].%s' % (u, i, ch))
        if len(out) == 1:
            return '{' + out[0] + '}'
        return '{' + ', '.join(out) + '}'
    text = re.sub(r'\b(View|Primitive|Material|TranslucentBasePass)\._m0\[(\d+)u\]\.([xyzw]{1,4})', ub, text)
    def cast(m):
        f, u, i, c = m.group(1), m.group(2), int(m.group(3)), m.group(4)
        out = [member(u, i, ch) or '%s[%d].%s' % (u, i, ch) for ch in c]
        return '%s(%s)' % (f, out[0] if len(out) == 1 else '{' + ', '.join(out) + '}')
    text = re.sub(r'\b(floatBitsToUint|floatBitsToInt)\((View|Primitive|Material|TranslucentBasePass)\._m0\[(\d+)u\]\)\.([xyzw]{1,4})', cast, text)
    for k, n in names.items():
        text = re.sub(r'\bMaterial_Texture2D_%d\b' % k, 'T_' + n, text)
    return text
done = 0
for r in recs:
    bp = r['basepass']
    vf = 'TGPUSkinVertexFactoryInfluence4' if 'TGPUSkinVertexFactoryInfluence4' in bp else ('FLocalVertexFactory' if 'FLocalVertexFactory' in bp else sorted(bp)[0])
    lib = bp[vf]['lib']
    g = 'bp/PS_%d.glsl' % lib
    if not os.path.exists(g):
        continue
    CUR['ue'] = UE.get(r['name'])
    tm = texmap.get(r['name'])
    names = {k: (n or 'Unnamed%d_%d' % (k, tex)) for k, n, tex in tm} if isinstance(tm, list) else {}
    text = rename(open(g).read(), names)
    on = ' '.join(sorted(k.rstrip('_') for k, v in r['switches'].items() if v))
    head = '// %s (%s, library shader %d)\n// switches on: %s\n// textures: %s\n' % (r['name'], vf, lib, on, ', '.join('%d=%s' % (k, v) for k, v in sorted(names.items())))
    open('named/%s.glsl' % r['name'], 'w').write(head + text)
    done += 1
print(done)
