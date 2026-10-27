"""Rebirth Niagara effect editing: find colour data in cooked (zen) Niagara system packages, change it in place,
and pack the changed packages into a game mod (IoStore _P container).

Where an effect's colour lives (found on Cloud's Cross Slash):
  * colour curves (NiagaraDataInterfaceColorCurve, the ColorFromCurve modules) — SQEX cooks each one inline in the
    script's CachedDefaultDataInterfaces as a frozen memory image ('VFX0'); only the baked LUT (RGBA per sample) is kept,
    the rich curves are stripped by the cooker, so the LUT is what the game samples, on the CPU and on the GPU.
  * parameter-store LinearColor values (e.g. Constants.<Emitter>.InitializeParticle.Color), Oodle-compressed in
    RapidIterationParameters when UncompressedSize > 0.
  * the materials (RMI_Particle_*) are shared, take their colours from the particles, and the effect textures are BC4
    (grey), so recolouring an effect never needs a material or texture change.
"""
import colorsys, json, os, shutil, struct, sys
sys.path[:0] = ['/work/iostore', '/work/cs', '/work/fx1018/tools', '/work/swap1012/tools']
from zen import Zen
from usmap import Usmap
import uprops, scriptobjs

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USMAP = os.path.join(HERE, 'Rebirth.usmap')
COLOR_CURVE_VT = 0xbfd80ddd6a8ec2a8      # vtable type hash of the frozen colour-curve data interface
COLOR_CURVE_TYPE = 0xa634ab99            # VFX1 type hash of UNiagaraDataInterfaceColorCurve
MOUNT = '../../../End/Content/'
PAK_TEMPLATE = '/work/aval1016/out1/AvalancheSephirothOutfit_P.pak'
RETAIL_HEADERS = {'pakchunk4': '/work/retailhdr/pakchunk4_header.bin'}

_u = None


def usmap():
    global _u
    if _u is None:
        _u = Usmap(USMAP)
    return _u


class Package:
    """A cooked zen package with its exports parsed (where they parse)."""

    def __init__(self, data, label=''):
        self.data = bytes(data)
        self.label = label
        self.z = Zen(self.data)
        self.name = self.z.mapped(self.z.name_mapped)
        self.paths, _ = scriptobjs.load()
        self.exports = {}
        self.errors = {}
        pos = self.z.bundle_positions()
        for i, e in enumerate(self.z.exports):
            try:
                cls, v, end, d = uprops.read_export(usmap(), self.z, i, self.paths)
                self.exports[i] = (cls, v, pos[i][0])
            except uprops.ParseError as ex:
                self.errors[i] = str(ex)

    def export_name(self, i):
        return self.z.exports[i]['name']

    def outer_name(self, i):
        o = self.z.exports[i]['outer']
        return self.z.exports[o]['name'] if o < len(self.z.exports) else None


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
            yield from _walk(a); yield from _walk(b)
    elif v.kind == 'native' and isinstance(v.value, dict):
        for x in v.value.values():
            if isinstance(x, uprops.V):
                yield from _walk(x)


def color_curves(pkg):
    """Every frozen colour-curve LUT: dict(export, script, emitter, name, samples, at (absolute offset of the first float
    in the package), floats)."""
    out = []
    for i, (cls, v, base) in pkg.exports.items():
        for x in _walk(v):
            if x.kind != 'native' or x.type != 'NiagaraScriptDataInterfaceInfo':
                continue
            img = x.value['image']
            if not img or not img['vtables'] or img['vtables'][0][0] != COLOR_CURVE_VT:
                continue
            im = img['image']
            ptr, num, mx = struct.unpack_from('<qii', im, 24)
            nm1 = struct.unpack_from('<f', im, 52)[0]
            samples = int(round(nm1)) + 1
            if not (ptr & 1) or num != mx or num != 4 * samples:
                raise ValueError('%s: unexpected colour-curve image in export %d' % (pkg.label, i))
            off = 24 + (ptr >> 1)
            props = x.value['props'].value
            out.append(dict(export=i, script=pkg.export_name(i), emitter=pkg.outer_name(i),
                            name=props['Name'].value if 'Name' in props else None, samples=samples,
                            at=base + img['image_at'] + off, floats=list(struct.unpack_from('<%df' % num, im, off))))
    return out


# --- colour transforms -------------------------------------------------------------------------------------------

