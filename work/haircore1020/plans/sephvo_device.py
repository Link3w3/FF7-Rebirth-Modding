import os
reads = {"pakchunk4": [[717986496, 3328], [717989824, 4352], [717994176, 48592], [718042768, 61152], [718103920, 61360], [718165280, 58176], [718223456, 56240], [718279696, 60960], [718340656, 58976], [718399632, 60720], [718460352, 37328], [721896400, 4528], [721900928, 47440], [721948368, 56864], [722005232, 57024], [722062256, 54656], [722116912, 52832], [722169744, 55472], [722225216, 55344], [722280560, 57408], [722337968, 34496]]}
base = os.path.expanduser("~/mnt/FINAL FANTASY VII REBIRTH/End/Content/Paks")
out = os.path.expanduser("~/mnt/FF7R2UProj/Saved/ModExtract/sephvo")
os.makedirs(out, exist_ok=True)
for chunk, ranges in reads.items():
    with open(os.path.join(base, chunk + "-WindowsNoEditor.ucas"), "rb") as f, open(os.path.join(out, chunk + ".blocks"), "wb") as o:
        n = 0
        for off, size in ranges:
            f.seek(off); d = f.read(size); assert len(d) == size, (chunk, off, size, len(d)); o.write(d); n += size
    print(chunk, len(ranges), n)
