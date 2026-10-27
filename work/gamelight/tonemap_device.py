import json, os, struct
pak = os.path.expanduser('~/mnt/FINAL FANTASY VII REBIRTH/End/Content/Paks/pakchunk0-WindowsNoEditor.pak')
out = os.path.expanduser('~/mnt/FF7R2UProj/Saved/ModExtract/shlib/tonemap.bundle')
plan = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tonemap_plan.json')))
f = open(pak, 'rb')
with open(out, 'wb') as o:
    for off, size, usize, freq, index, hsh in plan:
        f.seek(off); d = f.read(size); assert len(d) == size
        o.write(struct.pack('<IIIB', index, size, usize, freq)); o.write(bytes.fromhex(hsh)); o.write(d)
print(out, os.path.getsize(out), len(plan))
