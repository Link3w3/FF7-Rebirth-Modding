"""Reads .cacanim files as the editor's ReadKeyAnimation does (the same checks) and writes them as anim_run clips
(samples format: each frame's local rotation and translation of the file's bones), for an offline look.
    read_cacanim.py out_samples.json file.cacanim ..."""
import json, struct, sys, os
import numpy as np


def read(path):
    data = open(path, 'rb').read()
    o = 0
    assert data[:8] == b'CACANIM1', 'no header'
    o = 8
    version, fps, frames, flags, ntracks = struct.unpack_from('<IfiIi', data, o); o += 20
    assert version == 1 and 2 <= frames <= 100000 and 0 < fps <= 1000 and 1 <= ntracks <= 8192, (version, fps, frames, ntracks)
    tracks = []
    for _ in range(ntracks):
        (nl,) = struct.unpack_from('<H', data, o); o += 2
        assert 0 < nl <= 512
        name = data[o:o + nl].decode('ascii'); o += nl
        (keys,) = struct.unpack_from('<i', data, o); o += 4
        assert keys == 1 or keys == frames, (name, keys)
        v = np.frombuffer(data, dtype='<f4', count=keys * 10, offset=o).reshape(keys, 10); o += keys * 40
        tracks.append((name, v))
    assert o == len(data), 'data after the last track'
    return fps, frames, flags, tracks


out = {}
for path in sys.argv[2:]:
    fps, frames, flags, tracks = read(path)
    names = [n for n, _ in tracks]
    poses = []
    for f in range(frames):
        row = []
        for n, v in tracks:
            k = v[0] if len(v) == 1 else v[f]
            row.append([float(x) for x in list(k[3:7]) + list(k[0:3])])
        poses.append(row)
    name = 'Example/' + os.path.splitext(os.path.basename(path))[0]
    out[name] = {'length': (frames - 1) / fps, 'frames': frames, 'skeleton': 'PC0010_17_Compat_Skeleton', 'bones': names, 'poses': poses}
    print(name, 'fps', fps, 'frames', frames, 'loop', flags & 1, 'tracks', len(tracks), 'keyed', sum(1 for _, v in tracks if len(v) > 1))
json.dump(out, open(sys.argv[1], 'w'))
