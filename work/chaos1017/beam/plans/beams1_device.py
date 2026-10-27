import os
reads = {"pakchunk4": [[248842912, 20160], [248863072, 19600], [248882672, 3904], [352546800, 19760], [352566560, 17376], [352583936, 19408], [352603344, 3360], [353181648, 22432], [353204080, 6000], [353366816, 20592], [353387408, 15616], [353403024, 21088], [353424112, 4752], [459590704, 20256], [459610960, 14992], [459625952, 12896], [459638848, 3728], [460396592, 22912], [460419504, 16128], [460435632, 3200], [676974848, 14704], [676989552, 11616], [677001168, 17184], [677018352, 18960], [677037312, 16672], [677053984, 25504], [677079488, 4096], [677083584, 4736], [677088320, 768]], "pakchunk20": [[122362304, 18512], [122380816, 17760], [122398576, 7120], [122405696, 4032]], "pakchunk10": [[229238464, 17728], [229256192, 15216], [229271408, 5408]]}
base = os.path.expanduser("~/mnt/FINAL FANTASY VII REBIRTH/End/Content/Paks")
out = os.path.expanduser("~/mnt/FF7R2UProj/Saved/ModExtract/beams1")
os.makedirs(out, exist_ok=True)
for chunk, ranges in reads.items():
    with open(os.path.join(base, chunk + "-WindowsNoEditor.ucas"), "rb") as f, open(os.path.join(out, chunk + ".blocks"), "wb") as o:
        n = 0
        for off, size in ranges:
            f.seek(off); d = f.read(size); assert len(d) == size, (chunk, off, size, len(d)); o.write(d); n += size
    print(chunk, len(ranges), n)
