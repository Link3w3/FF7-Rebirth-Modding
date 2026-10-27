"""KH3 material -> End material spec (for build_kh3_shaders.py in the editor).

    python3 kh3matspec.py <KH3 Game root> <material path> [more...]      (prints the spec summary)

Root is the folder holding KH3's Game content (Shader/..., Character/...). KH3 content keeps its path under /Game/KH3
(/Game/X -> /Game/KH3/X).
"""
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, '/work/kh3fx', '/work/kh3bnm/src/rebirth_fx']
import kh3bonamik as k   # noqa: E402
import tagged            # noqa: E402
import kh3mat            # noqa: E402
import kh3uniform        # noqa: E402
import dxbc2hlsl as D    # noqa: E402
import kh3shaders        # noqa: E402
import kh3lit            # noqa: E402

SKIP_PARAMS = ('SelectionColor',)
TRANSLUCENT_OK = False
VF_ORDER = ('TGPUSkinVertexFactoryfalse', 'FLocalVertexFactory', 'TGPUSkinVertexFactorytrue')
BASE_PASS = ('TBasePassPSFNoLightMapPolicy', 'TBasePassPSFNoLightMapPolicySkylight',
             'TBasePassPSFCachedPointIndirectLightingPolicy')
OUTS = {'o0': 'xyz', 'o1': 'xyz', 'o2': 'xyz', 'o3': 'xyz', 'o4': 'xyzw'}


def ue_path(p):
    """/Game/X/y.y -> /Game/KH3/X/y.y; engine content stays."""
    if not p or not p.startswith('/Game/'):
        return p
    return '/Game/KH3/' + p[len('/Game/'):]


class Lib(object):
    def __init__(self, root):
        self.root = root
        self.cache = {}

    def file(self, path):
        pkg = path.split('.', 1)[0]
        assert pkg.startswith('/Game/'), path
        return os.path.join(self.root, *pkg[len('/Game/'):].split('/'))

    def package(self, path):
        pkg = path.split('.', 1)[0]
        if pkg not in self.cache:
            base = self.file(path)
            self.cache[pkg] = k.Package(open(base + '.uasset', 'rb').read(), open(base + '.uexp', 'rb').read())
        return self.cache[pkg]

    def exists(self, path):
        return os.path.exists(self.file(path) + '.uasset')

    def top(self, pk, classes):
        return [e for e in pk.exports if e['outer'] == 0 and pk.class_name(e) in classes][0]

    def props(self, pk, e):
        return tagged.parse(pk.data, e['offset'], e['offset'] + e['size'], pk.names)

    def mpc_by_guid(self):
        """{StateId hex: KH3 path} of every parameter collection under the root."""
        if getattr(self, '_mpcs', None) is None:
            self._mpcs = {}
            for dirpath, _, files in os.walk(self.root):
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
                    props = self.props(pk, tops[0])
                    sid = tagged.find(props, 'StateId')
                    rel = os.path.relpath(base, self.root).replace(os.sep, '/')
                    name = rel.rsplit('/', 1)[-1]
                    self._mpcs[pk.data[sid.value_start:sid.value_start + 16].hex()] = '/Game/%s.%s' % (rel, name)
        return self._mpcs

    def mpc(self, path):
        """(End path, scalar names, vector names) of a parameter collection."""
        pk = self.package(path)
        e = self.top(pk, ('MaterialParameterCollection',))
        props = self.props(pk, e)
        out = []
        for key in ('ScalarParameters', 'VectorParameters'):
            arr = tagged.find(props, key)
            names = []
            for (s, t, refs) in (arr.elements if arr else []):
                ch = tagged.parse(pk.data, s, t, pk.names)
                names.append({c.name: kh3mat._value(pk, c) for c in ch}.get('ParameterName'))
            out.append(names)
        return (ue_path(path), out[0], out[1])

    def texture_params(self, path, out=None, seen=None):
        """{parameter name: default texture} of a material and the functions it calls."""
        out = {} if out is None else out
        seen = set() if seen is None else seen
        if path in seen:
            return out
        seen.add(path)
        try:
            pk = self.package(path)
        except (IOError, OSError):
            return out
        e = self.top(pk, ('Material', 'MaterialFunction', 'MaterialInstanceConstant'))
        tp = self.props(pk, e)
        arr = tagged.find(tp, 'Expressions') or tagged.find(tp, 'FunctionExpressions')
        for a, _, _ in (arr.elements if arr else []):
            v = struct.unpack_from('<i', pk.data, a)[0]
            if v <= 0:
                continue
            ex = pk.exports[v - 1]
            c = pk.class_name(ex)
            if 'Texture' in c:
                p = self.props(pk, ex)
                t = tagged.find(p, 'Texture')
                pn = tagged.find(p, 'ParameterName')
                if pn is not None:
                    out.setdefault(kh3mat._value(pk, pn), kh3mat._value(pk, t) if t else None)
            elif c == 'MaterialExpressionMaterialFunctionCall':
                p = self.props(pk, ex)
                f = tagged.find(p, 'MaterialFunction')
                fn = kh3mat._value(pk, f) if f else None
                if fn and fn.startswith('/Game/'):
                    self.texture_params(fn, out, seen)
        return out


