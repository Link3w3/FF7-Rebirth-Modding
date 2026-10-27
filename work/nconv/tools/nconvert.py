"""End editor (UE 4.26 Niagara) system -> Rebirth cooked NiagaraSystem package (UE 5.1-era Niagara + SQEX).

Source: the editor's own saved .uasset (tagged properties) after the editor compiled it (CachedScriptVM up to date).
Output: export trees in the game's schema (nio.Writer), the SQEX blocks (KHCV system block, VFX0 frozen curve data
interfaces, VFX1 type tags), assembled into a zen package by nzen.

    nconvert.py <editor .uasset> <system object name> <out dir> [--package /Game/...] [--material ...]

What is converted (v0): CPU emitters, their particle spawn/update scripts, the system scripts, sprite renderers (game
particle material + the emitter's texture), float/vector/vector2D/color curve data interfaces. Mesh and light renderers
are left out (their emitters still run). Scripts keep the editor's compiled VM code; its constant operands are moved to
Rebirth's constant buffer layout (Rebirth's owner parameters are 16 bytes longer: 512 vs 496).
"""
import hashlib, json, os, struct, sys
sys.path[:0] = ['/work/nconv/tools', '/work/fx1018/editor/Python', '/work/iostore',
                '/work/cs']
import nio, nlegacy as L, nfrozen, nvvm, gv, nindep, nindep2, nremake, nscale
from gv import struct_ as S, b, i32, u32, f32, name, string, obj, enum, array, zero
from rebirth_fx import uwrite

# --- constant buffer layouts (bytes): global, system, owner, emitter
EDITOR_BUFFERS = (32, 48, 496, 32)
GAME_BUFFERS = (32, 48, 512, 32)
GAME_COMPILER_VERSION = [3620385749, 2419082786, 2957111053, 773726544]     # from the game's own scripts


class Fail(Exception):
    pass


def unwrap(p):
    while isinstance(p, L.P) and p.kind == 'native' and isinstance(p.value, L.P):
        p = p.value
    return p


def pv(p, key, default=None):
    """value of a field of a tagged struct (P), or default"""
    if p is None:
        return default
    p = unwrap(p)
    if isinstance(p, dict):
        d = p
    elif isinstance(p, L.P) and p.kind == 'struct':
        d = p.value
    elif isinstance(p, L.P) and p.kind == 'native' and isinstance(p.value, dict):
        d = p.value
    else:
        raise TypeError('not a struct: %r' % (p,))
    x = d.get(key)
    if x is None:
        return default
    return x.value if isinstance(x, L.P) else x


def val(x):
    return x.value if isinstance(x, L.P) else x


def enum_tail(s):
    return s.split('::')[-1] if isinstance(s, str) else s


class Source:
    def __init__(self, path):
        self.pkg = L.Package(open(path, 'rb').read())
        self._cache = {}

    def export(self, index):
        """(class, P) of export `index` (1-based FPackageIndex)"""
        if index not in self._cache:
            cls, v, tail = L.read_export(self.pkg, index - 1)
            self._cache[index] = (cls, v)
        return self._cache[index]

    def find(self, name, cls=None):
        i = self.pkg.find(name, cls)
        if i is None:
            raise Fail('no export %s' % name)
        return i + 1

    def typedef_key(self, td):
        """the editor type (import path, underlying type) of an FNiagaraTypeDefinition"""
        td = unwrap(td)
        c = pv(td, 'ClassStructOrEnum')
        ut = pv(td, 'UnderlyingType', 0)
        return (self.pkg.ref(c) if c else None), ut

    def game_type(self, td, what=''):
        path, ut = self.typedef_key(td)
        t = gv.TYPES.get(path)
        if t is None:
            raise Fail('no Rebirth type hash for %s (%s)' % (path, what))
        return t


# ----------------------------------------------------------------------------------------------------------------
# variables

def var_parts(src, v):
    """(name, game type (hash, utype), data) of an editor FNiagaraVariable / VariableBase native"""
    d = unwrap(v).value if isinstance(unwrap(v).value, dict) else None
    if d is None:
        raise Fail('not a variable: %r' % (v,))
    th = src.game_type(d['TypeDef'], d['Name'])
    return str(d['Name']), th, d.get('data', b'')


def type_size(th):
    lay = gv.LAYOUTS.get(th[0])
    if lay is None:
        raise Fail('no layout for type %08x' % th[0])
    return lay[2]


def g_var(src, v):
    nm, th, data = var_parts(src, v)
    return gv.var(nm, th, data)


def g_var_base(src, v):
    nm, th, data = var_parts(src, v)
    return gv.var_base(nm, th)


# ----------------------------------------------------------------------------------------------------------------
# data sets, layouts

def layout_of(th):
    fl, il, size = gv.LAYOUTS[th[0]]
    return fl, il


def build_layouts(vars_):
    """FNiagaraVariableLayoutInfo for a list of (name, type) in order (for the KHCV block)"""
    out = []
    fs = is_ = hs = 0
    for nm, th in vars_:
        fl, il = layout_of(th)
        out.append({'starts': (fs, is_, hs), 'pad': 0,
                    'offsets': [list(fl), list(range(len(fl))), list(il), list(range(len(il))), [], []]})
        fs += len(fl); is_ += len(il)
    return out, fs, is_


def dataset(src, p, sim_target_cpu=True, replace_vars=None):
    """game FNiagaraDataSetCompiledData from an editor one -> (V, [(name, type)]). replace_vars: the variables to
    write instead of the editor's (the editor's plus added ones)"""
    if p is None:
        return None, []
    vars_ = []
    for x in (pv(p, 'Variables') or []):
        nm, th, data = var_parts(src, x)
        vars_.append((nm, th))
    lay, fs, is_ = build_layouts(vars_)
    tf, ti = pv(p, 'TotalFloatComponents', 0), pv(p, 'TotalInt32Components', 0)
    if (tf, ti) != (fs, is_):
        raise Fail('dataset component totals %s differ from the layout %s' % ((tf, ti), (fs, is_)))
    if replace_vars is not None:
        vars_ = list(replace_vars)
        lay, fs, is_ = build_layouts(vars_)
    items = [gv.var(nm, th, b'') for nm, th in vars_]
    fields = {'Variables': array(items) if items else None,
              'TotalFloatComponents': u32(fs) if fs else None,
              'TotalInt32Components': u32(is_) if is_ else None}
    did = pv(p, 'ID')
    if did is not None:
        nm = pv(did, 'Name')
        ty = pv(did, 'Type')
        idf = {}
        if nm and nm != 'None':
            idf['Name'] = name(nm)
        if ty:
            idf['Type'] = enum(enum_tail(ty))
        if idf:
            fields['ID'] = S('NiagaraDataSetID', idf)
    if pv(p, 'bRequiresPersistentIDs'):
        fields['bRequiresPersistentIDs'] = b(True)
    st = pv(p, 'SimTarget')
    if st and enum_tail(st) != 'CPUSim':
        fields['SimTarget'] = enum(enum_tail(st))
    return S('NiagaraDataSetCompiledData', fields), vars_


