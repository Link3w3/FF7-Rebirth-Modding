"""The young voice bank's spec for cacs_soundbank: Sephiroth's US bank's sounds in its order, each with its volume,
category bytes, material id and length, its young US line and the young JP line of the JP bank's sound of that name."""
import os, sys, struct
sys.path[:0] = ['/work/vinsnd1016/tools', '/work/vinvoice1016/tools']
import sead, sead2
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def bank(lang):
    d = open(os.path.join(HERE, 'game', 'Sound__Voice__%s__Character__Player__VO_PC0010_00_Sephiroth.uasset' % lang), 'rb').read()
    _, sab = sead.sab_of(d)
    sab = sab[:struct.unpack_from('<I', sab, 0x0C)[0]]
    return sead2.Bank(sab), sab

us, usab = bank('US')
jp, _ = bank('JP')
jp_material = {jp.sound(i)['name']: jp.material_of_sound(i) for i in range(len(jp.snd))}
lines = ['container YoungSephirothVoice_P', 'bank VO_PC0010_13_YoungSephiroth', 'folder /Game/Sound/Voice/{language}/Character/Player',
         'alias /Game/Sound/Config/AliasSetting/VO_PC0010_00_Sephiroth', 'attenuation /Game/Sound/Config/Attenuation/player', 'kbps 85.25']
for i in range(len(us.snd)):
    sd = us.sound(i)
    e = us.snd[i]
    mi = us.material_of_sound(i)
    lines.append('line %s volume=%r category=%d bus=%d id=%d length=%r US=%s/young_us/%03d.wav JP=%s/young_jp/%03d.wav' % (
        sd['name'], sd['volume'], usab[e + 6], usab[e + 0x23], mi, sd['length'], HERE, mi, HERE, jp_material[sd['name']]))
open(os.path.join(HERE, 'bank1', 'spec.txt'), 'w').write('\n'.join(lines) + '\n')
print(len(lines) - 6, 'lines')
