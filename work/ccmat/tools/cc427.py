"""Crisis Core Reunion (UE 4.27, zen packages) materials: material instances' parameters and parents, and the inline
shader maps cooked into masters and static-permutation instances (their uniform expression sets and which shader of
the shader library each of their mesh shaders is).

    cc427.py mi <package.uasset> [...]        an instance's parent, parameters, overrides, static switches
    cc427.py maps <package.uasset> [...]      its inline shader maps: quality levels, map hashes, shaders
    cc427.py uniforms <package.uasset>        the (first) shader map's uniform buffer: every slot as an expression

Layouts (worked out against the packages; the engine's 4.26 headers for the names):
  * the inline shader maps sit at the end of the export: a private name table (count; FString + 2 hashes each), the
    resource locations (count; {u32 offset, u8 feature level, u8 quality level}), the byte count, then per resource
    {bCooked, bValid, quality level, feature level, cooked map id hash, layout parameters, the frozen
    FMaterialShaderMapContent, its FMemoryImageResult (vtables, script names: patched FScriptName offsets), the
    pointer table (shader types, vertex factory types: FHashedName), type dependencies, bShareCode, the map hash}
  * FMaterialShaderMapContent: OrderedMeshShaderMaps at 96; FUniformExpressionSet at 112 (vector preshaders, scalar
    preshaders, scalar parameters, vector parameters, 5 texture parameter lists, shader resource buffers, external
    textures, preshader data, VT stacks, parameter collections, uniform buffer layout)
  * FMeshMaterialShaderMap: shader types at 24, permutations at 40, shaders at 56, pipelines at 72, VF type name at 96
  * FShader: Type (indexed) at 176, VFType at 184, target at 192, resource index at 196
"""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, '/work/ccanim/tools')
from ccanim import Zen, R, SCHEMAS, Unversioned, DecodeError   # noqa: E402
from cityhash import cityhash64, hashed_name                   # noqa: E402
import shader_names427                                          # noqa: E402

OPS = ['Nop', 'ConstantZero', 'Constant', 'ScalarParameter', 'VectorParameter', 'Add', 'Sub', 'Mul', 'Div', 'Fmod', 'Min',
       'Max', 'Clamp', 'Sin', 'Cos', 'Tan', 'Asin', 'Acos', 'Atan', 'Atan2', 'Dot', 'Cross', 'Sqrt', 'Length', 'Saturate',
       'Abs', 'Floor', 'Ceil', 'Round', 'Trunc', 'Sign', 'Frac', 'Fractional', 'Log2', 'Log10', 'ComponentSwizzle',
       'AppendVector', 'TextureSize', 'TexelSize', 'ExternalTextureCoordinateScaleRotation',
       'ExternalTextureCoordinateOffset', 'RuntimeVirtualTextureUniform']
BINARY = {'Add': '+', 'Sub': '-', 'Mul': '*', 'Div': '/', 'Fmod': 'fmod', 'Min': 'min', 'Max': 'max', 'Atan2': 'atan2'}
UNARY = {'Sin', 'Cos', 'Tan', 'Asin', 'Acos', 'Atan', 'Sqrt', 'Length', 'Saturate', 'Abs', 'Floor', 'Ceil', 'Round', 'Trunc',
         'Sign', 'Frac', 'Fractional', 'Log2', 'Log10'}
TEXTURE_TYPES = ['Standard2D', 'Cube', 'Array2D', 'Volume', 'Virtual']
QUALITY = {0: 'Low', 1: 'High', 2: 'Medium', 3: 'Epic', 4: 'Num'}

