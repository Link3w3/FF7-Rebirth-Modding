set -e
O="$HOME/mnt/FF7R2UProj/Saved/ModExtract/lvl1027"
mkdir -p "$O"
P="$HOME/mnt/FINAL FANTASY VII REBIRTH/End/Content/Paks"
python3 - "$P/pakchunk7-WindowsNoEditor.ucas" "$O" 7 <<'PY'
import sys,json
src,out,k=sys.argv[1],sys.argv[2],sys.argv[3]
rs=json.loads('[[13275520, 13984]]')
f=open(src,"rb")
for o,s in rs:
    f.seek(o); open("%s/r%s_%d.bin"%(out,k,o),"wb").write(f.read(s))
print(k,len(rs))
PY
python3 - "$P/pakchunk8-WindowsNoEditor.ucas" "$O" 8 <<'PY'
import sys,json
src,out,k=sys.argv[1],sys.argv[2],sys.argv[3]
rs=json.loads('[[1807970816, 49104], [2151603296, 321920], [2310011360, 193808], [2477966112, 245760], [2504625344, 335360], [2765183456, 35440]]')
f=open(src,"rb")
for o,s in rs:
    f.seek(o); open("%s/r%s_%d.bin"%(out,k,o),"wb").write(f.read(s))
print(k,len(rs))
PY
python3 - "$P/pakchunk9-WindowsNoEditor.ucas" "$O" 9 <<'PY'
import sys,json
src,out,k=sys.argv[1],sys.argv[2],sys.argv[3]
rs=json.loads('[[211499280, 252016]]')
f=open(src,"rb")
for o,s in rs:
    f.seek(o); open("%s/r%s_%d.bin"%(out,k,o),"wb").write(f.read(s))
print(k,len(rs))
PY
python3 - "$P/pakchunk11-WindowsNoEditor.ucas" "$O" 11 <<'PY'
import sys,json
src,out,k=sys.argv[1],sys.argv[2],sys.argv[3]
rs=json.loads('[[95511472, 12880]]')
f=open(src,"rb")
for o,s in rs:
    f.seek(o); open("%s/r%s_%d.bin"%(out,k,o),"wb").write(f.read(s))
print(k,len(rs))
PY
python3 - "$P/pakchunk12-WindowsNoEditor.ucas" "$O" 12 <<'PY'
import sys,json
src,out,k=sys.argv[1],sys.argv[2],sys.argv[3]
rs=json.loads('[[687785408, 148560], [797113872, 306416], [900262256, 138144], [1062178208, 77200], [1066394560, 64976], [1132341776, 150976], [1505402960, 16656]]')
f=open(src,"rb")
for o,s in rs:
    f.seek(o); open("%s/r%s_%d.bin"%(out,k,o),"wb").write(f.read(s))
print(k,len(rs))
PY
python3 - "$P/pakchunk13-WindowsNoEditor.ucas" "$O" 13 <<'PY'
import sys,json
src,out,k=sys.argv[1],sys.argv[2],sys.argv[3]
rs=json.loads('[[895965200, 297600], [1183483056, 302928], [1322948688, 1744], [1322967856, 348128], [1582824752, 31248], [1582874224, 1104], [1582881648, 1104], [1582889056, 1104], [1582896480, 1104], [1582903904, 1104], [1582911328, 1104], [1582918736, 1104], [1582926160, 1104], [1582951008, 32976]]')
f=open(src,"rb")
for o,s in rs:
    f.seek(o); open("%s/r%s_%d.bin"%(out,k,o),"wb").write(f.read(s))
print(k,len(rs))
PY
python3 - "$P/pakchunk14-WindowsNoEditor.ucas" "$O" 14 <<'PY'
import sys,json
src,out,k=sys.argv[1],sys.argv[2],sys.argv[3]
rs=json.loads('[[248811600, 495248], [452896592, 11344]]')
f=open(src,"rb")
for o,s in rs:
    f.seek(o); open("%s/r%s_%d.bin"%(out,k,o),"wb").write(f.read(s))
print(k,len(rs))
PY
python3 - "$P/pakchunk15-WindowsNoEditor.ucas" "$O" 15 <<'PY'
import sys,json
src,out,k=sys.argv[1],sys.argv[2],sys.argv[3]
rs=json.loads('[[1430815552, 222320], [1431206304, 676000], [1545025456, 40944], [1545112832, 289264], [1994451248, 1744], [1994484144, 4192], [1994552272, 245312], [2144095152, 198816], [2173200416, 26080], [2173804464, 548144], [2382059184, 20464]]')
f=open(src,"rb")
for o,s in rs:
    f.seek(o); open("%s/r%s_%d.bin"%(out,k,o),"wb").write(f.read(s))
print(k,len(rs))
PY
python3 - "$P/pakchunk16-WindowsNoEditor.ucas" "$O" 16 <<'PY'
import sys,json
src,out,k=sys.argv[1],sys.argv[2],sys.argv[3]
rs=json.loads('[[1620712768, 707424], [1824238928, 416], [1873613216, 1936], [1878652624, 7728], [1924976592, 252112], [1960294240, 23264], [1962731008, 45824]]')
f=open(src,"rb")
for o,s in rs:
    f.seek(o); open("%s/r%s_%d.bin"%(out,k,o),"wb").write(f.read(s))
print(k,len(rs))
PY
python3 - "$P/pakchunk17-WindowsNoEditor.ucas" "$O" 17 <<'PY'
import sys,json
src,out,k=sys.argv[1],sys.argv[2],sys.argv[3]
rs=json.loads('[[553994112, 440848], [993896736, 171840], [1059556704, 163600], [1169411184, 63456], [1238923552, 14576]]')
f=open(src,"rb")
for o,s in rs:
    f.seek(o); open("%s/r%s_%d.bin"%(out,k,o),"wb").write(f.read(s))
print(k,len(rs))
PY
python3 - "$P/pakchunk18-WindowsNoEditor.ucas" "$O" 18 <<'PY'
import sys,json
src,out,k=sys.argv[1],sys.argv[2],sys.argv[3]
rs=json.loads('[[646664032, 594384], [1254082576, 2992], [1254185360, 154176], [1455669440, 46784], [1508212320, 15248]]')
f=open(src,"rb")
for o,s in rs:
    f.seek(o); open("%s/r%s_%d.bin"%(out,k,o),"wb").write(f.read(s))
print(k,len(rs))
PY
python3 - "$P/pakchunk20-WindowsNoEditor.ucas" "$O" 20 <<'PY'
import sys,json
src,out,k=sys.argv[1],sys.argv[2],sys.argv[3]
rs=json.loads('[[768328112, 102608], [828003440, 653872], [1292931888, 48720], [1293031312, 245088], [1522874400, 1744], [1522895488, 1744], [1529993104, 45472]]')
f=open(src,"rb")
for o,s in rs:
    f.seek(o); open("%s/r%s_%d.bin"%(out,k,o),"wb").write(f.read(s))
print(k,len(rs))
PY
python3 - "$P/pakchunk22-WindowsNoEditor.ucas" "$O" 22 <<'PY'
import sys,json
src,out,k=sys.argv[1],sys.argv[2],sys.argv[3]
rs=json.loads('[[12706000, 170928]]')
f=open(src,"rb")
for o,s in rs:
    f.seek(o); open("%s/r%s_%d.bin"%(out,k,o),"wb").write(f.read(s))
print(k,len(rs))
PY
cd "$O" && ls | wc -l && du -sh . && md5sum r*.bin > ../lvl1027.md5 && wc -l ../lvl1027.md5
