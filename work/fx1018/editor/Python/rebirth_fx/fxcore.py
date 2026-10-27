"""Rebirth effect data: read a cooked Niagara system package of FINAL FANTASY VII REBIRTH, list the curves Square Enix
cooked into it, write changed curve values back, and pack changed packages as a game mod. No Unreal imports here: the
same code runs inside the End editor and on its own.

Where an effect's colour lives: the colour curves (ColorFromCurve modules: UNiagaraDataInterfaceColorCurve). Square Enix
cooks each data interface inline in its script's CachedDefaultDataInterfaces as a frozen memory image ('VFX0'); only the
curve's baked LUT survives cooking (RGBA per sample, the rich curves are stripped), and the LUT is what the game samples
on the CPU and the GPU. Float curves (size, alpha, intensity over life) are the same with one value per sample.
"""
import json, os, struct

from .zen import Zen
from .usmap import Usmap
from . import uprops

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'data')
COLOR_CURVE_VT = 0xbfd80ddd6a8ec2a8
FLOAT_CURVE_VT = 0xc9ebb81f6e949b4c
KINDS = {COLOR_CURVE_VT: 'color', FLOAT_CURVE_VT: 'float'}

_usmap = None
_scripts = None


def usmap():
    global _usmap
    if _usmap is None:
        _usmap = Usmap(os.path.join(DATA, 'Rebirth.usmap'))
    return _usmap


def script_paths():
    """{FPackageObjectIndex value: '/Script/Module.Object'} of the game's script objects."""
    global _scripts
    if _scripts is None:
        raw = json.load(open(os.path.join(DATA, 'scriptobjects.json')))
        _scripts = {int(k, 16): v for k, v in raw.items()}
    return _scripts


class Package:
    """A cooked zen package, its exports parsed where they parse."""

    def __init__(self, data, label=''):
        self.data = bytes(data)
        self.label = label
        self.z = Zen(self.data)
        self.name = self.z.mapped(self.z.name_mapped)
        self.exports = {}
        self.errors = {}
        pos = self.z.bundle_positions()
        paths = script_paths()
        for i, e in enumerate(self.z.exports):
            try:
                cls, v, end, d = uprops.read_export(usmap(), self.z, i, paths)
                self.exports[i] = (cls, v, pos[i][0])
            except uprops.ParseError as ex:
                self.errors[i] = str(ex)

    def export_name(self, i):
        return self.z.exports[i]['name']

    def outer_name(self, i):
        o = self.z.exports[i]['outer']
        return self.z.exports[o]['name'] if o < len(self.z.exports) else None

    def classes(self):
        return {i: c for i, (c, v, b) in self.exports.items()}

    def is_niagara_system(self):
        return 'NiagaraSystem' in self.classes().values()


def _walk(v):
    yield v
    if v.kind == 'struct':
        for x in v.value.values():
            yield from _walk(x)
    elif v.kind in ('array', 'set'):
        for x in v.value:
            yield from _walk(x)
    elif v.kind == 'map':
        for a, b in v.value:
            yield from _walk(a)
            yield from _walk(b)
    elif v.kind == 'native' and isinstance(v.value, dict):
        for x in v.value.values():
            if isinstance(x, uprops.V):
                yield from _walk(x)


