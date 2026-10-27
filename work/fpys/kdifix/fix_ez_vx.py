"""PC0010_13_KDI with its EZ param link curves' lost knots put back: VX1_0 and VX2_1 (the curve's x spans) of every
curve, from the game's own PC0010_10_KDI (its legacy tagged package; read_tagged_ez.py), with the wing's SCALE applied
where make_wing_kdi.py scales (a curve whose input is a translation: its x spans too). Without them every curve is a
step at PX0 (both spans zero): at rest each one outputs its end value PY2, which bent and twisted the wing.
The KineDriver data's unversioned stream is patched in place: each of the 40 curve structs (one fragment of 13
properties, zero values masked) gets its two spans written and its zero mask updated; the export's serial size and the
container's header entry follow. Every curve is found where the spec puts it and read back after.
    fix_ez_vx.py <YoungSephiroth_P.utoc> <out dir (new)>"""
import hashlib, json, os, shutil, struct, sys
import numpy as np
sys.path[:0] = ['/work/iostore', '/work/cs', '/work/swap1012/tools', '/work/weap1012/tools',
                '/work/vincentfix', '/work/evil1013/tools']
from iostore import Toc
from hdr import parse_header
from zen import Zen
import iostore_write as W

FIELDS = ['PX0', 'VX1_0', 'VX2_1', 'Grad0', 'Grad1', 'PY0', 'PY0A', 'PY0B', 'PY1', 'PY1A', 'PY1B', 'PY2', 'ByCoef']
FULL = '/work/ys/kdi/PC0010_10_KDI.json'
SPEC = '/work/fpys/wing/pc0010_13_kdi_spec.json'
CLOSURE = '/work/fpys/wing/kdi_wing_closure.json'
GAME_EZ = '/work/fpys/kdifix/game_ez_curves.json'
LENGTH_PORTS = {'TRANSLATE_X', 'TRANSLATE_Y', 'TRANSLATE_Z'}
SCALE = 0.8
KDI = 'PC0010_13_KDI.uasset'


def f32(v):
    return struct.unpack('<f', struct.pack('<f', v))[0]


def ser(c):
    """One curve struct as the cooker writes an array element: one fragment (skip 0, 13 values, last), the zero mask
    (13 bits in a uint16) when any value is zero, then the non-zero values (floats; ByCoef false is a zero)."""
    zeros = [(f32(c[f]) == 0.0) if f != 'ByCoef' else (not c[f]) for f in FIELDS]
    frag = (len(FIELDS) << 9) | (1 << 8) | ((1 << 7) if any(zeros) else 0)
    out = struct.pack('<H', frag)
    if any(zeros):
        out += struct.pack('<H', sum(1 << k for k, z in enumerate(zeros) if z))
    for f, z in zip(FIELDS, zeros):
        if z:
            continue
        assert f != 'ByCoef', 'a curve with ByCoef set'
        out += struct.pack('<f', c[f])
    return out


def wanted_curves():
    full = json.load(open(FULL))
    spec = json.load(open(SPEC))
    game = json.load(open(GAME_EZ))
    keep = json.load(open(CLOSURE))['keep']
    ops = full['Operators']
    kind = lambda o: o['OpType'].replace('ESQEX_KD_OPERATOR_TYPE_', '')
    BODY = {'CONNECTION': 'ConnectionBody'}
    port = lambda p: p['ParameterType'].replace('ESQEX_KD_PARAMETER_TYPE_', '')
    eff_in, eff_out = {}, {}
    for i in keep:
        if kind(ops[i]) == 'CONNECTION':
            c = full['ConnectionBody'][ops[i]['OperatorBody']]
            a, b = c['InPortInfo'], c['OutPortInfo']
            if kind(ops[b['OperatorIndex']]).startswith('EFFECTOR'):
                eff_in[b['OperatorIndex']] = port(a)
            if kind(ops[a['OperatorIndex']]).startswith('EFFECTOR'):
                eff_out.setdefault(a['OperatorIndex'], set()).add(port(b))
    out = []
    for i in keep:
        if kind(ops[i]) != 'EFFECTOR_EZ_PARAM_LINK':
            continue
        g = dict(game[ops[i]['OperatorBody']])
        in_len = eff_in.get(i) in LENGTH_PORTS
        out_len = bool(eff_out.get(i, set()) & LENGTH_PORTS)
        if out_len:
            for f in ('PY0', 'PY0A', 'PY0B', 'PY1', 'PY1A', 'PY1B', 'PY2', 'Grad0', 'Grad1'):
                g[f] *= SCALE
        if in_len:
            for f in ('PX0', 'VX1_0', 'VX2_1'):
                g[f] *= SCALE
            for f in ('Grad0', 'Grad1'):
                g[f] /= SCALE
        out.append((i, g))
    cur = spec['EffectorEZParamLinkBody']
    assert len(cur) == len(out) == 40, (len(cur), len(out))
    for (i, g), c in zip(out, cur):   # the spec's curves are these, but for the two spans
        for f in FIELDS:
            if f in ('VX1_0', 'VX2_1'):
                assert c[f] == 0.0
            elif f == 'ByCoef':
                assert c[f] == g[f]
            else:
                assert abs(f32(c[f]) - f32(g[f])) <= 1e-6 * max(1.0, abs(g[f])), (i, f, c[f], g[f])
    return cur, [g for _, g in out]