def wanted_base():
    return {(o, c) for o, cs in OUTS.items() for c in cs}


def material_inputs(t, uset, tparams, refs, mpc_inputs, notes):
    inputs = []
    for i in sorted(int(u[2:]) for u in t.used_inputs if u.startswith('UV')):
        inputs.append(dict(name='UV%d' % i, kind='texcoord', index=i))
    for key, kind in (('VC', 'vertexcolor'), ('EA', 'eyeadaptation'), ('WPNO', 'worldpos_noofs')):
        if key in t.used_inputs:
            inputs.append(dict(name='K_' + key, kind=kind))
    params = D.params_of(uset, t.used_cb2)
    for pname in sorted(params):
        if pname in SKIP_PARAMS or pname.startswith('__'):
            continue
        kind, default = params[pname]
        inputs.append(dict(name=D.pname(pname), kind=kind, param=pname,
                           default=list(default) if kind == 'vector' else default))
    for i in sorted(t.used_tex):
        te = uset['textures2d'][i]
        if te[0] == 'texparam':
            pn = te[1]
            tex = refs[te[2]] if te[2] < len(refs) else tparams.get(pn)
            inputs.append(dict(name='Tex%d' % i, kind='textureparam', param=pn, texture=ue_path(tex) if tex else None,
                               sampler_source=te[3]))
        else:
            idx = te[1]
            tex = refs[idx] if idx < len(refs) else None
            if tex is None:
                notes.append('texture #%d (Texture2D_%d) not found' % (idx, i))
            inputs.append(dict(name='Tex%d' % i, kind='texture', texture=ue_path(tex) if tex else None,
                               sampler_source=te[2]))
    seen = set()
    for mi in mpc_inputs:
        if mi['name'] not in seen:
            seen.add(mi['name'])
            inputs.append(mi)
    return inputs


def merge_inputs(*lists):
    out, seen = [], set()
    for lst in lists:
        for i in lst:
            if i['name'] not in seen:
                seen.add(i['name'])
                out.append(i)
    return out


def normal_code(body):
    return '\n'.join(body + ['return normalize(o1.xyz * 2 - 1);'])


def main_code(body, mask_body):
    lines = list(body)
    if mask_body:
        lines.append('float KH3_DEPTHMASK = 1;')
        lines.append('{')
        lines += ['    ' + x for x in mask_body]
        lines.append('    KH3_DEPTHMASK = KH3_MASK;')
        lines.append('}')
        lines.append('KHMask = min(KH3_MASK, KH3_DEPTHMASK);')
    else:
        lines.append('KHMask = KH3_MASK;')
    lines += ['KHMetallic = o2.x;', 'KHSpecular = o2.y;', 'KHRoughness = o2.z;', 'KHEmissive = o0.xyz;',
              'KHSubsurface = o4.xyz * o4.xyz;', 'KHOpacity = o4.w;', 'return o3.xyz;']
    return '\n'.join(lines)


def translucent_code(body, mask_body):
    lines = list(body)
    if mask_body:
        lines.append('float KH3_DEPTHMASK = 1;')
        lines.append('{')
        lines += ['    ' + x for x in mask_body]
        lines.append('    KH3_DEPTHMASK = KH3_MASK;')
        lines.append('}')
        lines.append('KHMask = min(KH3_MASK, KH3_DEPTHMASK);')
    else:
        lines.append('KHMask = KH3_MASK;')
    lines += ['KHOpacity = o0.w * KHMask;', 'return o0.xyz;']
    return '\n'.join(lines)


