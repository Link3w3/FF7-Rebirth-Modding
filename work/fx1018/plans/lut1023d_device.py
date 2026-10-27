import os
reads = {"pakchunk0": [[98485664, 5376], [98491040, 7728], [98498768, 6608], [98505376, 3216], [98508592, 64], [98508656, 7312], [98515968, 11680], [98527648, 10336], [98537984, 4176], [98542160, 64], [98542224, 8832], [98551056, 11136], [98562192, 10000], [98572192, 6624], [98578816, 112]], "pakchunk8": [[1353963152, 14208], [1353977360, 15568], [1353992928, 14896], [1354007824, 10576], [1354018400, 176]]}
base = os.path.expanduser("~/mnt/FINAL FANTASY VII REBIRTH/End/Content/Paks")
out = os.path.expanduser("~/mnt/FF7R2UProj/Saved/ModExtract/lut1023d")
os.makedirs(out, exist_ok=True)
for chunk, ranges in reads.items():
    with open(os.path.join(base, chunk + "-WindowsNoEditor.ucas"), "rb") as f, open(os.path.join(out, chunk + ".blocks"), "wb") as o:
        n = 0
        for off, size in ranges:
            f.seek(off); d = f.read(size); assert len(d) == size, (chunk, off, size, len(d)); o.write(d); n += size
    print(chunk, len(ranges), n)