def binding_collection(p):
    if p is None:
        return S('NiagaraParameterDataSetBindingCollection', {})
    out = {}
    for key in ('FloatOffsets', 'Int32Offsets'):
        lst = pv(p, key) or []
        items = []
        for x in lst:
            po, dc = pv(x, 'ParameterOffset', 0), pv(x, 'DataSetComponentOffset', 0)
            items.append(S('NiagaraParameterDataSetBinding', {'ParameterOffset': i32(po) if po else None,
                                                              'DataSetComponentOffset': i32(dc) if dc else None}))
        if items:
            out[key] = array(items)
    return S('NiagaraParameterDataSetBindingCollection', out)


# ----------------------------------------------------------------------------------------------------------------
# frozen curve data interfaces (VFX0)

CURVE_VTABLES = {   # editor class -> (vtable type hash, components per sample)
    'NiagaraDataInterfaceCurve': (0xc9ebb81f6e949b4c, 1),
    'NiagaraDataInterfaceVector2DCurve': (0x33d78a10f8c7489b, 2),
    'NiagaraDataInterfaceVectorCurve': (0x0b17848a30d548bb, 3),
    'NiagaraDataInterfaceColorCurve': (0xbfd80ddd6a8ec2a8, 4),
}


def curve_image(cls, p):
    """the VFX0 memory image of a curve data interface (CPU: LUTOffset INDEX_NONE)"""
    vt, comps = CURVE_VTABLES[cls]
    lut = [val(x) for x in (pv(p, 'ShaderLUT') or [])]
    nm1 = pv(p, 'LUTNumSamplesMinusOne', 0.0)
    if not lut:
        raise Fail('%s has no LUT' % cls)
    if round(nm1 + 1) * comps != len(lut):
        raise Fail('%s LUT has %d floats for %d samples of %d' % (cls, len(lut), nm1 + 1, comps))
    lmin = pv(p, 'LUTMinTime', 0.0)
    lmax = pv(p, 'LUTMaxTime', 1.0)
    linv = pv(p, 'LUTInvTimeRange', 1.0)
    img = nfrozen.Image()
    root = img.section(8)
    img.raw(root, b'\xff' * 8 + b'\0' * 16)
    t = img.section(4)
    img.raw(t, struct.pack('<%df' % len(lut), *lut))
    img.array(root, t, len(lut))
    img.raw(root, struct.pack('<4fIB', lmin, lmax, linv, nm1, 0xffffffff, 1))
    img.pad_to(root, 8)
    data, align, names = img.flatten()
    pad = (-(len(data) % 8) + 8) % 8
    return {'magic': nio.VFX0, 'extra': None, 'size': len(data), 'align': 8, 'pad': 0, 'pad_bytes': b'',
            'image': data, 'vtables': [(vt, [(0, 0)])], 'script_names': [], 'minimal_names': []}


# ----------------------------------------------------------------------------------------------------------------
# scripts

class ScriptOut:
    def __init__(self, name, props):
        self.name, self.props = name, props


def remap_constants(code, ext, interpolated, ext_size, literal_size, particle):
    """constant offsets from the editor's constant table layout to Rebirth's"""
    ins = nvvm.decode(code, ext)
    if not particle:
        return code, ins         # system scripts: [global][external][literals], the same in both
    eb = EDITOR_BUFFERS + (ext_size,)
    gb = GAME_BUFFERS + (ext_size,)
    blocks = 2 if interpolated else 1
    ed_bases, gm_bases = [], []
    ea = ga = 0
    for _ in range(blocks):
        for sz_e, sz_g in zip(eb, gb):
            ed_bases.append((ea, sz_e)); gm_bases.append(ga)
            ea += sz_e; ga += sz_g
    lit_e, lit_g = ea, ga
    top = lit_e + literal_size

    def fn(c):
        if c >= top:
            raise Fail('constant offset %d beyond the constant table (%d)' % (c, top))
        if c >= lit_e:
            return lit_g + (c - lit_e)
        for (base, size), gbase in zip(ed_bases, gm_bases):
            if base <= c < base + size:
                return gbase + (c - base)
        raise Fail('constant offset %d not in a buffer' % c)
    stat_ops = {i.at for i in ins if i.op == 'enter_stat_scope'}
    b2 = bytearray(code)
    for i in ins:
        if i.at in stat_ops:
            continue
        for kind, pos, v in i.operands:
            if kind == 'c' or (kind == 'e' and not v & 0x8000):
                struct.pack_into('<H', b2, pos, fn(v))
    return bytes(b2), ins


# the owner parameters (game layout, 512 bytes) of an owner at the origin with no rotation and unit scale
_IDENT = [1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0]
IDENTITY_OWNER = struct.pack('<128f', *(_IDENT * 6 + [0, 0, 0, 1.0] + [0, 0, 0, 0] * 2 + [1.0, 0, 0, 0] + [0, 1.0, 0, 0] +
                                        [0, 0, 1.0, 0] + [1.0, 1.0, 1.0, 0] + [0, 0, 0, 0]))
assert len(IDENTITY_OWNER) == GAME_BUFFERS[2]


def localize(code, ext, interpolated, ext_size, literal_base, literals):
    """A world-space emitter's particle script made to simulate in its own space: every read of the owner parameters
    (Engine.Owner.*: the transforms, position, rotation, velocity, axes, scale) reads the values of an owner at the
    origin instead, so particles start where they would around an owner at the origin and the renderers (the emitter
    marked local space) put them at the component: they follow what the effect is attached to (the keyblade) and turn
    with it. Code in the game's constant layout. -> (code, literals)"""
    ins = nvvm.decode(code, ext)
    lits = bytearray(literals)
    at = {}
    owner0 = GAME_BUFFERS[0] + GAME_BUFFERS[1]
    blocks = [owner0]
    if interpolated:
        blocks.append(sum(GAME_BUFFERS) + ext_size + owner0)
    b2 = bytearray(code)
    stat = {i.at for i in ins if i.op == 'enter_stat_scope'}
    n = 0
    for i in ins:
        if i.at in stat:
            continue
        for kind, pos, v in i.operands:
            if not (kind == 'c' or (kind == 'e' and not v & 0x8000)):
                continue
            for base in blocks:
                if base <= v < base + GAME_BUFFERS[2]:
                    k = v - base
                    if k % 4:
                        raise Fail('an owner parameter read at an odd offset')
                    if k not in at:
                        at[k] = literal_base + len(lits)
                        lits += IDENTITY_OWNER[k:k + 4]
                    if kind == 'e' and at[k] >= 0x8000:
                        raise Fail('an external function input constant beyond 0x7fff')
                    struct.pack_into('<H', b2, pos, at[k])
                    n += 1
    return bytes(b2), bytes(lits), n


