import re, json, glob, subprocess, os
DXC = '/home/user/microsoft/dxc-build/bin/dxc'
ENV = dict(os.environ, LD_LIBRARY_PATH='/home/user/microsoft/dxc-build/lib')
maps = {}
res_names = {}
files = sorted(glob.glob('bp/PS_*.dxbc'))
for f in files:
    txt = subprocess.run([DXC, '-dumpbin', f], capture_output=True, text=True, env=ENV).stdout
    cur = None
    for line in txt.splitlines():
        m = re.match(r';\s*cbuffer (\w+)', line)
        if m:
            cur = m.group(1); maps.setdefault(cur, {}); continue
        m = re.match(r';\s+(?:row_major\s+)?(\w+)\s+(\w+)(\[\d+\])?;\s*; Offset:\s+(\d+)', line)
        if m and cur:
            typ, name, arr, off = m.group(1), m.group(2), m.group(3), int(m.group(4))
            maps[cur][off] = (typ + (arr or ''), name)
        m = re.match(r';\s+(\w+)\s+(texture|sampler|cbuffer|UAV)\s+(\w+)\s+(\w+)\s+(\w+)\s+(\w+)', line)
        if m:
            res_names.setdefault(m.group(1), m.group(2))
json.dump({k: {str(o): v for o, v in sorted(d.items())} for k, d in maps.items()}, open('cbuffer_layouts.json', 'w'), indent=0)
json.dump(res_names, open('resource_names.json', 'w'), indent=0)
for k, v in maps.items():
    print(k, len(v))
print(len(res_names), sorted(res_names)[:80])
