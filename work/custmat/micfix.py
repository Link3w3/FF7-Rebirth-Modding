"""Makes editor-cooked material instances readable by the game: rewrites their BasePropertyOverrides into the game's layout.

The End editor's engine has stock UE 4.26's FMaterialInstanceBasePropertyOverrides (12 properties). The game's has 44
(Square Enix added PreDepth, ReverseCullMode, Masked, TranslucencyRenderLayer ...), so in an unversioned cooked package
the game reads the editor's struct with the wrong schema: BlendMode / ShadingModel / OpacityMaskClipValue land on its
bool bOverride_PreDepth / bOverride_PreDepthTiming / bOverride_ReversePreDepth, the rest of the export is read a few
bytes off and the next array (CachedReferencedTextures) gets a garbage count: the game reads object references past the
end of the package and crashes (EXCEPTION_ACCESS_VIOLATION in the async loading thread).

fix_package(zen package bytes) rewrites every MaterialInstanceConstant export of an editor-cooked package:
  * an override that is on (bOverride_X set) is written in the game's layout, with its value (enums mapped by name);
  * a value whose override is off does nothing in the editor or the game, so it is left out;
  * a struct with nothing left is left out of the export (the game's defaults);
everything else in the export is byte for byte the same, and the export reads back cleanly with the game's schema.

    micfix.py <zen .uasset chunk> [out]      (checks, and writes the fixed package when out is given)
"""
import os, struct, sys
sys.path[:0] = [os.path.dirname(os.path.abspath(__file__)), '/work/fxlink/src/Content/Python',
                '/work/iostore', '/work/cs']
from rebirth_fx import uprops
from rebirth_fx.usmap import Usmap
from zen import Zen
import scriptobjs

USMAP = '/data/uploads/FF7R2UProj/Saved/ModExtract/usmap/Rebirth_Mappings.usmap'
STRUCT = 'MaterialInstanceBasePropertyOverrides'
MIC_CLASSES = ('MaterialInstanceConstant',)
# the editor's (stock UE 4.26) layout, in schema order: (name, kind, its override flag)
STOCK = [('bOverride_OpacityMaskClipValue', 'bool', None), ('bOverride_BlendMode', 'bool', None),
         ('bOverride_ShadingModel', 'bool', None), ('bOverride_DitheredLODTransition', 'bool', None),
         ('bOverride_CastDynamicShadowAsMasked', 'bool', None), ('bOverride_TwoSided', 'bool', None),
         ('TwoSided', 'bool', 'bOverride_TwoSided'), ('DitheredLODTransition', 'bool', 'bOverride_DitheredLODTransition'),
         ('bCastDynamicShadowAsMasked', 'bool', 'bOverride_CastDynamicShadowAsMasked'),
         ('BlendMode', 'EBlendMode', 'bOverride_BlendMode'), ('ShadingModel', 'EMaterialShadingModel', 'bOverride_ShadingModel'),
         ('OpacityMaskClipValue', 'float', 'bOverride_OpacityMaskClipValue')]
STOCK_ENUMS = {
    'EBlendMode': ['BLEND_Opaque', 'BLEND_Masked', 'BLEND_Translucent', 'BLEND_Additive', 'BLEND_Modulate',
                   'BLEND_AlphaComposite', 'BLEND_AlphaHoldout', 'BLEND_MAX'],
    'EMaterialShadingModel': ['MSM_Unlit', 'MSM_DefaultLit', 'MSM_Subsurface', 'MSM_PreintegratedSkin', 'MSM_ClearCoat',
                              'MSM_SubsurfaceProfile', 'MSM_TwoSidedFoliage', 'MSM_Hair', 'MSM_Cloth', 'MSM_Eye',
                              'MSM_SingleLayerWater', 'MSM_ThinTranslucent', 'MSM_NUM', 'MSM_FromMaterialExpression',
                              'MSM_MAX'],
}
_U = None


def usmap():
    global _U
    if _U is None:
        _U = Usmap(USMAP)
    return _U