def rapid_iteration_values(src, p):
    """{(name, size): bytes} of an editor script's RapidIterationParameters store (the values set on the emitter's
    modules; the compiled parameter list only has the module defaults)"""
    ri = p.get('RapidIterationParameters')
    if ri is None:
        return {}
    data = bytes(val(x) for x in (pv(ri, 'ParameterData') or []))
    out = {}
    for x in pv(ri, 'SortedParameterOffsets') or []:
        u = unwrap(x)
        u = u.value if isinstance(u, L.P) else u
        nm = str(u['Name'])
        off = int(val(u['Offset']))
        try:
            th = src.game_type(u['TypeDef'], nm)
        except Fail:
            continue                    # a type no compiled parameter of the scripts here uses
        sz = type_size(th)
        if off < 0 or off + sz > len(data):
            raise Fail('rapid iteration parameter %s outside the store' % nm)
        out[(nm, sz)] = data[off:off + sz]
    return out


def convert_script(src, out, index, outer, export_name, rename=None, inject=None, scale=None, local=False):
    """an editor NiagaraScript export -> a game NiagaraScript export (added to out). rename: emitter name mapping"""
    cls, p = src.export(index)
    usage = enum_tail(pv(p, 'Usage'))
    vm = p.get('CachedScriptVM')
    if vm is None or not pv(vm, 'ByteCode'):
        raise Fail('script %s (%s) has no compiled VM code: compile and save the system in the editor first'
                   % (export_name, usage))
    code = bytes(pv(vm, 'ByteCode'))
    vmid = p.get('CachedScriptVMId')
    interpolated = usage == 'ParticleSpawnScriptInterpolated'
    particle = usage.startswith('Particle')
    # external functions (inputs, outputs)
    ext = []
    ext_v = []
    for fn in (pv(vm, 'CalledVMExternalFunctions') or []):
        f = unwrap(fn)
        nin = len(pv(f, 'InputParamLocations') or [])
        nout = pv(f, 'NumOutputs', 0)
        ext.append((nin, nout))
        specs = []
        for sp in (pv(f, 'FunctionSpecifiers') or []):
            specs.append(S('VMFunctionSpecifier', {'Key': name(pv(sp, 'Key')), 'Value': name(pv(sp, 'Value'))}))
        ext_v.append(S('VMExternalFunctionBindingInfo', {
            'Name': name(pv(f, 'Name')), 'OwnerName': name(pv(f, 'OwnerName')),
            'InputParamLocations': array([b(val(x)) for x in (pv(f, 'InputParamLocations') or [])]) if nin else None,
            'NumOutputs': i32(nout) if nout else None,
            'FunctionSpecifiers': array(specs) if specs else None}))
    # parameters -> the external constant buffer (execution parameter store) and the literals
    params = [var_parts(src, x) for x in (pv(pv(vm, 'Parameters'), 'Parameters') or [])] if vm.get('Parameters') else []
    internal = [var_parts(src, x) for x in (pv(pv(vm, 'InternalParameters'), 'Parameters') or [])] if vm.get('InternalParameters') else []
    literals = b''.join(bytes(d) if len(d) == type_size(th) else (bytes(d) + b'\0' * type_size(th))[:type_size(th)]
                        for nm, th, d in internal)
    if sum(type_size(th) for _, th, _ in internal) != len(literals):
        raise Fail('literal sizes')
    ri_values = rapid_iteration_values(src, p)
    params = [(nm, th, ri_values.get((nm, type_size(th)), d)) for nm, th, d in params]
    data = bytearray()
    offsets = []
    for nm, th, d in params:
        sz = type_size(th)
        offsets.append((nm, th, len(data)))
        data += (bytes(d) + b'\0' * sz)[:sz]
    ext_size = len(data)
    if interpolated:
        for nm, th, d in params:
            sz = type_size(th)
            offsets.append(('PREV_' + nm, th, len(data)))
            data += (bytes(d) + b'\0' * sz)[:sz]
    # data interfaces
    dis = []
    di_infos = []
    di_compile = []
    for k, x in enumerate(pv(vm, 'DataInterfaceInfo') or []):
        info = unwrap(x)
        di_name = pv(info, 'Name')
        th = src.game_type(pv(info, 'Type'), di_name)
        read = pv(info, 'RegisteredParameterMapRead')
        write = pv(info, 'RegisteredParameterMapWrite')
        pname = read if read and read != 'None' else '__INTERNAL__.' + str(di_name)
        offsets.append((pname, th, k))
        di_compile.append(S('NiagaraScriptDataInterfaceCompileInfo', {
            'Name': name(di_name), 'UserPtrIdx': i32(pv(info, 'UserPtrIdx', -1)),
            'Type': gv.native('NiagaraTypeDefinition', gv.typedef(*th)),
            'RegisteredParameterMapRead': name(read) if read and read != 'None' else None,
            'RegisteredParameterMapWrite': name(write) if write and write != 'None' else None}))
    for k, x in enumerate(pv(p, 'CachedDefaultDataInterfaces') or []):
        info = unwrap(x)
        di_name = pv(info, 'Name')
        di_obj = pv(info, 'DataInterface')
        th = src.game_type(pv(info, 'Type'), di_name)
        dcls, dp = src.export(di_obj)
        if dcls not in CURVE_VTABLES:
            raise Fail('data interface %s (%s) is not supported yet' % (di_name, dcls))
        image = curve_image(dcls, dp)
        read = pv(info, 'RegisteredParameterMapRead')
        write = pv(info, 'RegisteredParameterMapWrite')
        di_infos.append(gv.native('NiagaraScriptDataInterfaceInfo', {
            'props': S('NiagaraScriptDataInterfaceInfo', {
                'Name': name(di_name), 'UserPtrIdx': i32(pv(info, 'UserPtrIdx', -1)),
                'Type': gv.native('NiagaraTypeDefinition', gv.typedef(*th)),
                'RegisteredParameterMapRead': name(read) if read and read != 'None' else None,
                'RegisteredParameterMapWrite': name(write) if write and write != 'None' else None}),
            'image': image}))
        dis.append(obj(0))
    if len(di_infos) != len(di_compile):
        raise Fail('script %s: %d data interfaces, %d compiled' % (export_name, len(di_infos), len(di_compile)))
    code2, ins = remap_constants(code, ext, interpolated, ext_size, len(literals), particle)
    localized = None
    if local:
        if not particle:
            raise Fail('local space is for particle scripts')
        literal_base = (sum(GAME_BUFFERS) + ext_size) * (2 if interpolated else 1)
        code2, literals, localized = localize(code2, ext, interpolated, ext_size, literal_base, literals)
        ins = nvvm.decode(code2, ext)
    if inject is not None:
        if not particle:
            raise Fail('material parameters go into particle scripts only')
        literal_base = (sum(GAME_BUFFERS) + ext_size) * (2 if interpolated else 1)
        try:
            if getattr(inject, 'TEMPS', False):
                code2, literals, num_temp_after = inject.transform(code2, ext, literal_base, literals,
                                                                   pv(vm, 'NumTempRegisters', 0))
            else:
                code2, literals = inject.transform(code2, ext, literal_base, literals)
                num_temp_after = None
        except ValueError as ex:
            raise Fail('script %s: %s' % (export_name, ex))
        ins = nvvm.decode(code2, ext)
    else:
        num_temp_after = None
    num_temp = pv(vm, 'NumTempRegisters', 0) if num_temp_after is None else num_temp_after
    scaled = None
    if scale is not None:
        if not particle:
            raise Fail('attribute scaling goes into particle scripts only')
        literal_base = (sum(GAME_BUFFERS) + ext_size) * (2 if interpolated else 1)
        code2, literals, num_temp = scale.transform(code2, ext, literal_base, literals, num_temp)
        scaled = dict(scale.last, k=scale.k)
        ins = nvvm.decode(code2, ext)
    sorted_offsets = sorted(offsets, key=lambda t: t[0].lower())
    pad16 = (ext_size + 15) // 16 * 16
    store = S('NiagaraScriptExecutionParameterStore', {
        'ParameterSize': i32(ext_size) if ext_size else None,
        'PaddedParameterSize': u32(pad16 * (2 if interpolated else 1)) if ext_size else None,
        'SortedParameterOffsets': array([gv.var_offset(nm, th, o) for nm, th, o in sorted_offsets]) if sorted_offsets else None,
        'ParameterData': gv.bytes_array(data) if data else None,
        'DataInterfaces': array(dis) if dis else None})
    base_hash = pv(vmid, 'BaseScriptCompileHash') if vmid is not None else None
    base_hash = bytes(val(x) for x in (pv(base_hash, 'DataHash') or [])) if base_hash is not None else b''
    if len(base_hash) != 20:
        base_hash = hashlib.sha1(code).digest()
    vm_id = S('NiagaraVMExecutableDataId', {
        'CompilerVersionID': gv.guid(GAME_COMPILER_VERSION),
        'ScriptUsageType': enum(usage),
        'bUsesRapidIterationParams': b(False),      # the default is true; the game writes false
        'bDisableDebugSwitches': b(True),
        'bInterpolatedSpawn': b(True) if interpolated else None,
        'BaseScriptCompileHash': S('NiagaraCompileHash', {'DataHash': gv.bytes_array(base_hash)})})
    vm_out = S('NiagaraVMExecutableData', {
        'ByteCode': gv.bytes_array(code2),
        'NumTempRegisters': i32(num_temp),
        'ScriptLiterals': gv.bytes_array(literals) if literals else None,
        'DataInterfaceInfo': array(di_compile) if di_compile else None,
        'CalledVMExternalFunctions': array(ext_v) if ext_v else None,
        'LastCompileStatus': enum('NCS_UpToDate')})
    props = S('NiagaraScript', {
        'Usage': enum(usage),
        'RapidIterationParameters': S('NiagaraParameterStore', {}),
        'ScriptExecutionParamStore': store,
        'CachedScriptVMId': vm_id,
        'CachedScriptVM': vm_out,
        'CachedDefaultDataInterfaces': array(di_infos) if di_infos else None})
    report = {'usage': usage, 'instructions': len(ins), 'external_functions': len(ext), 'parameters': len(params),
              'external_size': ext_size, 'literals': len(literals), 'data_interfaces': len(di_infos)}
    if scaled:
        report['scaled'] = scaled
    if localized is not None:
        report['owner_reads_localized'] = localized
    return out.add_export(export_name, outer, '/Script/Niagara.NiagaraScript', props, flags=0x8, filter_flags=2), report


