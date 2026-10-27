import os
reads = {"pakchunk20": [[1293031312, 2000], [1293043984, 6304], [1293050288, 3872], [1293054160, 688], [1293054848, 20976], [1293075824, 6544], [1293082368, 3904], [1293086272, 4320], [1293090592, 6256], [1293096848, 2720], [1293203472, 3232], [1369773568, 1072], [1470207104, 3120], [1476125616, 3072], [1481263696, 3280], [1496666800, 3424], [1499668944, 3168], [1504194992, 3072]]}
base = os.path.expanduser("~/mnt/FINAL FANTASY VII REBIRTH/End/Content/Paks")
out = os.path.expanduser("~/mnt/FF7R2UProj/Saved/ModExtract/lastbgm1")
os.makedirs(out, exist_ok=True)
for chunk, ranges in reads.items():
    with open(os.path.join(base, chunk + "-WindowsNoEditor.ucas"), "rb") as f, open(os.path.join(out, chunk + ".blocks"), "wb") as o:
        n = 0
        for off, size in ranges:
            f.seek(off); d = f.read(size); assert len(d) == size, (chunk, off, size, len(d)); o.write(d); n += size
    print(chunk, len(ranges), n)
