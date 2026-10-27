import os
reads = {"pakchunk3": [[2785912208, 1712], [2785913920, 1264], [2785915184, 34784], [2785949968, 12304], [2785962272, 3712], [2785965984, 3664], [2785969648, 3536], [2785973184, 3584], [2785976768, 3696], [2785980464, 3488], [2785983952, 3728], [2785987680, 3568], [2785991248, 3424], [2785994672, 3520], [2785998192, 3984], [2786002176, 3440], [2786005616, 8912], [2786014528, 4528], [2786550592, 10176], [2786560768, 2208], [2786564096, 1616], [2786565712, 19152], [2786584864, 2656], [2786587520, 4448], [2788641312, 13648], [2788654960, 96], [2788688048, 21408], [2788709456, 6208], [2788715664, 3200], [2788718864, 2624], [2788721488, 2656], [2788724144, 5744], [2788729888, 3648], [2788733536, 2768], [2788736304, 2320], [2788738624, 5840], [2788744464, 144], [2796109584, 1088]]}
base = os.path.expanduser("~/mnt/FINAL FANTASY VII REBIRTH/End/Content/Paks")
out = os.path.expanduser("~/mnt/FF7R2UProj/Saved/ModExtract/shop1")
os.makedirs(out, exist_ok=True)
for chunk, ranges in reads.items():
    with open(os.path.join(base, chunk + "-WindowsNoEditor.ucas"), "rb") as f, open(os.path.join(out, chunk + ".blocks"), "wb") as o:
        n = 0
        for off, size in ranges:
            f.seek(off); d = f.read(size); assert len(d) == size, (chunk, off, size, len(d)); o.write(d); n += size
    print(chunk, len(ranges), n)
