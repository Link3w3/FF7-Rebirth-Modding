import os
reads = {"pakchunk4": [[241369712, 5200], [247546160, 19808], [247565968, 13216], [247579184, 14928], [247594112, 18192], [247612304, 4928], [247617232, 624], [247617856, 17888], [247635744, 10656], [247646400, 10192], [247656592, 18672], [247675264, 10560]], "pakchunk3": [[591680, 9472], [601152, 4032]]}
base = os.path.expanduser("~/mnt/FINAL FANTASY VII REBIRTH/End/Content/Paks")
out = os.path.expanduser("~/mnt/FF7R2UProj/Saved/ModExtract/cross1")
os.makedirs(out, exist_ok=True)
for chunk, ranges in reads.items():
    with open(os.path.join(base, chunk + "-WindowsNoEditor.ucas"), "rb") as f, open(os.path.join(out, chunk + ".blocks"), "wb") as o:
        n = 0
        for off, size in ranges:
            f.seek(off); d = f.read(size); assert len(d) == size, (chunk, off, size, len(d)); o.write(d); n += size
    print(chunk, len(ranges), n)
