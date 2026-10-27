import os
reads = {"pakchunk28": [[762879120, 63776], [762942896, 65536], [763008432, 65536], [763073968, 65232], [1798301792, 63920], [1798365712, 65536], [1798431248, 65536], [1798496784, 65536], [1845862560, 61792], [1845924352, 65536], [1845989888, 65536], [1846055424, 65536], [1895758016, 46160], [1895804176, 65536], [1895869712, 65536], [1895935248, 65536], [2747158832, 62608], [2747221440, 65536], [2747286976, 65536], [2747352512, 65536]]}
base = os.path.expanduser("~/mnt/FINAL FANTASY VII REBIRTH/End/Content/Paks")
out = os.path.expanduser("~/mnt/FF7R2UProj/Saved/ModExtract/bgmhead1")
os.makedirs(out, exist_ok=True)
for chunk, ranges in reads.items():
    with open(os.path.join(base, chunk + "-WindowsNoEditor.ucas"), "rb") as f, open(os.path.join(out, chunk + ".blocks"), "wb") as o:
        n = 0
        for off, size in ranges:
            f.seek(off); d = f.read(size); assert len(d) == size, (chunk, off, size, len(d)); o.write(d); n += size
    print(chunk, len(ranges), n)
