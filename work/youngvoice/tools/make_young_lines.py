"""Young Sephiroth's lines (the medium setting: Praat's Change Gender, pitch +3 semitones, formants x1.09, loudness
matched, length kept) from every material of Sephiroth's US and JP voice banks.
  US: the user's AudioMog project WAVs (VO_PC0010_00_Sephiroth_###.wav, material order, exactly the materials' samples);
  JP: the JP bank's HCA streams decoded by ffmpeg, cut to the stream's own samples (its delay and padding off).
Writes young_us/###.wav and young_jp/###.wav (32 kHz mono, float)."""
import os, sys, struct, subprocess
import numpy as np
import soundfile as sf
sys.path[:0] = [os.path.dirname(os.path.abspath(__file__)), '/work/vinsnd1016/tools', '/work/vinvoice1016/tools']
import young
import sead, sead2
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def bank(lang):
    d = open(os.path.join(HERE, 'game', 'Sound__Voice__%s__Character__Player__VO_PC0010_00_Sephiroth.uasset' % lang), 'rb').read()
    _, sab = sead.sab_of(d)
    return sead2.Bank(sab[:struct.unpack_from('<I', sab, 0x0C)[0]])

def decode_hca(hca):
    r = subprocess.run(['ffmpeg', '-v', 'error', '-f', 'hca', '-i', '-', '-f', 'f32le', '-acodec', 'pcm_f32le', '-'], input=hca, capture_output=True)
    assert r.returncode == 0, r.stderr
    return np.frombuffer(r.stdout, dtype='<f4').astype(np.float64)

def main():
    report = []
    for lang in ('US', 'JP'):
        b = bank(lang)
        out = os.path.join(HERE, 'young_' + lang.lower())
        for i in range(len(b.mtrl)):
            m = b.material(i)
            info = sead.hca_header(m['extra'][16:])
            samples = info['blocks'] * 1024 - info['mute_head'] - info['mute_foot']
            if lang == 'US':
                x, sr = sf.read(os.path.join(HERE, 'src', 'VO_PC0010_00_Sephiroth_Project', 'VO_PC0010_00_Sephiroth_%03d.wav' % i), dtype='float64')
                assert sr == 32000 and len(x) == samples, (i, sr, len(x), samples)
            else:
                full = decode_hca(m['extra'][16:] + m['stream'])
                x = full[info['mute_head']:info['mute_head'] + samples]
                sr = 32000
            if np.abs(x).max() < 1e-6:
                y = np.zeros_like(x)
            else:
                y = young.young(x, sr, 'praat', 3.0, 1.09)
            sf.write(os.path.join(out, '%03d.wav' % i), y.astype(np.float32), sr, subtype='FLOAT')
            report.append('%s %03d %6d samples, peak %.3f -> %.3f' % (lang, i, len(x), np.abs(x).max(), np.abs(y).max()))
    open(os.path.join(HERE, 'young_lines.txt'), 'w').write('\n'.join(report) + '\n')
    print('\n'.join(report[:3] + ['...'] + report[-3:]))

main()