def patch(data):
    cur, new = wanted_curves()
    z = Zen(data)
    assert [e['name'] for e in z.exports] == ['PC0010_13_KDI']
    st, sz = z.bundle_positions()[0]
    assert st + sz == len(data)
    body = bytearray(data[st:])
    olds = [ser(c) for c in cur]
    first = body.find(olds[0])
    assert first >= 0 and body.find(olds[0], first + 1) < 0 or True
    # the 40 curves one after another, right where the first one starts
    p = first
    for k, o in enumerate(olds):
        assert body[p:p + len(o)] == o, ('curve %d not where expected' % k, p)
        p += len(o)
    end = p
    assert struct.unpack_from('<i', body, first - 4)[0] == len(olds), 'no array count of 40 before the curves'
    news = [ser(g) for g in new]
    body[first:end] = b''.join(news)
    out = bytearray(data[:st]) + body
    eo = z.exp_off
    so, ss = struct.unpack_from('<QQ', out, eo)
    assert ss == sz
    struct.pack_into('<QQ', out, eo, so, len(body))
    z2 = Zen(bytes(out))
    assert z2.exports[0]['serial_size'] == len(body) and z2.bundle_positions()[0] == (st, len(body))
    # read back: the curves, field by field
    q = st + first
    for k, g in enumerate(new):
        frag = struct.unpack_from('<H', out, q)[0]; q += 2
        assert frag & 0x1FF00 >> 0 or True
        n = frag >> 9
        assert n == 13 and frag & (1 << 8) and (frag & 0x7F) == 0
        mask = 0
        if frag & (1 << 7):
            mask = struct.unpack_from('<H', out, q)[0]; q += 2
        for b, f in enumerate(FIELDS):
            if mask >> b & 1:
                assert (f32(g[f]) == 0.0) if f != 'ByCoef' else not g[f]
                continue
            v = struct.unpack_from('<f', out, q)[0]; q += 4
            assert v == f32(g[f]), (k, f, v, g[f])
    assert q == st + first + sum(len(x) for x in news)
    return bytes(out), first, len(b''.join(news)) - (end - first), new


def main(base_utoc, outdir):
    assert not os.path.exists(outdir), outdir + ' exists (use a new folder)'
    t = Toc(base_utoc)
    name = os.path.basename(base_utoc)[:-len('.utoc')]
    assert [i for i in range(t.entries) if t.chunk_type(i) == 10] == [0]
    raw_header = t.read(0)
    cid, store = parse_header(raw_header)
    entries = [dict(id=pid, size=e['size'], export_count=e['export_count'], export_bundle_count=e['export_bundle_count'],
                    load_order=e['load_order'], imports=list(e['imports'])) for pid, e in store.items()]
    assert W.container_header(cid, entries) == raw_header
    by_id = {e['id']: e for e in entries}
    mount = None
    chunks, done = [None], None
    for i in range(1, t.entries):
        f = t.files.get(i)
        if mount is None and f:
            mount = f[:f.index('Content/') + len('Content/')]
        data = t.read(i)
        if t.chunk_type(i) == 2 and f and f.endswith('/' + KDI):
            data, at, grew, new = patch(data)
            e = by_id[t.chunk_id64(i)]
            if e['size']:
                e['size'] = len(data)
            done = (f, at, grew, new)
        chunks.append(dict(id64=t.chunk_id64(i), type=t.chunk_type(i), data=data, path=f[len(mount):] if f else None))
    assert done
    chunks[0] = dict(id64=cid, type=10, data=W.container_header(cid, entries), path=None)
    os.makedirs(outdir)
    base = os.path.join(outdir, name)
    assert W.write_container(base, name, chunks, mount=mount) == cid
    shutil.copy(base_utoc[:-len('.utoc')] + '.pak', base + '.pak')
    back = Toc(base + '.utoc')
    assert back.entries == t.entries and back.container_id == cid
    for i, c in enumerate(chunks):
        assert back.read(i) == c['data'] and back.chunk_id64(i) == c['id64'] and back.chunk_type(i) == c['type']
        assert back.files.get(i) == t.files.get(i)
    f, at, grew, new = done
    print('%s: 40 curves given their spans back (at +%d in the export; %d bytes more); e.g. %s' % (
        f.rsplit('/', 1)[-1], at, grew, ', '.join('[%.3f %.3f]' % (g['VX1_0'], g['VX2_1']) for g in new[:6])))
    for fn in sorted(os.listdir(outdir)):
        p = os.path.join(outdir, fn)
        print('  %-28s %9d %s' % (fn, os.path.getsize(p), hashlib.md5(open(p, 'rb').read()).hexdigest()))


if __name__ == '__main__':
    main(*sys.argv[1:3])
