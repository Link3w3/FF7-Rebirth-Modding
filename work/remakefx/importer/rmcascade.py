"""FINAL FANTASY VII REMAKE Cascade particle systems -> End editor (UE 4.26) packages the End editor opens and converts to
Niagara, and a sidecar JSON with what Cascade cannot carry for the game (each emitter's Remake material and its
parameters, its mesh, the effect's socket). The Remake Importer's effect converter, step 1.

Remake cooks its effects unversioned (no property tags) with Square Enix's own fields and lookup tables in place of most
distribution objects; the End editor has the same classes (its reflection comes from the game), so each object is
written again as tagged properties of the End editor's schema (end_fx_schema.json), with:
  - every distribution (a constant, a curve's lookup table, a random range) made a distribution object the editor's
    Cascade and Epic's Cascade To Niagara Converter read (DistributionFloatConstant, ...ConstantCurve, ...Uniform, ...);
  - Square Enix's own modules (lights, camera shakes, loop times) and fields (m_*) left out, noted in the sidecar;
  - GPU emitters made CPU emitters (the game's converted effects run on the CPU), beam and trail emitters left out;
  - an emitter's own placement (m_EndParticleModuleRequired location and rotation) as its Emitter Origin and Rotation;
  - a mesh emitter's mesh a stand-in (/Engine/BasicShapes/Plane): the sidecar names Remake's, the game has them;
  - a material parameter that moves over the particle's life (a UV offset curve) as a Dynamic Parameter module, so the
    Niagara emitter keeps the curve (Particles.DynamicMaterialParameter) for the game's per-particle material inputs.

    rmcascade.py <Remake .uasset (.uexp next to it)> <out .uasset> <out sidecar .json> [package path]
"""
import json
import os
import struct
import sys
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
RK418 = os.path.join(HERE, 'rk418')
if not os.path.isdir(RK418):
    RK418 = '/data/uploads/FF7R2UProj/Tools/RemakeImporter/rk418'      # (the cloud copy)
if RK418 not in sys.path:
    sys.path.insert(0, RK418)
import edpkg                                  # noqa: E402
import tagw                                   # noqa: E402
from tagw import Name, Enum, Obj              # noqa: E402

PARTICLE_SYSTEM_CUSTOM_VERSION = (struct.pack('<IIII', 0x4A56EB40, 0x10F511DC, 0x92D3347E, 0xB2C96AE7), 2)
RF_PUBLIC, RF_STANDALONE, RF_TRANSACTIONAL = 0x1, 0x2, 0x8
STAND_IN_MESH = '/Engine/BasicShapes/Plane.Plane'
DROP_TYPEDATA = ('EndParticleModuleTypeDataBeam', 'EndParticleModuleTypeDataTrail', 'ParticleModuleTypeDataBeam2',
                 'ParticleModuleTypeDataRibbon', 'ParticleModuleTypeDataAnimTrail', 'EndParticleModuleTypeDataEmitter')
CPU_TYPEDATA = ('EndParticleModuleTypeDataGpu', 'ParticleModuleTypeDataGpu')
LOCK = {'EDVLF_None': 0, 'EDVLF_XY': 1, 'EDVLF_XZ': 2, 'EDVLF_YZ': 3, 'EDVLF_XYZ': 4}
LOCK_NAMES = {v: k for k, v in LOCK.items()}


def load_schema():
    return json.load(open(os.path.join(HERE, 'end_fx_schema.json')))


# ---------------------------------------------------------------------------------------------------------------------
# Remake's values as plain Python

def plain(v):
    import uprops
    if not isinstance(v, uprops.V):
        return v
    if v.zero:
        return {'struct': {}, 'array': [], 'set': [], 'obj': None, 'name': Name('None'), 'str': '', 'map': []}.get(v.kind, 0)
    k = v.kind
    if k == 'struct':
        return {n: plain(x) for n, x in v.value.items()}
    if k in ('array', 'set'):
        return [plain(x) for x in v.value]
    if k == 'map':
        return [(plain(a), plain(b)) for a, b in v.value]
    if k == 'obj':
        return Obj(v.value) if v.value else None
    if k == 'name':
        return Name(v.value)
    if k == 'enum':
        return Enum(v.value)
    if k == 'native':
        if isinstance(v.value, dict):
            return {n: plain(x) for n, x in v.value.items()}
        return v.value
    return v.value


def vec(v):
    if isinstance(v, dict):
        return [float(v.get('X', 0) or 0), float(v.get('Y', 0) or 0), float(v.get('Z', 0) or 0)]
    if isinstance(v, (int, float)):
        return [float(v)] * 3
    return [0.0, 0.0, 0.0]


def V3(x):
    return {'X': x[0], 'Y': x[1], 'Z': x[2]}


def lock(x, flag):
    x = list(x)
    if flag == 1:
        x[1] = x[0]
    elif flag == 2:
        x[2] = x[0]
    elif flag == 3:
        x[2] = x[1]
    elif flag == 4:
        x[1] = x[2] = x[0]
    return x


def simplify(times, values, tol):
    """Ramer-Douglas-Peucker on a sampled curve (values: list of tuples): the sample indices to keep"""
    n = len(times)
    if n <= 2:
        return list(range(n))
    keep = {0, n - 1}
    stack = [(0, n - 1)]
    while stack:
        a, b = stack.pop()
        best, at = 0.0, None
        ta, tb = times[a], times[b]
        for i in range(a + 1, b):
            f = 0.0 if tb == ta else (times[i] - ta) / (tb - ta)
            err = max(abs(values[i][c] - (values[a][c] + (values[b][c] - values[a][c]) * f)) for c in range(len(values[i])))
            if err > best:
                best, at = err, i
        if at is not None and best > tol:
            keep.add(at)
            stack += [(a, at), (at, b)]
    return sorted(keep)