def curve_occurrences(pkg):
    """Every frozen curve LUT in the package (each data interface of each script):
    dict(export, script, emitter, name, kind ('color'|'float'|'curve<N>'), samples, elems, tmin, tmax, at, floats)."""
    out = []
    for i, (cls, v, base) in sorted(pkg.exports.items()):
        for x in _walk(v):
            if x.kind != 'native' or x.type != 'NiagaraScriptDataInterfaceInfo':
                continue
            img = x.value['image']
            if not img or not img['vtables']:
                continue
            im = img['image']
            if len(im) < 64:
                continue
            ptr, num, mx = struct.unpack_from('<qii', im, 24)
            if not (ptr & 1) or num <= 0 or num != mx:
                continue
            off = 24 + (ptr >> 1)
            if off < 64 or off + 4 * num > len(im):
                continue
            tmin, tmax, tinv, nm1 = struct.unpack_from('<4f', im, 40)
            samples = int(round(nm1)) + 1
            if samples <= 0 or num % samples:
                continue
            elems = num // samples
            vt = img['vtables'][0][0]
            kind = KINDS.get(vt, 'curve%d' % elems)
            if kind == 'color' and elems != 4:
                continue
            if kind == 'float' and elems != 1:
                continue
            props = x.value['props'].value
            out.append(dict(export=i, script=pkg.export_name(i), emitter=pkg.outer_name(i),
                            name=props['Name'].value if 'Name' in props else '?', kind=kind, samples=samples, elems=elems,
                            tmin=tmin, tmax=tmax, at=base + img['image_at'] + off,
                            floats=list(struct.unpack_from('<%df' % num, im, off))))
    return out


def curves(pkg):
    """The package's curves, one entry per (emitter, curve name): the same curve is cooked into each script that
    samples it (spawn and update), every copy is in `copies`."""
    groups = {}
    order = []
    for c in curve_occurrences(pkg):
        key = (c['emitter'], c['name'])
        if key not in groups:
            groups[key] = dict(emitter=c['emitter'], name=c['name'], kind=c['kind'], samples=c['samples'], elems=c['elems'],
                               tmin=c['tmin'], tmax=c['tmax'], floats=c['floats'], copies=[])
            order.append(key)
        g = groups[key]
        g['copies'].append(dict(export=c['export'], script=c['script'], at=c['at'], samples=c['samples'],
                                tmin=c['tmin'], tmax=c['tmax'], same=(c['floats'] == g['floats'])))
    return [groups[k] for k in order]


def sample_times(samples, tmin, tmax):
    if samples <= 1:
        return [tmin]
    return [tmin + (tmax - tmin) * k / float(samples - 1) for k in range(samples)]


def patch(pkg_bytes, writes):
    """writes: [(absolute offset, [floats])]. Returns the new package bytes (same size)."""
    data = bytearray(pkg_bytes)
    for at, floats in writes:
        struct.pack_into('<%df' % len(floats), data, at, *floats)
    return bytes(data)


def reduce_keys(times, values, tolerance=0.002):
    """Fewest keys that reproduce `values` (each a tuple) within `tolerance` with linear interpolation (greedy)."""
    n = len(times)
    if n <= 2:
        return list(range(n))
    keep = [0]
    a = 0
    b = 2
    while b < n:
        ok = True
        ta, tb = times[a], times[b]
        for k in range(a + 1, b):
            f = (times[k] - ta) / (tb - ta) if tb != ta else 0.0
            for ch in range(len(values[0])):
                v = values[a][ch] + (values[b][ch] - values[a][ch]) * f
                if abs(v - values[k][ch]) > tolerance:
                    ok = False
                    break
            if not ok:
                break
        if ok:
            b += 1
        else:
            keep.append(b - 1)
            a = b - 1
            b = a + 2
    keep.append(n - 1)
    return keep


# --- recolouring ---------------------------------------------------------------------------------------------------

def to_hue(r, g, b, hue=215.0, spread=0.25, sat=1.0, bright=1.0, warm_center=35.0):
    """Recolour keeping each colour's saturation and brightness: a white core stays white, an orange-to-red fade becomes a
    light-to-deep fade of `hue`. Warm hues keep a little of their spread around it."""
    import colorsys
    v = max(r, g, b)
    if v <= 0.0:
        return r, g, b
    h, s, _ = colorsys.rgb_to_hsv(r / v, g / v, b / v)
    d = (h * 360.0 - warm_center + 180.0) % 360.0 - 180.0
    nh = hue + spread * d if abs(d) <= 90.0 else hue
    s = min(1.0, s * sat)
    nr, ng, nb = colorsys.hsv_to_rgb((nh % 360.0) / 360.0, s, 1.0)
    return nr * v * bright, ng * v * bright, nb * v * bright