# ----------------------------------------------------------------------------------------------------------------
# output package model

class Out:
    def __init__(self, package):
        self.package = package
        self.exports = []       # dict(name, outer (0-based export index or None), cls, props, image, tail, flags, filter)
        self.imports = []       # object paths
        self.reports = {}

    def import_index(self, path):
        if path not in self.imports:
            self.imports.append(path)
        return -(self.imports.index(path) + 1)

    def add_export(self, name_, outer, cls, props, image=None, tail=b'\0\0\0\0', flags=0x8, filter_flags=0):
        self.exports.append(dict(name=name_, outer=outer, cls=cls, props=props, image=image, tail=tail, flags=flags,
                                 filter=filter_flags))
        return len(self.exports)          # FPackageIndex of the new export



# ----------------------------------------------------------------------------------------------------------------
# renderers

def sprite_renderer(src, out, index, outer, template, material, texture, keep_material_parameters=False):
    """a game NiagaraSpriteRendererProperties export: the template (a game sprite renderer's tree, SQEX fields and
    material bindings) with the editor renderer's settings, `material` (object path) and `texture` as its Emissive."""
    import copy
    cls, p = src.export(index)
    t = copy.deepcopy(template)
    f = t.value
    f['Material'] = obj(out.import_index(material))
    if not keep_material_parameters:
        for k in range(8):   # SQEX per-particle material parameters: without nindep the emitter has no such attributes
            f.pop('VfxMaterialIndependentParameters%d_Binding' % k, None)
    # material bindings: the template's, with the Emissive texture ours and the flip-book flag off unless sub images
    sub = pv(p, 'SubImageSize')
    sub_images = bool(sub) and (sub[0] > 1 or sub[1] > 1)
    binds = []
    for x in f['MaterialParameterBindings'].value:
        bn = x.value['MaterialParameterName'].value
        if bn == 'Emissive':
            x.value['m_Texture'] = obj(out.import_index(texture))
        elif bn == 'EmitterCoordinateEmitFlipBook' and not sub_images:
            continue
        binds.append(x)
    f['MaterialParameterBindings'] = array(binds)
    if sub_images:
        f['SubImageSize'] = gv.binary('Vector2D', sub)
    else:
        f.pop('SubImageSize', None)
        f.pop('VfxSubImage', None)
    for key, enum_name in (('FacingMode', 'ENiagaraSpriteFacingMode'), ('Alignment', 'ENiagaraSpriteAlignment'),
                           ('SortMode', 'ENiagaraSortMode')):
        v = pv(p, key)
        if v is not None:
            f[key] = enum(enum_tail(v))
        else:
            f.pop(key, None)
    so = pv(p, 'SortOrderHint')
    if so is not None:
        f['SortOrderHint'] = i32(so)
    # attribute bindings: which ones the emitter's data has (the editor knows)
    for key in ('PositionBinding', 'ColorBinding', 'VelocityBinding', 'SpriteRotationBinding', 'SpriteSizeBinding',
                'SpriteFacingBinding', 'SpriteAlignmentBinding', 'SubImageIndexBinding', 'DynamicMaterialBinding',
                'CameraOffsetBinding', 'UVScaleBinding', 'MaterialRandomBinding', 'CustomSortingBinding',
                'NormalizedAgeBinding'):
        eb = p.get(key)
        exists = bool(pv(eb, 'bBindingExistsOnSource')) if eb is not None else False
        if key not in out_schema_keys('NiagaraSpriteRendererProperties'):
            continue
        if exists:
            f[key] = S('NiagaraVariableAttributeBinding', {'bBindingExistsOnSource': b(True)})
        else:
            f.pop(key, None)
    return out.add_export('NiagaraSpriteRendererProperties_%d' % index, outer,
                          '/Script/Niagara.NiagaraSpriteRendererProperties', t, tail=b'\0' * 8, flags=0x8, filter_flags=0)