def to_blue(r, g, b, hue=215.0, spread=0.25, sat=1.0, bright=1.0, warm_center=35.0):
    """Recolour towards blue keeping each colour's saturation and brightness (so a white-hot core stays white and an
    orange-to-red fade becomes a light-to-deep blue fade). Warm hues keep a little of their spread around `hue`."""
    v = max(r, g, b)
    if v <= 0.0:
        return r, g, b
    h, s, _ = colorsys.rgb_to_hsv(r / v, g / v, b / v)    # hue/saturation of the normalised colour (HDR safe)
    hd = h * 360.0
    d = (hd - warm_center + 180.0) % 360.0 - 180.0
    nh = hue + spread * d if abs(d) <= 90.0 else hue
    s = min(1.0, s * sat)
    nr, ng, nb = colorsys.hsv_to_rgb((nh % 360.0) / 360.0, s, 1.0)
    return nr * v * bright, ng * v * bright, nb * v * bright


def swap_rb(r, g, b, **kw):
    return b, g, r


TRANSFORMS = {'blue': to_blue, 'swap_rb': swap_rb}


def recolor(pkg, transform='blue', only=None, **kw):
    """Returns (new package bytes, report). `only`: substrings of emitter or curve names to change (default: all)."""
    f = TRANSFORMS[transform] if isinstance(transform, str) else transform
    data = bytearray(pkg.data)
    report = []
    for c in color_curves(pkg):
        label = '%s %s' % (c['emitter'], c['name'])
        if only and not any(o.lower() in label.lower() for o in only):
            continue
        fl = c['floats']
        new = []
        for k in range(0, len(fl), 4):
            r, g, b, a = fl[k:k + 4]
            nr, ng, nb = f(r, g, b, **kw)
            new += [nr, ng, nb, a]
        struct.pack_into('<%df' % len(new), data, c['at'], *new)
        report.append(dict(emitter=c['emitter'], script=c['script'], curve=c['name'], samples=c['samples'],
                           before=[round(x, 4) for x in fl[:4]] + ['...'] + [round(x, 4) for x in fl[-4:]],
                           after=[round(x, 4) for x in new[:4]] + ['...'] + [round(x, 4) for x in new[-4:]]))
    return bytes(data), report


# --- packing -----------------------------------------------------------------------------------------------------

def store_entries(chunk='pakchunk4'):
    from hdr import parse_header
    return parse_header(open(RETAIL_HEADERS[chunk], 'rb').read())[1]


def package_path(name):
    """'/Game/A/B' -> 'A/B.uasset' under the content mount."""
    assert name.startswith('/Game/'), name
    return name[len('/Game/'):] + '.uasset'


def build_mod(packages, out_dir, mod_name, chunk='pakchunk4'):
    """packages: list of zen package bytes (each replacing the game's package of the same name)."""
    import iostore_write as W
    from iostore import Toc
    from hdr import parse_header
    assert mod_name.endswith('_P'), 'mod containers need the _P suffix to override the game'
    retail = store_entries(chunk)
    chunks, entries = [None], []
    for data in packages:
        z = Zen(data)
        name = z.mapped(z.name_mapped)
        pid = W.package_id(name)
        e = retail.get(pid)
        if e is None:
            raise KeyError('%s is not in the game\'s %s' % (name, chunk))
        if e['export_count'] != len(z.exports):
            raise ValueError('%s: %d exports, the game has %d' % (name, len(z.exports), e['export_count']))
        chunks.append(dict(id64=pid, type=2, data=data, path=package_path(name)))
        entries.append(dict(id=pid, size=len(data), export_count=e['export_count'], export_bundle_count=e['export_bundle_count'],
                            load_order=e['load_order'], imports=e['imports']))
    cid = W.container_id_from_name(mod_name)
    chunks[0] = dict(id64=cid, type=10, data=W.container_header(cid, entries), path=None)
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.join(out_dir, mod_name)
    W.write_container(base, mod_name, chunks, mount=MOUNT)
    shutil.copy(PAK_TEMPLATE, base + '.pak')
    # read it back
    back = Toc(base + '.utoc')
    assert back.container_id == cid and back.entries == len(chunks)
    for i, c in enumerate(chunks):
        assert back.read(i) == c['data'] and back.chunk_id64(i) == c['id64'] and back.chunk_type(i) == c['type']
        if c['path']:
            assert back.files.get(i) == MOUNT + c['path'], back.files.get(i)
    _, ents = parse_header(back.read(0))
    for c, e in zip(chunks[1:], entries):
        got = ents[c['id64']]
        assert (got['size'], got['export_count'], got['export_bundle_count'], got['imports']) == (e['size'], e['export_count'], e['export_bundle_count'], e['imports'])
    return [base + ext for ext in ('.utoc', '.ucas', '.pak')]
