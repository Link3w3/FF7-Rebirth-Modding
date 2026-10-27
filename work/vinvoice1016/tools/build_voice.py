"""Vincent's battle voice in Cloud's slot (VincentVoice_P): Cloud's three voice banks (VO_PC0000_00_Cloud, _01_Cloud_Past,
_02_Cloud_Insanity; the US ones) with the sounds of some aliases replaced by Vincent's own lines from the game (his
Nibelheim quest, the card game, the story), the bank's own cue names, ids, sequences and tracks kept; every other sound
of the banks is silent (volume 0), so Cloud's grunts, callouts and banter are gone. The game picks an alias's sound as
it always does (its alias setting, unchanged), so a replaced alias always says one of Vincent's lines.
    build_voice.py <out dir>"""
import json, os, re, shutil, struct, sys
sys.path[:0] = [os.path.dirname(os.path.abspath(__file__)), '/work/vinsnd1016/tools', '/work/cs',
                '/work/iostore', '/work/sephatb/tools']
import sead, sead2, alias
from zen import Zen
import iostore_write as W
from iostore import Toc

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKGS = os.path.join(HERE, 'pkgs')
NAME = 'VincentVoice_P'
MOUNT = '../../../End/Content/'
PAK_STUB = '/work/aval1016/out1/AvalancheSephirothOutfit_P.pak'
RETAIL_HEADER = '/work/retailhdr/pakchunk4_header.bin'   # pakchunk4's container header (the banks' entries)
BANKS = ['VO_PC0000_00_Cloud', 'VO_PC0000_01_Cloud_Past', 'VO_PC0000_02_Cloud_Insanity']
LANG = 'US'

# ---- Vincent's lines (US keys; the text is the game's subtitle)
L = {
    'go': 'NIBLE_QST_03_1600_0400_00_vin',            # Let's go.
    'ready': 'C3310_MAIN_0400_0900_00_vin',           # Hope you're ready for a fight.
    'duel': 'CARDG_QST_06_0100_1000_00_vin',          # A duel it is.
    'brief': 'C3110_MAIN_5400_0810_00_vin',           # Be brief.
    'find_out': 'NIBLE_QST_03_0800_1100_00_vin',      # We'll soon find out.
    'job': 'NIBLE_QST_03_0600_0300_00_vin',           # Gotta do my job sometime.
    'slumber': 'C3110_MAIN_5400_0200_00_vin',         # Who dares disturb my slumber?
    'hmph': 'C3110_MAIN_5400_1300_00_vin',            # Hmph.
    'diverting': 'CARDG_QST_06_0300_0200_00_vin',     # Diverting, if nothing else.
    'better_match': 'CARDG_QST_06_0300_0300_00_vin',  # I'd hoped for a better match than that.
    'ends_well': 'CARDG_QST_07_0300_2900_00_vin',     # All's well that ends well, I suppose.
    'dying': 'CARDG_QST_07_0300_3100_00_vin',         # Couldn't have you dying on me just yet.
    'not_blame': 'CARDG_QST_07_0300_2000_00_vin',     # You are not to blame for this.
    'expectations': 'C3310_MAIN_2100_0200_00_vin',    # Expectations often lead to disappointment.
    'sleep': 'C3110_MAIN_5500_0300_00_vin',           # Let me sleep.
    'resting': 'NIBLE_QST_03_1300_0100_00_vin',       # Just resting my eyes.
    'even_better': 'C3310_MAIN_0100_0400_00_vin',     # Even better.
    'get_out': 'C3110_MAIN_6200_1200_00_vin',         # Get out... Now.
    'sin': 'C3110_MAIN_5400_3100_00_vin',             # Then I've one more sin to atone for.
    'come': 'C3340_MAIN_1200_2000_00_vin',            # Come.
    'well': 'C3110_MAIN_5400_0400_00_vin',            # Well?
    'need': 'CARDG_QST_06_0100_0100_00_vin',          # Need something?
    'loud': 'NIBLE_QST_03_0800_0700_00_vin',          # Loud and clear.
    'trouble': 'NIBLE_QST_03_1300_0200_00_vin',       # You having trouble?
    'oh': 'NIBLE_QST_03_0700_0500_00_vin',            # Oh?
    'scared': 'NIBLE_QST_03_0400_1100_00_vin',        # Hmph... Scared?
    'enough': 'NIBLE_QST_03_0500_0100_00_vin',        # Had enough, then?
}
START = ['go', 'ready', 'duel', 'brief', 'find_out', 'job']
VOICED = {
    'Btl_Start_Monster_01': START, 'Btl_Start_Shinra_01': START, 'Btl_Start_Shinra_02': START,
    'Btl_Start_Monster_02': ['slumber', 'ready', 'duel', 'go'], 'Btl_Start_Secret_01': ['slumber', 'duel'],
    'Victory_01_Self': ['hmph', 'diverting', 'better_match', 'ends_well'], 'Victory_02_self': ['hmph', 'diverting', 'ends_well'],
    'Squat_Victory_01': ['diverting'],
    'Victory_02_Dead': ['dying', 'not_blame'],
    'GameOver': ['expectations'],
    'Dead_Self': ['sleep'],
    'Return_Dead': ['resting'],
    'Recover_04': ['even_better'], 'Recover_05': ['even_better'],
    'Atk_Limit_Start': ['get_out', 'sin'],
    'Summon_Start_0000': ['come'],
    'Change_01_Normal': ['well', 'need', 'loud'], 'Change_02_Normal': ['well', 'need', 'loud'],
    'Change_01_Crisis': ['trouble'], 'Change_02_Crisis': ['trouble'],
    'Change_01_Normal_Burst': ['oh'], 'Change_02_Normal_Burst': ['oh'],
    'Burst_Start': ['scared'],
    'Atk_Enemy_Down': ['enough'],
    'Atk_Finish': ['hmph'],
}


