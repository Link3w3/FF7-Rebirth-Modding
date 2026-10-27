"""Rebirth materials: a cooked material instance package of FINAL FANTASY VII REBIRTH (its parent, parameter values, static
switches), written back with values changed or added. No Unreal imports: the same code runs inside the End editor and on
its own.

How the game's materials are built: three base materials (/Game/Renderer/Material/RM_Surface, RM_Particle,
RM_UserInterface) -> RMI_* instances with static switches (each one a compiled shader permutation in the game's shader
library) -> the per-asset instances (a character's PC0000_00_TopsA: textures and values on top of an RMI_*).
"""
import struct

from .fxcore import Package, usmap
from .cityhash import CityHash64
from . import uprops, uwrite
from .zen import Zen

PARAM_ARRAYS = (('scalar', 'ScalarParameterValues', 'ScalarParameterValue'),
                ('vector', 'VectorParameterValues', 'VectorParameterValue'),
                ('texture', 'TextureParameterValues', 'TextureParameterValue'))
ASSOCIATIONS = ['LayerParameter', 'BlendParameter', 'GlobalParameter']


def import_hash(object_path):
    """FPackageObjectIndex of an import of another package's object ('/Game/A/B.B' or '/Game/A/B.B:Sub')."""
    s = ''.join('/' if ch in '.:' else ch.lower() for ch in object_path)
    return (2 << 62) | (CityHash64(s.encode('utf-16-le')) & ~(3 << 62))


def resolve_imports(z, extra_packages=()):
    """{import index: '/Game/Pkg.Object'} for the package imports whose package name is in the name map (cooked zen
    packages of this game list their imports' package names there) or in extra_packages."""
    from .fxcore import script_paths
    paths = script_paths()
    cands = set(n for n in z.names if n.startswith('/')) | set(extra_packages)
    by_hash = {}
    for pkg in cands:
        obj = pkg + '.' + pkg.rsplit('/', 1)[-1]
        by_hash[import_hash(obj)] = obj
    out = {}
    for k, v in enumerate(z.imports):
        if v == 0xFFFFFFFFFFFFFFFF:
            continue
        if (v >> 62) == 1:
            out[k] = paths.get(v)
        elif (v >> 62) == 2:
            out[k] = by_hash.get(v)
    return out


class MaterialInstance:
    """A cooked MaterialInstanceConstant package: parent, parameters (with where their bytes are), static switches."""

    def __init__(self, data, label=''):
        self.data = bytes(data)
        self.pkg = Package(self.data, label)
        self.z = self.pkg.z
        self.name = self.pkg.name
        self.index = None
        for i, (cls, v, base) in self.pkg.exports.items():
            if cls in ('MaterialInstanceConstant', 'MaterialInstanceDynamic'):
                self.index = i
                break
        if self.index is None:
            raise ValueError('%s is not a material instance (%s)' % (self.name, sorted(set(self.pkg.classes().values()))))
        self.cls, self.v, self.base = self.pkg.exports[self.index]
        self.imports = resolve_imports(self.z)
        props = self.v.value
        self.parent = self.object_path(props['Parent'].value) if 'Parent' in props else None
        self.params = []
        for kind, arr, sname in PARAM_ARRAYS:
            if arr not in props:
                continue
            for k, el in enumerate(props[arr].value):
                f = el.value
                info = f['ParameterInfo'].value
                pv = f.get('ParameterValue')
                p = dict(kind=kind, name=info['Name'].value, association=info['Association'].value, index=info['Index'].value,
                         at=None, size=0, array_index=k)
                if pv is None or pv.zero:
                    p['value'] = 0.0 if kind == 'scalar' else ([0.0, 0.0, 0.0, 0.0] if kind == 'vector' else None)
                else:
                    p['at'] = self.base + pv.at
                    p['size'] = pv.size
                    if kind == 'scalar':
                        p['value'] = pv.value
                    elif kind == 'vector':
                        p['value'] = list(pv.value)
                    else:
                        p['value'] = self.object_path(pv.value)
                        p['package_index'] = pv.value
                self.params.append(p)
        self.static_switches = []
        sp = props.get('StaticParameters')
        if sp is not None and 'StaticSwitchParameters' in sp.value:
            for el in sp.value['StaticSwitchParameters'].value:
                f = el.value
                self.static_switches.append(dict(name=f['ParameterInfo'].value['Name'].value,
                                                 value=bool(f['Value'].value) if 'Value' in f else False))
        self.has_static_permutation = bool(props['bHasStaticPermutationResource'].value) if 'bHasStaticPermutationResource' in props else False

    def object_path(self, package_index):
        """An FPackageIndex of this package's properties -> object path ('' for null)."""
        if package_index == 0:
            return ''
        if package_index < 0:
            return self.imports.get(-package_index - 1) or '?import%d' % (-package_index - 1)
        return self.name + '.' + self.z.exports[package_index - 1]['name']

    def package_index_in(self, object_path):
        return self.package_index_of(object_path)

    def package_index_of(self, object_path):
        """The FPackageIndex this package already has for object_path, or None."""
        for k, p in self.imports.items():
            if p and p.lower() == object_path.lower():
                return -(k + 1)
        return None

    def find(self, kind, name):
        for p in self.params:
            if p['kind'] == kind and p['name'] == name:
                return p
        return None