# --- packing -------------------------------------------------------------------------------------------------------

def build_mod(packages, headers, out_dir, mod_name, mount='../../../End/Content/', like=None):
    """packages: list of zen package bytes, each replacing the game's package of the same name. headers: list of the game's
    container header bytes (the containers holding those packages): their store entries give each package's imports
    and load order. like: {new package name: game package name} for packages the game does not have (a copy of a game
    package under a new name takes that one's store entry). Writes <out_dir>/<mod_name>.utoc/.ucas/.pak and returns the
    three paths."""
    import shutil
    from . import iostore_write as W
    from .hdr import parse_header
    if not mod_name.endswith('_P'):
        raise ValueError('a mod container needs the _P suffix to override the game')
    retail = {}
    for h in headers:
        retail.update(parse_header(h)[1])
    chunks, entries = [None], []
    for data in packages:
        z = Zen(data)
        name = z.mapped(z.name_mapped)
        pid = W.package_id(name)
        e = retail.get(pid)
        if e is None and like and name in like:
            e = retail.get(W.package_id(like[name]))
        if e is None:
            raise KeyError('%s is not in the given containers' % name)
        if e['export_count'] != len(z.exports):
            raise ValueError('%s: %d exports, the game has %d' % (name, len(z.exports), e['export_count']))
        if not name.startswith('/Game/'):
            raise ValueError('%s: only /Game packages' % name)
        chunks.append(dict(id64=pid, type=2, data=data, path=name[len('/Game/'):] + '.uasset'))
        # the packages it imports: the game's list, plus any an edit added (they are in the package's graph data)
        imports = list(e['imports'])
        try:
            from .matcore import graph_packages
            for gid, arcs in graph_packages(data):
                if gid not in imports:
                    imports.append(gid)
        except Exception:
            pass
        entries.append(dict(id=pid, size=len(data), export_count=e['export_count'], export_bundle_count=e['export_bundle_count'],
                            load_order=e['load_order'], imports=imports))
    cid = W.container_id_from_name(mod_name)
    chunks[0] = dict(id64=cid, type=10, data=W.container_header(cid, entries), path=None)
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    base = os.path.join(out_dir, mod_name)
    W.write_container(base, mod_name, chunks, mount=mount)
    shutil.copy(os.path.join(DATA, 'empty_P.pak'), base + '.pak')
    return [base + '.utoc', base + '.ucas', base + '.pak']


def read_container(utoc):
    """{package id: chunk bytes} and the header bytes of an uncompressed container this module wrote (for checks)."""
    data = open(utoc, 'rb').read()
    ucas = open(utoc[:-5] + '.ucas', 'rb').read()
    hdr_size, entries, blocks, entry_size, ncm, cmname_len, block_size, dir_size, parts = struct.unpack_from('<IIIIIIIII', data, 20)
    p = hdr_size
    ids = []
    for k in range(entries):
        cid, idx, pad, typ = struct.unpack_from('<QHBB', data, p)
        ids.append((cid, typ)); p += 12
    offlen = []
    for k in range(entries):
        b = data[p:p + 10]; p += 10
        offlen.append((int.from_bytes(b[0:5], 'big'), int.from_bytes(b[5:10], 'big')))
    blk = []
    for k in range(blocks):
        b = data[p:p + 12]; p += 12
        blk.append((int.from_bytes(b[0:5], 'little'), int.from_bytes(b[5:8], 'little'), int.from_bytes(b[8:11], 'little')))
    out, header = {}, None
    for (cid, typ), (off, ln) in zip(ids, offlen):
        first = off // block_size
        chunk = bytearray()
        bi = first
        while len(chunk) < ln:
            pos, cs, us = blk[bi]
            chunk += ucas[pos:pos + cs]
            bi += 1
        chunk = bytes(chunk[:ln])
        if typ == 10:
            header = chunk
        else:
            out[cid] = chunk
    return out, header
