"""Reads the raw-key dumps of Sora's KH2 move animations (dump_kh2_raw.py in the editor): per track position (N,3),
rotation (N,4 xyzw), scale (N,3), each N = 1 (constant) or the frame count."""
import json, os, struct
import numpy as np

RAW = '/work/sorakh2/raw'


class Anim:
    def __init__(self, name, raw=RAW):
        self.index = json.load(open(os.path.join(raw, name + '.json')))
        blob = open(os.path.join(raw, name + '.bin'), 'rb').read()
        self.name = name
        self.frames = self.index['frames']
        self.length = self.index['length']
        self.tracks = {}
        p = 0
        for t, npos, nrot, nscl in self.index['tracks']:
            pos = np.frombuffer(blob, '<f4', npos * 3, p).reshape(npos, 3).astype(np.float64); p += npos * 12
            rot = np.frombuffer(blob, '<f4', nrot * 4, p).reshape(nrot, 4).astype(np.float64); p += nrot * 16
            scl = np.frombuffer(blob, '<f4', nscl * 3, p).reshape(nscl, 3).astype(np.float64) if nscl else None; p += nscl * 12
            self.tracks[t] = (pos, rot, scl)
        assert p == len(blob), (name, p, len(blob))

    def local(self, track, frame):
        pos, rot, scl = self.tracks[track]
        f = min(frame, len(pos) - 1) if len(pos) > 1 else 0
        g = min(frame, len(rot) - 1) if len(rot) > 1 else 0
        return rot[g], pos[f]