# ---------------------------------------------------------------------------------------------------------------------
# writing
# ---------------------------------------------------------------------------------------------------------------------

def _param_element(u, names, sname, kind, name, value_bytes, association='GlobalParameter', index=-1, guid_bytes=None):
    info = uwrite.struct_bytes(u, 'MaterialParameterInfo', {
        'Name': names.encode(name),
        'Association': uwrite.zero_or(struct.pack('<B', ASSOCIATIONS.index(association) if association in ASSOCIATIONS else 2)),
        'Index': uwrite.zero_or(uwrite.i32(index)),
    })
    fields = {'ParameterInfo': info, 'ParameterValue': value_bytes}
    if 'ExpressionGUID' in [p.name for _, p, _ in uwrite.schema(u, sname)]:
        fields['ExpressionGUID'] = uwrite.zero_or(guid_bytes or b'\0' * 16)
    return uwrite.struct_bytes(u, sname, fields)


def edit(mi, changes):
    """New package bytes: `changes` = [dict(kind='scalar'|'vector'|'texture', name=..., value=...)] applied to `mi` (an
    existing override changes, a new one is added; a texture is an object path, imported when the package did not use it
    yet). Returns (bytes, report lines)."""
    data = mi.data
    added = []
    for c in changes:
        if c['kind'] == 'texture' and c['value'] and MaterialInstance.package_index_in(mi, c['value']) is None:
            data, _ = add_import(data, c['value'])
            added.append(c['value'])
    if added:
        mi = MaterialInstance(data, mi.pkg.label)
    report = ['imports %s' % a for a in added]
    same_size = []
    rebuild = {}           # array property -> [changes] to set by re-encoding the array
    for c in changes:
        kind, name, value = c['kind'], c['name'], c['value']
        p = mi.find(kind, name)
        if kind == 'texture':
            pi = mi.package_index_of(value) if value else 0
            if p is not None and p['at'] is not None and pi:
                same_size.append((p['at'], struct.pack('<i', pi)))
                report.append('%s: texture -> %s' % (name, value))
                continue
        elif p is not None and p['at'] is not None:
            same_size.append((p['at'], uwrite.f32(value) if kind == 'scalar' else uwrite.linear_color(value)))
            report.append('%s: %s' % (name, value))
            continue
        arr = dict((k, a) for k, a, s_ in PARAM_ARRAYS)[kind]
        rebuild.setdefault(arr, []).append(c)
        report.append('%s: %s (%s)' % (name, value, 'new override' if p is None else 'was zero'))
    out = bytearray(data)
    for at, b in same_size:
        out[at:at + len(b)] = b
    if not rebuild:
        return bytes(out), report
    return _rebuild_props(mi, bytes(out), rebuild), report


def _rebuild_props(mi, data, rebuild):
    """Re-encodes the material instance's property block with the arrays in `rebuild` changed; the rest of the package is
    copied. The name map grows when a new parameter name needs it."""
    u = usmap()
    mi2 = MaterialInstance(data, mi.pkg.label)        # (offsets of the same-size edits already applied)
    names = uwrite.Names(mi2.z.names)
    ex_start, ex_size = mi2.z.bundle_positions()[mi2.index]
    ex = data[ex_start:ex_start + ex_size]
    v = mi2.v
    props = v.value
    fields = {}
    for key, x in props.items():
        fields[key] = None if x.zero else ex[x.at:x.at + x.size]
    for kind, arr, sname in PARAM_ARRAYS:
        if arr not in rebuild:
            continue
        old = props[arr].value if arr in props else []
        elems = [ex[el.at:el.at + el.size] for el in old]
        names_in = {}
        for k, el in enumerate(old):
            names_in[el.value['ParameterInfo'].value['Name'].value] = k
        for c in rebuild[arr]:
            if kind == 'scalar':
                vb = uwrite.zero_or(uwrite.f32(c['value']))
            elif kind == 'vector':
                vb = uwrite.zero_or(uwrite.linear_color(c['value']))
            else:
                pi = mi2.package_index_of(c['value']) if c['value'] else 0
                vb = uwrite.zero_or(struct.pack('<i', pi))
            k = names_in.get(c['name'])
            if k is not None:
                f = old[k].value
                info = f['ParameterInfo'].value
                g = f.get('ExpressionGUID')
                gb = ex[g.at:g.at + g.size] if g is not None and not g.zero else None
                elems[k] = _param_element(u, names, sname, kind, c['name'], vb, info['Association'].value, info['Index'].value, gb)
            else:
                elems.append(_param_element(u, names, sname, kind, c['name'], vb))
        fields[arr] = struct.pack('<i', len(elems)) + b''.join(elems)
    block = uwrite.struct_bytes(u, mi2.cls, fields)
    new_ex = block + ex[v.at + v.size:]
    return replace_export(data, mi2.index, new_ex, names.names if names.added else None)


