"""His tail in an offline run: how far its tip and middle swing from side to side (Y, from the hips) and how high its tip is,
over the frames after the first second and a half.
    tail_metrics.py rig.json frames.bin [label]"""
import json, sys
import numpy as np
rig = json.load(open(sys.argv[1])); frames = sys.argv[2]; label = sys.argv[3] if len(sys.argv) > 3 else frames
index = {b['name']: i for i, b in enumerate(rig['bones'])}
raw = np.fromfile(frames, dtype=np.float32)
nb, nf = int(raw[:1].view(np.int32)[0]), int(raw[1:2].view(np.int32)[0])
F = raw[2:].reshape(nf, nb, 7).astype(np.float64)
T = F[int(nf / 7.0 * 1.5):, :, 4:]
hip = T[:, index['C_Hip_a']]
tip = T[:, index['Tail28']] - hip; mid = T[:, index['Tail14']] - hip
print('%-22s NaN %s | tail tip side %+6.1f .. %+6.1f cm (spread %5.1f), middle side %+5.1f .. %+5.1f, tip height %5.1f .. %5.1f cm' % (
    label, bool(np.isnan(F).any()), tip[:, 1].min(), tip[:, 1].max(), tip[:, 1].std() * 2, mid[:, 1].min(), mid[:, 1].max(),
    T[:, index['Tail28'], 2].min(), T[:, index['Tail28'], 2].max()))