def pkg(path):
    return open(os.path.join(PKGS, path.replace('/', '__') + '.uasset'), 'rb').read()


def vincent_lines():
    files = {f.split('__')[-1][:-7]: os.path.join(PKGS, f) for f in os.listdir(PKGS) if f.endswith('_vin.uasset')}
    out = {}
    for k, key in L.items():
        d = open(files[key], 'rb').read()
        _, s = sead.sab_of(d)
        b = sead2.Bank(s)
        m = b.material(b.material_of_sound(0))
        assert m['codec'] == 7 and m['channels'] == 1 and m['rate'] == 32000, (key, m['codec'], m['channels'], m['rate'])
        out[k] = m
    return out


def block_size_at(e, at, sab_size):
    """Where the SQEXSEADSound export keeps the size of its data block (the 16 bytes before the sab and the sab): a u32
    sab size + 16 followed by 00 00 01 00 10 00 (then a u16 pad count and that many zeros, so the block starts 16-aligned).
    The game reads the block by this size and then the 0x30 bytes after it (the bCooked flag among them): left at the old
    size, it reads them from inside a bigger sab and stops with "audio data was not cooked into SQEXSEADSound" (v1's crash
    of 2026-10-16). AudioMog (FixTotalFileSizeStep, its 2025 branch) updates the same three sizes."""
    pat = struct.pack('<I', sab_size + 16) + b'\x00\x00\x01\x00\x10\x00'
    hits = [i for i in range(max(0, at - 128), at) if e[i:i + len(pat)] == pat]
    assert len(hits) == 1, ('data block size field', hits)
    p = hits[0]
    pad = struct.unpack_from('<H', e, p + 10)[0]
    assert p + 12 + pad == at - 16 and not any(e[p + 12:at - 16]), ('pad', p - at, pad)
    assert e[at - 16:at - 8] == b'\x21' + b'\0' * 7, e[at - 16:at - 8].hex()
    return p


def rebuild_package(d, new_sab):
    """The bank package with its sab blob replaced (its three size fields and the export's size updated)."""
    z = Zen(d)
    assert len(z.exports) == 1
    e = z.export_data(0)
    at = e.find(b'sabf')
    old = struct.unpack_from('<I', e, at + 0x0C)[0]
    assert struct.unpack_from('<II', e, at - 8) == (old, old), e[at - 16:at].hex()
    tail = e[at + old:]
    assert len(tail) == 0x30, len(tail)
    assert len(new_sab) % 16 == 0 and struct.unpack_from('<I', new_sab, 0x0C)[0] == len(new_sab)
    p = block_size_at(e, at, old)
    ne = bytearray(e[:at]) + new_sab + tail
    struct.pack_into('<II', ne, at - 8, len(new_sab), len(new_sab))
    struct.pack_into('<I', ne, p, len(new_sab) + 16)
    start = z.header_end + (z.exports[0]['serial_offset'] - z.cooked_header_size if z.exports[0]['serial_offset'] >= z.cooked_header_size
                            else z.exports[0]['serial_offset'])
    assert start + len(e) == len(d), (start, len(e), len(d))
    head = bytearray(d[:start])
    struct.pack_into('<Q', head, z.exp_off + 8, len(ne))
    return bytes(head) + bytes(ne)


