"""FullyPlayableYoungSephirothDataAssets_P v7: v6 with the sword auras changed.
  * WE1021_00_SephirothIllusion_Masamune (the Nameless of the normal form, SephirothSwordFX_P's blueprint wearing WE1021_49):
    its resident effect (the trail FX_PC0010_BurstChain00_10_01_Trail_02 on C_Body_a) is off: m_bEnable false and its
    template None. Same bytes otherwise (in place, no size change).
  * WE1021_10_SephirothIllusion_MasamuneCutScale (the forms' Masamune): its resident effect plays the PC0010_10 boss's
    sword aura, FX_PC0010_10_SetFeeler_Sword_01 (the feeler aura over the blade's mesh), in place of the trail: the template's
    name in the name map renamed (the name map and its hashes rebuilt, the header offsets after it moved).
Everything else of v6 is byte for byte; the container keeps its name and id.
    build_fpys_data_v7.py <out dir (new)> <v6 .utoc>"""
import hashlib, os, shutil, struct, sys
sys.path[:0] = ['/work/fpys/tools', '/work/evilboss1016/data', '/work/iostore', '/work/cs',
                '/work/weap1012/tools', '/work/evil1013/tools', '/work/swap1012/tools', '/work/vincentfix']
from zen import Zen
from iostore import Toc
import iostore_write as W
import hdr
import zenrename
import build_evilcloud_data as BED
import build_fpys_data as B
import build_fpys_data_v6 as V6

NAMELESS_BP = 'BluePrint/Character/Weapon/WE1021_00_SephirothIllusion_Masamune.uasset'
FORMS_BP = 'BluePrint/Character/Weapon/WE1021_10_SephirothIllusion_MasamuneCutScale.uasset'
TRAIL = '/Game/Effect/Character/Player/PC0010_Sephiroth/Particle/FX_PC0010_BurstChain00_10_01_Trail_02.FX_PC0010_BurstChain00_10_01_Trail_02'
FEELER = '/Game/Effect/Character/Player/PC0010_10_Sephiroth_Transform/Particle/FX_PC0010_10_SetFeeler_Sword_01.FX_PC0010_10_SetFeeler_Sword_01'


def resident_effect(data):
    """The one resident effect of a weapon blueprint's class default object: positions (in the package) of its m_bEnable
    value byte and its m_Template's FName, and the template's name."""
    z = Zen(data)
    pos = z.bundle_positions()
    cdo = [k for k, e in enumerate(z.exports) if e['name'].startswith('Default__')]
    assert len(cdo) == 1, cdo
    start, size = pos[cdo[0]]
    e = data[start:start + size]
    t = V6.Tags(z.names, e)
    o = 0
    found = None
    while o < len(e):
        p = t.tag(o)
        if p['name'] == 'None':
            break
        if p['name'] == 'ResidentEffects':
            assert p['type'] == 'ArrayProperty' and p['extra'] == 'StructProperty'
            assert struct.unpack_from('<i', e, p['value'])[0] == 1, 'one resident effect'
            inner = t.tag(p['value'] + 4)
            assert inner['extra'] == 'EndCharacterResidentEffect'
            q = t.tag(inner['value'])
            assert q['name'] == 'm_NiagaraCreateParams', q
            r = q['value']
            enable = template = None
            while True:
                x = t.tag(r)
                if x['name'] == 'None':
                    break
                if x['name'] == 'm_bEnable':
                    assert x['type'] == 'BoolProperty'
                    enable = x['size_at'] + 8
                if x['name'] == 'm_NiagaraParameterInfo':
                    y = t.tag(x['value'])
                    assert y['name'] == 'm_Template' and y['extra'] == 'SoftObjectPath', y
                    template = y['value']
                r = x['end']
            assert enable is not None and template is not None
            index, number = struct.unpack_from('<II', e, template)
            found = (start + enable, start + template, z.names[index], number)
        o = p['end']
    assert found, 'no ResidentEffects'
    return found


def nameless_off(data):
    """In place: the resident effect off (m_bEnable false) and its template None."""
    enable_at, template_at, name, number = resident_effect(data)
    assert name == TRAIL and number == 0, name
    assert data[enable_at] == 1
    z = Zen(data)
    none = z.names.index('None')
    out = bytearray(data)
    out[enable_at] = 0
    struct.pack_into('<II', out, template_at, none, 0)
    out = bytes(out)
    e2, t2, n2, _ = resident_effect(out)
    assert out[e2] == 0 and n2 == 'None' and len(out) == len(data)
    assert sum(a != b for a, b in zip(out, data)) <= 5
    return out