def refs_in_order(lib, path):
    import texrefs417
    return texrefs417.refs(lib, path)


def refs_in_order_old(lib, path):
    """Unique textures of the material's expressions (and its functions', where the call is), plus parameter
    defaults: KH3's ExpressionTextureReferences order (Texture2D_i of plain textures)."""
    out, seen = [], set()

    def walk(p):
        if p in seen:
            return
        seen.add(p)
        try:
            pk = lib.package(p)
        except (IOError, OSError):
            return
        e = lib.top(pk, ('Material', 'MaterialFunction'))
        tp = lib.props(pk, e)
        arr = tagged.find(tp, 'Expressions') or tagged.find(tp, 'FunctionExpressions')
        for a, _, _ in (arr.elements if arr else []):
            v = struct.unpack_from('<i', pk.data, a)[0]
            if v <= 0:
                continue
            ex = pk.exports[v - 1]
            c = pk.class_name(ex)
            if 'Texture' in c and 'Parameter' not in c:
                pp = lib.props(pk, ex)
                t = tagged.find(pp, 'Texture')
                tex = kh3mat._value(pk, t) if t else None
                if tex and tex not in out:
                    out.append(tex)
            elif 'Texture' in c:
                pp = lib.props(pk, ex)
                t = tagged.find(pp, 'Texture')
                tex = kh3mat._value(pk, t) if t else None
                if tex and tex not in out:
                    out.append(tex)
            elif c == 'MaterialExpressionMaterialFunctionCall':
                pp = lib.props(pk, ex)
                f = tagged.find(pp, 'MaterialFunction')
                fn = kh3mat._value(pk, f) if f else None
                if fn and fn.startswith('/Game/'):
                    walk(fn)
    walk(path)
    return out


def read_info(lib, path):
    base = lib.file(path)
    return kh3mat.read_material(open(base + '.uasset', 'rb').read(), open(base + '.uexp', 'rb').read())


def chain(lib, path):
    """[(path, info)] from the instance up to its root material."""
    out = []
    seen = set()
    while path and path not in seen and path.startswith('/Game/'):
        seen.add(path)
        if not lib.exists(path):
            break
        info = read_info(lib, path)
        out.append((path, info))
        if info['cls'] == 'Material':
            break
        path = info.get('parent')
    return out


def settings_of(lib, root_path, mi_chain=()):
    """The root material's blend / shading / two-sided / clip, with the instances' BasePropertyOverrides."""
    props = read_info(lib, root_path)['props']
    st = dict(blend=props.get('BlendMode', 'BLEND_Opaque'), shading=props.get('ShadingModel', 'MSM_DefaultLit'),
              two_sided=bool(props.get('TwoSided')), clip=props.get('OpacityMaskClipValue', 0.3333),
              skeletal=bool(props.get('bUsedWithSkeletalMesh')), morph=bool(props.get('bUsedWithMorphTargets')),
              cloth=bool(props.get('bUsedWithClothing')), domain=props.get('MaterialDomain', 'MD_Surface'))
    for path, info in reversed(list(mi_chain)):
        bpo = info['props'].get('BasePropertyOverrides') or {}
        if not isinstance(bpo, dict):
            continue
        for key, field in (('BlendMode', 'blend'), ('ShadingModel', 'shading'), ('TwoSided', 'two_sided'),
                           ('OpacityMaskClipValue', 'clip')):
            if bpo.get('bOverride_' + key):
                v = bpo.get(key)
                if key == 'TwoSided':
                    v = bool(v)
                if v is not None:
                    st[field] = v
    return st


