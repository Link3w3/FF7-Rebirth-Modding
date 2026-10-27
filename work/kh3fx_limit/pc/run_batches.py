"""Imports every mesh or texture in batches through the editor link:
    python3 run_batches.py mesh|tex [batch size] [first key index] [key count]"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE]
import link   # noqa: E402

kind = sys.argv[1]
size = int(sys.argv[2]) if len(sys.argv) > 2 else 15
info = json.load(open(os.path.join(HERE, 'mesh_info.json' if kind == 'mesh' else 'tex_settings.json')))
keys = sorted(info)
first = int(sys.argv[3]) if len(sys.argv) > 3 else 0
keys = keys[first:first + int(sys.argv[4])] if len(sys.argv) > 4 else keys[first:]
template = open(os.path.join(HERE, 'import_batch.py')).read()
summary = {}
for i in range(0, len(keys), size):
    code = template.replace('__KIND__', repr(kind)).replace('__KEYS__', repr(keys[i:i + size]))
    s = link.run(code, 170)
    if not s.get('ok'):
        print('batch', i, 'failed:', str(s.get('error'))[-800:])
        break
    for k, v in (s.get('result') or {}).items():
        summary[v] = summary.get(v, 0) + 1
        if v not in ('ok', 'already there'):
            print('  ', k, v)
    print('batch %d-%d: %.1f s' % (i, i + size, s.get('seconds', 0)), flush=True)
    time.sleep(0.5)
print(kind, summary)