def forms_feeler(data):
    """The template's name renamed from the trail to the boss's sword aura."""
    enable_at, template_at, name, number = resident_effect(data)
    assert name == TRAIL and number == 0 and data[enable_at] == 1, name
    z = Zen(data)
    assert z.names.count(TRAIL) == 1 and FEELER not in z.names
    out = zenrename.rebuild(data, {TRAIL: FEELER})
    z2 = Zen(out)
    e2, t2, n2, _ = resident_effect(out)
    assert n2 == FEELER and out[e2] == 1
    assert z2.names == [FEELER if n == TRAIL else n for n in z.names]
    assert z2.imports == z.imports and [x['serial_size'] for x in z2.exports] == [x['serial_size'] for x in z.exports]
    assert out[z2.header_end:] == data[z.header_end:], 'the export data changed'
    return out


def main(out, base_utoc):
    assert not os.path.exists(out), out + ' exists (use a new folder)'
    base_ucas = base_utoc[:-len('.utoc')] + '.ucas'
    old = Toc(base_utoc)
    assert [i for i in range(old.entries) if old.chunk_type(i) == 10] == [0]
    cid, store = hdr.parse_header(old.read(0))
    assert cid == W.container_id_from_name(B.NAME)
    order = [old.chunk_id64(i) for i in range(old.entries) if old.chunk_type(i) == 2]
    entries = [dict(id=p, size=store[p]['size'], export_count=store[p]['export_count'], export_bundle_count=store[p]['export_bundle_count'],
                    load_order=store[p]['load_order'], imports=list(store[p]['imports'])) for p in order]
    assert W.container_header(cid, entries) == old.read(0), 'the header does not write back as it is'
    entry_of = {e['id']: e for e in entries}
    by_path = {old.files[i][len(B.MOUNT):]: i for i in old.files}
    changes, report = {}, []
    for path, fix, what in ((NAMELESS_BP, nameless_off, 'resident effect off (m_bEnable false, template None)'),
                            (FORMS_BP, forms_feeler, 'resident effect plays FX_PC0010_10_SetFeeler_Sword_01')):
        i = by_path[path]
        data = old.read(i)
        new = fix(data)
        e = entry_of[old.chunk_id64(i)]
        assert e['size'] in (0, len(data)), (path, e['size'], len(data))
        if e['size']:
            e['size'] = len(new)
        changes[i] = new
        report.append('%s: %s (%d -> %d bytes)' % (path.rsplit('/', 1)[1], what, len(data), len(new)))
    changes[0] = W.container_header(cid, entries)
    os.makedirs(out)
    path = os.path.join(out, B.NAME)
    BED.append_container(old, base_ucas, changes, [], path + '.utoc', path + '.ucas.tail')
    with open(path + '.ucas', 'wb') as f:
        with open(base_ucas, 'rb') as g:
            shutil.copyfileobj(g, f, 1 << 24)
        f.write(open(path + '.ucas.tail', 'rb').read())
    shutil.copy(base_utoc[:-len('.utoc')] + '.pak', path + '.pak')
    new = Toc(path + '.utoc')
    assert new.container_id == cid and new.entries == old.entries
    same = 0
    for k in range(new.entries):
        d = new.read(k)
        assert hashlib.sha1(d).digest() == new.b[new.metas_off + 33 * k:new.metas_off + 33 * k + 20]
        if k in changes:
            assert d == changes[k]
        else:
            assert d == old.read(k) and new.files.get(k) == old.files.get(k)
            same += 1
    cid2, ents = hdr.parse_header(new.read(0))
    for e in entries:
        b = ents[e['id']]
        for key in ('size', 'export_count', 'export_bundle_count', 'load_order', 'imports'):
            assert b[key] == e[key], key
    report.append('%d chunks byte for byte v6\'s; the header and %d packages changed' % (same, len(changes) - 1))
    for line in report:
        print(line)
    for f in sorted(os.listdir(out)):
        p = os.path.join(out, f)
        print('  %-48s %10d %s' % (f, os.path.getsize(p), hashlib.md5(open(p, 'rb').read()).hexdigest()))


if __name__ == '__main__':
    main(*sys.argv[1:3])
