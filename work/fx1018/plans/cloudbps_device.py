import os
reads = {"pakchunk4": [[230228816, 4048], [324690320, 1664], [325855968, 1808], [325952240, 2224], [327051792, 1680], [327166416, 1776]], "pakchunk10": [[663012688, 1664], [664072656, 1680], [665115472, 1680], [666222272, 1664], [667558480, 1680], [668873136, 1744], [669674160, 2176], [669739824, 2176], [669763472, 1712], [670865168, 1632], [671996912, 1680], [672077120, 1856], [672162864, 1680], [672199504, 1696], [672221296, 1696], [672469248, 2160], [719836912, 2208], [721501552, 1568]]}
base = os.path.expanduser("~/mnt/FINAL FANTASY VII REBIRTH/End/Content/Paks")
out = os.path.expanduser("~/mnt/FF7R2UProj/Saved/ModExtract/cloudbps")
os.makedirs(out, exist_ok=True)
for chunk, ranges in reads.items():
    with open(os.path.join(base, chunk + "-WindowsNoEditor.ucas"), "rb") as f, open(os.path.join(out, chunk + ".blocks"), "wb") as o:
        n = 0
        for off, size in ranges:
            f.seek(off); d = f.read(size); assert len(d) == size, (chunk, off, size, len(d)); o.write(d); n += size
    print(chunk, len(ranges), n)
