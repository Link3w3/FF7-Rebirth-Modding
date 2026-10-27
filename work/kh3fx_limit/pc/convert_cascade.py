"""KH3 Cascade systems of one par folder -> End editor packages (kh3cascade.py) with every KH3 mesh / material
reference pointing at the converted content under /Game/KH3/Effects (only what is in the project).
    python3 convert_cascade.py <Effects folder> <par folder under Effects> <out folder>   -> out/<name>.uasset, report.json
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, 'tools')]
import kh3cascade   # noqa: E402

root, par, out = sys.argv[1], sys.argv[2], sys.argv[3]
CONTENT = os.path.expanduser('~/mnt/FF7R2UProj/Content/')
CLASS = {'StaticMesh': ('/Script/Engine', 'StaticMesh'), 'Material': ('/Script/Engine', 'Material'),
         'MaterialInstanceConstant': ('/Script/Engine', 'MaterialInstanceConstant')}
survey = json.load(open(os.path.join(HERE, 'survey.json')))
remap, missing = {}, []
for p, v in survey['items'].items():
    if v.get('cls') not in CLASS:
        continue
    end = '/Game/KH3/' + p[len('/Game/'):]
    pkg = end.split('.', 1)[0]
    if os.path.isfile(CONTENT + pkg[len('/Game/'):] + '.uasset'):
        remap[p] = CLASS[v['cls']] + (end,)
    else:
        missing.append(p)
os.makedirs(out, exist_ok=True)
report = {}
for src in sorted(glob.glob(os.path.join(root, *par.split('/'), '*.uasset'))):
    name = os.path.basename(src)[:-7]
    pkg = '/Game/KH3/Effects/%s/%s' % (par, name)
    c, data = kh3cascade.convert_file(src, os.path.join(out, name + '.uasset'), pkg, remap)
    report[name] = dict(size=len(data), notes=c.notes)
json.dump(dict(remap=len(remap), not_in_project=missing, systems=report), open(os.path.join(out, 'report.json'), 'w'), indent=1)
print('remap', len(remap), 'not in the project', len(missing), missing)
for n, r in report.items():
    left = [x for x in r['notes'] if not x.startswith('remapped')]
    print('%-22s %7d  remapped %2d  %s' % (n, r['size'], sum(1 for x in r['notes'] if x.startswith('remapped')), '; '.join(left)[:400]))
