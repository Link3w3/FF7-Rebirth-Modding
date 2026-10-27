import json, os, sys
def tree(path):
    out = []
    for name in sorted(os.listdir(path)):
        full = os.path.join(path, name)
        if os.path.isdir(full):
            out.append({'name': name, 'type': 'directory', 'contents': tree(full)})
        elif os.path.isfile(full):
            out.append({'name': name, 'type': 'file', 'external-contents': full})
    return out
roots = sys.argv[2:]
doc = {'version': 0, 'case-sensitive': 'false', 'roots': [{'name': r, 'type': 'directory', 'contents': tree(r)} for r in roots]}
json.dump(doc, open(sys.argv[1], 'w'))