def renderer_material(src, rcls, rp):
    """the editor renderer's material (object path): a sprite renderer's Material, a mesh renderer's override"""
    if rcls == 'NiagaraSpriteRendererProperties':
        mat = pv(rp, 'Material')
        return src.pkg.ref(mat) if mat else None
    if rcls == 'NiagaraMeshRendererProperties':
        for ov in (pv(rp, 'OverrideMaterials') or []):
            m = pv(ov, 'ExplicitMat')
            if m:
                return src.pkg.ref(m)
    return None


def mesh_renderer(src, out, index, outer, template, material, texture, keep_material_parameters=False):
    """a game NiagaraMeshRendererProperties export: the template (a game mesh renderer: SQEX fields, material bindings,
    double-sided) with the editor renderer's mesh, its material overridden by `material` (object path) with `texture` as
    its Emissive, and the editor's attribute bindings."""
    import copy
    cls, p = src.export(index)
    t = copy.deepcopy(template)
    f = t.value
    mesh = pv(p, 'ParticleMesh')
    if not mesh:
        raise Fail('mesh renderer %d has no mesh' % index)
    meshes = f['Meshes'].value
    meshes[0].value['Mesh'] = obj(out.import_index(src.pkg.ref(mesh)))
    del meshes[1:]
    f['bOverrideMaterials'] = b(True)
    ov = f['OverrideMaterials'].value
    ov[0].value['ExplicitMat'] = obj(out.import_index(material))
    del ov[1:]
    if not keep_material_parameters:
        for k in range(8):
            f.pop('VfxMaterialIndependentParameters%d_Binding' % k, None)
    # material bindings: the template's (its flip-book switch is already off), with our Emissive texture
    for x in f['MaterialParameterBindings'].value:
        if x.value['MaterialParameterName'].value == 'Emissive':
            x.value['m_Texture'] = obj(out.import_index(texture))
    for key, enum_name in (('FacingMode', 'ENiagaraMeshFacingMode'), ('SortMode', 'ENiagaraSortMode')):
        v = pv(p, key)
        if v is not None:
            f[key] = enum(enum_tail(v))
    keys = out_schema_keys('NiagaraMeshRendererProperties')
    for key in ('PositionBinding', 'ColorBinding', 'VelocityBinding', 'MeshOrientationBinding', 'ScaleBinding',
                'SubImageIndexBinding', 'DynamicMaterialBinding', 'DynamicMaterial1Binding', 'DynamicMaterial2Binding',
                'DynamicMaterial3Binding', 'MaterialRandomBinding', 'NormalizedAgeBinding', 'CameraOffsetBinding'):
        # (CustomSortingBinding stays the template's: the game's mesh renderers all bind it to nothing)
        if key not in keys:
            continue
        eb = p.get(key)
        exists = bool(pv(eb, 'bBindingExistsOnSource')) if eb is not None else False
        if exists:
            f[key] = S('NiagaraVariableAttributeBinding', {'bBindingExistsOnSource': b(True)})
        else:
            f.pop(key, None)
    # (no derived data after the properties, unlike the sprite renderer's cutout data: the game's tail is 4 bytes)
    return out.add_export('NiagaraMeshRendererProperties_%d' % index, outer,
                          '/Script/Niagara.NiagaraMeshRendererProperties', t, tail=b'\0' * 4, flags=0x8, filter_flags=0)


_schema_keys = {}


def out_schema_keys(sname):
    if sname not in _schema_keys:
        u = nio.usmap()
        _schema_keys[sname] = {p.name for s in u.chain(sname) for p in s.props}
    return _schema_keys[sname]


# ----------------------------------------------------------------------------------------------------------------
# system

def emitter_compiled_data(src, tail):
    """the editor system's EmitterCompiledData (after its properties): [P struct]"""
    r = L.Tagged(src.pkg, tail)
    if r.u32() != 0:
        raise Fail('system tail: object GUID present')
    n = r.i32()
    out = [r.props('NiagaraEmitterCompiledData') for _ in range(n)]
    if r.p != len(tail):
        raise Fail('system tail: %d bytes left' % (len(tail) - r.p))
    return out


