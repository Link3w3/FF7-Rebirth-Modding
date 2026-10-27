import os
reads = {"pakchunk1": [[38388272, 17696], [38405968, 17696], [38423664, 18128], [38441792, 13952], [38455744, 13648], [38469392, 14144], [38483536, 13008], [38496544, 18192], [38514736, 16320], [38531056, 17312], [38548368, 18384], [38566752, 17872], [38584624, 15264], [38599888, 11840], [38611728, 14032], [38625760, 10384], [38636144, 17952], [38654096, 18496], [38672592, 17984], [38690576, 14560], [38705136, 10272], [38715408, 19312], [38734720, 15520], [38750240, 16272], [38766512, 15792], [38782304, 5440], [38787744, 8704], [38796448, 11200], [38807648, 14368], [38822016, 12736], [38834752, 15504], [38850256, 14736], [38864992, 16784], [38881776, 17904], [38899680, 20192], [38919872, 17888]], "pakchunk4": [[816694080, 22128], [816716208, 14928], [816731136, 64], [819714000, 17136]]}
base = os.path.expanduser("~/mnt/FINAL FANTASY VII REBIRTH/End/Content/Paks")
out = os.path.expanduser("~/mnt/FF7R2UProj/Saved/ModExtract/title2")
os.makedirs(out, exist_ok=True)
for chunk, ranges in reads.items():
    with open(os.path.join(base, chunk + "-WindowsNoEditor.ucas"), "rb") as f, open(os.path.join(out, chunk + ".blocks"), "wb") as o:
        n = 0
        for off, size in ranges:
            f.seek(off); d = f.read(size); assert len(d) == size, (chunk, off, size, len(d)); o.write(d); n += size
    print(chunk, len(ranges), n)
