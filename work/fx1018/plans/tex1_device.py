import os
reads = {"pakchunk3optional": [[3944752, 2208], [3959648, 704], [3980800, 1648], [3982448, 1664], [3985152, 1024], [3987552, 2656], [3990208, 2208], [3997408, 1680], [4001920, 2880], [4004800, 2160], [4023472, 2480], [4139136, 1488], [4292800, 2064], [4304784, 1648], [4316288, 1728]], "pakchunk4optional": [[4117200, 1680], [4118880, 880], [4119760, 2016]], "pakchunk3": [[650944, 6384], [657328, 4192], [734416, 6592], [741008, 4592], [818624, 6880], [825504, 4624], [865104, 6480], [871584, 4192], [1358976, 6720], [1365696, 4576], [9887056, 7056], [9894112, 4608], [11719104, 6816], [11725920, 4304]]}
base = os.path.expanduser("~/mnt/FINAL FANTASY VII REBIRTH/End/Content/Paks")
out = os.path.expanduser("~/mnt/FF7R2UProj/Saved/ModExtract/tex1")
os.makedirs(out, exist_ok=True)
for chunk, ranges in reads.items():
    with open(os.path.join(base, chunk + "-WindowsNoEditor.ucas"), "rb") as f, open(os.path.join(out, chunk + ".blocks"), "wb") as o:
        n = 0
        for off, size in ranges:
            f.seek(off); d = f.read(size); assert len(d) == size, (chunk, off, size, len(d)); o.write(d); n += size
    print(chunk, len(ranges), n)
