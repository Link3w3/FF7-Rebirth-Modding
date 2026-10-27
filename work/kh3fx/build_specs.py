"""KH3 materials -> build specs for the End editor (build_materials.py): each KH3 Material becomes an End material
whose Custom node runs KH3's own pixel shader code (dxbc2hlsl), each KH3 material instance an End instance with
KH3's values. KH3 content keeps its path under /Game/KH3 (/Game/Effects/X -> /Game/KH3/Effects/X).

    python3 build_specs.py <folder with KH3's Effects/...> <materials.json> <out specs.json>
"""
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, '/work/kh3bnm/src/rebirth_fx']
import kh3bonamik as k   # noqa: E402
import tagged            # noqa: E402
import kh3mat            # noqa: E402
import kh3pick
import kh3shaders           # noqa: E402
import kh3uniform        # noqa: E402
import dxbc2hlsl         # noqa: E402

TEX_EXPRS = ('MaterialExpressionTextureSample', 'MaterialExpressionTextureSampleParameter2D',
             'MaterialExpressionTextureObject', 'MaterialExpressionTextureObjectParameter',
             'MaterialExpressionTextureSampleParameterSubUV', 'MaterialExpressionParticleSubUV',
             'MaterialExpressionTextureSampleParameter', 'MaterialExpressionAntialiasedTextureMask')
SKIP_PARAMS = ('SelectionColor',)


def ue_path(kh3_path):
    """/Game/Effects/a/b.b -> /Game/KH3/Effects/a/b.b (object name kept)"""
    pkg, obj = kh3_path.split('.', 1)
    assert pkg.startswith('/Game/Effects/'), kh3_path
    return '/Game/KH3/Effects/%s/%s.%s' % ('/'.join(pkg[len('/Game/Effects/'):].split('/')[:-1]), obj, obj)


class Lib(object):
    def __init__(self, root):
        self.root = root
        self.cache = {}

    def package(self, path):
        pkg = path.split('.', 1)[0]
        if pkg not in self.cache:
            base = os.path.join(self.root, *pkg[len('/Game/'):].split('/'))
            self.cache[pkg] = k.Package(open(base + '.uasset', 'rb').read(), open(base + '.uexp', 'rb').read())
        return self.cache[pkg]

    def props(self, pk, export):
        return tagged.parse(pk.data, export['offset'], export['offset'] + export['size'], pk.names)

    def mpc_by_guid(self):
        """{StateId hex: KH3 path} of every parameter collection under root/Shader (KH3's are in Shader/*_set)."""
        if getattr(self, '_mpcs', None) is None:
            self._mpcs = {}
            for dirpath, _, files in os.walk(os.path.join(self.root, 'Shader')):
                for f in files:
                    if not f.endswith('.uasset'):
                        continue
                    base = os.path.join(dirpath, f[:-7])
                    try:
                        pk = k.Package(open(base + '.uasset', 'rb').read(), open(base + '.uexp', 'rb').read())
                    except Exception:
                        continue
                    tops = [e for e in pk.exports if e['outer'] == 0 and pk.class_name(e) == 'MaterialParameterCollection']
                    if not tops:
                        continue
                    sid = tagged.find(self.props(pk, tops[0]), 'StateId')
                    rel = os.path.relpath(base, self.root).replace(os.sep, '/')
                    self._mpcs[pk.data[sid.value_start:sid.value_start + 16].hex()] = '/Game/%s.%s' % (rel, rel.rsplit('/', 1)[-1])
        return self._mpcs

    def mpc(self, path):
        """(End path, scalar names, vector names) of a parameter collection."""
        pk = self.package(path)
        e = [x for x in pk.exports if x['outer'] == 0 and pk.class_name(x) == 'MaterialParameterCollection'][0]
        props = self.props(pk, e)
        out = []
        for key in ('ScalarParameters', 'VectorParameters'):
            arr = tagged.find(props, key)
            names = []
            for (s0, t0, refs) in (arr.elements if arr else []):
                ch = tagged.parse(pk.data, s0, t0, pk.names)
                names.append({c.name: kh3mat._value(pk, c) for c in ch}.get('ParameterName'))
            out.append(names)
        return ('/Game/KH3/' + path[len('/Game/'):], out[0], out[1])

    def texture_refs(self, path, out=None, params=None, seen=None):
        """The material's ExpressionTextureReferences order: unique textures of its expressions in order, a
        function call's textures where the call is; and every texture parameter's default."""
        out = [] if out is None else out
        params = {} if params is None else params
        seen = set() if seen is None else seen
        if path in seen:
            return out, params
        seen.add(path)
        pk = self.package(path)
        top = [e for e in pk.exports if e['outer'] == 0 and pk.class_name(e) in ('Material', 'MaterialFunction')][0]
        tp = self.props(pk, top)
        arr = tagged.find(tp, 'Expressions') or tagged.find(tp, 'FunctionExpressions')
        if arr is None:
            return out, params
        for a, _, _ in arr.elements:
            v = struct.unpack_from('<i', pk.data, a)[0]
            if v <= 0:
                continue
            e = pk.exports[v - 1]
            c = pk.class_name(e)
            if c in TEX_EXPRS:
                p = self.props(pk, e)
                t = tagged.find(p, 'Texture')
                tex = kh3mat._value(pk, t) if t else None
                if tex and tex not in out:
                    out.append(tex)
                pn = tagged.find(p, 'ParameterName')
                if pn is not None:
                    params.setdefault(kh3mat._value(pk, pn), tex)
            elif c == 'MaterialExpressionMaterialFunctionCall':
                p = self.props(pk, e)
                f = tagged.find(p, 'MaterialFunction')
                fn = kh3mat._value(pk, f) if f else None
                if fn and fn.startswith('/Game/'):
                    try:
                        self.texture_refs(fn, out, params, seen)
                    except (IOError, OSError):
                        pass
        return out, params


