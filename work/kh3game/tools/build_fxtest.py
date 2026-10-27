"""KH3FxTest_P: KH3's keyblade appear effect (VW_SO010_APP0, converted to Niagara in the End editor, cooked there with
its 5 meshes) with its 10 KH3 material imports pointed at the game's own particle material RMI_Particle_Emit, so the
only new thing the game has to accept is a Niagara system cooked by the End editor. Read back chunk by chunk.
    build_fxtest.py <retoc .utoc> <out dir> [material object path]"""
import hashlib, os, sys
sys.path[:0] = ['/work/soradata', '/work/iostore', '/work/cs', '/work/fx1018/editor/Python',
                '/work/custmat', '/work/weap1012/tools']
import build_sora_assets as B
import build_sora_bps as S
import iostore_write as W
import hdr
from iostore import Toc
from zen import Zen
from custom_mi import replace_import
from rebirth_fx import matcore

NAME = 'KH3FxTest_P'
MOUNT = '../../../End/Content/'
SYSTEM = 'KH3/w_so010/Cascade/VW_SO010_APP0_Converted.uasset'
KH3_MATERIALS = ['/Game/KH3/Effects/texcom/mat_mdl/jmi_sho_00a', '/Game/KH3/Effects/texcom/mat_part/jmi_glt_05k',
                 '/Game/KH3/Effects/texcom/mat_part/jmi_glw_01sk', '/Game/KH3/Effects/trescom/mat_mdl/nmi_ora_01sla',
                 '/Game/KH3/Effects/trescom/mat_mdl/zmi_rng_00sa', '/Game/KH3/Effects/trescom/mat_part/tmi_fls_05a',
                 '/Game/KH3/Effects/trescom/mat_part/zmi_crs_03csk', '/Game/KH3/Effects/trescom/mat_part/zmi_glw_00sk',
                 '/Game/KH3/Effects/trescom/mat_part/zmi_glw_01sk', '/Game/KH3/Effects/wep/w_so010/mat/smt_frn_01a']
GAME_MATERIAL = '/Game/Renderer/MaterialInstance/Particle/RMI_Particle_Emit.RMI_Particle_Emit'


def obj(pkg):
    return pkg + '.' + pkg.rsplit('/', 1)[1]


def main(utoc, out_dir, material=GAME_MATERIAL):
    chunks, store = B.read(utoc)
    retail = dict(S.retail_entries())
    for extra in ('/work/custmat/pakchunk0_container_header.bin', '/work/custmat/pakchunk3_container_header.bin'):
        _, ents = hdr.parse_header(open(extra, 'rb').read())
        for pid, x in ents.items():
            retail.setdefault(pid, ('extra', x))
    ours = {c['id64'] for c in chunks if c['type'] == 2}
    entries = []
    for c in chunks:
        if c['type'] != 2:
            continue
        e = B.entry(c, store[c['id64']])
        if c['path'] == SYSTEM:
            data = c['data']
            for m in KH3_MATERIALS:
                data = replace_import(data, obj(m), material)
            z0, z1 = Zen(c['data']), Zen(data)
            assert len(z1.exports) == len(z0.exports)
            assert data[z1.header_end:] == c['data'][z0.header_end:], 'export data changed'
            gone = {W.package_id(m) for m in KH3_MATERIALS}
            assert gone <= set(e['imports']), 'not every KH3 material was imported'
            imports = [i for i in e['imports'] if i not in gone]
            mp = W.package_id(material.split('.')[0])
            if mp not in imports:
                imports.append(mp)
            e['imports'] = sorted(imports) if list(e['imports']) == sorted(e['imports']) else imports
            c['data'] = data
            e['size'] = len(data)
        missing = [hex(i) for i in e['imports'] if i not in retail and i not in ours]
        assert not missing, (c['path'], missing)
        entries.append(e)
    B.load_orders(chunks, entries)
    os.makedirs(out_dir, exist_ok=True)
    cid = W.container_id_from_name(NAME)
    allc = [dict(id64=cid, type=10, data=W.container_header(cid, entries), path=None)] + chunks
    base = os.path.join(out_dir, NAME)
    W.write_container(base, NAME, allc, mount=MOUNT)
    open(base + '.pak', 'wb').write(open(utoc[:-5] + '.pak', 'rb').read())
    back = Toc(base + '.utoc')
    cid2, ents = hdr.parse_header(back.read(0))
    by = {x['id']: x for x in entries}
    for i in range(1, back.entries):
        c = allc[i]
        assert back.read(i) == c['data'] and back.chunk_id64(i) == c['id64'], c['path']
        b, x = ents[c['id64']], by[c['id64']]
        assert (b['size'], b['load_order'], list(b['imports'])) == (x['size'], x['load_order'], x['imports']), c['path']
    for c in chunks:
        if c['type'] == 2:
            x = by[c['id64']]
            print('%-60s %7d bytes, load order %d, %d imported packages' % (c['path'], len(c['data']), x['load_order'], len(x['imports'])))
    for ext in ('utoc', 'ucas', 'pak'):
        p = base + '.' + ext
        print('%-20s %8d %s' % (os.path.basename(p), os.path.getsize(p), hashlib.md5(open(p, 'rb').read()).hexdigest()))


if __name__ == '__main__':
    main(*sys.argv[1:4])
