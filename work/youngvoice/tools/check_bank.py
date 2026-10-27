"""Reads a sound bank container back with the Python tools (independent of the C++ that wrote it): the toc, the
container header (store entries, imports, localization record), every package (zen, its export with the game's
property schema, the SEAD bank) and every material decoded by ffmpeg against its source line."""
import os, sys, struct, subprocess, io, warnings
import numpy as np, soundfile as sf
warnings.filterwarnings('ignore')
sys.path[:0] = ['/work/iostore', '/work/cs', '/work/swap1012/tools', '/work/vinsnd1016/tools',
                '/work/vinvoice1016/tools', '/work/fxlink/src/Content/Python', '/work/weap1012/tools']
from iostore import Toc
from zen import Zen
from hdr import parse_header
import iostore_write as W
import sead, sead2, scriptobjs, gameids
from rebirth_fx.usmap import Usmap
from rebirth_fx import uprops
USMAP = '/data/uploads/FF7R2UProj/Saved/ModExtract/usmap/Rebirth_Mappings.usmap'

def imp(path):
    return (2 << 62) | gameids.objhash(path)

def main(utoc, spec):
    lines = {}
    for l in open(spec):
        t = l.split()
        if t and t[0] == 'line':
            lines[t[1]] = dict(kv.split('=', 1) for kv in t[2:])
    t = Toc(utoc)
    name = os.path.basename(utoc)[:-5]
    assert t.container_id == W.container_id_from_name(name), 'container id'
    heads = [i for i in range(t.entries) if t.chunk_type(i) == 10]
    assert heads == [0]
    hdr = t.read(0)
    cid, store = parse_header(hdr)
    assert cid == t.container_id
    n = struct.unpack_from('<I', hdr, 8)[0]
    recs = struct.unpack_from('<I', hdr, 12)[0]
    print('container', name, 'packages', n, 'localization records', recs)
    so = scriptobjs.load()
    paths = so[0] if isinstance(so, tuple) else so
    u = Usmap(USMAP)
    pkgs = {}
    for i in range(1, t.entries):
        assert t.chunk_type(i) == 2
        f = t.files.get(i)
        p = '/Game/' + f[len('../../../End/Content/'):-len('.uasset')]
        assert t.chunk_id64(i) == W.package_id(p), p
        pkgs[p] = t.read(i)
    assert set(store) == {W.package_id(p) for p in pkgs}
    source = [p for p in pkgs if '/JP/' in p or len(pkgs) == 1][0]
    for p, d in sorted(pkgs.items()):
        z = Zen(d)
        e = store[W.package_id(p)]
        assert e['size'] & ((1 << 60) - 1) == len(d) and e['size'] >> 60 == 4, hex(e['size'])
        assert e['export_count'] == 1 and e['export_bundle_count'] == 1
        assert z.mapped(z.name_mapped) == p and z.mapped(z.srcname_mapped) == source, (z.mapped(z.name_mapped), z.mapped(z.srcname_mapped))
        asset = p.rsplit('/', 1)[1]
        ex = z.exports[0]
        assert ex['name'] == asset and ex['global_import'] == imp(source + '.' + asset)
        assert paths.get(ex['cls']) == '/Script/SQEXSEAD.SQEXSEADSound' and paths.get(ex['template']) == '/Script/SQEXSEAD.Default__SQEXSEADSound'
        assert z.header_end % 16 == 0
        imports = sorted(e['imports'])
        assert imports == sorted([W.package_id('/Game/Sound/Config/Attenuation/player'), W.package_id('/Game/Sound/Config/AliasSetting/VO_PC0010_00_Sephiroth')])
        g, q = [], z.graph_off + 4
        for _ in range(struct.unpack_from('<i', d, z.graph_off)[0]):
            pid, arcs = struct.unpack_from('<Qi', d, q)
            assert arcs == 1 and struct.unpack_from('<ii', d, q + 12) == (0, 0)
            g.append(pid)
            q += 12 + 8 * arcs
        assert g == imports, (g, imports)
        cls, v, end, data = uprops.read_export(u, z, 0, paths)
        assert cls == 'SQEXSEADSound'
        table = v.value['SoundNameIndexTable'].value
        alias = v.value['SoundNameAliasSetting'].value
        att = v.value['AttenuationSettings'].value
        assert z.imports[-1 - alias] == imp('/Game/Sound/Config/AliasSetting/VO_PC0010_00_Sephiroth.VO_PC0010_00_Sephiroth')
        assert z.imports[-1 - att] == imp('/Game/Sound/Config/Attenuation/player.player')
        assert abs(v.value['Duration'].value - 10000.0) < 1e-3
        at = data.find(b'sabf')
        assert (z.header_end + at) % 16 == 0
        size = struct.unpack_from('<I', data, at + 0x0C)[0]
        assert struct.unpack_from('<II', data, at - 8) == (size, size) and struct.unpack_from('<I', data, end + 4)[0] == size + 16
        assert len(data) == at + size + 0x30
        b = sead2.Bank(data[at:at + size])
        assert b.name == 'VO_PC0010_13_YoungSephiroth' and len(b.snd) == len(table) == len(lines)
        lang = 'JP' if '/JP/' in p else 'US'
        snrs = []
        for k in range(len(b.snd)):
            sd = b.sound(k)
            key, val = table[k]
            assert key.value == sd['name'] and val.value['SoundIndex'].value == k
            assert abs(val.value['Duration'].value - sd['length']) < 1e-6
            spec_line = lines[sd['name']]
            mi = b.material_of_sound(k)
            assert mi == int(spec_line['id'])
            m = b.material(mi)
            assert m['codec'] == 7 and m['channels'] == 1 and m['rate'] == 32000
            hca = m['extra'][16:] + m['stream']
            info = sead.hca_header(m['extra'][16:])
            r = subprocess.run(['ffmpeg', '-v', 'error', '-f', 'hca', '-i', '-', '-f', 'f32le', '-acodec', 'pcm_f32le', '-'], input=hca, capture_output=True)
            assert r.returncode == 0, r.stderr
            y = np.frombuffer(r.stdout, dtype='<f4')
            samples = info['blocks'] * 1024 - info['mute_head'] - info['mute_foot']
            y = y[info['mute_head']:info['mute_head'] + samples]
            x, sr = sf.read(spec_line[lang])
            assert len(x) == samples, (sd['name'], len(x), samples)
            if (x ** 2).sum() > 0:
                snrs.append(10 * np.log10((x ** 2).sum() / max(1e-20, ((x - y) ** 2).sum())))
        print('  %-70s %d sounds, decoded SNR min %.1f median %.1f dB, %d bytes' % (p, len(b.snd), min(snrs), np.median(snrs), len(d)))
    # the localization record
    if recs:
        ids = list(struct.unpack_from('<%dQ' % n, hdr, 36))
        o = 36 + 8 * n
        sz = struct.unpack_from('<i', hdr, o)[0]
        o += 4 + sz + 8
        blob_size = struct.unpack_from('<i', hdr, o)[0]
        blob = hdr[o + 4:o + 4 + blob_size]
        src = store[W.package_id(source)]
        rec = blob[src['pad']:]
        k = rec[1]
        variants = struct.unpack_from('<%dQ' % k, rec, 8)
        names = {W.package_id(p): p for p in pkgs}
        print('  record of', source, rec[:8].hex(), '->', [names.get(v, hex(v)) for v in variants])
    print('ok')

main(sys.argv[1], sys.argv[2])