def material_spec(lib, kh3_path, info):
    pk = lib.package(kh3_path)
    e = [x for x in pk.exports if pk.class_name(x) == 'Material' and x['outer'] == 0][0]
    uset = kh3uniform.read_set(pk, e)
    vf, b = kh3pick.pick(pk)
    # the shader's own uniform buffer slots and texture slots (the slots are not the same in every shader: a sprite
    # shader has SpriteVF at b2 and the Material buffer at b3, a lit one PrecomputedLightingBuffer at b2)
    sh = [x for x in kh3shaders.shaders(pk) if x.offset == b['offset']]
    if len(sh) != 1:
        raise dxbc2hlsl.TranslateError('%s: the picked shader is not in the shader list' % kh3_path)
    guids = lib.mpc_by_guid() if uset.get('collections') else {}
    mpcs = []
    for g in uset.get('collections', []):
        if g not in guids:
            raise dxbc2hlsl.TranslateError('parameter collection %s not found under Shader' % g)
        mpcs.append(lib.mpc(guids[g]))
    tr = dxbc2hlsl.translate(b['blob'], vf, uset, kh3_path.split('.')[-1], ubs=sh[0].ubs, texmap=sh[0].textures, mpcs=mpcs)
    refs, tparams = lib.texture_refs(kh3_path)
    inputs = []
    for name, kind, extra in (('UV0', 'texcoord', 0), ('UV1', 'texcoord', 1)):
        if name in tr['inputs']:
            inputs.append(dict(name=name, kind=kind, index=extra))
    for key, kind in (('VC', 'vertexcolor'), ('PC', 'particlecolor'), ('DP', 'dynamicparameter'),
                      ('DEPTH', 'scenedepth'), ('PT', 'particletime'), ('PPOS', 'particleposition')):
        if key in tr['inputs']:
            inputs.append(dict(name='K_' + key, kind=kind))
    inputs += tr.get('mpc_inputs', [])
    params = dxbc2hlsl.params_of(uset, tr['cb2'])
    for pname in sorted(params):
        if pname in SKIP_PARAMS:
            continue
        kind, default = params[pname]
        inputs.append(dict(name=dxbc2hlsl.pname(pname), kind=kind, param=pname,
                           default=list(default) if kind == 'vector' else default))
    problems = []
    for i in tr['textures']:
        te = uset['textures2d'][i]
        if te[0] == 'texparam':
            pn, idx = te[1], te[2]
            tex = tparams.get(pn)
            if idx < len(refs) and refs[idx] != tex:
                problems.append('texture parameter %s: #%d is %s in the reference order, its default is %s'
                                % (pn, idx, refs[idx], tex))
            inputs.append(dict(name='Tex%d' % i, kind='textureparam', param=pn, texture=ue_path(tex) if tex else None))
        else:
            idx = te[1]
            tex = refs[idx] if idx < len(refs) else None
            if tex is None:
                problems.append('texture #%d not found' % idx)
            inputs.append(dict(name='Tex%d' % i, kind='texture', texture=ue_path(tex) if tex else None))
    props = info['props']
    code = tr['code'].replace('P_SelectionColor', 'float4(0, 0, 0, 0)')
    rev = bool(props.get('SQEXEnableEmissiveRevEyeAdaptation')) or bool(tr.get('lit'))
    if rev:
        inputs.append(dict(name='K_EA', kind='eyeadaptation'))
        lines = code.rstrip().split('\n')
        last = lines[-1]
        assert last.startswith('return float4(')
        inner = last[len('return float4('):-2]
        em, op = inner.rsplit(', ', 1)
        lines[-1] = 'return float4((%s) / K_EA, %s);' % (em, op)
        code = '\n'.join(lines)
    if tr.get('lit'):
        props = dict(props, BlendMode=props.get('BlendMode', 'BLEND_Opaque'))
    return dict(kh3=kh3_path, path=ue_path(kh3_path), cls='Material', vf=vf, code=code, inputs=inputs, lit=bool(tr.get('lit')),
                blend=props.get('BlendMode', 'BLEND_Opaque'), two_sided=bool(props.get('TwoSided')),
                sprites=bool(props.get('bUsedWithParticleSprites')), meshes=bool(props.get('bUsedWithMeshParticles')),
                beams=bool(props.get('bUsedWithBeamTrails')), notes=tr['notes'] + problems, ninstr=tr['ninstr'])