# ---- material instance schemas (unversioned: own properties first, then UMaterialInstance's, then UMaterialInterface's)
SCHEMAS.update({
    'MaterialInstanceConstant': (
        [('PhysMaterialMask', 'obj'), ('PhysMaterial', 'obj')] + [('PhysicalMaterialMap%d' % i, 'obj') for i in range(8)] +
        [('Parent', 'obj'), ('Unknown11', None), ('bHasStaticPermutationResource', 'bool'), ('bOverrideSubsurfaceProfile', 'bool'),
         ('Unknown14', 'bool'),
         ('ScalarParameterValues', ('arr', ('struct', 'ScalarParameterValue'))),
         ('VectorParameterValues', ('arr', ('struct', 'VectorParameterValue'))),
         ('TextureParameterValues', ('arr', ('struct', 'TextureParameterValue'))),
         ('RuntimeVirtualTextureParameterValues', ('arr', ('struct', 'TextureParameterValue'))),
         ('FontParameterValues', None),
         ('BasePropertyOverrides', ('struct', 'MaterialInstanceBasePropertyOverrides')),
         ('StaticParameters', ('struct', 'StaticParameterSet')),
         ('CachedLayerParameters', None),
         ('CachedReferencedTextures', ('arr', 'obj')),
         ('SubsurfaceProfile', 'obj'), ('LightmassSettings', None),
         ('TextureStreamingData', ('arr', ('struct', 'MaterialTextureInfo'))),
         ('AssetUserData', ('arr', 'obj'))]),
    'MaterialParameterInfo': [('Name', 'name'), ('Association', 'u8'), ('Index', 'i32')],
    'ScalarParameterValue': [('ParameterInfo', ('struct', 'MaterialParameterInfo')), ('ParameterValue', 'f32'), ('ExpressionGUID', 'guid')],
    'VectorParameterValue': [('ParameterInfo', ('struct', 'MaterialParameterInfo')), ('ParameterValue', 'quat'), ('ExpressionGUID', 'guid')],
    'TextureParameterValue': [('ParameterInfo', ('struct', 'MaterialParameterInfo')), ('ParameterValue', 'obj'), ('ExpressionGUID', 'guid')],
    # Reunion's has 18 fields (4.27's 12 and 6 of its own); indices 0, 1, 9, 10, 15, 16, 17 are the ones its
    # character instances use (0: clip override with its value 17, 1: blend override with 15, 9: two-sided hair and
    # lashes, 10: dithered LOD fades on the opaque parts, 15/16: EBlendMode / EMaterialShadingModel bytes)
    'MaterialInstanceBasePropertyOverrides': [
        ('bOverride_OpacityMaskClipValue', 'bool'), ('bOverride_BlendMode', 'bool'), ('bOverride_ShadingModel', 'bool'),
        ('bOverride_DitheredLODTransition', 'bool'), ('bOverride_CastDynamicShadowAsMasked', 'bool'), ('bOverride_TwoSided', 'bool'),
        ('bOverride_6', 'bool'), ('bOverride_7', 'bool'), ('bOverride_8', 'bool'),
        ('TwoSided', 'bool'), ('DitheredLODTransition', 'bool'), ('bCastDynamicShadowAsMasked', 'bool'),
        ('Extra12', 'bool'), ('Extra13', 'bool'), ('Extra14', 'bool'),
        ('BlendMode', 'u8'), ('ShadingModel', 'u8'), ('OpacityMaskClipValue', 'f32')],
    'StaticParameterSet': [('StaticSwitchParameters', ('arr', ('struct', 'StaticSwitchParameter'))),
                           ('StaticComponentMaskParameters', ('arr', ('struct', 'StaticComponentMaskParameter'))),
                           ('TerrainLayerWeightParameters', None), ('MaterialLayersParameters', None)],
    'StaticSwitchParameter': [('Value', 'bool'), ('ParameterInfo', ('struct', 'MaterialParameterInfo')), ('bOverride', 'bool'),
                              ('ExpressionGUID', 'guid')],
    'StaticComponentMaskParameter': [('R', 'bool'), ('G', 'bool'), ('B', 'bool'), ('A', 'bool'),
                                     ('ParameterInfo', ('struct', 'MaterialParameterInfo')), ('bOverride', 'bool'),
                                     ('ExpressionGUID', 'guid')],
    'MaterialTextureInfo': [('SamplingScale', 'f32'), ('UVChannelIndex', 'i32'), ('TextureName', 'name'), ('TextureIndex', 'i32')],
})


def import_id(object_path):
    """FPackageObjectIndex of a package import (4.27 IoStore): CityHash64 of the lower-cased UTF-16 path, '.' and ':'
    as '/', the top two bits the type (2: package import)"""
    s = ''.join('/' if c in '.:' else c.lower() for c in object_path)
    return (2 << 62) | (cityhash64(s.encode('utf-16-le')) & ~(3 << 62))