# --- the unversioned header (UE 4.26 FUnversionedHeader)
def read_header(d, p):
    frags = []
    while True:
        v = struct.unpack_from('<H', d, p)[0]; p += 2
        frags.append((v & 0x7f, bool(v & 0x80), v >> 9, bool(v & 0x100)))
        if v & 0x100:
            break
    zn = sum(f[2] for f in frags if f[1])
    mask = []
    if zn:
        if zn <= 8:
            w = d[p]; p += 1; mask = [(w >> b) & 1 for b in range(8)]
        elif zn <= 16:
            w = struct.unpack_from('<H', d, p)[0]; p += 2; mask = [(w >> b) & 1 for b in range(16)]
        else:
            for _ in range((zn + 31) // 32):
                w = struct.unpack_from('<I', d, p)[0]; p += 4; mask += [(w >> b) & 1 for b in range(32)]
    out, idx, zi = [], 0, 0
    for skip, hz, num, last in frags:
        idx += skip
        for _ in range(num):
            zero = False
            if hz:
                zero = bool(mask[zi]); zi += 1
            out.append((idx, zero))
            idx += 1
    return out, p


def write_header(props):
    """props: [(schema index, is zero)] ascending -> header bytes, as FUnversionedHeaderBuilder writes them."""
    frags = [[0, False, 0]]           # skip, has zeroes, values
    zmask, frag_bits = [], [[]]
    nxt = 0
    for idx, zero in props:
        assert idx >= nxt, 'indices must ascend'
        for _ in range(idx - nxt):     # ExcludeProperty
            if frags[-1][2] or frags[-1][0] == 127:
                frags.append([0, False, 0]); frag_bits.append([])
            frags[-1][0] += 1
        if frags[-1][2] == 127:        # IncludeProperty
            frags.append([0, False, 0]); frag_bits.append([])
        frags[-1][2] += 1
        frags[-1][1] |= zero
        frag_bits[-1].append(zero)
        nxt = idx + 1
    while len(frags) > 1 and frags[-1][2] == 0:
        frags.pop(); frag_bits.pop()
    out = b''
    for k, (skip, hz, num) in enumerate(frags):
        v = skip | (0x80 if hz else 0) | (num << 9) | (0x100 if k == len(frags) - 1 else 0)
        out += struct.pack('<H', v)
        if hz:
            zmask += frag_bits[k]
    if zmask:
        n = len(zmask)
        word = sum(1 << b for b, z in enumerate(zmask) if z)
        if n <= 8:
            out += struct.pack('<B', word)
        elif n <= 16:
            out += struct.pack('<H', word)
        else:
            out += b''.join(struct.pack('<I', (word >> (32 * k)) & 0xFFFFFFFF) for k in range((n + 31) // 32))
    return out


# --- the struct
def read_stock(d, p):
    """The editor's struct at p -> ({name: value}, end)."""
    hdr, p = read_header(d, p)
    vals = {}
    for idx, zero in hdr:
        if idx >= len(STOCK):
            raise ValueError('not the editor layout: property %d of %s' % (idx, STRUCT))
        name, kind, _ = STOCK[idx]
        if kind == 'float':
            v = 0.0 if zero else struct.unpack_from('<f', d, p)[0]; p += 0 if zero else 4
        else:
            v = 0 if zero else d[p]; p += 0 if zero else 1
            if kind == 'bool':
                v = bool(v)
        vals[name] = v
    return vals, p


def game_struct(vals, u):
    """{stock name: value} -> (the game's struct bytes or None, [kept names], [dropped names])."""
    s = u.structs[STRUCT]
    index = {p.name: p.index for p in s.props}
    kinds = {n: k for n, k, _ in STOCK}
    flags = {n: f for n, _, f in STOCK}
    keep = {}
    for n, v in vals.items():
        f = flags[n]
        if f is None:
            if v:
                keep[n] = v
        elif vals.get(f):
            keep[n] = v
    dropped = sorted(set(vals) - set(keep))
    if not keep:
        return None, [], dropped
    body = b''
    props = []
    for n in sorted(keep, key=lambda n: index[n]):
        v, k = keep[n], kinds[n]
        if k == 'float':
            body += struct.pack('<f', v)
        elif k == 'bool':
            body += struct.pack('<B', 1 if v else 0)
        else:
            name = STOCK_ENUMS[k][v] if v < len(STOCK_ENUMS[k]) else None
            game = u.enums.get(k, [])
            if name is None or name not in game:
                raise ValueError('%s value %d has no match in the game' % (k, v))
            body += struct.pack('<B', game.index(name))
        props.append((index[n], False))
    return write_header(props) + body, sorted(keep), dropped


# --- exports and packages
def fix_export(blob, names, cls, u):
    """-> (new blob or None when nothing changes, note)."""
    hdr, p = read_header(blob, 0)
    assert write_header(hdr) == blob[:p], 'header round trip'
    r = uprops.Reader(u, names, blob, p, len(blob))
    pieces, out_props, note = [], [], None
    for idx, zero in hdr:
        prop, elem, owner = u.prop_at(cls, idx)
        if prop is None:
            raise ValueError('%s has no property %d' % (cls, idx))
        start = r.p
        if zero:
            out_props.append((idx, True))
            continue
        if prop.ptype.type == 'StructProperty' and prop.ptype.struct == STRUCT:
            vals, end = read_stock(blob, start)
            new, kept, dropped = game_struct(vals, u)
            note = dict(values={k: (round(v, 6) if isinstance(v, float) else v) for k, v in vals.items()}, kept=kept, dropped=dropped)
            if new is not None:
                pieces.append(new); out_props.append((idx, False))
            r.p = end
            continue
        r.value(prop.ptype)
        pieces.append(blob[start:r.p]); out_props.append((idx, False))
    if note is None:
        return None, None
    new_blob = write_header(out_props) + b''.join(pieces) + blob[r.p:]
    # it reads back with the game's schema, to the same tail
    r2 = uprops.Reader(u, names, new_blob, 0, len(new_blob))
    r2.props(cls)
    assert new_blob[r2.p:] == blob[r.p:], 'the tail moved'
    return new_blob, note


def rebuild(z, blobs):
    """A zen package with some exports' data replaced: {export index: new bytes}."""
    d = bytearray(z.d[:z.header_end])
    pos = z.bundle_positions()
    order = sorted(pos, key=lambda i: pos[i][0])
    delta_at = []
    for i in order:
        if i in blobs:
            old = z.exports[i]['serial_size']
            delta_at.append((z.exports[i]['serial_offset'], len(blobs[i]) - old))
            struct.pack_into('<Q', d, z.exp_off + 72 * i + 8, len(blobs[i]))
    for i, e in enumerate(z.exports):
        shift = sum(dl for off, dl in delta_at if off < e['serial_offset'])
        if shift:
            struct.pack_into('<Q', d, z.exp_off + 72 * i, e['serial_offset'] + shift)
    body = b''.join(blobs.get(i, z.d[pos[i][0]:pos[i][0] + pos[i][1]]) for i in order)
    end = max(s + n for s, n in pos.values())
    return bytes(d) + body + z.d[end:]


def fix_package(data, u=None):
    """-> (new package bytes, [notes]); the same bytes when nothing needed fixing."""
    u = u or usmap()
    so = scriptobjs.load()
    paths = so[0] if isinstance(so, tuple) else so
    z = Zen(data)
    blobs, notes = {}, []
    for i, e in enumerate(z.exports):
        cls = uprops.class_of(z, i, paths)
        if cls not in MIC_CLASSES:
            continue
        new, note = fix_export(z.export_bytes(i), z.names, cls, u)
        if new is not None:
            blobs[i] = new
            notes.append(dict(export=e['name'], size=(e['serial_size'], len(new)), **note))
    if not blobs:
        return data, notes
    out = rebuild(z, blobs)
    z2 = Zen(out)
    for i in range(len(z.exports)):
        want = blobs.get(i, z.export_bytes(i))
        assert z2.export_bytes(i) == want, 'export %d did not land' % i
        if uprops.class_of(z2, i, paths) in MIC_CLASSES:
            uprops.read_export(u, z2, i, paths)
    return out, notes


if __name__ == '__main__':
    data = open(sys.argv[1], 'rb').read()
    out, notes = fix_package(data)
    for n in notes:
        print(n)
    print('changed' if out != data else 'nothing to fix', len(data), '->', len(out))
    if len(sys.argv) > 2:
        open(sys.argv[2], 'wb').write(out)