def material_spec(lib, path, shader_owner=None, mi_chain=()):
    """Spec of a KH3 Material, or (shader_owner) of a material instance's own static permutation of it."""
    owner = shader_owner or path
    pk = lib.package(owner)
    cls = 'MaterialInstanceConstant' if shader_owner else 'Material'
    e = lib.top(pk, (cls,))
    uset = kh3uniform.read_set(pk, e)
    if uset is None:
        raise kh3lit.TranslateError('no uniform expression set (no shaders)')
    guids = lib.mpc_by_guid()
    mpcs = []
    for g in uset.get('collections', []):
        if g not in guids:
            raise kh3lit.TranslateError('parameter collection %s not found' % g)
        mpcs.append(lib.mpc(guids[g]))
    shs = kh3shaders.shaders(pk)
    notes = []
    bp = None
    for tname in BASE_PASS:
        bp = kh3shaders.pick(shs, tname, VF_ORDER)
        if bp:
            break
    if bp is None:
        raise kh3lit.TranslateError('no base pass pixel shader')
    if not bp.ubs or bp.ubs[0] != 'View':
        raise kh3lit.TranslateError('not compiled by KH3 (a stock UE4 build: uniform buffers %s); a community material'
                                    % bp.ubs)
    translucent = settings_of(lib, path, mi_chain)['blend'] in ('BLEND_Translucent', 'BLEND_Additive', 'BLEND_Modulate')
    wanted = {('o0', c) for c in 'xyzw'} if translucent else wanted_base()
    t, body, minputs, uvs, nkeep, ncode = kh3lit.translate(bp.blob, bp, uset, mpcs, wanted, owner)
    if translucent:
        tn, nbody, nminputs, nkeep_n = None, None, [], 0
    else:
        tn, nbody, nminputs, _, nkeep_n, _ = kh3lit.translate(bp.blob, bp, uset, mpcs, {('o1', c) for c in 'xyz'},
                                                             owner)
    dp = kh3shaders.pick(shs, 'FDepthOnlyPS', (bp.vf,) + VF_ORDER)
    mask_body, td, dminputs = None, None, []
    if dp is not None:
        td, mask_body, dminputs, _, nkeep_d, _ = kh3lit.translate(dp.blob, dp, uset, mpcs, set(), owner)
        if not td.discards:
            mask_body = None
    tparams = lib.texture_params(path)
    refs = refs_in_order(lib, path)
    ins_main = material_inputs(t, uset, tparams, refs, minputs, notes)
    ins_norm = material_inputs(tn, uset, tparams, refs, nminputs, notes) if tn else []
    ins_mask = material_inputs(td, uset, tparams, refs, dminputs, notes) if mask_body else []
    unmapped = sorted(t.unmapped | (tn.unmapped if tn else set()) | (td.unmapped if td else set()))
    if unmapped:
        notes.append('unmapped: %s' % ', '.join(unmapped))
    st = settings_of(lib, path, mi_chain)
    if st['domain'] != 'MD_Surface':
        raise kh3lit.TranslateError('%s material (built separately)' % st['domain'])
    import hashlib
    bh = hashlib.sha1(bp.blob + (dp.blob if dp is not None else b'')).hexdigest()[:8]
    spec = dict(kh3=path, path=ue_path(path), cls='Material', vf=bp.vf, shader=bp.type, translucent=translucent,
                blob_hash=bh,
                main=dict(code=(translucent_code if translucent else main_code)(body, mask_body),
                          inputs=merge_inputs(ins_main, ins_mask)),
                normal=dict(code=normal_code(nbody), inputs=ins_norm) if nbody else None,
                mpcs=[m[0] for m in mpcs], notes=notes,
                stats=dict(base_kept=nkeep, base_total=ncode, normal_kept=nkeep_n,
                           mask=bool(mask_body), discards=(td.discards if td else 0)))
    spec.update(st)
    return spec


def code_hash(spec):
    """The permutation's identity: KH3's own compiled base pass and depth pass (stable whatever the translator does)."""
    if spec.get('blob_hash'):
        return spec['blob_hash']
    import hashlib
    h = hashlib.sha1()
    for part in ('main', 'normal'):
        if not spec.get(part):
            continue
        h.update(spec[part]['code'].encode())
        h.update(json.dumps([(i['name'], i['kind'], i.get('param')) for i in spec[part]['inputs']]).encode())
    for key in ('blend', 'shading', 'two_sided'):
        h.update(str(spec[key]).encode())
    return h.hexdigest()[:8]


def merged_values(mi_chain):
    """Scalars / vectors / textures of an instance chain, the instance's own winning."""
    sc, vc, tx = {}, {}, {}
    for path, info in reversed([c for c in mi_chain if c[1]['cls'] == 'MaterialInstanceConstant']):
        sc.update(info['scalars'])
        vc.update(info['vectors'])
        tx.update(info['textures'])
    return sc, vc, tx


