import os
reads = {"pakchunk10": [[720710496, 1520], [720712016, 1488], [720713504, 1488], [720714992, 1536], [720716528, 1520], [720718048, 1552], [720719600, 1680], [720721280, 1536], [720722816, 1632], [720724448, 1536], [720725984, 1648], [720727632, 1488], [720729120, 1536], [720730656, 1584], [720732240, 1600], [720733840, 1504], [720735344, 1504], [720736848, 1504], [720738352, 1488], [720739840, 1520], [720741360, 1296], [720742656, 1584], [720744240, 1568], [720745808, 1616], [720747424, 1680], [720749104, 1568]]}
base = os.path.expanduser("~/mnt/FINAL FANTASY VII REBIRTH/End/Content/Paks")
out = os.path.expanduser("~/mnt/FF7R2UProj/Saved/ModExtract/face2")
os.makedirs(out, exist_ok=True)
for chunk, ranges in reads.items():
    with open(os.path.join(base, chunk + "-WindowsNoEditor.ucas"), "rb") as f, open(os.path.join(out, chunk + ".blocks"), "wb") as o:
        n = 0
        for off, size in ranges:
            f.seek(off); d = f.read(size); assert len(d) == size, (chunk, off, size, len(d)); o.write(d); n += size
    print(chunk, len(ranges), n)
