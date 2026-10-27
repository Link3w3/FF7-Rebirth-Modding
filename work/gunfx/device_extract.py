import json, os
reads = {"pakchunk12": [[84577328, 34528], [84611856, 31440], [84643296, 29888], [84784480, 12160], [84796640, 4992], [84801632, 10112], [84859024, 31680], [84890704, 18784], [84909488, 28976], [85139344, 8864], [85148208, 7456], [85155664, 13024], [85247680, 55312], [85302992, 5856]]}
base = os.path.expanduser("~/mnt/FINAL FANTASY VII REBIRTH/End/Content/Paks")
out = os.path.expanduser("~/mnt/FF7R2UProj/Saved/ModExtract/gunfx")
os.makedirs(out, exist_ok=True)
for chunk, ranges in reads.items():
    with open(os.path.join(base, chunk + "-WindowsNoEditor.ucas"), "rb") as f, open(os.path.join(out, chunk + ".blocks"), "wb") as o:
        n = 0
        for off, size in ranges:
            f.seek(off); d = f.read(size); assert len(d) == size, (chunk, off, size, len(d)); o.write(d); n += size
    print(chunk, len(ranges), n)
