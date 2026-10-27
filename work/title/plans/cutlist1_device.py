import os
reads = {"pakchunk20": [[1529996672, 18576], [1530015248, 2848], [1530018096, 6720], [1530024816, 2368]], "pakchunk8": [[2765186960, 15824], [2765202784, 2144], [2765204928, 6048]], "pakchunk1": [[38962944, 12672], [38975616, 12640], [38988256, 13728], [39001984, 1680], [39003664, 14816], [39018480, 15264], [39033744, 15440], [39049184, 16512], [39065696, 17856], [39083552, 5248]]}
base = os.path.expanduser("~/mnt/FINAL FANTASY VII REBIRTH/End/Content/Paks")
out = os.path.expanduser("~/mnt/FF7R2UProj/Saved/ModExtract/cutlist1")
os.makedirs(out, exist_ok=True)
for chunk, ranges in reads.items():
    with open(os.path.join(base, chunk + "-WindowsNoEditor.ucas"), "rb") as f, open(os.path.join(out, chunk + ".blocks"), "wb") as o:
        n = 0
        for off, size in ranges:
            f.seek(off); d = f.read(size); assert len(d) == size, (chunk, off, size, len(d)); o.write(d); n += size
    print(chunk, len(ranges), n)
