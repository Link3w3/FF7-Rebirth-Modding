"""Scan a Rebirth Niagara system package: data interfaces (with their frozen LUTs), parameter-store values,
renderer material bindings.   fxscan.py <usmap> <zen package> [--all]"""
import struct, sys, colorsys
sys.path[:0] = ['/work/iostore', '/work/cs', '/work/fx1018/tools']
from zen import Zen
from usmap import Usmap
import uprops, scriptobjs

COLOR_CURVE_VT = 0xbfd80ddd6a8ec2a8
FLOAT_CURVE_VT = 0xc9eb3b0b1f0c0f4c


def walk(v, path=''):
    """yield (path, V) for every value in a parsed tree"""
    yield path, v
    if v.kind == 'struct':
        for k, x in v.value.items():
            yield from walk(x, path + '/' + k)
    elif v.kind in ('array', 'set'):
        for i, x in enumerate(v.value):
            yield from walk(x, '%s[%d]' % (path, i))
    elif v.kind == 'map':
        for i, (a, b) in enumerate(v.value):
            yield from walk(a, '%s{k%d}' % (path, i)); yield from walk(b, '%s{v%d}' % (path, i))
    elif v.kind == 'native' and isinstance(v.value, dict):
        for k, x in v.value.items():
            if isinstance(x, uprops.V):
                yield from walk(x, path + '/' + k)


def lut_of(img):
    """(num, samples-1, elems per sample, data offset in export, floats) of a frozen curve DI image, or None."""
    im = img['image']
    if len(im) < 64:
        return None
    ptr, num, mx = struct.unpack_from('<qii', im, 24)
    if not (ptr & 1) or num <= 0 or num != mx:
        return None
    off = 24 + (ptr >> 1)
    if off + 4 * num > len(im):
        return None
    lmin, lmax, linv, nm1 = struct.unpack_from('<4f', im, 40)
    samples = int(round(nm1)) + 1
    elems = num // samples if samples and num % samples == 0 else None
    return dict(num=num, samples=samples, elems=elems, at=img['image_at'] + off, tmin=lmin, tmax=lmax,
                floats=list(struct.unpack_from('<%df' % num, im, off)))


def scan(u, path, show_all=False):
    z = Zen(open(path, 'rb').read())
    paths, _ = scriptobjs.load()
    out = {'dis': [], 'params': [], 'bindings': [], 'errors': []}
    for i, e in enumerate(z.exports):
        try:
            cls, v, end, data = uprops.read_export(u, z, i, paths)
        except uprops.ParseError as ex:
            out['errors'].append((i, e['name'], str(ex)))
            continue
        owner = e['outer']
        oname = z.exports[owner]['name'] if owner < len(z.exports) else '-'
        for p, x in walk(v):
            if x.kind == 'native' and x.type == 'NiagaraScriptDataInterfaceInfo':
                props = x.value['props'].value
                nm = props['Name'].value if 'Name' in props else None
                img = x.value['image']
                if img:
                    vt = img['vtables'][0][0] if img['vtables'] else None
                    lut = lut_of(img)
                    out['dis'].append(dict(export=i, script=e['name'], emitter=oname, name=nm, vtable=vt, lut=lut, image=img))
            if x.kind == 'struct' and x.type in ('NiagaraParameterStore', 'NiagaraScriptExecutionParameterStore', 'NiagaraUserRedirectionParameterStore'):
                st = x.value
                offs = st.get('SortedParameterOffsets')
                pdata = st.get('ParameterData')
                if offs is None or pdata is None or pdata.zero:
                    continue
                raw_at = pdata.at + 4
                raw = bytes(b.value for b in pdata.value)
                for o in offs.value:
                    vv = o.value
                    out['params'].append(dict(export=i, script=e['name'], emitter=oname, store=p.split('/')[1] if '/' in p else p,
                                              name=vv['Name'], offset=vv['Offset'], vfx1=vv['vfx1'], data_at=raw_at, raw=raw))
            if x.kind == 'struct' and x.type == 'NiagaraMaterialAttributeBinding':
                b = x.value
                cv = b.get('m_ConstantValue')
                tex = b.get('m_Texture')
                out['bindings'].append(dict(export=i, renderer=e['name'], emitter=oname,
                                            mat_param=b.get('MaterialParameterName').value if b.get('MaterialParameterName') else None,
                                            const=(None if cv is None or cv.zero else cv.value), const_at=(cv.at if cv is not None and not cv.zero else None),
                                            tex=(None if tex is None or tex.zero else tex.value),
                                            flags=''.join(k[5] if (b.get(k) is not None and not b.get(k).zero and b.get(k).value) else '-' for k in ('m_bIsStatic', 'm_bIsDynamic', 'm_bIsTexture', 'm_bIsBuffer'))))
    return z, out


if __name__ == '__main__':
    u = Usmap(sys.argv[1])
    z, out = scan(u, sys.argv[2])
    for e in out['errors']:
        print('ERROR export', e)
    print('-- data interfaces with frozen images')
    for d in out['dis']:
        lut = d['lut']
        kind = {COLOR_CURVE_VT: 'ColorCurve', FLOAT_CURVE_VT: 'FloatCurve'}.get(d['vtable'], '%016x' % (d['vtable'] or 0))
        if lut and lut['elems'] == 4:
            f = lut['floats']
            first = f[:4]; last = f[-4:]
            h = colorsys.rgb_to_hsv(*[max(0.0, min(1.0, c)) for c in first[:3]])
            print('  %-14s %-12s %-44s %-10s LUT %3d x%d first %s last %s (hue %.0f)' % (d['emitter'], d['script'], d['name'], kind, lut['samples'], lut['elems'],
                  [round(c, 3) for c in first], [round(c, 3) for c in last], h[0] * 360))
        else:
            print('  %-14s %-12s %-44s %-10s %s' % (d['emitter'], d['script'], d['name'], kind, ('LUT %d x%s' % (lut['samples'], lut['elems'])) if lut else 'no LUT'))
    print('-- parameters named *Color* / *Tint* / *Light*')
    for p in out['params']:
        if any(k in p['name'] for k in ('Color', 'Tint', 'Light', 'Emit')):
            raw = p['raw']; o = p['offset']
            val = list(struct.unpack_from('<4f', raw, o)) if o + 16 <= len(raw) else raw[o:o + 16].hex()
            print('  %-14s %-12s %-26s %-60s ofs %4d hash %08x %s' % (p['emitter'], p['script'], p['store'], p['name'], o, p['vfx1']['hash'] if p['vfx1'] else 0,
                  [round(x, 4) for x in val] if isinstance(val, list) else val))
    print('-- renderer material bindings')
    for b in out['bindings']:
        imp = b['tex']
        tname = None
        if imp is not None and imp < 0:
            tname = 'import %d' % (-imp - 1)
        print('  %-14s %-36s %-48s %s const %s tex %s' % (b['emitter'], b['renderer'], b['mat_param'], b['flags'],
              [round(x, 4) for x in b['const']] if b['const'] else None, tname))
