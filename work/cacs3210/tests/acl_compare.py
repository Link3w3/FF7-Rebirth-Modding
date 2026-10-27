"""Compares AclDecode.hpp (acl_dump) with the Python decoder (acl13) on cooked AnimSequence packages."""
import glob, os, subprocess, sys
import numpy as np
sys.path[:0] = ['/work/acl']
import acl13
SCR = '/tmp/scratch/acl_cmp.bin'
worst = 0.0
n = 0
fails = []
for path in sys.argv[1:]:
    data = open(path, 'rb').read()
    try:
        c = acl13.Clip(data)
        rot, _, _ = c.decompress()
    except Exception as e:
        fails.append((os.path.basename(path), 'python: %s' % e))
        continue
    r = subprocess.run(['./acl_dump', path, SCR], capture_output=True, text=True)
    if r.returncode != 0:
        fails.append((os.path.basename(path), 'c++: ' + r.stdout.strip()))
        continue
    raw = np.fromfile(SCR, dtype=np.float32)
    t, s = raw[:2].view(np.int32)
    q = raw[3:].reshape(t, s, 4)
    py = np.transpose(rot, (1, 0, 2))
    d = np.abs(np.abs(np.sum(q * py, axis=2)) - 1.0).max()
    diff = np.abs(q - py).max()
    worst = max(worst, diff)
    n += 1
print('clips compared', n, 'largest component difference', worst)
print('failures', fails[:20], len(fails))