class Pkg:
    def __init__(self, path):
        self.path = path
        self.d = open(path, 'rb').read()
        self.z = Zen(self.d)
        self.names = self.z.names
        self._ids = {}
        for n in self.names:
            if n.startswith('/') and not n.startswith('/Script/'):
                op = n + '.' + n.rsplit('/', 1)[1]
                self._ids[import_id(op)] = op

    def ref(self, v):
        """an FPackageIndex as an object path (exports by name)"""
        if v == 0:
            return None
        if v > 0:
            return 'export:' + self.z.exports[v - 1]['name']
        g = self.z.imports[-v - 1]
        return self._ids.get(g, 'import:%016x' % g)

    def export(self):
        return self.z.export_bytes(0)


def _fix_refs(pkg, v):
    if isinstance(v, dict):
        return {k: _fix_refs(pkg, x) for k, x in v.items()}
    if isinstance(v, list):
        return [_fix_refs(pkg, x) for x in v]
    return v


def mi(pkg):
    """a material instance's own properties (parent, parameters, overrides, static switches)"""
    b = pkg.export()
    r = R(b)
    uv = Unversioned(pkg.z)
    p = uv.struct(r, 'MaterialInstanceConstant')
    out = {'parent': pkg.ref(p['Parent']), 'props_end': r.p, 'export_size': len(b),
           'static_permutation': bool(p['bHasStaticPermutationResource']),
           'scalars': {}, 'vectors': {}, 'textures': {}, 'switches': {}, 'masks': {}}
    for e in p['ScalarParameterValues'] or []:
        out['scalars'][e['ParameterInfo']['Name']] = e['ParameterValue']
    for e in p['VectorParameterValues'] or []:
        out['vectors'][e['ParameterInfo']['Name']] = list(e['ParameterValue'])
    for e in p['TextureParameterValues'] or []:
        out['textures'][e['ParameterInfo']['Name']] = pkg.ref(e['ParameterValue'])
    bo = p['BasePropertyOverrides'] or {}
    out['overrides'] = {k: v for k, v in bo.items() if not k.startswith('_') and k in bo.get('_present', [])}
    sp = p['StaticParameters'] or {}
    for e in sp.get('StaticSwitchParameters') or []:
        out['switches'][e['ParameterInfo']['Name']] = {'value': bool(e['Value']), 'override': bool(e['bOverride'])}
    for e in sp.get('StaticComponentMaskParameters') or []:
        out['masks'][e['ParameterInfo']['Name']] = [bool(e[c]) for c in 'RGBA']
    out['subsurface_profile'] = pkg.ref(p['SubsurfaceProfile']) if p.get('SubsurfaceProfile') else None
    out['referenced_textures'] = [pkg.ref(x) for x in p['CachedReferencedTextures'] or []]
    out['unknown14'] = p.get('Unknown14')
    return out


# ---------------------------------------------------------------------------------------------------------------------
# inline shader maps
# ---------------------------------------------------------------------------------------------------------------------
def _u32(b, p):
    return struct.unpack_from('<I', b, p)[0]


def find_resources(b):
    """(names start, names end / locations start, data start, [(offset, feature level, quality level)]) or None"""
    n = len(b)
    for L in range(n - 32, 0, -1):
        c = _u32(b, L)
        if not 1 <= c <= 8:
            continue
        q = L + 4
        locs = []
        ok = True
        for k in range(c):
            if q + 6 > n:
                ok = False
                break
            off, fl, ql = struct.unpack_from('<IBB', b, q)
            q += 6
            if fl > 4 or ql > 4 or (k == 0 and off != 0) or (locs and off <= locs[-1][0]):
                ok = False
                break
            locs.append((off, fl, ql))
        if not ok or q + 4 > n:
            continue
        size = _u32(b, q)
        if q + 4 + size != n or (locs and locs[-1][0] >= size):
            continue
        data = q + 4
        # the private name table ends at L: find its start
        for S in range(L - 8, max(0, L - 400000), -1):
            cnt = _u32(b, S)
            if not 0 < cnt < 10000:
                continue
            p = S + 4
            good = True
            for _ in range(cnt):
                if p + 4 > L:
                    good = False
                    break
                ln = struct.unpack_from('<i', b, p)[0]
                if not 0 < ln < 1024 or p + 4 + ln + 4 > L or b[p + 4 + ln - 1] != 0:
                    good = False
                    break
                p += 4 + ln + 4
            if good and p == L:
                return S, L, data, locs
        return None
    return None