def convert(src_path, system_name, package, options):
    """-> (zen bytes, store entry, report)"""
    src = Source(src_path)
    out = Out(package)
    sys_index = src.find(system_name, 'NiagaraSystem')
    cls, sp = src.export(sys_index)
    data_tail = L.read_export(src.pkg, sys_index - 1)[2]
    ecd = emitter_compiled_data(src, data_tail)
    handles = pv(sp, 'EmitterHandles') or []
    if len(handles) != len(ecd):
        raise Fail('%d emitter handles, %d emitter compiled data' % (len(handles), len(ecd)))
    template_renderer = options.get('sprite_template')
    report = {'emitters': []}
    # the system is the last export; reserve its index after everything else: build emitters first
    pending_handles = []
    emitter_exports = []
    for k, h in enumerate(handles):
        hv = unwrap(h)
        em = pv(hv, 'Instance')
        hname = pv(hv, 'Name')
        enabled = pv(hv, 'bIsEnabled', True)
        ecls, ep = src.export(em)
        er = {'name': hname, 'enabled': bool(enabled), 'renderers': []}
        emitter_exports.append((k, hv, em, ep, er))
    # exports: emitters (placeholders), their scripts and renderers, system scripts, system (last)
    n_emitters = len(emitter_exports)
    em_idx = {}
    for k, hv, em, ep, er in emitter_exports:
        em_idx[k] = out.add_export(src.pkg.export_name(em - 1), None, '/Script/Niagara.NiagaraEmitter', None,
                                   flags=0x8, filter_flags=2)
    plans = {}
    for k, hv, em, ep, er in emitter_exports:
        me = em_idx[k]
        # the sprite renderers this emitter will get (a texture for their KH3 material)
        kinds = set()
        for r in (pv(ep, 'RendererProperties') or []):
            ri = val(r)
            rcls, rp = src.export(ri)
            mpath = renderer_material(src, rcls, rp)
            if mpath is None or not options['textures'].get(mpath):
                continue
            if rcls == 'NiagaraSpriteRendererProperties':
                kinds.add('sprite')
            elif rcls == 'NiagaraMeshRendererProperties' and options.get('mesh_template') is not None:
                kinds.add('mesh')
        plan = None
        rmk = (options.get('remake') or {}).get(str(er['name']))
        if rmk is not None:
            ds_vars = dataset(src, pv(ecd[k], 'DataSetCompiledData'))[1]
            plan = nindep2.Plan(ds_vars, gv.LAYOUTS, nremake.PREFIX[rmk['kind']], rmk['ip'])
            plans[k] = plan
        elif options.get('independent_params') and kinds:
            ds_vars = dataset(src, pv(ecd[k], 'DataSetCompiledData'))[1]
            prefixes = [pf for kind, pf in (('sprite', nindep.PREFIX), ('mesh', nindep.MESH_PREFIX)) if kind in kinds]
            plan = nindep.Plan(ds_vars, gv.LAYOUTS, prefixes)
            plans[k] = plan
        spawn = pv(pv(ep, 'SpawnScriptProps'), 'Script')
        update = pv(pv(ep, 'UpdateScriptProps'), 'Script')
        scaler = None
        k_size = (options.get('size_scale') or {}).get(str(er['name']))
        if k_size:
            final_vars = plan.new_vars if plan is not None else dataset(src, pv(ecd[k], 'DataSetCompiledData'))[1]
            comps, _ = nindep.float_components(final_vars, gv.LAYOUTS)
            sel = [c for nm in ('SpriteSize', 'Scale') for c in comps.get(nm, [])]
            scaler = nscale.Scaler(sel, k_size)
            er['size_scale'] = k_size
        loc = options.get('local_space')
        make_local = (not pv(ep, 'bLocalSpace')) and (loc == 'all' or (isinstance(loc, list) and str(er['name']) in loc))
        if make_local:
            er['made_local_space'] = True
        si, srep = convert_script(src, out, spawn, me - 1, 'SpawnScript', inject=plan, scale=scaler, local=make_local)
        ui, urep = convert_script(src, out, update, me - 1, 'UpdateScript', inject=plan, scale=scaler, local=make_local)
        er['scripts'] = [srep, urep]
        if rmk is not None:
            er['material_parameters'] = 'remake recipe (%s)' % ', '.join(str(x) for x in sorted(rmk['ip']))
            if plan.warnings:
                er['material_parameter_defaults'] = [str(w) for w in plan.warnings]
        elif plan is not None:
            er['material_parameters'] = 'added (%s)' % ('from Color' if plan.color else 'white')
        rends = []
        for r in (pv(ep, 'RendererProperties') or []):
            ri = val(r)
            rcls, rp = src.export(ri)
            if rmk is not None:
                if rends:
                    er['renderers'].append('%s left out (the recipe makes one renderer)' % rcls)
                    continue
                rends.append(nremake.renderer(src, out, ri, me - 1, rmk))
                er['renderers'].append('%s %s' % (rmk['kind'], rmk['material'].rsplit('.', 1)[-1]))
                continue
            if rcls == 'NiagaraSpriteRendererProperties':
                mat = pv(rp, 'Material')
                mpath = src.pkg.ref(mat) if mat else None
                tex = options['textures'].get(mpath)
                if not tex:
                    er['renderers'].append('sprite skipped (no texture for %s)' % mpath)
                    continue
                rends.append(sprite_renderer(src, out, ri, me - 1, template_renderer, options['material'], tex,
                                             keep_material_parameters=plan is not None))
                er['renderers'].append('sprite %s' % tex.rsplit('.', 1)[-1])
            elif rcls == 'NiagaraMeshRendererProperties' and options.get('mesh_template') is not None:
                mpath = renderer_material(src, rcls, rp)
                tex = options['textures'].get(mpath)
                if not tex:
                    er['renderers'].append('mesh skipped (no texture for %s)' % mpath)
                    continue
                rends.append(mesh_renderer(src, out, ri, me - 1, options['mesh_template'],
                                           options.get('mesh_material', options['material']), tex,
                                           keep_material_parameters=plan is not None))
                er['renderers'].append('mesh %s %s' % (src.pkg.ref(pv(rp, 'ParticleMesh')).rsplit('.', 1)[-1],
                                                       tex.rsplit('.', 1)[-1]))
            else:
                er['renderers'].append('%s left out' % rcls)
        sim = pv(ep, 'SimTarget')
        if sim and enum_tail(sim) != 'CPUSim':
            raise Fail('emitter %s is a GPU emitter' % pv(hv, 'Name'))
        spawn_attrs = [str(val(a)) for a in (pv(ecd[k], 'SpawnAttributes') or [])]
        fields = {
            'bLocalSpace': b(True) if pv(ep, 'bLocalSpace') or make_local else None,
            'bDeterminism': b(True) if pv(ep, 'bDeterminism') else None,
            'UpdateScriptProps': S('NiagaraEmitterScriptProperties', {'Script': obj(ui)}),
            'SpawnScriptProps': S('NiagaraEmitterScriptProperties', {'Script': obj(si)}),
            'Platforms': S('NiagaraPlatformSet', {'QualityLevelMask': i32(31)}),
            'bInterpolatedSpawning': b(True) if pv(ep, 'bInterpolatedSpawning') else None,
            'bRequiresPersistentIDs': b(True) if pv(ep, 'bRequiresPersistentIDs') else None,
            'm_VfxSpawnBurst': b(True) if any('SpawnBurst' in a for a in spawn_attrs) else None,
            'm_VfxSpawnRate': b(True) if any('SpawnRate' in a for a in spawn_attrs) else None,
            'UniqueEmitterName': string(pv(ep, 'UniqueEmitterName')),
            'RendererProperties': array([obj(x) for x in rends]) if rends else None,
            'GPUComputeScript': obj(0),         # the game's CPU emitters store it, as null
        }
        out.exports[me - 1]['props'] = S('NiagaraEmitter', fields)
        out.exports[me - 1]['outer'] = 'SYSTEM'
        report['emitters'].append(er)
    ssi, ssrep = convert_script(src, out, pv(sp, 'SystemSpawnScript'), 'SYSTEM', 'SystemSpawnScript')
    sui, surep = convert_script(src, out, pv(sp, 'SystemUpdateScript'), 'SYSTEM', 'SystemUpdateScript')
    report['system_scripts'] = [ssrep, surep]
    # compiled data
    scd = sp.get('SystemCompiledData')
    ds_sys, v_sys = dataset(src, pv(scd, 'DataSetCompiledData'))
    ds_spawn, v_spawn = dataset(src, pv(scd, 'SpawnInstanceParamsDataSetCompiledData'))
    ds_update, v_update = dataset(src, pv(scd, 'UpdateInstanceParamsDataSetCompiledData'))
    bindings = {}
    for key in ('SpawnInstanceGlobalBinding', 'SpawnInstanceSystemBinding', 'SpawnInstanceOwnerBinding',
                'UpdateInstanceGlobalBinding', 'UpdateInstanceSystemBinding', 'UpdateInstanceOwnerBinding'):
        bindings[key] = binding_collection(pv(scd, key))
    for key in ('SpawnInstanceEmitterBindings', 'UpdateInstanceEmitterBindings'):
        bindings[key] = array([binding_collection(x) for x in (pv(scd, key) or [])])
    scd_out = S('NiagaraSystemCompiledData', dict(
        DataSetCompiledData=ds_sys, SpawnInstanceParamsDataSetCompiledData=ds_spawn,
        UpdateInstanceParamsDataSetCompiledData=ds_update, **bindings))
    # emitter compiled data (export tail) and the KHCV block
    em_cd = []
    khcv_emitters = []
    for k, e in enumerate(ecd):
        fields = {}
        for key in ('EmitterSpawnIntervalVar', 'EmitterInterpSpawnStartDTVar', 'EmitterSpawnGroupVar', 'EmitterAgeVar',
                    'EmitterRandomSeedVar', 'EmitterInstanceSeedVar', 'EmitterTotalSpawnedParticlesVar',
                    'm_VfxMaterialIndependentParameter_InstanceSeedVar'):
            x = e.get(key)
            if x is not None:
                nm, th, d = var_parts(src, x)
                fields[key] = gv.var(nm, th, b'')
        # the End editor leaves SQEX's seed variable default (no name, a Vector4); the game's cooker names it after the
        # emitter like the instance seed, as an int32
        seed = e.get('EmitterInstanceSeedVar')
        if seed is not None:
            nm, th, d = var_parts(src, seed)
            if nm.endswith('.InstanceSeed'):
                fields['m_VfxMaterialIndependentParameter_InstanceSeedVar'] = gv.var(
                    nm[:-len('InstanceSeed')] + 'VfxMaterialIndependentParameterInstanceSeed', th, b'')
        plan = plans.get(k)
        dsv, vars_ = dataset(src, pv(e, 'DataSetCompiledData'), replace_vars=plan.new_vars if plan else None)
        fields['DataSetCompiledData'] = dsv
        em_cd.append(S('NiagaraEmitterCompiledData', fields))
        khcv_emitters.append({'spawn_attributes': [str(val(a)) for a in (pv(e, 'SpawnAttributes') or [])],
                              'layouts': build_layouts(vars_)[0]})
    khcv = {'system': build_layouts(v_sys)[0], 'spawn_params': build_layouts(v_spawn)[0],
            'update_params': build_layouts(v_update)[0], 'emitters': khcv_emitters}
    image, align, minimal = nfrozen.encode_khcv(khcv)
    khcv_image = {'magic': nio.KHCV, 'extra': 0, 'size': len(image), 'align': align, 'pad': 0, 'pad_bytes': b'',
                  'image': image, 'vtables': [], 'script_names': [], 'minimal_names': sorted(minimal.items())}
    handles_out = []
    for k, hv, em, ep, er in emitter_exports:
        handles_out.append(S('NiagaraEmitterHandle', {
            'ID': gv.guid(pv(hv, 'Id')), 'IdName': name(pv(hv, 'IdName')),
            # written either way: an omitted bIsEnabled loads as the handle's constructor default (enabled)
            'bIsEnabled': b(True) if pv(hv, 'bIsEnabled', True) and k not in options.get('disable', ()) else zero(),
            'Name': name(pv(hv, 'Name')), 'Instance': obj(em_idx[k]),
            'VersionedInstance': S('VersionedNiagaraEmitter', {})}))
    bounds = options.get('bounds', 500.0)
    sys_fields = {
        'bFixedBounds': b(True),
        'EmitterHandles': array(handles_out),
        'SystemSpawnScript': obj(ssi), 'SystemUpdateScript': obj(sui),
        'SystemCompiledData': scd_out,
        'ExposedParameters': gv.native('NiagaraUserRedirectionParameterStore', {
            'props': S('NiagaraUserRedirectionParameterStore', {'UserParameterRedirects': V_map(), 'UncompressedSize': i32(-1)}),
            'khcv': []}),
        'FixedBounds': gv.binary('Box', [-bounds, -bounds, -bounds, bounds, bounds, bounds, 1]),
        'bDeterminism': b(True) if pv(sp, 'bDeterminism') else None,
    }
    tail = struct.pack('<Ii', 0, len(em_cd))
    sys_export = out.add_export(package.rsplit('/', 1)[-1], None, '/Script/Niagara.NiagaraSystem',
                                S('NiagaraSystem', sys_fields), image=khcv_image, tail=tail, flags=0xb, filter_flags=0)
    out.exports[sys_export - 1]['tail_structs'] = em_cd
    for e in out.exports:
        if e['outer'] == 'SYSTEM':
            e['outer'] = sys_export - 1
    report['khcv'] = len(image)
    return out, report


