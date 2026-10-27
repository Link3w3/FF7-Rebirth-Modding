import sys, struct
import numpy as np
sys.path[:0] = ['/work/iostore', '/work/cs']
from iostore import Toc
from zen import Zen
t = Toc(sys.argv[1]); want = sys.argv[2]
for i in range(t.entries):
    if t.chunk_type(i) != 2 or not t.files.get(i, '').endswith('/' + want + '.uasset'): continue
    z = Zen(t.read(i))
    k = [n for n, e in enumerate(z.exports) if e['name'] == want][0]
    data = z.export_bytes(k)
    found = 0
    for p in range(0, len(data) - 16):
        a, n, b, m = struct.unpack_from('<iiii', data, p)
        if a == 12 and b == 12 and n == m and 100 < n < 2000000 and p + 16 + n * 12 <= len(data):
            v = np.frombuffer(data, '<f4', n * 3, p + 16).reshape(-1, 3)
            print('positions at', p, 'n', n, 'min', v.min(0).round(1), 'max', v.max(0).round(1))
            found += 1
            if found >= 3: break
            if found == 1:
                body = v[(np.abs(v[:, 1]) < 40) & (np.abs(v[:, 0]) < 40)]
                print('  body-ish verts', len(body), 'z percentiles 1/50/99/100:', np.percentile(body[:, 2], [1, 50, 99, 100]).round(1))
                print('  x range', np.percentile(body[:, 0], [1, 99]).round(1), 'y range', np.percentile(body[:, 1], [1, 99]).round(1))
