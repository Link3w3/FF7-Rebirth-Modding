import json, sys, os
base = sys.argv[1]; ranges = json.load(open(sys.argv[2])); out = sys.argv[3]
with open(out, 'wb') as o:
    for cont, off, csz in ranges:
        with open(os.path.join(base, cont + '.ucas'), 'rb') as f:
            f.seek(off); raw = f.read((csz + 15) & ~15)[:csz]
            assert len(raw) == csz
            o.write(raw)
print('wrote', os.path.getsize(out))
