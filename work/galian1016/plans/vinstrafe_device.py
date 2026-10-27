import os
reads = {"pakchunk4": [[223138768, 5520], [223336560, 9376], [725361072, 7888], [725368960, 6944], [725375904, 5056], [725380960, 8048], [725389008, 2032], [725391040, 11296], [725402336, 6352], [725408688, 7264], [725415952, 5984], [725421936, 2032], [725423968, 7504], [725431472, 6960], [725438432, 7280], [725445712, 7920], [725453632, 6976], [725460608, 8032], [725468640, 7072], [725475712, 8144], [725483856, 2784], [725486640, 5344], [725491984, 4544], [725496528, 7408], [725503936, 5200], [725509136, 2048], [725605808, 4464]]}
base = os.path.expanduser("~/mnt/FINAL FANTASY VII REBIRTH/End/Content/Paks")
out = os.path.expanduser("~/mnt/FF7R2UProj/Saved/ModExtract/vinstrafe")
os.makedirs(out, exist_ok=True)
for chunk, ranges in reads.items():
    with open(os.path.join(base, chunk + "-WindowsNoEditor.ucas"), "rb") as f, open(os.path.join(out, chunk + ".blocks"), "wb") as o:
        n = 0
        for off, size in ranges:
            f.seek(off); d = f.read(size); assert len(d) == size, (chunk, off, size, len(d)); o.write(d); n += size
    print(chunk, len(ranges), n)
