import os
reads = {"pakchunk4": [[230219040, 7712], [230226752, 2064]], "pakchunk3": [[2786038960, 15728], [2786054688, 2800], [2786057488, 18624], [2786076112, 1168], [2786077280, 2816], [2786080096, 3504], [2786083600, 7392], [2786090992, 1120], [2798438480, 9920]]}
base = os.path.expanduser("~/mnt/FINAL FANTASY VII REBIRTH/End/Content/Paks")
out = os.path.expanduser("~/mnt/FF7R2UProj/Saved/ModExtract/talk")
os.makedirs(out, exist_ok=True)
for chunk, ranges in reads.items():
    with open(os.path.join(base, chunk + "-WindowsNoEditor.ucas"), "rb") as f, open(os.path.join(out, chunk + ".blocks"), "wb") as o:
        n = 0
        for off, size in ranges:
            f.seek(off); d = f.read(size); assert len(d) == size, (chunk, off, size, len(d)); o.write(d); n += size
    print(chunk, len(ranges), n)
