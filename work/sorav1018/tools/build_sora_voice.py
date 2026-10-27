"""Sora's battle voice in Cloud's slot (SoraVoice_P): Cloud's three US battle voice banks (VO_PC0000_00_Cloud,
_01_Cloud_Past, _02_Cloud_Insanity) with the sounds of the aliases below replaced by the KH2 Sora battle lines
(Battle_Sora_Project of the KH3 mod: 180 WAVs, their KH3 cue users in TrackUsers.txt), encoded to HCA (v2.00, mono,
frame 0x155, unencrypted: the same layout as the game's own voice materials). The banks' cue names, ids, sequences and
tracks stay; every other sound of the banks is silent (volume 0), so none of Cloud's lines play. Built on Vincent's
voice build (vinvoice1016/tools/build_voice.py: bank rewrite, package sizes, container).
    build_sora_voice.py <out dir>"""
import array
import io
import json
import os
import struct
import sys
import wave

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = ['/work/vinvoice1016/tools', '/work/vinsnd1016/tools', '/work/cs',
                '/work/iostore', '/work/sephatb/tools', os.path.join(HERE, 'ext', 'old')]
import CriCodecs        # noqa: E402  (PyCriCodecs 0.4.9's codec, built here)
import sead2            # noqa: E402
import build_voice as BV  # noqa: E402

WAV = os.path.join(HERE, 'wav')
GAIN = 0.78             # Sora's lines are ~2.2 dB louder than Cloud's (median active RMS 10781 vs 8397)
RATE = 48000

T = json.load(open(os.path.join(HERE, 'sora_tracks.json')))
DUR = {int(k): v for k, v in T['dur'].items()}
CATS = {int(k): v for k, v in T['cats'].items()}

ATTACK = sorted([i for i, c in CATS.items() if c == 'attack'] + [45, 53, 55, 62, 63, 64, 68, 69, 70, 73, 74] +
                list(range(99, 115)))
ATK_SHORT = [i for i in ATTACK if DUR[i] < 0.5]
ATK_MED = [i for i in ATTACK if 0.5 <= DUR[i] < 0.9]
ATK_LONG = [i for i in ATTACK if DUR[i] >= 0.9]
CAST = [42, 47, 52, 61]
DMG_S = [23, 24, 25, 26, 27]
DMG_B = [28, 29, 30, 31]
DEAD = [33, 34, 36, 37, 38]


def k(ids):
    return ['s%03d' % i for i in ids]


VOICED = {}
for a in ('Atk_Normal_01', 'Atk_Normal_02', 'Atk_Normal_03', 'Atk_Normal_04', 'Atk_Normal_05', 'Atk_Normal_01_Move',
          'Atk_Air_01', 'Atk_Air_02', 'Atk_Air_03', 'Avoid_02', 'Avoid_03', 'Avoid_Start', 'Guard_Start',
          'Guard_Success_01', 'Guard_Success_02', 'Parry_01', 'penetrate_01', 'Atk_Unique_Counter_01',
          'Atk_Unique_Counter_02', 'Atk_Unique_Counter_03'):
    VOICED[a] = k(ATK_SHORT)
MED = ('Atk_Ability_', 'Atk_Unique_', 'Atk_Normal_Combi_')
LIMIT = ('Atk_Limit_01', 'Atk_Limit_02', 'Atk_Limit_03', 'Atk_Limit_03_02', 'Atk_Limit_Start')
SPECIAL = {
    'Magic_Attribute_Fire': k([78, 79]), 'Magic_Attribute_Ice': k([80, 81]), 'Magic_Attribute_Thunder': k([82, 83]),
    'Magic_Attribute_Wind': k([84, 85]), 'Magic_Attribute_Common': k(CAST + [88, 89]), 'Magic_Add_Cast': k(CAST),
    'Magic_Barrier': k([86, 87, 77]), 'Magic_Resist': k([86, 87, 77]), 'Magic_Hast': k([77, 86, 87]),
    'Damage_01': k(DMG_S), 'Damage_02': k(DMG_S), 'Damage_03': k(DMG_B), 'Damage_04': k(DMG_B),
    'Damage_Catch_01': k(DMG_B), 'Damage_Catch_02': k(DMG_B), 'Damage_Catch_03': k(DMG_B),
    'Damage_Stun_01': k([23, 26, 28]), 'Damage_Stun_02': k([31, 24]), 'Damage_Stun_03': k([29, 27]),
    'Damage_Sleep_01': k([25]), 'Damage_Sleep_02': k([25]), 'Damage_Sleep_03': k([25]),
    'Dead_Self': k(DEAD), 'GameOver': k([36, 37]), 'Change_02_Dead': k([33, 34]),
    'Return_Dead': k([39, 40, 41]), 'Return_Down_01': k([25, 26]), 'Return_Down_02': k([23, 24]),
    'item_01': k([117, 118]), 'item_02': k([118, 117]), 'item_03': k([117, 118]),
    'Atk_Enemy_Down': k(ATK_MED), 'Atk_Finish': k(ATK_LONG), 'Burst_Start': k(ATK_MED), 'Buff_01': k(CAST),
    'Steal': k(ATK_SHORT),
}
for p in ('Magic_Debuff_Common', 'Magic_Debuff_Death', 'Magic_Debuff_Despell', 'Magic_Debuff_Poison',
          'Magic_Debuff_Silence', 'Magic_Debuff_Sleep', 'Magic_Debuff_Slow'):
    SPECIAL[p] = k(CAST + [77])


