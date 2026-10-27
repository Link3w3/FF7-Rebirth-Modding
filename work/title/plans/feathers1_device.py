import os
reads = {"pakchunk20": [[1906268224, 10912], [1906303248, 10112], [1906340384, 10368], [1906350752, 10432], [1906361184, 10912], [1906372096, 10656], [1979830672, 13184], [2190532624, 11088], [2190543712, 10896], [2217368176, 11040], [2217659008, 10896], [2217731216, 11152], [2217742368, 11136], [2281228912, 10944], [2281239856, 10688], [2319744400, 10624]], "pakchunk18": [[1671860448, 14304], [1678101632, 10336], [1678130656, 14608]]}
base = os.path.expanduser("~/mnt/FINAL FANTASY VII REBIRTH/End/Content/Paks")
out = os.path.expanduser("~/mnt/FF7R2UProj/Saved/ModExtract/feathers1")
os.makedirs(out, exist_ok=True)
for chunk, ranges in reads.items():
    with open(os.path.join(base, chunk + "-WindowsNoEditor.ucas"), "rb") as f, open(os.path.join(out, chunk + ".blocks"), "wb") as o:
        n = 0
        for off, size in ranges:
            f.seek(off); d = f.read(size); assert len(d) == size, (chunk, off, size, len(d)); o.write(d); n += size
    print(chunk, len(ranges), n)