def instance_spec(kh3_path, info):
    overrides = {}
    bpo = info['props'].get('BasePropertyOverrides') or {}
    for key in ('BlendMode', 'TwoSided', 'ShadingModel', 'OpacityMaskClipValue'):
        if bpo.get('bOverride_' + key):
            overrides[key] = bpo.get(key, True if key == 'TwoSided' else None)
    tex = {}
    for n, v in info['textures'].items():
        if n not in SKIP_PARAMS:
            tex[n] = ue_path(v) if v and v.startswith('/Game/Effects/') else v
    return dict(kh3=kh3_path, path=ue_path(kh3_path), cls='MaterialInstanceConstant',
                parent=ue_path(info['parent']) if info.get('parent', '').startswith('/Game/Effects/') else info.get('parent'),
                scalars={n: v for n, v in info['scalars'].items() if n not in SKIP_PARAMS},
                vectors={n: v for n, v in info['vectors'].items() if n not in SKIP_PARAMS},
                textures=tex, overrides=overrides)


if __name__ == '__main__':
    root, mats_json, out = sys.argv[1], sys.argv[2], sys.argv[3]
    mats = json.load(open(mats_json))
    lib = Lib(root)
    specs, errors = [], {}
    for p in sorted(mats):
        v = mats[p]
        if v.get('cls') != 'Material':
            continue
        try:
            specs.append(material_spec(lib, p, v))
        except Exception as ex:
            errors[p] = str(ex)
    # instances, parents first
    done = {s['kh3'] for s in specs}
    inst = {p: v for p, v in mats.items() if v.get('cls') == 'MaterialInstanceConstant'}
    while inst:
        ready = [p for p, v in inst.items() if v.get('parent') in done or v.get('parent') not in inst]
        if not ready:
            errors.update({p: 'parent chain not resolved' for p in inst})
            break
        for p in sorted(ready):
            specs.append(instance_spec(p, inst.pop(p)))
            done.add(p)
    json.dump(dict(specs=specs, errors=errors), open(out, 'w'), indent=1)
    nm = sum(1 for s in specs if s['cls'] == 'Material')
    print('materials', nm, 'instances', len(specs) - nm, 'errors', len(errors))
    for p, e in errors.items():
        print('ERR', p, e)
    for s in specs:
        if s.get('notes'):
            print('NOTE', s['path'], s['notes'])