def V_map():
    return gv.V('map', '', 0, 0, [])


# ----------------------------------------------------------------------------------------------------------------
# package assembly

def assemble(out, package):
    import nzen, scriptobjs
    from rebirth_fx.matcore import import_hash
    script_paths, rev = scriptobjs.load()
    names = uwrite.Names([package])
    w = nio.Writer(names, exact=False)
    # export data
    datas = []
    for e in out.exports:
        cls = e['cls'].rsplit('.', 1)[-1]
        body = bytearray()
        if e.get('image') is not None:
            body += w.memory_image(e['image'])
        body += w.props(cls, e['props'])
        body += e['tail']
        for st in e.get('tail_structs', []):
            body += w.props('NiagaraEmitterCompiledData', st)
        datas.append(bytes(body))
    # imports: package imports in out.imports order, then the script classes and CDOs
    imports = []
    pkg_imports = []
    for path in out.imports:
        imports.append(import_hash(path))
        pkg_imports.append(path.split('.')[0])
    def script(path):
        h = rev.get(path)
        if h is None:
            raise Fail('no script object %s' % path)
        return h
    exports = []
    for i, e in enumerate(out.exports):
        cls_path = e['cls']
        cdo = cls_path.rsplit('.', 1)[0] + '.Default__' + cls_path.rsplit('.', 1)[1]
        exports.append(dict(name=e['name'], outer=e['outer'], cls=script(cls_path), template=script(cdo),
                            public=bool(e['flags'] & 1), oflags=e['flags'], filter=e['filter'], data=datas[i],
                            path=package + '.' + e['name']))
    for p in pkg_imports:
        names.encode(p)
    order = bundle_order(out)
    data, entry = nzen.write(package, names, imports, pkg_imports, exports, order)
    # the game's memory images start 8-aligned (their alignment) counted in serial offsets, as the archive's Tell()
    # sees them: the cooker pads each one (pad 0..7). Find ours in the written package and pad them the same way.
    datas = align_images(data, [e['data'] for e in exports], script_paths)
    for e, d in zip(exports, datas):
        e['data'] = d
    data, entry = nzen.write(package, names, imports, pkg_imports, exports, order)
    bad = [x for x in image_alignment(data, script_paths) if x[2]]
    if bad:
        raise Fail('memory images not aligned: %s' % bad[:5])
    return data, entry