PRIORITY = ('Dead_Self', 'GameOver', 'Change_02_Dead', 'Damage_', 'Return_', 'item_', 'Magic_Attribute_', 'Magic_',
            'Atk_Limit_', 'Atk_Finish', 'Atk_Enemy_Down', 'Burst_Start', 'Atk_Ability_', 'Atk_Unique_', 'Atk_Normal_Combi_')


def rank(a):
    """Shared cues (a recorded line the bank uses for several aliases) take the line of the first alias that claims
    them: the specific kinds (KO, damage, items, magic) go first, the attack pools last."""
    for r, p in enumerate(PRIORITY):
        if a.startswith(p):
            return r
    return len(PRIORITY)


def voiced_for(aliases):
    """The alias -> line keys table for the aliases a bank has, in claiming order (rank)."""
    out = {}
    for a in sorted(aliases, key=lambda x: (rank(x), list(aliases).index(x))):
        if a in SPECIAL:
            out[a] = SPECIAL[a]
        elif a in VOICED:
            out[a] = VOICED[a]
        elif a in LIMIT:
            out[a] = k(ATK_LONG)
        elif a.startswith(MED):
            out[a] = k(ATK_MED)
    return out


def pcm_of(i):
    w = wave.open(os.path.join(WAV, 'Battle_Sora_%03d.wav' % i))
    assert w.getnchannels() == 1 and w.getsampwidth() == 2
    s = np.frombuffer(w.readframes(w.getnframes()), dtype='<i2').astype(np.float64)
    if w.getframerate() != RATE:
        n = int(round(len(s) * RATE / w.getframerate()))
        s = np.interp(np.linspace(0, len(s) - 1, n), np.arange(len(s)), s)
    return np.clip(np.round(s * GAIN), -32767, 32767).astype('<i2')


def material(i):
    """A SEAD material dict (head, extra, stream, length) of line i: HCA of its PCM, the 0x10 SEAD header before it."""
    pcm = pcm_of(i)
    buf = io.BytesIO()
    w = wave.open(buf, 'wb')
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(RATE)
    w.writeframes(pcm.tobytes())
    w.close()
    hca = CriCodecs.HcaEncode(buf.getvalue(), 1, 1)
    assert hca[:4] == b'HCA\0' and struct.unpack_from('>H', hca, 4)[0] == 0x200, hca[:8]
    hdr = struct.unpack_from('>H', hca, 6)[0]
    comp = hca.find(b'comp', 0, hdr)
    fmt = hca.find(b'fmt\0', 0, hdr)
    assert comp > 0 and fmt > 0 and hca.find(b'ciph', 0, hdr) > 0
    assert struct.unpack_from('>H', hca, hca.find(b'ciph', 0, hdr) + 4)[0] == 0
    frame = struct.unpack_from('>H', hca, comp + 4)[0]
    mute_head = struct.unpack_from('>H', hca, fmt + 12)[0]
    blocks = struct.unpack_from('>I', hca, fmt + 8)[0]
    assert len(hca) == hdr + blocks * frame, (len(hca), hdr, blocks, frame)
    extra = struct.pack('<BBHHHHHHH', 1, 0x10, hdr, frame, 0, 0, mute_head, 0, 0) + hca[:hdr]
    stream = hca[hdr:]
    head = struct.pack('<BBHBBHIIIIII', 1, 0, 0x20, 1, 7, 0, RATE, 0, 0, len(extra), len(stream), 0)
    assert len(head) == 0x20 and len(extra) == 0x10 + hdr
    m = dict(head=head, extra=extra, stream=stream, rate=RATE, channels=1, codec=7)
    m['length'] = sead2.Bank.hca_length(extra, RATE)
    assert abs(m['length'] - len(pcm) / RATE) < 0.002, (i, m['length'], len(pcm) / RATE)
    # decodes back to what went in
    back = CriCodecs.HcaDecode(hca, hdr, 0, 0)
    bw = wave.open(io.BytesIO(back))
    assert bw.getnframes() == len(pcm), (i, bw.getnframes(), len(pcm))
    return m


def main():
    out_dir = sys.argv[1]
    os.makedirs(out_dir, exist_ok=True)
    keys = sorted({x for v in list(VOICED.values()) + list(SPECIAL.values()) for x in v} | set(k(ATK_LONG + ATK_MED)))
    lines = {key: material(int(key[1:])) for key in keys}
    BV.NAME = 'SoraVoice_P'
    BV.L = {key: 'Battle_Sora_%s' % key[1:] for key in lines}
    report = ['Sora lines used: %d of 180 (attack pool %d: short %d, medium %d, long %d)' % (
        len(lines), len(ATTACK), len(ATK_SHORT), len(ATK_MED), len(ATK_LONG))]
    # each bank gets the table for its own aliases
    import alias
    tables = {}
    for name in BV.BANKS:
        _, rows, _, _ = alias.read(BV.pkg('Sound/Config/AliasSetting/' + name))
        tables[name] = voiced_for([r[0] for r in rows])
    orig_build_bank = BV.build_bank

    def build_bank(name, lns, rep):
        BV.VOICED = tables[name]
        return orig_build_bank(name, lns, rep)
    BV.build_bank = build_bank
    sys.argv = [sys.argv[0], out_dir]
    BV.main.__globals__['vincent_lines'] = lambda: lines
    BV.main()
    with open(os.path.join(out_dir, 'report.txt')) as f:
        text = f.read().replace("Vincent's", "Sora's")
    with open(os.path.join(out_dir, 'report.txt'), 'w') as f:
        f.write('\n'.join(report) + '\n' + text)
    json.dump({n: t for n, t in tables.items()}, open(os.path.join(out_dir, 'aliases.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