def private_names(b, S):
    cnt = _u32(b, S)
    p = S + 4
    out = []
    for _ in range(cnt):
        ln = struct.unpack_from('<i', b, p)[0]
        out.append(b[p + 4:p + 4 + ln - 1].decode('latin-1'))
        p += 4 + ln + 4
    return out


class Frozen:
    def __init__(self, fz):
        self.fz = fz

    def ptr(self, off):
        v = struct.unpack_from('<Q', self.fz, off)[0]
        if not v & 1:
            return None
        o = (v >> 1) & ((1 << 40) - 1)
        if o & (1 << 39):
            o -= 1 << 40
        return off + o

    def arr(self, off):
        return self.ptr(off), struct.unpack_from('<i', self.fz, off + 8)[0]


def parse_resource(b, R0, R1, names):
    p = R0
    cooked, valid = struct.unpack_from('<II', b, p)
    if not valid:
        return {'valid': False}
    ql, fl = struct.unpack_from('<II', b, p + 8)
    id_hash = b[p + 16:p + 36].hex()
    align, flags, size = struct.unpack_from('<III', b, p + 36)
    F0 = p + 48
    fz = b[F0:F0 + size]
    q = F0 + size
    nvt, nsn, nmn = struct.unpack_from('<III', b, q)
    q += 12
    for _ in range(nvt):
        th, num = struct.unpack_from('<QI', b, q)
        q += 12 + 8 * num
    patch = {}
    for _ in range(nsn):
        ni, num, c = struct.unpack_from('<IIi', b, q)
        q += 12
        nm = names[ni] + ('' if num == 0 else '_%d' % (num - 1))
        for k in range(c):
            patch[_u32(b, q)] = nm
            q += 4
    for _ in range(nmn):
        ni, num, c = struct.unpack_from('<IIi', b, q)
        q += 12 + 4 * c
    nt, nv = struct.unpack_from('<ii', b, q)
    q += 8
    types = list(struct.unpack_from('<%dQ' % nt, b, q))
    q += 8 * nt
    vfs = list(struct.unpack_from('<%dQ' % nv, b, q))
    q += 8 * nv
    nd = struct.unpack_from('<i', b, q)[0]
    q += 4 + 32 * nd
    share = _u32(b, q)
    q += 4
    map_hash = b[q:q + 20].hex() if share else None
    res = {'valid': True, 'quality': QUALITY.get(ql, ql), 'feature_level': fl, 'id_hash': id_hash, 'layout': (align, flags),
           'map_hash': map_hash, 'shared': bool(share), 'frozen_at': F0, 'frozen_size': size}
    F = Frozen(fz)
    res['uniform'] = uniform_set(F, fz, patch)
    res['shaders'] = mesh_shaders(F, fz, types, vfs)
    return res


def _pname(patch, off):
    return patch.get(off, '?@%d' % off)