def _images(z, i, script_paths):
    """[(at, image_at, pad, align)] of the memory images in export i (the KHCV block and frozen data interfaces)"""
    cls, v, extra, d = nio.read_export(z, i, script_paths)
    found = []
    if extra.get('image'):
        found.append(extra['image'])

    def walk(x):
        if hasattr(x, 'kind'):
            if x.kind == 'native' and isinstance(x.value, dict):
                im = x.value.get('image')
                if isinstance(im, dict) and 'image_at' in im:
                    found.append(im)
                for y in x.value.values():
                    walk(y)
            elif x.kind == 'struct':
                for y in x.value.values():
                    walk(y)
            elif x.kind in ('array', 'set'):
                for y in x.value:
                    walk(y)
    walk(v)
    return sorted((im['at'], im['image_at'], im['pad'], im['align']) for im in found)


def align_images(package_data, datas, script_paths):
    """export datas (export-map order) with every memory image padded so it starts aligned in serial offsets"""
    from zen import Zen
    z = Zen(package_data)
    at_serial = z.cooked_header_size
    out = []
    for i, d in enumerate(datas):
        assert z.export_bytes(i) == d
        nd = bytearray()
        prev = 0
        for at, image_at, pad, align in _images(z, i, script_paths):
            hdr = image_at - pad - at
            nd += d[prev:at + hdr]
            start = at_serial + len(nd)                  # where the pad bytes go, in serial offsets
            new_pad = (-start) % align
            struct.pack_into('<H', nd, len(nd) - 2, new_pad)
            nd += b'\0' * new_pad
            prev = image_at
        nd += d[prev:]
        out.append(bytes(nd))
        at_serial += len(nd)
    return out


def image_alignment(package_data, script_paths):
    """[(export, image_at, misalignment)] for every memory image of a written package"""
    from zen import Zen
    z = Zen(package_data)
    res = []
    for i in range(len(z.exports)):
        so = z.exports[i]['serial_offset']
        for at, image_at, pad, align in _images(z, i, script_paths):
            res.append((i, image_at, (so + image_at) % align))
    return res


def bundle_order(out):
    """the cooker's pattern: system created first; each emitter created, its scripts created and serialized, its
    renderers created; then the system scripts; emitters and renderers serialized; the system serialized last"""
    n = len(out.exports)
    sys_i = n - 1
    order = [(sys_i, 0)]
    done_c, done_s = {sys_i}, set()
    children = {}
    for i, e in enumerate(out.exports):
        children.setdefault(e['outer'], []).append(i)
    emitters = [i for i, e in enumerate(out.exports) if e['cls'].endswith('NiagaraEmitter')]
    late = []
    for em in emitters:
        order.append((em, 0)); done_c.add(em)
        for c in children.get(em, []):
            if out.exports[c]['cls'].endswith('NiagaraScript'):
                order += [(c, 0), (c, 1)]
                done_c.add(c); done_s.add(c)
        for c in children.get(em, []):
            if c not in done_c:
                order.append((c, 0)); done_c.add(c); late.append(c)
        late.insert(0, em)
    for c in children.get(sys_i, []):
        if c not in done_c:
            order += [(c, 0), (c, 1)]
            done_c.add(c); done_s.add(c)
    for c in late:
        if c not in done_s:
            order.append((c, 1)); done_s.add(c)
    order.append((sys_i, 1))
    return order


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('source')
    ap.add_argument('system')
    ap.add_argument('out')
    ap.add_argument('--package', required=True)
    ap.add_argument('--options', required=True, help='json: material, textures {KH3 material: texture}, sprite_template')
    a = ap.parse_args()
    opts = json.load(open(a.options))
    if opts.get('sprite_template_from'):
        opts['sprite_template'] = load_template(opts['sprite_template_from'], opts['sprite_template_export'])
    opts.setdefault('textures', {})
    for rname, rec in (opts.get('remake') or {}).items():
        rec['template'] = load_template(rec['template_from'], rec['template_export'])
    if opts.get('mesh_template_from'):
        opts['mesh_template'] = load_template(opts['mesh_template_from'], opts['mesh_template_export'])
    out, report = convert(a.source, a.system, a.package, opts)
    data, entry = assemble(out, a.package)
    os.makedirs(a.out, exist_ok=True)
    open(os.path.join(a.out, a.package.rsplit('/', 1)[-1] + '.zen'), 'wb').write(data)
    json.dump({'package': a.package, 'entry': entry, 'report': report}, open(os.path.join(a.out, 'report.json'), 'w'), indent=1, default=str)
    print(json.dumps(report, indent=1, default=str)[:4000])


def load_template(path, export_index):
    from zen import Zen
    import scriptobjs
    sp, _ = scriptobjs.load()
    z = Zen(open(path, 'rb').read())
    cls, v, extra, data = nio.read_export(z, export_index, sp)
    # strip what refers to the template package itself
    return v


if __name__ == '__main__':
    main()