def _encode_name(s):
    try:
        b = s.encode('ascii'); wide = False
    except UnicodeEncodeError:
        b = s.encode('utf-16-le'); wide = True
    return struct.pack('>H', (0x8000 if wide else 0) | len(s)), b, wide


def _name_hash(s):
    try:
        return CityHash64(s.lower().encode('ascii'))
    except UnicodeEncodeError:
        return CityHash64(s.lower().encode('utf-16-le'))


def graph_packages(data):
    """[(imported package id, [(from bundle, to bundle)])] of a zen package's graph data."""
    z = Zen(data)
    g = data[z.graph_off:z.graph_off + z.graph_size]
    n = struct.unpack_from('<i', g, 0)[0]
    o, out = 4, []
    for _ in range(n):
        pid, arcs = struct.unpack_from('<Qi', g, o); o += 12
        out.append((pid, [struct.unpack_from('<ii', g, o + 8 * k) for k in range(arcs)]))
        o += 8 * arcs
    return out


def rebuild(data, names=None, imports=None, graph=None, export_index=None, new_export=None):
    """The zen package rebuilt with any of: a new name map (names), import map (list of u64), graph ([(id, arcs)]), and
    export `export_index`'s data replaced (its size may change). Export serial offsets keep counting from the cooked header
    size, as the game's packages do (positions inside the export data)."""
    z = Zen(data)
    exports = bytearray(data[z.exp_off:z.eb_off])
    body = bytearray(data[z.header_end:])
    if export_index is not None:
        pos = z.bundle_positions()
        start, size = pos[export_index]
        delta = len(new_export) - size
        struct.pack_into('<Q', exports, export_index * 72 + 8, len(new_export))
        for j, (s_, n_) in pos.items():
            if s_ > start:
                off = struct.unpack_from('<Q', exports, j * 72)[0]
                struct.pack_into('<Q', exports, j * 72, off + delta)
        rel = start - z.header_end
        body[rel:rel + size] = new_export
    names = names if names is not None else z.names
    nb = bytearray()
    for s_ in names:
        h, b, wide = _encode_name(s_)
        nb += h
        if wide and (64 + len(nb)) & 1:
            nb.append(0)
        nb += b
    nm_off, nm_size = 64, len(nb)
    p_ = nm_off + nm_size
    pad = (8 - p_ % 8) % 8
    nh_off = p_ + pad
    hashes = struct.pack('<Q', z.hash_version) + b''.join(struct.pack('<Q', _name_hash(s_)) for s_ in names)
    imp = data[z.imp_off:z.exp_off] if imports is None else b''.join(struct.pack('<Q', x) for x in imports)
    bundles = data[z.eb_off:z.graph_off]
    if graph is None:
        gr = data[z.graph_off:z.graph_off + z.graph_size]
    else:
        gr = bytearray(struct.pack('<i', len(graph)))
        for pid, arcs in graph:
            gr += struct.pack('<Qi', pid, len(arcs)) + b''.join(struct.pack('<ii', a, b) for a, b in arcs)
        gr = bytes(gr)
    imp_off = nh_off + len(hashes)
    exp_off = imp_off + len(imp)
    eb_off = exp_off + len(exports)
    graph_off = eb_off + len(bundles)
    header_end = graph_off + len(gr)
    summary = struct.pack('<QQIIiiiiiiiiii', z.name_mapped, z.srcname_mapped, z.flags, z.cooked_header_size, nm_off, nm_size,
                          nh_off, len(hashes), imp_off, exp_off, eb_off, graph_off, len(gr), z.pad)
    out = bytearray(summary) + nb + b'\0' * pad + hashes + imp + exports + bundles + gr
    assert len(out) == header_end
    return bytes(out + body)


def replace_export(data, index, new_export, names=None):
    return rebuild(data, names=names, export_index=index, new_export=new_export)


def add_import(data, object_path):
    """(package bytes, FPackageIndex) with an import of object_path ('/Game/Pkg.Obj') added when it was not there: the
    import map, the graph data (the package loads first) and the name map (its names, as the game's packages list them)."""
    from .iostore_write import package_id
    z = Zen(data)
    h = import_hash(object_path)
    if h in z.imports:
        return data, -(z.imports.index(h) + 1)
    package = object_path.split('.', 1)[0]
    short = object_path.rsplit('.', 1)[-1].split(':')[0]
    imports = list(z.imports) + [h]
    graph = graph_packages(data)
    pid = package_id(package)
    if pid not in [g[0] for g in graph]:
        graph.append((pid, [(0, 0)]))
        graph.sort(key=lambda g: g[0])
    names = list(z.names)
    for nm in (package, short):
        if nm not in names:
            names.append(nm)
    return rebuild(data, names=names, imports=imports, graph=graph), -len(imports)