def uniform_set(F, fz, patch):
    base = 112
    vp, nv = F.arr(base + 0)
    sp, ns = F.arr(base + 16)
    spar, nsp = F.arr(base + 32)
    vpar, nvp = F.arr(base + 48)
    tex = {}
    for k, t in enumerate(TEXTURE_TYPES):
        tp, nt = F.arr(base + 64 + 16 * k)
        items = []
        for i in range(nt):
            o = tp + 28 * i
            idx, assoc, ti, ss, vl = struct.unpack_from('<iBxxxiBB', fz, o + 12)
            items.append({'name': _pname(patch, o), 'index': idx, 'association': assoc, 'texture_index': ti,
                          'sampler_source': ss, 'vt_layer': vl})
        tex[t] = items
    srb_p, nsrb = F.arr(base + 144)
    ext_p, next_ = F.arr(base + 160)
    dat, nd = F.arr(base + 176)
    data = fz[dat:dat + nd] if nd else b''
    vt_p, nvt = F.arr(base + 192)
    pc_p, npc = F.arr(base + 208)
    scalars = []
    for i in range(nsp):
        o = spar + 24 * i
        idx, assoc, val = struct.unpack_from('<iBxxxf', fz, o + 12)
        scalars.append({'name': _pname(patch, o), 'index': idx, 'association': assoc, 'default': val})
    vectors = []
    for i in range(nvp):
        o = vpar + 36 * i
        idx, assoc = struct.unpack_from('<iB', fz, o + 12)
        vectors.append({'name': _pname(patch, o), 'index': idx, 'association': assoc,
                        'default': list(struct.unpack_from('<4f', fz, o + 20))})
    pres = {'vectors': [], 'scalars': []}
    for key, (pp, n) in (('vectors', (vp, nv)), ('scalars', (sp, ns))):
        for i in range(n):
            off, size = struct.unpack_from('<II', fz, pp + 8 * i)
            pres[key].append(decode_preshader(data[off:off + size], scalars, vectors))
    collections = [fz[pc_p + 16 * i:pc_p + 16 * i + 16].hex() for i in range(npc)]
    return {'vector_expressions': pres['vectors'], 'scalar_expressions': pres['scalars'], 'scalar_parameters': scalars,
            'vector_parameters': vectors, 'textures': tex, 'num_srb': nsrb, 'num_external': next_, 'num_vt_stacks': nvt,
            'parameter_collections': collections}


def decode_preshader(code, scalars, vectors):
    """a preshader program (4.26/4.27 EMaterialPreshaderOpcode) as an expression tree"""
    st = []
    p = 0
    while p < len(code):
        op = OPS[code[p]]
        p += 1
        if op == 'Nop':
            continue
        if op == 'ConstantZero':
            st.append({'op': 'const', 'value': [0.0, 0.0, 0.0, 0.0]})
        elif op == 'Constant':
            st.append({'op': 'const', 'value': list(struct.unpack_from('<4f', code, p))})
            p += 16
        elif op == 'ScalarParameter':
            i = struct.unpack_from('<H', code, p)[0]
            p += 2
            s = scalars[i]
            st.append({'op': 'sparam', 'name': s['name'], 'default': s['default']})
        elif op == 'VectorParameter':
            i = struct.unpack_from('<H', code, p)[0]
            p += 2
            v = vectors[i]
            st.append({'op': 'vparam', 'name': v['name'], 'default': v['default']})
        elif op in BINARY:
            b_ = st.pop()
            a_ = st.pop()
            st.append({'op': 'binary', 'fn': op, 'a': a_, 'b': b_})
        elif op == 'Clamp':
            c_ = st.pop()
            b_ = st.pop()
            a_ = st.pop()
            st.append({'op': 'clamp', 'x': a_, 'lo': b_, 'hi': c_})
        elif op in ('Dot', 'Cross'):
            vt = code[p]
            p += 1
            b_ = st.pop()
            a_ = st.pop()
            st.append({'op': op.lower(), 'type': vt, 'a': a_, 'b': b_})
        elif op in UNARY:
            st.append({'op': 'unary', 'fn': op, 'x': st.pop()})
        elif op == 'ComponentSwizzle':
            n = code[p]
            idx = list(code[p + 1:p + 5])
            p += 5
            st.append({'op': 'swizzle', 'n': n, 'index': idx, 'x': st.pop()})
        elif op == 'AppendVector':
            na = code[p]
            p += 1
            b_ = st.pop()
            a_ = st.pop()
            st.append({'op': 'append', 'na': na, 'a': a_, 'b': b_})
        elif op in ('TextureSize', 'TexelSize'):
            # FHashedMaterialParameterInfo (name hash u64, index i32, association u8) then the texture index
            nh, idx, assoc = struct.unpack_from('<QiB', code, p)
            p += 13
            ti = struct.unpack_from('<i', code, p)[0]
            p += 4
            st.append({'op': op.lower(), 'name_hash': '%016x' % nh, 'texture_index': ti})
        else:
            raise ValueError('preshader opcode %s not handled' % op)
    if len(st) != 1:
        raise ValueError('preshader left %d values' % len(st))
    return st[0]


