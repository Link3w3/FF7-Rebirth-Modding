import os
reads = {"pakchunk16": [[700361808, 43040], [707237872, 18928], [728172352, 34272], [738037168, 10544], [763741984, 60704], [763802688, 25552], [1965500624, 63728], [1965564352, 10384], [2038592064, 33696], [2069796848, 48816], [2133708192, 23520], [2300702368, 31520], [2401917632, 62816], [2401980448, 63056], [2586692864, 38880], [2725582608, 61008], [2725643616, 672], [2995209472, 25120]]}
base = os.path.expanduser("~/mnt/FINAL FANTASY VII REBIRTH/End/Content/Paks")
out = os.path.expanduser("~/mnt/FF7R2UProj/Saved/ModExtract/cutsample")
os.makedirs(out, exist_ok=True)
for chunk, ranges in reads.items():
    with open(os.path.join(base, chunk + "-WindowsNoEditor.ucas"), "rb") as f, open(os.path.join(out, chunk + ".blocks"), "wb") as o:
        n = 0
        for off, size in ranges:
            f.seek(off); d = f.read(size); assert len(d) == size, (chunk, off, size, len(d)); o.write(d); n += size
    print(chunk, len(ranges), n)