def instance_spec(path, parent_end, values):
    sc, vc, tx = values
    return dict(kh3=path, path=ue_path(path), cls='MaterialInstanceConstant', parent=parent_end,
                scalars={n: v for n, v in sc.items() if n not in SKIP_PARAMS and not str(n).startswith('__')},
                vectors={n: v for n, v in vc.items() if n not in SKIP_PARAMS and not str(n).startswith('__')},
                textures={n: ue_path(v) for n, v in tx.items() if n not in SKIP_PARAMS})


def all_specs(lib, classes, only=None):
    """Specs for every Material and MaterialInstanceConstant (materials first, permutation materials of instances
    with their own static permutation, then instances parents first)."""
    mats = sorted('/Game/%s.%s' % (rel, rel.rsplit('/', 1)[-1]) for rel, c in classes.items() if c == 'Material')
    mis = sorted('/Game/%s.%s' % (rel, rel.rsplit('/', 1)[-1]) for rel, c in classes.items()
                 if c == 'MaterialInstanceConstant')
    if only:
        mats = [m for m in mats if any(o in m for o in only)]
        mis = [m for m in mis if any(o in m for o in only)]
    specs, errors, hashes = [], {}, {}
    by_path = {}
    for m in mats:
        try:
            sp = material_spec(lib, m)
            sp['hash'] = code_hash(sp)
            specs.append(sp)
            by_path[m] = sp
            hashes[(m, sp['hash'])] = sp['path']
        except Exception as ex:
            errors[m] = '%s: %s' % (type(ex).__name__, str(ex)[:300])
    perm_of = {}
    for mi in mis:
        ch = chain(lib, mi)
        if not ch or ch[-1][1]['cls'] != 'Material':
            errors[mi] = 'parent chain does not reach a material (%s)' % (ch[-1][1].get('parent') if ch else None)
            continue
        root = ch[-1][0]
        pk = lib.package(mi)
        own = bool(kh3shaders.shaders(pk))
        if not own:
            continue
        try:
            sp = material_spec(lib, root, shader_owner=mi, mi_chain=ch[:-1])
        except Exception as ex:
            errors[mi] = 'own permutation: %s: %s' % (type(ex).__name__, str(ex)[:300])
            continue
        hsh = code_hash(sp)
        key = (root, hsh)
        if key in hashes:
            perm_of[mi] = hashes[key]
            continue
        base = ue_path(root)
        pkg, obj = base.split('.', 1)
        sp['path'] = '%s_P%s.%s_P%s' % (pkg, hsh, obj, hsh)
        sp['hash'] = hsh
        sp['permutation_of'] = root
        sp['first_instance'] = mi
        specs.append(sp)
        hashes[key] = sp['path']
        perm_of[mi] = sp['path']
    done = set(by_path)
    pending = list(mis)
    order = []
    while pending:
        progressed = False
        for mi in list(pending):
            ch = chain(lib, mi)
            if not ch or ch[-1][1]['cls'] != 'Material':
                pending.remove(mi)
                continue
            if mi in perm_of:
                order.append((mi, perm_of[mi], merged_values(ch)))
                pending.remove(mi)
                done.add(mi)
                progressed = True
                continue
            parent = ch[0][1].get('parent')
            if parent in done or parent not in mis:
                own_vals = ch[0][1]
                order.append((mi, ue_path(parent), (own_vals['scalars'], own_vals['vectors'], own_vals['textures'])))
                pending.remove(mi)
                done.add(mi)
                progressed = True
        if not progressed:
            for mi in pending:
                errors[mi] = 'parent not built'
            break
    for mi, parent_end, vals in order:
        specs.append(instance_spec(mi, parent_end, vals))
    return specs, errors


if __name__ == '__main__':
    root = sys.argv[1]
    classes = json.load(open(sys.argv[2]))
    out = sys.argv[3]
    only = sys.argv[4].split(',') if len(sys.argv) > 4 else None
    lib = Lib(root)
    specs, errors = all_specs(lib, classes, only)
    json.dump(dict(specs=specs, errors=errors), open(out, 'w'), indent=1)
    nm = sum(1 for x in specs if x['cls'] == 'Material')
    print('materials', nm, '(permutations %d)' % sum(1 for x in specs if x.get('permutation_of')),
          'instances', len(specs) - nm, 'errors', len(errors))
    for p_, e_ in sorted(errors.items()):
        print('ERR', p_, e_)
    for x in specs:
        if x.get('notes'):
            print('NOTE', x['path'], x['notes'][:3])
