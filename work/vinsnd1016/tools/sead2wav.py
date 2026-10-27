import sys, os, struct, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sead
def dump(path, outdir, only=None):
    d = open(path, 'rb').read()
    names = sead.sound_names(d)
    base = os.path.basename(path).split('__')[-1].replace('.uasset', '')
    outs = []
    for m in sead.materials(d):
        if m['codec'] != 7 or m['hca_at'] < 0:
            continue
        if only is not None and m['index'] not in only:
            continue
        doff = m['hca']['data_offset']
        hdr = d[m['hca_at']:m['hca_at'] + doff]
        stream = d[m['stream_at']:m['stream_at'] + m['stream_size']]
        hca = os.path.join(outdir, f"{base}_m{m['index']:03d}.hca")
        open(hca, 'wb').write(hdr + stream)
        wav = hca[:-4] + '.wav'
        r = subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', hca, wav], capture_output=True, text=True)
        outs.append((m['index'], wav, r.returncode, r.stderr.strip()[:200]))
    return outs
if __name__ == '__main__':
    outdir = sys.argv[1]
    for p in sys.argv[2:]:
        for o in dump(p, outdir): print(o)