def mesh_shaders(F, fz, types, vfs):
    out = []
    for k in range(2 if F.ptr(96) is not None else 0):
        pass
    mp, nmm = F.arr(96)
    for k in range(nmm):
        mm = F.ptr(mp + 8 * k)
        vfh = struct.unpack_from('<Q', fz, mm + 96)[0]
        vf = shader_names427.VF_BY_HASH.get(vfh, '%016x' % vfh)
        tp, n = F.arr(mm + 24)
        sp, _ = F.arr(mm + 56)
        pp, _ = F.arr(mm + 40)
        for i in range(n):
            th = struct.unpack_from('<Q', fz, tp + 8 * i)[0]
            so = F.ptr(sp + 8 * i)
            tgt, ri, ni = struct.unpack_from('<IiI', fz, so + 192)
            perm = struct.unpack_from('<i', fz, pp + 4 * i)[0]
            out.append({'vf': vf, 'type': shader_names427.TYPE_BY_HASH.get(th, '%016x' % th), 'resource': ri,
                        'frequency': tgt & 0xf, 'instructions': ni, 'permutation': perm})
    out.sort(key=lambda s: (s['resource'], s['vf'], s['type']))
    return out


def shader_maps(pkg):
    b = pkg.export()
    found = find_resources(b)
    if found is None:
        return []
    S, L, data, locs = found
    names = private_names(b, S)
    size = _u32(b, data - 4)
    out = []
    for k, (off, fl, ql) in enumerate(locs):
        R0 = data + off
        R1 = data + (locs[k + 1][0] if k + 1 < len(locs) else size)
        res = parse_resource(b, R0, R1, names)
        res['loc'] = {'offset': off, 'feature_level': fl, 'quality': QUALITY.get(ql, ql)}
        out.append(res)
    return out


# ---------------------------------------------------------------------------------------------------------------------
def expr_text(x):
    op = x['op']
    if op == 'const':
        return '(%s)' % ', '.join('%g' % v for v in x['value'])
    if op == 'sparam':
        return '%s' % x['name']
    if op == 'vparam':
        return '%s' % x['name']
    if op == 'binary':
        f = BINARY[x['fn']]
        if len(f) == 1:
            return '(%s %s %s)' % (expr_text(x['a']), f, expr_text(x['b']))
        return '%s(%s, %s)' % (f, expr_text(x['a']), expr_text(x['b']))
    if op == 'unary':
        return '%s(%s)' % (x['fn'].lower(), expr_text(x['x']))
    if op == 'clamp':
        return 'clamp(%s, %s, %s)' % (expr_text(x['x']), expr_text(x['lo']), expr_text(x['hi']))
    if op == 'swizzle':
        return '%s.%s' % (expr_text(x['x']), ''.join('xyzw'[i] for i in x['index'][:x['n']]))
    if op == 'append':
        return 'append%d(%s, %s)' % (x['na'], expr_text(x['a']), expr_text(x['b']))
    if op in ('dot', 'cross'):
        return '%s%d(%s, %s)' % (op, x['type'], expr_text(x['a']), expr_text(x['b']))
    return '%s(%s)' % (op, x.get('texture_index'))


def main():
    cmd = sys.argv[1]
    for path in sys.argv[2:]:
        pkg = Pkg(path)
        if cmd == 'mi':
            print(json.dumps({os.path.basename(path): mi(pkg)}, indent=1))
        elif cmd == 'maps':
            for r in shader_maps(pkg):
                if not r['valid']:
                    print(os.path.basename(path), 'invalid resource')
                    continue
                u = r['uniform']
                print('%s: %s, map %s, %d vector + %d scalar expressions, %d textures' % (
                    os.path.basename(path), r['quality'], r['map_hash'], len(u['vector_expressions']),
                    len(u['scalar_expressions']), sum(len(v) for v in u['textures'].values())))
        elif cmd == 'uniforms':
            r = [x for x in shader_maps(pkg) if x['valid']][-1]
            u = r['uniform']
            for i, e in enumerate(u['vector_expressions']):
                print('cb[%2d]      = %s' % (i, expr_text(e)))
            nv = len(u['vector_expressions'])
            for j, e in enumerate(u['scalar_expressions']):
                print('cb[%2d].%s    = %s' % (nv + j // 4, 'xyzw'[j % 4], expr_text(e)))
            for t, items in u['textures'].items():
                for i, it in enumerate(items):
                    print('%s %d: %s' % (t, i, it['name']))


if __name__ == '__main__':
    main()