def build_bank(name, lines, report):
    path = 'Sound/Voice/%s/Character/Player/%s' % (LANG, name)
    d = pkg(path)
    _, sab = sead.sab_of(d)
    b = sead2.Bank(sab)
    _, rows, _, _ = alias.read(pkg('Sound/Config/AliasSetting/' + name))
    by_alias = {a: [('%s_%d' % (n, num - 1)) if num else n for n, num, w in s] for a, s, sil, ig, _ in rows}
    index = {b.sound(i)['name']: i for i in range(len(b.snd))}
    cue_line = {}
    for a, keys in VOICED.items():
        cues = by_alias.get(a)
        if not cues:
            report.append('  %s: no alias %s' % (name, a))
            continue
        for k, cue in enumerate(cues):
            if cue in cue_line or cue not in index:
                continue
            cue_line[cue] = keys[k % len(keys)]
    replacements = {}
    voiced = muted = 0
    for i in range(len(b.snd)):
        sd = b.sound(i)
        k = cue_line.get(sd['name'])
        if k is None:
            b.set_sound(i, volume=0.0)
            muted += 1
            continue
        m = lines[k]
        mi = b.material_of_sound(i)
        replacements[mi] = m
        b.set_sound(i, length=round(m['length'], 3))
        b.set_play_length(sd['seq_index'], round(m['length'], 3))
        voiced += 1
    new_sab = b.write(replacements)
    out = rebuild_package(d, new_sab)
    # ---- read back
    z = Zen(out)
    e = z.export_data(0)
    # as the game reads it: the data block by its size, then the same 0x30 bytes as the game's own bank (bCooked set)
    at = e.find(b'sabf')
    sab_size = struct.unpack_from('<I', e, at + 0x0C)[0]
    p = block_size_at(e, at, sab_size)
    block = struct.unpack_from('<I', e, p)[0]
    assert block == sab_size + 16 and struct.unpack_from('<II', e, at - 8) == (sab_size, sab_size)
    orig = Zen(d).export_data(0)
    assert e[at - 16 + block:] == orig[-0x30:] and len(e) == at - 16 + block + 0x30
    assert e[:p] == orig[:p] and e[p + 4:at - 8] == orig[p + 4:at - 8]
    assert (z.header_end + at) % 16 == 0 and len(e) % 16 == 0
    _, s2 = sead.sab_of(e)
    b2 = sead2.Bank(s2[:struct.unpack_from('<I', s2, 0x0C)[0]])
    assert len(b2.snd) == len(b.snd)
    for i in range(len(b2.snd)):
        sd = b2.sound(i)
        m2 = b2.material(b2.material_of_sound(i))
        k = cue_line.get(sd['name'])
        if k is None:
            assert sd['volume'] == 0.0, sd
        else:
            assert m2['stream'] == lines[k]['stream'] and m2['extra'] == lines[k]['extra'], sd['name']
            assert abs(sd['length'] - lines[k]['length']) < 0.002
    report.append('%s (%s): %d sounds, %d of them Vincent\'s now (%d aliases), %d silent; %d -> %d bytes' % (
        name, LANG, len(b.snd), voiced, len([a for a in VOICED if a in by_alias]), muted, len(d), len(out)))
    for a in VOICED:
        if a in by_alias:
            report.append('    %-24s %s' % (a, ', '.join(sorted({cue_line[c] for c in by_alias[a] if c in cue_line}))))
    return path, out


def main():
    out_dir = sys.argv[1]
    os.makedirs(out_dir, exist_ok=True)
    report = []
    lines = vincent_lines()
    for k, m in sorted(lines.items()):
        report.append('  line %-13s %-32s %.2f s' % (k, L[k], m['length']))
    chunks, entries = [None], []
    import build_atb as B
    sys.path.insert(0, '/work/swap1012/tools')
    from hdr import parse_header
    _, retail = parse_header(open(RETAIL_HEADER, 'rb').read())
    for name in BANKS:
        path, data = build_bank(name, lines, report)
        pid = W.package_id('/Game/' + path)
        chunks.append(dict(id64=pid, type=2, data=data, path=path + '.uasset'))
        # the game's own entry for the bank (pakchunk4): its export alignment shift (4) and load order kept
        r = retail[pid]
        e = B.store_entry(pid, data)
        assert r['size'] >> 60 == 4 and r['export_count'] == e['export_count'] and r['export_bundle_count'] == e['export_bundle_count']
        assert sorted(r['imports']) == sorted(e['imports']), (name, r['imports'], e['imports'])
        e['imports'] = r['imports']
        e['size'] = len(data) | (r['size'] >> 60) << 60
        e['load_order'] = r['load_order']
        entries.append(e)
    cid = W.container_id_from_name(NAME)
    chunks[0] = dict(id64=cid, type=10, data=W.container_header(cid, entries), path=None)
    outb = os.path.join(out_dir, NAME)
    W.write_container(outb, NAME, chunks, mount=MOUNT)
    shutil.copy(PAK_STUB, outb + '.pak')
    back = Toc(outb + '.utoc')
    assert back.entries == len(chunks)
    for i, c in enumerate(chunks):
        assert back.read(i) == c['data']
        if c['path']:
            assert back.files.get(i) == MOUNT + c['path'], back.files.get(i)
    open(os.path.join(out_dir, 'report.txt'), 'w').write('\n'.join(report) + '\n')
    print('\n'.join(report))


if __name__ == '__main__':
    main()
