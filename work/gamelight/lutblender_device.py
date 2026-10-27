import json, os, struct
pak = os.path.expanduser('~/mnt/FINAL FANTASY VII REBIRTH/End/Content/Paks/pakchunk0-WindowsNoEditor.pak')
out = os.path.expanduser('~/mnt/FF7R2UProj/Saved/ModExtract/shlib/lutblender.bundle')
plan = json.loads('[[608211284, 2010, 3313, 7, 4349, "9eda55d0b6e173059d26109ac1f1b912b1969554"], [608213294, 2105, 3353, 5, 4350, "cfdd7d07a7fe5c2a2122811c47c0e734e3756cd1"]]')
f = open(pak, 'rb')
with open(out, 'wb') as o:
    for off, size, usize, freq, index, hsh in plan:
        f.seek(off); d = f.read(size); assert len(d) == size
        o.write(struct.pack('<IIIB', index, size, usize, freq)); o.write(bytes.fromhex(hsh)); o.write(d)
print(out, os.path.getsize(out), len(plan))
