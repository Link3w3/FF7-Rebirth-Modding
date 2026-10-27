"""python3 run_build.py FIRST COUNT [batch]: builds specs FIRST..FIRST+COUNT-1 through the editor link, in batches."""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE]
import link   # noqa: E402

first, count = int(sys.argv[1]), int(sys.argv[2])
batch = int(sys.argv[3]) if len(sys.argv) > 3 else 6
template = open(os.path.join(HERE, 'build_materials.py')).read()
for start in range(first, first + count, batch):
    n = min(batch, first + count - start)
    s = link.run(template.replace('__FIRST__', str(start)).replace('__COUNT__', str(n)), 170)
    if not s.get('ok'):
        print('batch', start, 'failed:', str(s.get('error'))[-1200:])
        break
    for k, v in (s.get('result') or {}).items():
        print('%-26s %s' % (k, v))
    print('-- %d..%d %.1f s' % (start, start + n - 1, s.get('seconds', 0)), flush=True)
    time.sleep(0.5)