class Converter(object):
    def __init__(self, path, schema=None):
        import pkg418, uprops
        from schema import Schema
        self.pkg = pkg418.Package(path)
        rs = Schema(os.path.join(RK418, 'remake_schema.json'))
        self.ex = []
        for i, e in enumerate(self.pkg.exports):
            cls, v, end = uprops.read_export(rs, self.pkg, i)
            self.ex.append((cls, plain(v)))
        self.schema = schema or load_schema()
        self.notes = []
        self.sidecar = {'emitters': {}, 'dropped': [], 'notes': self.notes}
        self.out = []              # dict(key, cls, outer, name, props, flags, is_asset)
        self.by_key = {}
        self.counters = {}

    # -- source graph ----------------------------------------------------------------------------------------------
    def cls(self, ref):
        return self.ex[ref.key - 1][0] if isinstance(ref, Obj) and ref.key > 0 else None

    def props(self, ref):
        return self.ex[ref.key - 1][1] if isinstance(ref, Obj) and ref.key > 0 else {}

    def name(self, ref):
        return self.pkg.exports[ref.key - 1]['name']

    def import_path(self, ref):
        return self.pkg.import_path(ref.key) if isinstance(ref, Obj) and ref.key < 0 else None

    def known(self, cls):
        return cls in self.schema['structs']

    # -- output ----------------------------------------------------------------------------------------------------
    def add(self, key, cls, outer, name, props, flags=RF_TRANSACTIONAL, is_asset=False):
        if cls.startswith('DistributionFloat'):
            props.pop('bIsDirty', None)            # (a float distribution's is not a property in 4.26)
        rec = dict(key=key, cls=cls, outer=outer, name=name, props=props, flags=flags, is_asset=is_asset)
        self.out.append(rec)
        self.by_key[key] = rec
        return Obj(('out', key))

    def new_name(self, cls):
        n = self.counters.get(cls, 0)
        self.counters[cls] = n + 1
        return '%s_%d' % (cls, n)

    # -- distributions ---------------------------------------------------------------------------------------------
    def distribution(self, raw, kind, outer_key, what):
        """a RawDistributionFloat/Vector of Remake's -> the End editor's (with a distribution object)"""
        raw = raw if isinstance(raw, dict) else {}
        d = raw.get('Distribution')
        if isinstance(d, Obj) and d.key > 0:
            key = ('src', d.key)
            if key not in self.by_key:
                self.convert_distribution_object(d, outer_key)
            out = {'Distribution': Obj(('out', key))}
        else:
            cls, p = self.distribution_from_table(raw, kind, what)
            key = ('new', len(self.out), cls)
            self.add(key, cls, outer_key, self.new_name(cls), p)
            out = {'Distribution': Obj(('out', key))}
        for k in ('MinValue', 'MaxValue'):
            if isinstance(raw.get(k), (int, float)):
                out[k] = float(raw[k])
        for k in ('MinValueVec', 'MaxValueVec'):
            if isinstance(raw.get(k), dict):
                out[k] = V3(vec(raw[k]))
        return out

    def convert_distribution_object(self, ref, outer_key):
        cls, p = self.cls(ref), dict(self.props(ref))
        stock = {'EndEffectLinearVector': 'DistributionVectorConstantCurve', 'EndEffectNoiseVector': 'DistributionVectorConstantCurve',
                 'EndEffectSinCosFloat': 'DistributionFloatConstantCurve', 'EndEffectNoiseFloat': 'DistributionFloatConstantCurve',
                 'VfxDistributionFloatNonUniform': 'DistributionFloatUniform'}.get(cls, cls)
        if stock != cls:
            self.notes.append('%s %s: Square Enix distribution taken as a plain %s' % (cls, self.name(ref), stock))
            fields = self.schema['structs'].get(stock, {}).get('props', [])
            own = set(n for n, d, t in self.schema['structs'].get(cls, {}).get('props', []))
            p = {k: v for k, v in p.items() if k not in own}
        p['bIsDirty'] = True
        outer = ('src', self.pkg.exports[ref.key - 1]['outer']) if self.pkg.exports[ref.key - 1]['outer'] > 0 else outer_key
        if outer not in self.by_key and outer != outer_key:
            outer = outer_key
        self.add(('src', ref.key), stock, outer, self.name(ref), p)

    def distribution_from_table(self, raw, kind, what):
        t = raw.get('Table') if isinstance(raw.get('Table'), dict) else {}
        op = int(t.get('Op', 0) or 0)
        n = int(t.get('EntryCount', 0) or 0)
        stride = int(t.get('EntryStride', 0) or 0)
        sub = int(t.get('SubEntryStride', 0) or 0)
        scale = float(t.get('TimeScale', 0) or 0)
        bias = float(t.get('TimeBias', 0) or 0)
        vals = [float(x) for x in (t.get('Values') or [])]
        flag = int(t.get('LockFlag', 0) or 0)
        comps = 1 if kind == 'float' else 3
        vfx_lock = LOCK.get(str(raw.get('m_VfxLockedAxes') or 'EDVLF_None'), 0)
        if op == 0 or n == 0:
            # Square Enix's constant: m_VfxValue (the cooked table is not used then)
            v = raw.get('m_VfxValue', 0)
            if kind == 'float':
                return 'DistributionFloatConstant', {'Constant': float(v or 0.0), 'bIsDirty': True}
            x = lock(vec(v), vfx_lock or flag)
            return 'DistributionVectorConstant', {'Constant': V3(x), 'bIsDirty': True}
        times = [bias + (i / scale if scale else 0.0) for i in range(n)]
        if op == 1:
            entries = [tuple(vals[i * stride:i * stride + comps]) for i in range(n)]
            if kind != 'float':
                entries = [tuple(lock(e, flag)) for e in entries]
            if n == 1:
                if kind == 'float':
                    return 'DistributionFloatConstant', {'Constant': entries[0][0], 'bIsDirty': True}
                return 'DistributionVectorConstant', {'Constant': V3(entries[0]), 'bIsDirty': True}
            span = max(max(e) for e in entries) - min(min(e) for e in entries)
            keep = simplify(times, entries, max(span * 0.004, 1e-6))
            if kind == 'float':
                pts = [{'InVal': times[i], 'OutVal': entries[i][0], 'ArriveTangent': 0.0, 'LeaveTangent': 0.0,
                        'InterpMode': Enum('CIM_Linear')} for i in keep]
                return 'DistributionFloatConstantCurve', {'ConstantCurve': {'Points': pts}, 'bIsDirty': True}
            pts = [{'InVal': times[i], 'OutVal': V3(entries[i]), 'ArriveTangent': V3([0, 0, 0]), 'LeaveTangent': V3([0, 0, 0]),
                    'InterpMode': Enum('CIM_Linear')} for i in keep]
            return 'DistributionVectorConstantCurve', {'ConstantCurve': {'Points': pts}, 'bIsDirty': True}
        if op in (2, 3):
            sub = sub or comps
            pairs_ = [(tuple(vals[i * stride:i * stride + comps]), tuple(vals[i * stride + sub:i * stride + sub + comps])) for i in range(n)]
            if kind != 'float':
                pairs_ = [(tuple(lock(a, flag)), tuple(lock(b, flag))) for a, b in pairs_]
            if n == 1:
                a, b = pairs_[0]
                if kind == 'float':
                    return 'DistributionFloatUniform', {'Min': a[0], 'Max': b[0], 'bIsDirty': True}
                return 'DistributionVectorUniform', {'Min': V3(a), 'Max': V3(b), 'bIsDirty': True, 'bUseExtremes': op == 3}
            flat = [a + b for a, b in pairs_]
            span = max(max(e) for e in flat) - min(min(e) for e in flat)
            keep = simplify(times, flat, max(span * 0.004, 1e-6))
            if kind == 'float':
                pts = [{'InVal': times[i], 'OutVal': {'X': pairs_[i][0][0], 'Y': pairs_[i][1][0]}, 'ArriveTangent': {'X': 0, 'Y': 0},
                        'LeaveTangent': {'X': 0, 'Y': 0}, 'InterpMode': Enum('CIM_Linear')} for i in keep]
                return 'DistributionFloatUniformCurve', {'ConstantCurve': {'Points': pts}, 'bIsDirty': True}
            pts = [{'InVal': times[i], 'OutVal': {'v1': V3(pairs_[i][0]), 'v2': V3(pairs_[i][1])},
                    'ArriveTangent': {'v1': V3([0, 0, 0]), 'v2': V3([0, 0, 0])}, 'LeaveTangent': {'v1': V3([0, 0, 0]), 'v2': V3([0, 0, 0])},
                    'InterpMode': Enum('CIM_Linear')} for i in keep]
            return 'DistributionVectorUniformCurve', {'ConstantCurve': {'Points': pts}, 'bIsDirty': True, 'bUseExtremes': op == 3}
        self.notes.append('%s: distribution table op %d taken as its first value' % (what, op))
        if kind == 'float':
            return 'DistributionFloatConstant', {'Constant': vals[0] if vals else 0.0, 'bIsDirty': True}
        return 'DistributionVectorConstant', {'Constant': V3(vals[:3] + [0.0] * (3 - len(vals[:3]))), 'bIsDirty': True}

    def sample(self, raw, kind, times):
        """values of a Remake raw distribution at times (for the sidecar): constant, its curve, or the middle of its range"""
        raw = raw if isinstance(raw, dict) else {}
        d = raw.get('Distribution')
        comps = 1 if kind == 'float' else 3
        if isinstance(d, Obj) and d.key > 0:
            p = self.props(d)
            curve = (p.get('ConstantCurve') or {}).get('Points') or []
            if curve:
                ins = [float(x.get('InVal', 0) or 0) for x in curve]
                outs = [(vec(x.get('OutVal')) if comps == 3 else [float(x.get('OutVal', 0) or 0)]) for x in curve]
                res = []
                for t in times:
                    if t <= ins[0]:
                        res.append(outs[0])
                    elif t >= ins[-1]:
                        res.append(outs[-1])
                    else:
                        j = max(k for k in range(len(ins)) if ins[k] <= t)
                        f = (t - ins[j]) / ((ins[j + 1] - ins[j]) or 1)
                        res.append([outs[j][c] + (outs[j + 1][c] - outs[j][c]) * f for c in range(comps)])
                return res
            if 'Constant' in p:
                c = vec(p['Constant']) if comps == 3 else [float(p['Constant'] or 0)]
                return [c for _ in times]
        cls, p = self.distribution_from_table(raw, kind, 'sample')
        if cls.endswith('Constant'):
            c = vec(p['Constant']) if comps == 3 else [float(p['Constant'])]
            return [c for _ in times]
        if cls.endswith('ConstantCurve'):
            pts = p['ConstantCurve']['Points']
            ins = [x['InVal'] for x in pts]
            outs = [vec(x['OutVal']) if comps == 3 else [x['OutVal']] for x in pts]
            res = []
            for t in times:
                if t <= ins[0]:
                    res.append(outs[0])
                elif t >= ins[-1]:
                    res.append(outs[-1])
                else:
                    j = max(k for k in range(len(ins)) if ins[k] <= t)
                    f = (t - ins[j]) / ((ins[j + 1] - ins[j]) or 1)
                    res.append([outs[j][c] + (outs[j + 1][c] - outs[j][c]) * f for c in range(comps)])
            return res
        if cls.endswith('Uniform'):
            a = vec(p['Min']) if comps == 3 else [p['Min']]
            b = vec(p['Max']) if comps == 3 else [p['Max']]
            return [[(a[c] + b[c]) / 2 for c in range(comps)] for _ in times]
        return [[0.0] * comps for _ in times]

    # -- modules ---------------------------------------------------------------------------------------------------
    def convert_struct_fields(self, sname, values, outer_key, where):
        """a module's (or struct's) fields for the End editor: distributions made objects, m_* fields and unknown ones out"""
        w = tagw.Writer(self.schema, tagw.Names(), lambda o: 0)
        fields = w.fields(sname)
        out = {}
        for k, v in values.items():
            f = fields.get(k.lower())
            if f is None:
                if not k.startswith('m_'):
                    self.notes.append('%s.%s: not in the End editor, left out' % (where, k))
                continue
            name, dim, td = f
            if name.startswith('m_'):
                continue
            out[name] = self.convert_value(td, v, outer_key, '%s.%s' % (where, name))
        return out

    def convert_value(self, td, v, outer_key, where):
        t = td['t']
        if t == 'Struct':
            sn = td['s']
            if sn == 'RawDistributionFloat':
                return self.distribution(v, 'float', outer_key, where)
            if sn == 'RawDistributionVector':
                return self.distribution(v, 'vector', outer_key, where)
            if sn in tagw.NATIVE or not isinstance(v, dict):
                return v
            return self.convert_struct_fields(sn, v, outer_key, where)
        if t == 'Array':
            return [self.convert_value(td['i'], x, outer_key, '%s[%d]' % (where, i)) for i, x in enumerate(v or [])]
        if t in ('Object', 'Class'):
            if isinstance(v, Obj) and v.key > 0:
                return Obj(('src-ref', v.key))         # resolved at write time (kept or not)
            return None                                 # Remake content outside the package: left out
        return v

    def convert_module(self, ref, outer_key, emitter_name):
        cls, p = self.cls(ref), self.props(ref)
        key = ('src', ref.key)
        props = self.convert_struct_fields(cls, p, key, '%s/%s' % (emitter_name, cls))
        return key, cls, props

    # -- material parameters (sidecar) -----------------------------------------------------------------------------
    def material_params(self, mp, emitter_name):
        out = {'vectors': {}, 'scalars': {}, 'textures': {}}
        if not isinstance(mp, dict):
            return out
        times = [i / 15.0 for i in range(16)]
        for x in mp.get('m_VectorParams') or []:
            nm = str(x.get('m_ParamName', ''))
            xyz = x.get('m_ValueXYZ') or {}
            w = x.get('m_ValueW') or {}
            curve = isinstance(xyz.get('Distribution'), Obj) or int(((xyz.get('Table') or {}).get('Op', 0)) or 0) in (1, 2, 3) and int(((xyz.get('Table') or {}).get('EntryCount', 0)) or 0) > 1
            a = self.sample(xyz, 'vector', times)
            b = self.sample(w, 'float', times)
            vals = [[round(a[i][0], 5), round(a[i][1], 5), round(a[i][2], 5), round(b[i][0], 5)] for i in range(len(times))]
            if curve and any(v != vals[0] for v in vals):
                out['vectors'][nm] = {'curve': vals, 'times': times, 'since_creation': bool(x.get('m_UseSinceCreationTime'))}
            else:
                out['vectors'][nm] = {'const': vals[0]}
        for x in mp.get('m_ScalarParams') or []:
            nm = str(x.get('m_ParamName', ''))
            v = x.get('m_Value') or {}
            a = self.sample(v, 'float', times)
            vals = [round(a[i][0], 5) for i in range(len(times))]
            curve = isinstance(v.get('Distribution'), Obj) or int(((v.get('Table') or {}).get('Op', 0)) or 0) in (1, 2, 3) and int(((v.get('Table') or {}).get('EntryCount', 0)) or 0) > 1
            if curve and any(q != vals[0] for q in vals):
                out['scalars'][nm] = {'curve': vals, 'times': times, 'since_creation': bool(x.get('m_UseSinceCreationTime'))}
            else:
                out['scalars'][nm] = {'const': vals[0]}
        for x in mp.get('m_TexutreParams') or []:
            nm = str(x.get('m_ParamName', ''))
            tex = x.get('m_Texture') or x.get('m_Value')
            out['textures'][nm] = self.import_path(tex) if isinstance(tex, Obj) else None
        for k in ('m_CullMode', 'm_OverrideCullMode', 'm_ParticleFadeDistancePreset', 'm_RenderSortPriority', 'm_Masked', 'm_PreDepth'):
            if k in mp:
                out[k[2:]] = mp[k] if not isinstance(mp[k], (Enum, Name)) else str(mp[k])
        return out

    # -- the whole system ------------------------------------------------------------------------------------------
    def build(self, package_path):
        sys_i = [i for i, (c, p) in enumerate(self.ex) if c == 'ParticleSystem' and self.pkg.exports[i]['outer'] == 0]
        if not sys_i:
            raise ValueError('no ParticleSystem in the package')
        sysref = Obj(sys_i[0] + 1)
        sp = self.props(sysref)
        sys_key = ('src', sysref.key)
        asset_name = package_path.rsplit('/', 1)[-1]
        extra = sp.get('m_EndEffectExtraData') or {}
        sock = extra.get('m_BindSocketName') or {}
        self.sidecar.update(source=self.pkg.path, package=package_path,
                            socket=str(sock.get('m_DirectName')) if isinstance(sock, dict) and sock.get('m_DirectName') else None,
                            bind_time=extra.get('m_BindTime'),
                            exposure=str(extra.get('m_ExposureCondition')) if extra.get('m_ExposureCondition') else None,
                            bounds=sp.get('FixedRelativeBoundingBox'))
        kept_emitters = []
        for em in sp.get('Emitters') or []:
            if not isinstance(em, Obj) or em.key <= 0:
                continue
            r = self.convert_emitter(em, sys_key)
            if r is not None:
                kept_emitters.append(r)
        sys_props = self.convert_struct_fields('ParticleSystem', {k: v for k, v in sp.items() if k not in ('Emitters',)}, sys_key, 'ParticleSystem')
        for k in ('CurveEdSetup', 'PreviewComponent', 'ThumbnailImage'):
            sys_props.pop(k, None)
        sys_props['Emitters'] = kept_emitters
        if isinstance(sp.get('FixedRelativeBoundingBox'), dict) and sp['FixedRelativeBoundingBox'].get('IsValid'):
            sys_props['bUseFixedRelativeBoundingBox'] = True
        self.add(sys_key, 'ParticleSystem', None, asset_name, sys_props, flags=RF_PUBLIC | RF_STANDALONE | RF_TRANSACTIONAL, is_asset=True)
        return self.write(package_path)

    def convert_emitter(self, em, sys_key):
        ecls, ep = self.cls(em), self.props(em)
        ename = str(ep.get('EmitterName') or self.name(em))
        lods = [l for l in (ep.get('LODLevels') or []) if isinstance(l, Obj) and l.key > 0]
        if not lods:
            self.sidecar['dropped'].append({'emitter': ename, 'why': 'no LOD level'})
            return None
        lod = self.props(lods[0])
        req, spawn, td = lod.get('RequiredModule'), lod.get('SpawnModule'), lod.get('TypeDataModule')
        rp = self.props(req)
        tdcls = self.cls(td) if isinstance(td, Obj) else None
        material = self.import_path(rp.get('Material')) if isinstance(rp.get('Material'), Obj) else None
        mods = [m for m in (lod.get('Modules') or []) if isinstance(m, Obj) and m.key > 0]
        mod_classes = [self.cls(m) for m in mods]
        info = {'class': ecls, 'material': material, 'typedata': tdcls,
                'modules': mod_classes, 'local_space': bool(rp.get('bUseLocalSpace'))}
        if tdcls in DROP_TYPEDATA:
            self.sidecar['dropped'].append({'emitter': ename, 'why': 'a %s emitter (no Niagara CPU equivalent here)' % tdcls})
            return None
        sq = [c for c in mod_classes if c and (c.startswith('End') or c.startswith('Vfx'))]
        if material is None and tdcls != 'ParticleModuleTypeDataMesh':
            what = {}
            for m, c in zip(mods, mod_classes):
                if c == 'EndParticleModuleLight':
                    lp = self.props(m)
                    what['light'] = {'color': self.sample(lp.get('m_Color'), 'vector', [0.0])[0],
                                     'intensity': [x[0] for x in self.sample(lp.get('m_Intensity'), 'float', [i / 15.0 for i in range(16)])],
                                     'radius': self.sample(lp.get('m_AttenuationRadius'), 'float', [0.0])[0][0]}
                elif c == 'EndParticleModuleCameraShake':
                    what['camera_shake'] = self.props(m).get('m_EndCameraShakeParam')
            self.sidecar['dropped'].append(dict({'emitter': ename, 'why': 'no material (a helper emitter: %s)' % (', '.join(sq) or 'nothing drawn')}, **what))
            return None
        sp_ = self.props(spawn)
        if sp_.get('bEnabled') is False and not sp_.get('BurstList'):
            self.sidecar['dropped'].append({'emitter': ename, 'why': 'its spawn module is off'})
            return None
        em_key = ('src', em.key)
        lod_key = ('src', lods[0].key)
        kept = []
        for m, c in zip(mods, mod_classes):
            mp = self.props(m)
            if c is None or not self.known(c):
                self.notes.append('%s: module %s is not in the End editor, left out' % (ename, c))
                continue
            if c.startswith('End') or c.startswith('Vfx'):
                if c not in ('EndParticleModuleLight', 'EndParticleModuleCameraShake'):
                    self.notes.append('%s: Square Enix module %s left out' % (ename, c))
                continue
            if mp.get('bEnabled') is False:
                continue
            k, cc, props = self.convert_module(m, em_key, ename)
            self.add(k, cc, sys_key, self.name(m), props)
            kept.append(Obj(('out', k)))
        # (modules are outered to the system, as Cascade makes them; LOD levels to their emitter)
        # the required module: Remake's own placement as Emitter Origin / Rotation; no material (the sidecar has it)
        rk, rc, rprops = self.convert_module(req, em_key, ename)
        rprops.pop('Material', None)
        er = rp.get('m_EndParticleModuleRequired') or {}
        loc = self.sample(er.get('m_Location'), 'vector', [0.0])[0] if er.get('m_Location') else [0.0, 0.0, 0.0]
        rot = self.sample(er.get('m_Rotation'), 'vector', [0.0])[0] if er.get('m_Rotation') else [0.0, 0.0, 0.0]
        if any(abs(x) > 1e-6 for x in loc):
            rprops['EmitterOrigin'] = V3(loc)
        if any(abs(x) > 1e-6 for x in rot):
            # Square Enix rotations are in turns about X, Y and Z
            rprops['EmitterRotation'] = {'Pitch': rot[1] * 360.0, 'Yaw': rot[2] * 360.0, 'Roll': rot[0] * 360.0}
        for k2 in ('m_Location', 'm_Rotation', 'm_Scale'):
            d = er.get(k2)
            if isinstance(d, dict) and (isinstance(d.get('Distribution'), Obj) or int(((d.get('Table') or {}).get('Op', 0)) or 0) in (2, 3)):
                self.notes.append('%s: its %s moves or is random; its first value is kept' % (ename, k2[2:]))
        self.add(rk, rc, sys_key, self.name(req), rprops)
        sk, sc, sprops = self.convert_module(spawn, em_key, ename)
        self.add(sk, sc, sys_key, self.name(spawn), sprops)
        td_out = None
        if tdcls == 'ParticleModuleTypeDataMesh':
            tk, tc, tprops = self.convert_module(td, em_key, ename)
            info['mesh'] = self.import_path(self.props(td).get('Mesh')) if isinstance(self.props(td).get('Mesh'), Obj) else None
            tprops['Mesh'] = Obj(('import', STAND_IN_MESH))
            tprops.pop('bOverrideMaterial', None)
            for k2 in ('m_VfxPivotCenterScale', 'm_VfxPivotCenterRotation'):
                if self.props(td).get(k2):
                    info[k2[2:]] = self.props(td)[k2]
            self.add(tk, tc, sys_key, self.name(td), tprops)
            td_out = Obj(('out', tk))
        elif tdcls in CPU_TYPEDATA:
            info['was_gpu'] = True
        elif tdcls:
            self.notes.append('%s: type data %s left out' % (ename, tdcls))
        # Remake's material and its parameters: in the sidecar. What moves over the particle's life goes into one
        # Dynamic Parameter module (Niagara keeps it as Particles.DynamicMaterialParameter, 4 floats), for the game's
        # per-particle material parameters: a layer's coordinate offset as a scale along a fixed direction (Rebirth's
        # IndependentParameter5.x), then the tone and luminance curves.
        params = self.material_params(rp.get('m_EndMaterialParam'), ename)
        info['params'] = params
        slots = []
        for nm, v in params['vectors'].items():
            if 'curve' not in v or ':Coordinate:' not in nm or ':Offset' not in nm:
                if 'curve' in v:
                    self.notes.append('%s: %s moves over the life; its first value is kept' % (ename, nm))
                continue
            xs = [q[0] for q in v['curve']]
            ys = [q[1] for q in v['curve']]
            mx, my = max(xs) - min(xs) > 1e-5, max(ys) - min(ys) > 1e-5
            if mx and my:
                dx, dy = xs[-1] - xs[0], ys[-1] - ys[0]
                ln = (dx * dx + dy * dy) ** 0.5
                d = (dx / ln, dy / ln) if ln > 1e-6 else (1.0, 0.0)
                vals = [x * d[0] + y * d[1] for x, y in zip(xs, ys)]
                off = max(abs(x * d[1] - y * d[0]) for x, y in zip(xs, ys))
                if off > 1e-3:
                    self.notes.append('%s: %s moves off a line (by %.3f); taken along its first-to-last direction' % (ename, nm, off))
            elif mx:
                d, vals = (1.0, 0.0), xs
                if abs(ys[0]) > 1e-5:
                    self.notes.append('%s: %s: its fixed v (%.3f) is dropped (the moving u is kept)' % (ename, nm, ys[0]))
            elif my:
                d, vals = (0.0, 1.0), ys
                if abs(xs[0]) > 1e-5:
                    self.notes.append('%s: %s: its fixed u (%.3f) is dropped (the moving v is kept)' % (ename, nm, xs[0]))
            else:
                continue
            slots.append({'param': nm, 'kind': 'offset', 'layer': nm.split(':')[0], 'dir': [round(d[0], 6), round(d[1], 6)],
                          'curve': vals, 'times': v['times'], 'since_creation': bool(v.get('since_creation'))})
        prio = ['L:6:ToneLuminance(Float1)', 'L:0:Luminance(Float1)', 'L:5:ToneColor(Float1)']
        scal = sorted([(nm, v) for nm, v in params['scalars'].items() if 'curve' in v],
                      key=lambda t: prio.index(t[0]) if t[0] in prio else len(prio))
        for nm, v in scal:
            slots.append({'param': nm, 'kind': 'scalar', 'curve': v['curve'], 'times': v['times'],
                          'since_creation': bool(v.get('since_creation'))})
        offsets = [x for x in slots if x['kind'] == 'offset']
        if len(offsets) > 1:
            self.notes.append('%s: %d layer offsets move; the game has one per-particle offset scale: %s kept, %s at their first value'
                              % (ename, len(offsets), offsets[0]['param'], ', '.join(x['param'] for x in offsets[1:])))
            slots = [offsets[0]] + [x for x in slots if x['kind'] != 'offset']
        if len(slots) > 4:
            self.notes.append('%s: more than 4 moving material parameters; %s at their first value'
                              % (ename, ', '.join(x['param'] for x in slots[4:])))
            slots = slots[:4]
        if slots:
            info['dynamic'] = []
            dps = []
            for x in slots:
                pts = [{'InVal': t, 'OutVal': float(x['curve'][i]), 'ArriveTangent': 0.0, 'LeaveTangent': 0.0,
                        'InterpMode': Enum('CIM_Linear')} for i, t in enumerate(x['times'])]
                dkey = ('new', len(self.out), 'dyn')
                self.add(dkey, 'DistributionFloatConstantCurve', ('dynmod', em.key), self.new_name('DistributionFloatConstantCurve'),
                         {'ConstantCurve': {'Points': pts}, 'bIsDirty': True})
                dps.append({'ParamName': Name('Param%d' % len(dps)), 'bUseEmitterTime': bool(x['since_creation']), 'bSpawnTimeOnly': False,
                            'ValueMethod': Enum('EDPV_UserSet'), 'bScaleVelocityByParamValue': False,
                            'ParamValue': {'Distribution': Obj(('out', dkey))}})
                rec = {'param': x['param'], 'kind': x['kind'], 'slot': len(dps) - 1}
                if x['kind'] == 'offset':
                    rec.update(layer=x['layer'], dir=x['dir'])
                info['dynamic'].append(rec)
            while len(dps) < 4:
                # an unused slot: auto-set (the converter skips it) and still a distribution (it reads every slot's)
                zkey = ('new', len(self.out), 'dynzero')
                self.add(zkey, 'DistributionFloatConstant', ('dynmod', em.key), self.new_name('DistributionFloatConstant'),
                         {'Constant': 0.0})
                dps.append({'ParamName': Name('Param%d' % len(dps)), 'bUseEmitterTime': False, 'bSpawnTimeOnly': False,
                            'ValueMethod': Enum('EDPV_AutoSet'), 'bScaleVelocityByParamValue': False,
                            'ParamValue': {'Distribution': Obj(('out', zkey))}})
            dk = ('dynmod', em.key)
            self.add(dk, 'ParticleModuleParameterDynamic', sys_key, self.new_name('ParticleModuleParameterDynamic'),
                     {'DynamicParams': dps, 'bSpawnModule': True, 'bUpdateModule': True})
            kept.append(Obj(('out', dk)))
            # (the distributions above were made before their module: their outer is fixed at write time)
        lprops = {'Level': int(lod.get('Level', 0) or 0), 'bEnabled': True, 'RequiredModule': Obj(('out', rk)),
                  'Modules': kept, 'SpawnModule': Obj(('out', sk)), 'PeakActiveParticles': int(lod.get('PeakActiveParticles', 0) or 0)}
        if td_out is not None:
            lprops['TypeDataModule'] = td_out
        self.add(lod_key, 'ParticleLODLevel', em_key, self.name(lods[0]), lprops)
        eprops = {'EmitterName': Name(ename), 'LODLevels': [Obj(('out', lod_key))]}
        for k2 in ('PeakActiveParticles', 'InitialAllocationCount', 'QualityLevelSpawnRateScale', 'DetailModeBitmask', 'SignificanceLevel',
                   'bUseLegacySpawningBehavior', 'bDisabledLODsKeepEmitterAlive', 'EmitterRenderMode'):
            if k2 in ep:
                eprops[k2] = ep[k2]
        ecls_out = ecls if ecls in ('ParticleSpriteEmitter', 'ParticleEmitter') else 'ParticleSpriteEmitter'
        self.add(em_key, ecls_out, sys_key, self.name(em), eprops)
        self.sidecar['emitters'][ename] = info
        return Obj(('out', em_key))

    # -- the package -----------------------------------------------------------------------------------------------
    def write(self, package_path):
        names = tagw.Names()
        # export order: the system first (the asset), then the rest in the order made
        order = [r for r in self.out if r['is_asset']] + [r for r in self.out if not r['is_asset']]
        index = {r['key']: i + 1 for i, r in enumerate(order)}
        imports = []                     # (class package, class name, outer, name)
        imp_index = {}

        def imp(class_package, class_name, outer, name):
            k = (class_package, class_name, outer, name)
            if k not in imp_index:
                imports.append(k)
                imp_index[k] = -len(imports)
            return imp_index[k]
        engine = imp('/Script/CoreUObject', 'Package', 0, '/Script/Engine')

        def class_index(cls):
            return imp('/Script/CoreUObject', 'Class', engine, cls)

        def objref(o):
            if o is None:
                return 0
            k = o.key
            if isinstance(k, tuple) and k[0] == 'out':
                return index.get(k[1], 0)
            if isinstance(k, tuple) and k[0] == 'src-ref':
                return index.get(('src', k[1]), 0)
            if isinstance(k, tuple) and k[0] == 'import':
                pkg, objname = k[1].split('.', 1)
                p = imp('/Script/CoreUObject', 'Package', 0, pkg)
                return imp('/Script/Engine', 'StaticMesh', p, objname)
            return 0
        w = tagw.Writer(self.schema, names, objref)
        exports = []
        for r in order:
            data = w.props(r['cls'], r['props'], r['name']) + b'\0\0\0\0'
            outer = r['outer']
            outer_i = index.get(outer, 0) if outer is not None else 0
            if outer is not None and outer_i == 0:
                outer_i = index.get(('src', self.sys_key_value()), 1)
            exports.append(dict(cls=class_index(r['cls']), outer=outer_i, name=r['name'], flags=r['flags'],
                                data=data, is_asset=1 if r['is_asset'] else 0))
        self.notes.extend(w.notes)
        return self._package(package_path, names, imports, exports)

    def sys_key_value(self):
        for r in self.out:
            if r['is_asset']:
                return r['key'][1]
        return None

    def _package(self, package_path, names, imports, exports):
        asset_name = package_path.rsplit('/', 1)[-1]
        for rec in imports:
            for s in (rec[0], rec[1], rec[3]):
                names.add(s)
        for ex in exports:
            names.add(ex['name'])
        names.add('None')
        nm = names.ref
        s = edpkg.Summary()
        s.legacy, s.legacy_ue3, s.ue4, s.licensee = -7, 864, 522, 0
        s.custom_versions = [PARTICLE_SYSTEM_CUSTOM_VERSION]
        s.folder = 'None'
        s.flags = 0
        s.localization_id = uuid.uuid4().hex.upper()
        s.text_count = s.text_offset = 0
        s.soft_count = 0
        s.guid = uuid.uuid4().bytes
        s.persistent_guid = uuid.uuid4().bytes
        s.saved_by = ((0, 0, 0, 0), '')
        s.compatible_with = ((0, 0, 0, 0), '')
        s.compression_flags = 0
        s.package_source = 0
        s.additional_packages = []
        s.world_tile_offset = 0
        s.chunk_ids = []
        s.preload_count = -1
        s.import_count = len(imports)
        s.export_count = len(exports)
        s.thumbnail_offset = 0
        s.total_header_size = s.name_offset = s.export_offset = s.import_offset = s.depends_offset = 0
        s.soft_offset = s.searchable_offset = s.asset_registry_offset = s.preload_offset = 0
        s.bulk_data_start_offset = 0

        def layout():
            s.name_count = len(names.list)
            s.generations = [(len(exports), len(names.list))]
            out = bytearray(s.bytes())
            s.name_offset = len(out)
            for n in names.list:
                out += edpkg.fstring_bytes(n) + struct.pack('<HH', *edpkg.name_hashes(n))
            s.import_offset = len(out)
            for cp, cn, outer, name in imports:
                out += nm(cp) + nm(cn) + struct.pack('<i', outer) + nm(name) + nm('None')
            s.export_offset = len(out)
            offsets_at = []
            for ex in exports:
                out += struct.pack('<iiii', ex['cls'], 0, 0, ex['outer']) + nm(ex['name']) + struct.pack('<I', ex['flags'])
                offsets_at.append(len(out))
                out += struct.pack('<qq', len(ex['data']), 0)
                out += struct.pack('<iii', 0, 0, 0) + b'\0' * 16 + struct.pack('<I', 0)
                out += struct.pack('<ii', 1, ex['is_asset']) + struct.pack('<iiiii', -1, 0, 0, 0, 0)
            s.depends_offset = len(out)
            for ex in exports:
                deps = sorted(set(d for d in (ex['cls'], ex['outer']) if d))
                out += struct.pack('<i', len(deps)) + b''.join(struct.pack('<i', d) for d in deps)
            s.soft_offset = len(out)
            s.searchable_offset = len(out)
            out += struct.pack('<i', 0)
            s.asset_registry_offset = len(out)
            ar = bytearray()
            ar += struct.pack('<q', 0)
            ar += struct.pack('<i', 1)
            ar += edpkg.fstring_bytes(asset_name) + edpkg.fstring_bytes('ParticleSystem') + struct.pack('<i', 0)
            dep_at = s.asset_registry_offset + len(ar)
            struct.pack_into('<q', ar, 0, dep_at)
            nimp = len(imports)
            words = (nimp + 31) // 32
            bits = [0] * words
            for i in range(nimp):
                bits[i // 32] |= 1 << (i % 32)
            ar += struct.pack('<i', nimp) + b''.join(struct.pack('<I', x) for x in bits) + struct.pack('<i', 0)
            out += ar
            s.total_header_size = len(out)
            s.preload_offset = len(out)
            pos = len(out)
            for ex, at in zip(exports, offsets_at):
                struct.pack_into('<q', out, at + 8, pos)
                pos += len(ex['data'])
            s.bulk_data_start_offset = pos
            return out
        layout()
        head = layout()
        body = b''.join(ex['data'] for ex in exports)
        return bytes(head) + body + struct.pack('<I', edpkg.TAG)


def convert_file(src, dst, sidecar_path, package_path):
    c = Converter(src)
    data = c.build(package_path)
    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    with open(dst, 'wb') as f:
        f.write(data)
    c.sidecar['exports'] = len(c.out)
    with open(sidecar_path, 'w') as f:
        json.dump(c.sidecar, f, indent=1, default=lambda o: o.key if isinstance(o, Obj) else str(o))
    return c, data


if __name__ == '__main__':
    src, dst, side = sys.argv[1], sys.argv[2], sys.argv[3]
    pkg = sys.argv[4] if len(sys.argv) > 4 else '/Game/RemakeFx/Cascade/' + os.path.basename(src)[:-7]
    c, data = convert_file(src, dst, side, pkg)
    print(dst, len(data), 'bytes,', len(c.out), 'exports,', len(c.sidecar['emitters']), 'emitters kept,', len(c.sidecar['dropped']), 'left out')
    for n in c.notes[:60]:
        print('  ', n)
