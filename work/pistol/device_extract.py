import json, os
reads = {"pakchunk4":[[221879760,47536],[287708656,2880],[287711536,3920],[287715456,1120]],"pakchunk10":[[3683936,12192],[212353408,5584]],"pakchunk11":[[19079328,23344],[19102672,16832],[20192512,4960],[20197472,6640],[20204112,10608],[21263696,23616],[21287312,5376],[21292688,15136],[21676128,6720]]}
base = os.path.expanduser("~/mnt/FINAL FANTASY VII REBIRTH/End/Content/Paks")
out = os.path.expanduser("~/mnt/FF7R2UProj/Saved/ModExtract/pistol")
os.makedirs(out, exist_ok=True)
for chunk, ranges in reads.items():
    with open(os.path.join(base, chunk + "-WindowsNoEditor.ucas"), "rb") as f, open(os.path.join(out, chunk + ".blocks"), "wb") as o:
        n = 0
        for off, size in ranges:
            f.seek(off); d = f.read(size); assert len(d) == size; o.write(d); n += size
    print(chunk, len(ranges), n)
