import json, os, sys
reads = {"pakchunk8-WindowsNoEditor.ucas": [[2478131360, 18432], [2478161824, 9632], [2504853072, 10480], [2504866016, 2944], [2504887952, 4992]], "pakchunk10-WindowsNoEditor.ucas": [[715834880, 4528]], "pakchunk12-WindowsNoEditor.ucas": [[1066423376, 12032], [1066444160, 5024], [1132435952, 11600], [1132458000, 4224]], "pakchunk13-WindowsNoEditor.ucas": [[1183701648, 7280], [1183710544, 2816], [1183727472, 3552]], "pakchunk14-WindowsNoEditor.ucas": [[249171808, 20416], [249208880, 4992]], "pakchunk15-WindowsNoEditor.ucas": [[1431708656, 9968], [1431751120, 4288], [1545359744, 9536], [1545372928, 3312], [1994715728, 19232], [1994742928, 6432], [2174197392, 26656], [2174253552, 7312]], "pakchunk16-WindowsNoEditor.ucas": [[1621197776, 20944], [1621265680, 11120]], "pakchunk17-WindowsNoEditor.ucas": [[554370224, 2384], [1059656528, 17408], [1059681968, 6608]], "pakchunk18-WindowsNoEditor.ucas": [[1254290384, 12000], [1254309456, 3664]]}
src = os.path.expanduser("~/mnt/FINAL FANTASY VII REBIRTH/End/Content/Paks")
dst = os.path.expanduser("~/mnt/FF7R2UProj/_mod_extract/b01abil")
total = 0
for ucas, ranges in reads.items():
    d = os.path.join(dst, ucas.split("-")[0])
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(src, ucas), "rb") as f:
        for off, size in ranges:
            f.seek(off)
            b = f.read(size)
            assert len(b) == size, (ucas, off, size, len(b))
            open(os.path.join(d, "r_%d.bin" % off), "wb").write(b)
            total += size
print("read", total, "bytes")
