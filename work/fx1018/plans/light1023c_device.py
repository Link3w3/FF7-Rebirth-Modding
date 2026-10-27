import os
reads = {"pakchunk8": [[1402795184, 11856], [1402807040, 19024], [1651090784, 52224], [1651143008, 51520], [1651194528, 50448], [1651244976, 51456], [1651296432, 56560], [1651352992, 36896], [1651389888, 45440], [1651435328, 38496], [1651473824, 4272], [1651478096, 29056], [1651507152, 62464], [1651569616, 60720], [1651630336, 62816], [1651693152, 60512], [1651753664, 61072], [1651814736, 58160], [1651872896, 56624], [1651929520, 38896], [1651968416, 5168], [1651973584, 38784], [1652012368, 57440], [1652069808, 9808], [1652079616, 11280], [1652090896, 30096], [1652120992, 52768], [1652173760, 45952], [1652219712, 61888], [1652281600, 48624], [1652330224, 54768], [1652384992, 51872], [1652436864, 50192], [1652487056, 25024]]}
base = os.path.expanduser("~/mnt/FINAL FANTASY VII REBIRTH/End/Content/Paks")
out = os.path.expanduser("~/mnt/FF7R2UProj/Saved/ModExtract/light1023c")
os.makedirs(out, exist_ok=True)
for chunk, ranges in reads.items():
    with open(os.path.join(base, chunk + "-WindowsNoEditor.ucas"), "rb") as f, open(os.path.join(out, chunk + ".blocks"), "wb") as o:
        n = 0
        for off, size in ranges:
            f.seek(off); d = f.read(size); assert len(d) == size, (chunk, off, size, len(d)); o.write(d); n += size
    print(chunk, len(ranges), n)
