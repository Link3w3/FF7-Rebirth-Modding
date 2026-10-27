"""Material_Texture2D_k -> texture parameter name, per RMI (the uniform expression set of its shader map)."""
import sys, json, glob
sys.path[:0] = ['/work/custmat', '/work/iostore', '/work/cs', '/work/fx1018/editor/Python']
import carriers
out = {}
for path in sorted(glob.glob('/work/rmsurf/rmi/p*/pkgs/Renderer__MaterialInstance__Surface__*.uasset')):
    name = path.rsplit('__', 1)[1][:-7]
    try:
        c = carriers.Carrier(path)
        out[name] = [(k, n, tex) for k, n, tex in carriers.texture_parameters(c)]
    except Exception as e:
        out[name] = 'error: %s' % e
json.dump(out, open('texmap.json', 'w'), indent=1)
print(len(out), sum(1 for v in out.values() if isinstance(v, str)), 'errors')
print(json.dumps(out.get('RMI_Surface_Standard')))
print(json.dumps(out.get('RMI_Surface_Hair_Wide')))
